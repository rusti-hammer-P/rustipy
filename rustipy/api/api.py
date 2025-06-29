import json
import struct
from typing import Any, Callable, Coroutine

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.responses import Response

from rustipy.app import pkg, setting


class AuthRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            if (
                setting.token
                and request.headers.get("authorization", None) != setting.token
            ):
                raise HTTPException(status_code=401, detail="Unauthorized")
            return await original_route_handler(request)

        return custom_route_handler


API = APIRouter(prefix="/api", route_class=AuthRoute)


def parse_request(body: bytes):
    meta_size: int = struct.unpack("<I", body[:4])[0]

    meta_bytes = body[4 : 4 + meta_size]
    if len(meta_bytes) != meta_size:
        raise

    metadata = json.loads(meta_bytes)

    try:
        crate_name: str = metadata["name"]
        crate_ver: str = metadata["vers"]
    except KeyError:
        raise KeyError("Invalid metadata")    

    lest = body[4 + meta_size :]

    crate_size = struct.unpack("<I", lest[:4])[0]
    crate_bytes = lest[4:]

    if len(crate_bytes) != crate_size:
        raise SystemError("Invalid crate size!")

    return crate_name, crate_ver, crate_bytes


@API.put("/v1/crates/new")
async def upload_crate(request: Request):
    body = await request.body()
    try:
        crate_name, crate_ver, crate_bytes = parse_request(body)
    except Exception as e:
        raise HTTPException(500, e.args)
    pkgs = await pkg.find_package(crate_name)
    file_name = f"{crate_name}-{crate_ver}.crate"
    if pkgs and crate_ver in pkgs:
        raise HTTPException(500, "Crate already exists")

    try:
        await pkg.save(file_name, crate_bytes)
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save crate file: {e}")

    return JSONResponse(
        {},
        status_code=200,
    )
