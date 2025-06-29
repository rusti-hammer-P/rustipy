import json
import struct

import pytest

from rustipy.api.api import parse_request


def meta_data():
    meta = json.dumps({"name": "sample", "vers": "1.1.0"}).encode()
    crate: bytes = "test".encode()

    return meta, crate


def invalid_meta_data():
    meta = json.dumps({"nam": "sample", "vers": "1.1.0"}).encode()
    crate: bytes = "test".encode()

    return meta, crate


def test_request():
    meta, crate = meta_data()

    s = struct.pack("<I", len(meta))
    dummy_crate_bytes = struct.pack("<I", len(crate))

    crate_name, crate_ver, crate_bytes = parse_request(
        b"".join([s, meta, dummy_crate_bytes, crate])
    )

    assert crate_name == "sample"
    assert crate_ver == "1.1.0"
    assert crate_bytes == crate


def test_request_invalid_meta():
    meta, crate = invalid_meta_data()

    s = struct.pack("<I", len(meta))
    dummy_crate_bytes = struct.pack("<I", len(crate))

    with pytest.raises(KeyError):
        crate_name, crate_ver, crate_bytes = parse_request(
            b"".join([s, meta, dummy_crate_bytes, crate])
        )


def test_request_invalid_json_size():
    meta, crate = meta_data()

    s = struct.pack("<I", len(meta) + 1)
    dummy_crate_bytes = struct.pack("<I", len(crate))

    with pytest.raises(json.decoder.JSONDecodeError):
        parse_request(b"".join([s, meta, dummy_crate_bytes, crate]))


def test_request_invalid_metadata_size():
    meta, crate = meta_data()

    s = struct.pack("<I", len(meta))
    dummy_crate_bytes = struct.pack("<I", len(crate) + 1)

    with pytest.raises(SystemError):
        parse_request(b"".join([s, meta, dummy_crate_bytes, crate]))
