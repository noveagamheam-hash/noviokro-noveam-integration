"""Exercise the actual gateway handler with a synthetic HTTP transport."""
import ast
import asyncio
import importlib.util
import os
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]/'app'
spec=importlib.util.spec_from_file_location('gateway_contract',ROOT/'noveam_gateway_contract.py')
contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
class HTTPException(Exception):
 def __init__(self,status_code,detail): self.status_code,self.detail=status_code,detail
class Request:
 method='POST';scope={'query_string':b'q=a%2Bb&limit=2'}
 headers={'authorization':'Bearer synthetic-user','x-admin-key':'synthetic-admin','content-type':'application/json'}
 async def stream(self): yield b'{"text":"hello"}'
class Response:
 def __init__(self,body=None,status_code=200,headers=None,content=None,media_type=None): self.body,self.status_code,self.headers=content if content is not None else body,status_code,headers

def handler(status=200):
 calls=[]
 class App:
  def __init__(self,**kw): pass
  def add_middleware(self,*a,**kw): pass
  def api_route(self,*a,**kw):
   def register(fn): setattr(self,fn.__name__,fn);return fn
   return register
 class URL:
  def __init__(self,base): self.base=base
  def copy_with(self,path,query): return self.base+path+('?' + query.decode() if query else '')
 class Upstream:
  status_code=status;headers={'content-type':'application/json','set-cookie':'private','connection':'close'}
  async def __aenter__(self): return self
  async def __aexit__(self,*a): pass
  async def aiter_bytes(self): yield b'{"ok":true}'
 class Client:
  def __init__(self,**kw): assert kw['trust_env'] is False and kw['follow_redirects'] is False
  async def __aenter__(self): return self
  async def __aexit__(self,*a): pass
  def stream(self,method,target,**kw): calls.append((method,target,kw));return Upstream()
 class TransportError(Exception): pass
 ns=dict(json=json,os=os,httpx=SimpleNamespace(URL=URL,AsyncClient=Client,Timeout=lambda v:v,TimeoutException=TransportError,RequestError=TransportError),FastAPI=App,HTTPException=HTTPException,Request=Request,Response=Response,CORSMiddleware=object,MAX_BODY=1024,MAX_RESPONSE=1024,api_path=contract.api_path,backend_origin=contract.backend_origin,forwarded_headers=contract.forwarded_headers)
 tree=ast.parse((ROOT/'noveam_gateway.py').read_text(encoding='utf-8-sig'))
 fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='create_noveam_gateway')
 exec(compile(ast.Module(body=[fn],type_ignores=[]),'noveam_gateway.py','exec'),ns)
 app=ns['create_noveam_gateway']()
 app.forward.realtime_config=app.realtime_config
 return app.forward,calls

class GatewayChecks(unittest.TestCase):
 def test_realtime_uses_same_configured_upstream(self):
  fn,calls=handler()
  for base,expected in [('https://staging.example','wss://staging.example/ws/communication'),('http://127.0.0.1:8000','ws://127.0.0.1:8000/ws/communication')]:
   with patch.dict(os.environ,{'NOVIOKRO_NOVEAM_GATEWAY_ENABLED':'1','NOVIOKRO_SERVICE_NOVEAM_BACKEND':base}):
    response=asyncio.run(fn.realtime_config())
   self.assertEqual(json.loads(response.body)['websocket_url'],expected)
   self.assertEqual(response.headers['Cache-Control'],'no-store')
  self.assertEqual(calls,[])
 def test_realtime_disabled_or_invalid_upstream_fails_closed(self):
  fn,_=handler()
  for enabled,base in [('0','https://staging.example'),('1','https://user:password@example.test')]:
   with patch.dict(os.environ,{'NOVIOKRO_NOVEAM_GATEWAY_ENABLED':enabled,'NOVIOKRO_SERVICE_NOVEAM_BACKEND':base}):
    with self.assertRaises(HTTPException): asyncio.run(fn.realtime_config())
 def call(self,fn,path='posts'):
  with patch.dict(os.environ,{'NOVIOKRO_NOVEAM_GATEWAY_ENABLED':'1','NOVIOKRO_SERVICE_NOVEAM_BACKEND':'http://127.0.0.1:8000'}):
   return asyncio.run(fn(path,Request()))
 def test_authorization_query_body_and_status_forwarding(self):
  fn,calls=handler();response=self.call(fn)
  method,target,options=calls[0]
  self.assertEqual(method,'POST');self.assertEqual(target,'http://127.0.0.1:8000/api/posts?q=a%2Bb&limit=2')
  self.assertEqual(options['headers']['authorization'],'Bearer synthetic-user')
  self.assertNotIn('x-admin-key',options['headers']);self.assertEqual(options['content'],b'{"text":"hello"}')
  self.assertEqual(response.body,b'{"ok":true}');self.assertEqual(response.headers['Cache-Control'],'no-store')
  self.assertNotIn('set-cookie',response.headers)
 def test_backend_authorization_rejections_are_preserved(self):
  for status in [401,403,428,429]:
   fn,_=handler(status);self.assertEqual(self.call(fn).status_code,status)
 def test_disabled_gateway_is_closed(self):
  fn,calls=handler()
  with patch.dict(os.environ,{'NOVIOKRO_NOVEAM_GATEWAY_ENABLED':'0'}):
   with self.assertRaises(HTTPException) as error: asyncio.run(fn('users/me',Request()))
  self.assertEqual(error.exception.status_code,503);self.assertEqual(calls,[])
 def test_path_escape_is_rejected(self):
  for path in ['../health','auth/../login','auth/%2e%2e/login','auth\\login','/api/users','users//me']:
   fn,calls=handler()
   with self.assertRaises(HTTPException): self.call(fn,path)
   self.assertEqual(calls,[])
 def test_upstream_configuration_validation(self):
  for base in ['http://remote.example','http://127.0.0.1:8002','https://user:secret@example.test','https://example.test/path','https://example.test:wrong']:
   with self.assertRaises(ValueError): contract.backend_origin(base)
  self.assertEqual(contract.backend_origin('https://noveam-backend.onrender.com/'),'https://noveam-backend.onrender.com')
 def test_connection_nominated_and_forwarding_headers_are_removed(self):
  headers=contract.forwarded_headers([('connection','x-private'),('x-private','secret'),('forwarded','for=trusted'),('cookie','secret'),('Authorization','Bearer user')])
  self.assertEqual(headers,{'Authorization':'Bearer user'})
 def test_oversized_request_is_rejected(self):
  fn,calls=handler()
  class Large(Request):
   async def stream(self): yield b'x'*1025
  with patch.dict(os.environ,{'NOVIOKRO_NOVEAM_GATEWAY_ENABLED':'1','NOVIOKRO_SERVICE_NOVEAM_BACKEND':'http://127.0.0.1:8000'}):
   with self.assertRaises(HTTPException) as error: asyncio.run(fn('files/upload',Large()))
  self.assertEqual(error.exception.status_code,413);self.assertEqual(calls,[])
if __name__=='__main__': unittest.main()
