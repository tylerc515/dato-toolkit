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


def _make_mock_requests(monkeypatch, tag="v99.0.0", body="## What's New\n\n- Cool feature",
                         published_at="2026-06-15T10:00:00Z",
                         html_url="https://github.com/tylerc515/trace-tracker-builder/releases/tag/v99.0.0",
                         exe_url="https://example.com/DATOToolkit_v99.0.0.exe",
                         assets_names=None):
    import requests as req
    if assets_names is None:
        assets = [{"name": "DATOToolkit_v99.0.0.exe", "browser_download_url": exe_url}]
    else:
        assets = [{"name": n, "browser_download_url": exe_url} for n in assets_names]

    class _Resp:
        def raise_for_status(self): pass
        def json(self):
            return {"tag_name": tag, "body": body, "published_at": published_at,
                    "html_url": html_url, "assets": assets}
    monkeypatch.setattr(req, "get", lambda *a, **kw: _Resp())


def test_check_for_update_returns_release_notes(monkeypatch):
    _make_mock_requests(monkeypatch)
    result = check_for_update("1.0.0")
    assert "What's New" in result.release_notes
    assert result.update_available is True


def test_check_for_update_returns_download_url(monkeypatch):
    _make_mock_requests(monkeypatch)
    result = check_for_update("1.0.0")
    assert result.download_url == "https://example.com/DATOToolkit_v99.0.0.exe"


def test_check_for_update_returns_published_at_and_current_version(monkeypatch):
    _make_mock_requests(monkeypatch)
    result = check_for_update("1.0.0")
    assert result.published_at == "2026-06-15T10:00:00Z"
    assert result.current_version == "1.0.0"


def test_check_for_update_no_exe_asset_gives_none_url(monkeypatch):
    _make_mock_requests(monkeypatch, assets_names=["checksums.txt"])
    result = check_for_update("1.0.0")
    assert result.download_url is None


def test_check_for_update_empty_body_gives_fallback(monkeypatch):
    _make_mock_requests(monkeypatch, body="")
    result = check_for_update("1.0.0")
    assert result.release_notes == "No release notes provided for this version."


def test_check_for_update_returns_release_url(monkeypatch):
    _make_mock_requests(monkeypatch)
    result = check_for_update("1.0.0")
    assert "trace-tracker-builder" in result.release_url


def test_format_published_at_iso_to_human():
    from app.updater import format_published_at
    assert format_published_at("2026-06-15T10:00:00Z") == "June 15, 2026"


def test_format_published_at_empty_returns_empty():
    from app.updater import format_published_at
    assert format_published_at("") == ""


def test_format_published_at_invalid_returns_original():
    from app.updater import format_published_at
    assert format_published_at("not-a-date") == "not-a-date"
