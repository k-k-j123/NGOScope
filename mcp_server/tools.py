from typing import Optional
from mcp_server.scrapers.serpapi_search import (
    search_web_info as _search_web_info,
    search_adverse_media as _search_adverse_media,
    analyze_ngo_credibility as _analyze_ngo_credibility,
)


async def search_ngo_web_info(
    ngo_name: str,
    state: Optional[str] = None,
    max_results: int = 5,
) -> dict:
    return await _search_web_info(ngo_name=ngo_name, state=state, max_results=max_results)


async def search_adverse_media(
    ngo_name: str,
    state: Optional[str] = None,
    max_results: int = 5,
) -> dict:
    return await _search_adverse_media(ngo_name=ngo_name, state=state, max_results=max_results)


async def analyze_ngo_credibility(
    ngo_name: str,
    state: Optional[str] = None,
    max_results: int = 5,
) -> dict:
    return await _analyze_ngo_credibility(ngo_name=ngo_name, state=state, max_results=max_results)


TOOL_REGISTRY = {
    "search_ngo_web_info": search_ngo_web_info,
    "search_adverse_media": search_adverse_media,
    "analyze_ngo_credibility": analyze_ngo_credibility,
}