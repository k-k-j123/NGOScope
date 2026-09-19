import pytest
import httpx

from mcp_server.scrapers import serpapi_search


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def _make_mock_get(responses):
    """Build an AsyncClient.get mock that routes by tbm param."""

    def _pick(params):
        tbm = params.get("tbm")
        if tbm == "nws":
            return responses.get("news")
        return responses.get("web", responses.get("news"))

    async def fake_get(self, url, params=None, **kwargs):
        resp = _pick(params or {})
        return FakeResponse(resp[0], resp[1])

    return fake_get


@pytest.mark.asyncio
async def test_missing_api_key_returns_error(monkeypatch):
    monkeypatch.setattr(serpapi_search, "SERPAPI_KEY", "")
    result = await serpapi_search.search_web_info("Pratham")
    assert "error" in result
    assert "SERPAPI_KEY" in result["error"]


@pytest.mark.asyncio
async def test_network_error_reports_exception_class(monkeypatch):
    calls = {"n": 0}

    async def fake_get(self, url, params=None, **kwargs):
        calls["n"] += 1
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(serpapi_search, "SERPAPI_KEY", "test-key")
    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)
    result = await serpapi_search.search_web_info("Pratham")
    assert "ConnectError" in result["error"]
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_single_transient_failure_recovers(monkeypatch):
    calls = {"n": 0}

    async def fake_get(self, url, params=None, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("Connection refused")
        return FakeResponse(200, {"organic_results": []})

    monkeypatch.setattr(serpapi_search, "SERPAPI_KEY", "test-key")
    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)
    result = await serpapi_search.search_web_info("Pratham")
    assert result["error"] is None
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_http_429_quota_error(monkeypatch):
    async def fake_get(self, url, params=None, **kwargs):
        return FakeResponse(429, {"error_message": "quota"})

    monkeypatch.setattr(serpapi_search, "SERPAPI_KEY", "test-key")
    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)
    result = await serpapi_search.search_adverse_media("Pratham", "Maharashtra")
    assert result["error"] and "429" in result["error"]


@pytest.mark.asyncio
async def test_web_search_parses_organic_results(monkeypatch):
    payload = {
        "organic_results": [
            {"position": 1, "title": "Pratham", "link": "https://pratham.org", "snippet": "Education for every child"},
        ]
    }
    monkeypatch.setattr(serpapi_search, "SERPAPI_KEY", "test-key")
    monkeypatch.setattr(
        "httpx.AsyncClient.get",
        _make_mock_get({"web": (200, payload), "news": (200, {"news_results": []})}),
    )
    result = await serpapi_search.search_web_info("Pratham")
    assert result["error"] is None
    assert len(result["results"]) == 1
    assert result["results"][0]["title"] == "Pratham"
    assert result["results"][0]["link"] == "https://pratham.org"


@pytest.mark.asyncio
async def test_news_sentiment_negative(monkeypatch):
    payload = {
        "news_results": [
            {"title": "NGO Pratham investigated for corruption", "link": "u", "snippet": "scam allegations", "source": {"name": "Times"}, "date": "today"},
        ]
    }
    monkeypatch.setattr(serpapi_search, "SERPAPI_KEY", "test-key")
    monkeypatch.setattr("httpx.AsyncClient.get", _make_mock_get({"news": (200, payload)}))
    result = await serpapi_search.search_adverse_media("Pratham")
    assert result["sentiment"] == "negative"
    assert result["results"][0]["source"] == "Times"


@pytest.mark.asyncio
async def test_news_no_coverage(monkeypatch):
    monkeypatch.setattr(serpapi_search, "SERPAPI_KEY", "test-key")
    monkeypatch.setattr("httpx.AsyncClient.get", _make_mock_get({"news": (200, {"news_results": []})}))
    result = await serpapi_search.search_adverse_media("Some Rare NGO")
    assert result["sentiment"] == "no_coverage"


@pytest.mark.asyncio
async def test_credibility_score_official_site_and_clean_news(monkeypatch):
    web_payload = {
        "organic_results": [
            {"position": 1, "title": "Pratham Education Foundation", "link": "https://www.pratham.org", "snippet": "Education for every child"},
            {"position": 2, "title": "Pratham on Wikipedia", "link": "https://en.wikipedia.org/wiki/Pratham", "snippet": "NGO info"},
        ]
    }
    news_payload = {
        "news_results": [
            {"title": "Pratham scales digital learning", "link": "u", "snippet": "partnership", "source": "Times", "date": "today"},
        ]
    }
    monkeypatch.setattr(serpapi_search, "SERPAPI_KEY", "test-key")
    monkeypatch.setattr(
        "httpx.AsyncClient.get",
        _make_mock_get({"web": (200, web_payload), "news": (200, news_payload)}),
    )
    report = await serpapi_search.analyze_ngo_credibility("Pratham Education Foundation")
    assert report["error"] is None
    assert report["score"] == 90
    assert report["verdict"] == "trustworthy"
    assert any("official" in s.lower() for s in report["signals"])


@pytest.mark.asyncio
async def test_credibility_score_negative_news_pulls_down(monkeypatch):
    web_payload = {
        "organic_results": [
            {"position": 1, "title": "Pratham Education Foundation", "link": "https://www.pratham.org", "snippet": "Education for every child"},
        ]
    }
    news_payload = {
        "news_results": [
            {"title": "Pratham caught in fraud probe", "link": "u", "snippet": "scam", "source": "Hindu", "date": "today"},
        ]
    }
    monkeypatch.setattr(serpapi_search, "SERPAPI_KEY", "test-key")
    monkeypatch.setattr(
        "httpx.AsyncClient.get",
        _make_mock_get({"web": (200, web_payload), "news": (200, news_payload)}),
    )
    report = await serpapi_search.analyze_ngo_credibility("Pratham Education Foundation")
    assert report["error"] is None
    assert report["sentiment"] == "negative"
    assert report["verdict"] == "caution"