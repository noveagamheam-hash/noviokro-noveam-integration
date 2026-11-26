"""Opt-in NOVEAM HTTP gateway. NOVEAM remains the authority for user access."""
import os
import json
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from .noveam_gateway_contract import api_path, backend_origin, forwarded_headers

MAX_BODY = 25 * 1024 * 1024
MAX_RESPONSE = 64 * 1024 * 1024


def create_noveam_gateway():
    gateway = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    gateway.add_middleware(CORSMiddleware,
        allow_origins=[value.strip() for value in os.getenv('NOVIOKRO_NOVEAM_FRONTEND_ORIGINS',
            'http://127.0.0.1:5500,http://localhost:5500').split(',') if value.strip()],
        allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'],
        allow_headers=['Authorization', 'Content-Type', 'Accept'],
        expose_headers=['Retry-After', 'Content-Disposition'], max_age=600)

    @gateway.api_route('/api/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD'])
    async def forward(path: str, request: Request):
        if os.getenv('NOVIOKRO_NOVEAM_GATEWAY_ENABLED') != '1':
            raise HTTPException(503, 'NOVEAM gateway is not enabled')
        try:
            base = backend_origin(os.getenv('NOVIOKRO_SERVICE_NOVEAM_BACKEND', ''))
            target_path = api_path(path)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_BODY:
                raise HTTPException(413, 'NOVEAM request body is too large')
            chunks.append(chunk)
        target = httpx.URL(base).copy_with(path=target_path,
            query=request.scope.get('query_string', b''))
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0),
                    follow_redirects=False, trust_env=False) as client:
                async with client.stream(request.method, target,
                        headers=forwarded_headers(request.headers.items()),
                        content=b''.join(chunks)) as upstream:
                    content, received = [], 0
                    async for chunk in upstream.aiter_bytes():
                        received += len(chunk)
                        if received > MAX_RESPONSE:
                            raise HTTPException(502, 'NOVEAM response exceeds the gateway limit')
                        content.append(chunk)
                    headers = forwarded_headers(upstream.headers.items(), response=True)
                    headers['Cache-Control'] = 'no-store'
                    return Response(b''.join(content), status_code=upstream.status_code, headers=headers)
        except httpx.TimeoutException as exc:
            raise HTTPException(504, 'NOVEAM backend timed out') from exc
        except httpx.RequestError as exc:
            raise HTTPException(502, 'NOVEAM backend is unavailable') from exc

    @gateway.api_route('/realtime-config', methods=['GET'])
    async def realtime_config():
        if os.getenv('NOVIOKRO_NOVEAM_GATEWAY_ENABLED') != '1':
            raise HTTPException(503, 'NOVEAM gateway is not enabled')
        try:
            base = backend_origin(os.getenv('NOVIOKRO_SERVICE_NOVEAM_BACKEND', ''))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        # Browsers connect directly to the same configured upstream as HTTP.
        # The upstream must be browser-reachable and allow the frontend origin.
        scheme, rest = base.split('://', 1)
        return Response(
            content=json.dumps({'websocket_url': ('wss' if scheme == 'https' else 'ws') + '://' + rest + '/ws/communication'}),
            media_type='application/json', headers={'Cache-Control': 'no-store'},
        )

    return gateway
