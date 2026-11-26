"""Bounded OpenAPI metadata conversion; never executes catalog operations."""
METHODS = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}


def openapi_endpoints(spec):
    if (not isinstance(spec, dict) or not isinstance(spec.get('paths'), dict)
            or not isinstance(spec.get('openapi'), str) or not spec['openapi'].startswith('3.')):
        raise ValueError('Expected OpenAPI 3 document')
    endpoints = []
    for path, operations in spec['paths'].items():
        if (not isinstance(path, str) or not path.startswith('/api/')
                or len(path) > 500 or any(ord(c) < 32 for c in path)
                or not isinstance(operations, dict)):
            continue
        common = operations.get('parameters', [])
        for method, operation in operations.items():
            if method not in METHODS or not isinstance(operation, dict):
                continue
            query = []
            for parameters in [common, operation.get('parameters', [])]:
                if not isinstance(parameters, list):
                    continue
                for parameter in parameters:
                    if (isinstance(parameter, dict) and parameter.get('in') == 'query'
                            and isinstance(parameter.get('name'), str)
                            and parameter['name'] not in query):
                        query.append(parameter['name'])
            endpoints.append({'id': f'{method.upper()} {path}', 'method': method.upper(),
                              'path': path, 'query': query,
                              'summary': str(operation.get('summary', ''))[:300]})
            if len(endpoints) >= 2000:
                return endpoints
    return endpoints
