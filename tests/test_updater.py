from app.updater import _parse_version, check_for_update


def test_parse_version():
    assert _parse_version("v1.2.3") == (1, 2, 3)
    assert _parse_version("1.0.0") == (1, 0, 0)
    assert _parse_version("v2.0") == (2, 0)


def test_version_comparison():
    assert _parse_version("v1.0.1") > _parse_version("1.0.0")
    assert _parse_version("v1.1.0") > _parse_version("v1.0.9")


def test_check_for_update_handles_network_error(monkeypatch):
    import requests

    def boom(*args, **kwargs):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr(requests, "get", boom)
    result = check_for_update("1.0.0")
    assert result.error is True
    assert result.update_available is False
