import asyncio
import hashlib
import tarfile
import tempfile
import tomllib
from asyncio import Future
from pathlib import Path

import aiofiles
from watchdog.events import DirDeletedEvent, FileDeletedEvent, FileSystemEventHandler
from watchdog.observers import Observer


def _read_metadata(crate_path: Path):
    if crate_path.name != "Cargo.toml":
        raise FileNotFoundError(f"Expected 'Cargo.toml' but found '{crate_path.name}'")
    if not crate_path.is_file():
        raise FileNotFoundError(f"File not found or is not a file: '{crate_path}'")
    with open(crate_path, "r") as f:
        return tomllib.loads(f.read())


def _cksum(crate_path: Path):
    hash = hashlib.sha256()
    with open(crate_path, "rb") as f:
        while True:
            chunk = f.read(2048 * hash.block_size)
            if len(chunk) == 0:
                break
            hash.update(chunk)

    return hash.hexdigest()


async def unpack_meta(crate_path: Path):
    def inner():
        crate_dir = crate_path.stem
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(crate_path) as tar:
                tar.extractall(tmpdir)
            tmp = _read_metadata(Path(tmpdir) / crate_dir / "Cargo.toml")
            return Crate(tmp, _cksum(crate_path))

    return await asyncio.to_thread(inner)


def strip_name_ver(filen: str):
    parts = filen.rstrip(".crate").rsplit("-", 1)

    if len(parts) == 2:
        package_name = parts[0]
        version = parts[1]
        return package_name, version
    else:
        raise ValueError(f"Invalid crate filename format: {filen}")


class Crate:
    def __init__(self, metadata: dict[str, dict], cksum: str):
        self.metadata = metadata
        self.cksum = cksum

    @property
    def deps(self):
        if "dependencies" not in self.metadata:
            return []

        dependencies: dict[str, dict] = self.metadata["dependencies"]

        if "target" in self.metadata:
            for v in self.metadata["target"].values():
                if isinstance(v, dict):
                    dependencies = {**dependencies, **v.get("dependencies", {})}

        return [
            {
                "name": k,
                "req": v["version"],
                "features": v.get("features", []),
                "optional": v.get("optional", False),
                "default_features": v.get("default-features", False),
                "target": None,
                "kind": "normal",  # TODO: reflect cargo feature
            }
            for k, v in dependencies.items()
        ]

    @property
    def features(self):
        return self.metadata.get("features", {})

    @property
    def name(self) -> str:
        return self.metadata["package"]["name"]

    @property
    def vers(self) -> str:
        return self.metadata["package"]["version"]


class Crates:
    def __init__(self, name: str):
        self.name = name
        self.vers: dict[str, Future[Crate]] = {}

    def add_crate(self, ver: str, crate: Future[Crate]):
        self.vers[ver] = crate

    def delist(self, ver: str):
        self.vers.pop(ver)

    @property
    def is_empty(self):
        return len(self.vers) == 0

    async def find_package(self):
        async def inner(c: Future[Crate]):
            if c.done():
                return c.result()
            d, _p = await asyncio.wait([c], timeout=10)
            if len(d):
                return c.result()
            raise TimeoutError()

        return {k: await inner(v) for k, v in self.vers.items()}


class Packages:
    def __init__(self, package_path: str):
        self.metas: dict[str, Crates] = {}
        self.package_path: Path = Path(package_path)
        self._lock = asyncio.Lock()

    async def find_package(self, name: str):
        if name not in self.metas:
            return None
        return await self.metas[name].find_package()

    async def load(self, crate_path: Path):
        name, ver = strip_name_ver(crate_path.name)
        async with self._lock:
            if name in self.metas:
                self.metas[name].add_crate(ver, await self.fetch(crate_path))
            else:
                self.metas[name] = Crates(name)
                self.metas[name].add_crate(ver, await self.fetch(crate_path))

    async def fetch(self, path: Path):
        task = asyncio.create_task(unpack_meta(path))
        return task

    async def loads(self):
        for path in self.package_path.glob("*.crate"):
            await self.load(path)

    async def delist(self, crate_path: Path):
        name, ver = strip_name_ver(crate_path.name)
        async with self._lock:
            if name in self.metas:
                self.metas[name].delist(ver)
                if self.metas[name].is_empty:
                    self.metas.pop(name)

    async def save(self, file_name: str, content: bytes):
        crate_path = self.package_path / file_name
        async with aiofiles.open(crate_path, "+wb") as f:
            await f.write(content)


class FileWatch(FileSystemEventHandler):
    def __init__(self, pkgs: Packages, corr) -> None:
        self.corr = corr
        self.pkgs = pkgs

    def on_created(self, event):
        assert not event.is_directory
        if event.src_path.endswith(".crate"):  # type: ignore
            p: str = (
                event.src_path.decode()
                if isinstance(event.src_path, bytes)
                else str(event.src_path)
            )
            asyncio.run_coroutine_threadsafe(self.pkgs.load(Path(p)), self.corr)

    def on_deleted(self, event: DirDeletedEvent | FileDeletedEvent) -> None:
        if isinstance(event, FileDeletedEvent):
            if event.src_path.endswith(".crate"):  # type: ignore
                p: str = (
                    event.src_path.decode()
                    if isinstance(event.src_path, bytes)
                    else str(event.src_path)
                )
                asyncio.run_coroutine_threadsafe(self.pkgs.delist(Path(p)), self.corr)


async def start_watch(package_path: Path, pkgs: Packages):
    event_handler = FileWatch(pkgs, asyncio.get_running_loop())
    observer = Observer()
    observer.schedule(event_handler, str(package_path), recursive=False)
    observer.start()
    return observer
