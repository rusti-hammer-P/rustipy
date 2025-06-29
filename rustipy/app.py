from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from pydantic_settings import BaseSettings, SettingsConfigDict

from .crates import Packages


class Setting(BaseSettings):
    host: str = "localhost"
    port: int = 8000
    protocol: str = "http"
    package_path: str = "./packages"
    token: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def root_url(self):
        return f"{self.protocol}://{self.host}:{self.port}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .crates import start_watch

    await pkg.loads()
    _observer = await start_watch(Path(setting.package_path), pkg)
    yield
    if _observer:
        _observer.stop()
        _observer.join()


setting = Setting()
app = FastAPI(lifespan=lifespan)
pkg = Packages(setting.package_path)
