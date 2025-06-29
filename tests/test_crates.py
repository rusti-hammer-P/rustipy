import asyncio
import tempfile
from pathlib import Path

import pytest

from rustipy.crates import (
    Crate,
    Crates,
    Packages,
    _read_metadata,
    strip_name_ver,
    start_watch,
)


class MockPackages(Packages):
    def __init__(self, package_path: str, crate):
        self.crate = crate
        super().__init__(package_path)

    async def fetch(self, path):
        return asyncio.create_task(self.crate())


def make_mock_crate():
    toml = """
[package]
name = "sample"
version = "0.1.0"
edition = "2024"
publish = ["local-regist"] 

[dependencies]
ferris-says = {version = "*", registry ="local-regist"}
"""
    with tempfile.TemporaryDirectory() as td:
        crate_path = Path(td) / "Cargo.toml"
        with open(crate_path, "w") as f:
            f.write(toml)
        metadata = _read_metadata(crate_path)
    return Crate(metadata, "")


def test_strip_name_ver():
    assert strip_name_ver("colorchoice-1.0.4.crate") == ("colorchoice", "1.0.4")


def test_crate():
    crate = make_mock_crate()

    assert crate.deps == [
        {
            "name": "ferris-says",
            "req": "*",
            "features": [],
            "optional": False,
            "default_features": False,
            "target": None,
            "kind": "normal",
        }
    ]
    assert crate.features == {}


@pytest.mark.asyncio()
async def test_crates():
    crates = Crates("sample")
    crate = make_mock_crate()

    async def _crate():
        return crate

    assert crates.is_empty

    assert await crates.find_package() == {}
    crates.add_crate(ver="1.1.0", crate=asyncio.create_task(_crate()))

    assert not crates.is_empty
    assert await crates.find_package() == {"1.1.0": crate}
    crates.delist("1.1.0")

    assert await crates.find_package() == {}
    assert crates.is_empty


@pytest.mark.asyncio()
async def test_crates_timeout():
    crates = Crates("sample")
    crate = make_mock_crate()

    stop = asyncio.Event()

    async def _crate():
        await stop.wait()
        return crate

    assert crates.is_empty

    assert await crates.find_package() == {}
    crates.add_crate(ver="1.1.0", crate=asyncio.create_task(_crate()))

    assert not crates.is_empty
    with pytest.raises(TimeoutError):
        await crates.find_package()

    stop.set()


@pytest.mark.asyncio()
async def test_package():
    crate = make_mock_crate()

    async def _crate():
        return crate

    pkg = MockPackages("", crate=_crate)
    await pkg.load(Path("/sample-1.1.0.crate"))

    assert await pkg.find_package("sample") == {"1.1.0": crate}

    await pkg.delist(Path("/sample-1.1.0.crate"))

    assert not await pkg.find_package("sample")

    await pkg.load(Path("/sample-1.1.0.crate"))
    await pkg.load(Path("/sample-1.1.0.crate"))

    assert await pkg.find_package("sample") == {"1.1.0": crate}


@pytest.mark.asyncio()
async def test_package_load():
    crate = make_mock_crate()
    stop = asyncio.Event()

    async def _crate():
        await stop.wait()
        return crate

    pkg = MockPackages("", crate=_crate)
    await pkg.load(Path("/sample-1.1.0.crate"))

    with pytest.raises(TimeoutError):
        assert await pkg.find_package("sample") == {"1.1.0": crate}

    stop.set()
    assert await pkg.find_package("sample") == {"1.1.0": crate}


@pytest.mark.asyncio()
async def test_filewatch():
    crate = make_mock_crate()

    async def _crate():
        return crate

    pkg = MockPackages("", crate=_crate)

    with tempfile.TemporaryDirectory() as td:
        crate_path = Path(td)
        await start_watch(crate_path, pkg)

        (crate_path / "sample-1.1.0.crate").touch()
        await asyncio.sleep(1)
        assert await pkg.find_package("sample") == {"1.1.0": crate}

        (crate_path / "sample-1.1.0.crate").unlink()
        await asyncio.sleep(1)
        assert not await pkg.find_package("sample")
