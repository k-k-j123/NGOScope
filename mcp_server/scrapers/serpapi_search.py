import os
import httpx
from dotenv import load_dotenv
from typing import Optional

# Load a local .env if one exists, so the key does not have to be exported by
# hand for every entry point (server, CLI, tests). load_dotenv() does NOT
# override variables already in the environment, so a real SERPAPI_KEY from CI,
# docker or `$env:SERPAPI_KEY` still takes precedence over the file.
load_dotenv()

SERPAPI_URL = "https://serpapi.com/search.json"
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")

# HTTPClient kwargs for every SerpAPI call.
_CLIENT_KWARGS = {
    "timeout": httpx.Timeout(30.0, connect=10.0),
    "follow_redirects": True,
    "trust_env": True,
}

NEGATIVE_KEYWORDS = [
    "fraud", "scam", "fake", "suspended", "banned", "investigation",
    "arrest", "corruption", "embezzle", "misuse", "sued", "fined", "raided",
]


async def _serpapi_get(params: dict) -> dict:
    if not SERPAPI_KEY:
        return {"error": "SERPAPI_KEY environment variable not set"}
    params["api_key"] = SERPAPI_KEY

    resp = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(**_CLIENT_KWARGS) as client:
                resp = await client.get(SERPAPI_URL, params=params)
            break
        except httpx.TransportError as e:
            if attempt == 1:
                return {
                    "error": f"Network error ({type(e).__name__}): {str(e) or 'no details'}"
                }
    if resp is None:
        return {"error": "Network error: unable to reach SerpAPI"}
    if resp.status_code == 401:
        return {"error": "Invalid SerpAPI key (HTTP 401)"}
    if resp.status_code == 429:
        return {"error": "SerpAPI quota exceeded or rate limited (HTTP 429)"}
    if resp.status_code != 200:
        return {"error": f"SerpAPI returned HTTP {resp.status_code}"}
    body = resp.json()
    if isinstance(body, dict) and body.get("error"):
        return {"error": f"SerpAPI error: {body['error']}"}
    return body


def _build_query(ngo_name: str, state: Optional[str]) -> str:
    query = f'"{ngo_name}" NGO'
    if state:
        query += f" {state}"
    return query


async def search_web_info(
    ngo_name: str,
    state: Optional[str] = None,
    max_results: int = 5,
) -> dict:
    result = {
        "source": "serpapi_google",
        "ngo_name": ngo_name,
        "results": [],
        "fetch_method": "api",
        "error": None,
    }
    body = await _serpapi_get(
        {
            "engine": "google",
            "q": _build_query(ngo_name, state),
            "num": str(max_results),
            "hl": "en",
            "gl": "in",
        }
    )
    if body.get("error"):
        result["error"] = body["error"]
        return result

    organic = body.get("organic_results") or []
    for item in organic[:max_results]:
        entry = {
            "position": item.get("position"),
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        }
        result["results"].append(entry)
    return result


async def search_adverse_media(
    ngo_name: str,
    state: Optional[str] = None,
    max_results: int = 5,
) -> dict:
    result = {
        "source": "serpapi_google_news",
        "ngo_name": ngo_name,
        "results": [],
        "sentiment": "unknown",
        "fetch_method": "api",
        "error": None,
    }
    body = await _serpapi_get(
        {
            "engine": "google",
            "q": _build_query(ngo_name, state),
            "tbm": "nws",
            "num": str(max_results),
            "hl": "en",
            "gl": "in",
        }
    )
    if body.get("error"):
        result["error"] = body["error"]
        return result

    news = body.get("news_results") or body.get("top_stories") or []
    for item in news[:max_results]:
        entry = {
            "title": item.get("title", ""),
            "snippet": item.get("snippet", "") or item.get("description", ""),
            "url": item.get("link") or item.get("url", ""),
            "source": item.get("source", {}).get("name", "") if isinstance(item.get("source"), dict) else item.get("source", ""),
            "date": item.get("date", ""),
        }
        if entry["title"]:
            result["results"].append(entry)

    if not result["results"]:
        result["sentiment"] = "no_coverage"
    else:
        haystack = " ".join(
            (r.get("title", "") + " " + r.get("snippet", "")).lower()
            for r in result["results"]
        )
        if any(kw in haystack for kw in NEGATIVE_KEYWORDS):
            result["sentiment"] = "negative"
        else:
            result["sentiment"] = "neutral"
    return result


def _is_official_domain(title: str, link: str, ngo_name: str) -> bool:
    name_tokens = set(w for w in ngo_name.lower().split() if len(w) > 3)
    if not name_tokens:
        return False
    combined = (title + link).lower()
    return any(tok in combined for tok in name_tokens)


async def analyze_ngo_credibility(
    ngo_name: str,
    state: Optional[str] = None,
    max_results: int = 5,
) -> dict:
    web = await search_web_info(ngo_name, state, max_results)
    news = await search_adverse_media(ngo_name, state, max_results)

    report = {
        "ngo_name": ngo_name,
        "state": state,
        "score": None,
        "verdict": None,
        "signals": [],
        "explanation": "",
        "web_results": web.get("results", []),
        "news_results": news.get("results", []),
        "sentiment": news.get("sentiment", "unknown"),
        "sources": ["serpapi_google", "serpapi_google_news"],
        "error": None,
    }

    errors = [e for e in (web.get("error"), news.get("error")) if e]
    if errors:
        report["error"] = " | ".join(errors)
        return report

    score = 50
    signals = []

    web_results = web.get("results", [])
    news_results = news.get("results", [])
    sentiment = news.get("sentiment", "unknown")

    official = [
        r for r in web_results
        if _is_official_domain(r.get("title", ""), r.get("link", ""), ngo_name)
    ]
    if official:
        score += 20
        signals.append(f"Official/primary website found: {official[0]['link']}")
    elif web_results:
        signals.append("No obvious official website in top results")

    if web_results:
        score = min(score + 10, 100)
        signals.append(f"{len(web_results)} web results found (online presence)")

    if sentiment == "negative":
        score -= 30
        signals.append(f"Negative media coverage ({len(news_results)} articles)")
    elif sentiment == "neutral":
        score += 10
        signals.append("Recent news coverage present, no adverse signals")
    elif sentiment == "no_coverage":
        signals.append("No recent news coverage found")

    score = max(0, min(100, score))

    if score >= 70:
        verdict = "trustworthy"
    elif score >= 40:
        verdict = "caution"
    else:
        verdict = "investigate"

    explanation = (
        f"{ngo_name} scores {score}/100 based on live web signals. "
        + " ".join(signals)
    )
    if not signals:
        explanation += " No reliable web signals could be gathered."

    report.update(
        {
            "score": score,
            "verdict": verdict,
            "signals": signals,
            "explanation": explanation,
        }
    )
    return report