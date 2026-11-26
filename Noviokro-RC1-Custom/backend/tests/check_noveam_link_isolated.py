"""Isolated integration contract checks; no framework/database/provider required."""
import ast
import asyncio
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / 'app'
spec = importlib.util.spec_from_file_location('catalog_contract', ROOT / 'catalog.py')
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)

class HTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code, self.detail = status_code, detail

class HTTPError(Exception):
    pass

class Response:
    def __init__(self, code, payload):
        self.status_code, self.payload = code, payload
        self.content = b'{}'
        self.is_success = 200 <= code < 300
    def raise_for_status(self):
        if not self.is_success:
            raise HTTPError()
    def json(self):
        return self.payload

class LinkingChecks(unittest.TestCase):
    def namespace(self, responses):
        calls = []
        class Client:
            def __init__(self, **kwargs):
                assert kwargs['follow_redirects'] is False
                assert kwargs['trust_env'] is False
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def get(self, url, **kwargs):
                calls.append((url, kwargs))
                return responses[url]
        class HTTP:
            AsyncClient = Client
            HTTPError = HTTPError
            RequestError = HTTPError
        def authorize(key):
            if key != 'synthetic-admin':
                raise HTTPException(401, 'Unauthorized')
        def save(body, title, version, endpoints):
            return {'endpoint_count': len(endpoints), 'endpoints': endpoints, 'spec_version': version}
        from urllib.parse import urlsplit
        import re
        ns = dict(os=os, urlsplit=urlsplit, HTTPException=HTTPException, httpx=HTTP,
                  Header=lambda *a, **kw: None, DiscoveryRequest=object,
                  require_admin=authorize, PROJECTS={'noveam', 'noveomediater'},
                  SERVICE_NAME=re.compile(r'^[a-z][a-z0-9_]{0,63}$'),
                  openapi_endpoints=catalog.openapi_endpoints, save_discovery=save,
                  CUSTOM_FORMAT='noviokro-api/1',
                  noveam_endpoints=lambda spec: spec['routes'])
        tree = ast.parse((ROOT / 'integrations.py').read_text(encoding='utf-8-sig'))
        names = {'operator_target', 'discover', 'service_health', 'noveam_professional_categories'}
        functions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
        for fn in functions:
            fn.decorator_list = []
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'integrations.py', 'exec'), ns)
        return ns, calls

    def test_openapi_metadata_and_query_names(self):
        endpoints = catalog.openapi_endpoints({'openapi': '3.1.0', 'paths': {
            '/api/search': {'parameters': [{'in':'query','name':'q'}], 'get': {'parameters': [{'in':'query','name':'q'}, {'in':'query','name':'limit'}], 'summary':'Search'}},
            '/private-ui': {'get': {}}, '/api/items': {'post': {}},
        }})
        self.assertEqual(len(endpoints), 2)
        self.assertEqual(endpoints[0]['query'], ['q', 'limit'])
        self.assertEqual(endpoints[1]['method'], 'POST')

    def test_invalid_openapi_and_bounded_catalog(self):
        for value in [None, [], {'openapi':'2.0', 'paths':{}}, {'openapi':'3.1.0', 'paths':[]}]:
            with self.assertRaises(ValueError):
                catalog.openapi_endpoints(value)
        self.assertEqual(len(catalog.openapi_endpoints({'openapi':'3.1.0','paths':{f'/api/{i}':{'get':{}} for i in range(2100)}})), 2000)

    def test_missing_custom_catalog_falls_back_to_openapi(self):
        base = 'http://127.0.0.1:8000'
        ns, calls = self.namespace({base+'/api.json':Response(404,{}),base+'/openapi.json':Response(200,{'openapi':'3.1.0','paths':{'/api/users/me':{'get':{}}}})})
        from types import SimpleNamespace
        with patch.dict(os.environ, {'NOVIOKRO_SERVICE_NOVEAM_BACKEND':base}):
            result = asyncio.run(ns['discover'](SimpleNamespace(project='noveam',service='backend'), 'synthetic-admin'))
        self.assertEqual(result['endpoint_count'], 1)
        self.assertEqual([url for url,_ in calls], [base+'/api.json',base+'/openapi.json'])
        self.assertTrue(all('X-Admin-Key' not in options.get('headers',{}) for _,options in calls))

    def test_custom_catalog_stays_supported(self):
        base='http://127.0.0.1:8000'
        ns,calls=self.namespace({base+'/api.json':Response(200,{'routes':[{'method':'GET','path':'/api/test'}]})})
        from types import SimpleNamespace
        with patch.dict(os.environ, {'NOVIOKRO_SERVICE_NOVEAM_BACKEND':base}):
            result=asyncio.run(ns['discover'](SimpleNamespace(project='noveam',service='backend'),'synthetic-admin'))
        self.assertEqual(result['spec_version'],'noviokro-api/1')
        self.assertEqual(len(calls),1)

    def test_auth_failure_does_not_trigger_fallback(self):
        base='http://127.0.0.1:8000'
        ns,calls=self.namespace({base+'/api.json':Response(401,{})})
        from types import SimpleNamespace
        with patch.dict(os.environ, {'NOVIOKRO_SERVICE_NOVEAM_BACKEND':base}):
            with self.assertRaises(HTTPException) as error:
                asyncio.run(ns['discover'](SimpleNamespace(project='noveam',service='backend'),'synthetic-admin'))
        self.assertEqual(error.exception.status_code,502)
        self.assertEqual(len(calls),1)

    def test_categories_use_configured_destination_and_admin_gate(self):
        base='http://127.0.0.1:8000'
        ns,calls=self.namespace({base+'/api/professional/categories':Response(200,{'categories':[]})})
        with patch.dict(os.environ, {'NOVIOKRO_SERVICE_NOVEAM_BACKEND':base}):
            with self.assertRaises(HTTPException) as error:
                asyncio.run(ns['noveam_professional_categories']('wrong'))
            self.assertEqual(error.exception.status_code,401)
            self.assertEqual(calls,[])
            result=asyncio.run(ns['noveam_professional_categories']('synthetic-admin'))
        self.assertEqual(result,{'categories':[]})
        self.assertEqual(calls[0][0],base+'/api/professional/categories')

    def test_health_reports_catalog_errors_as_unavailable(self):
        base='http://127.0.0.1:8000'
        ns,_=self.namespace({base+'/api.json':Response(404,{}),base+'/openapi.json':Response(503,{})})
        with patch.dict(os.environ, {'NOVIOKRO_SERVICE_NOVEAM_BACKEND':base}):
            result=asyncio.run(ns['service_health']('noveam','backend','synthetic-admin'))
        self.assertTrue(result['reachable'])
        self.assertFalse(result['available'])
        self.assertEqual(result['probe_path'],'/openapi.json')

if __name__ == '__main__':
    unittest.main()
