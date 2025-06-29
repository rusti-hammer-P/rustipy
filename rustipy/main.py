import json
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    PlainTextResponse,
)

from .api import API
from .app import app, pkg, setting
from .crates import Crate


@app.get("/")
def index() -> HTMLResponse:
    links = "<br>".join(
        [
            f"<a href='{setting.root_url}/sparse/{i[:2]}/{i[2:4]}/{i}'>{i}</a>"
            for i in pkg.metas.keys()
        ]
    )
    # HACK: USE jinja
    text = f"""
<html>
<br>
{links}
</html>
"""
    return HTMLResponse(text)


@app.get("/sparse/config.json")
def config_json():
    return {"dl": f"{setting.root_url}/crates", "api": f"{setting.root_url}"}


@app.get("/sparse/{aa}/{bb}/{name}")
async def package_index(aa: str, bb: str, name: str):
    try:
        pkgs = await pkg.find_package(name)
    except TimeoutError:
        raise HTTPException(500, detail="timeout error")
    if not pkgs:
        raise HTTPException(404, detail="Crate not found")

    def make_metadata_dict(p: Crate):
        return {
            "name": p.name,
            "vers": p.vers,
            "deps": p.deps,
            "cksum": p.cksum,
            "v": 2,
            "yanked": False,
            "features2": p.features,
        }

    return PlainTextResponse(
        "\n".join([str(json.dumps(make_metadata_dict(p))) for p in pkgs.values()])
    )


@app.get("/crates/{name}/{version}/download")
async def download(name: str, version: str):
    file = Path(setting.package_path) / (f"{name}-{version}.crate")
    if file.exists():
        return FileResponse(file)
    else:
        raise HTTPException(404, detail="certain version crate not found")


def initialize():
    app.include_router(API)

    return app
