import argparse
import asyncio

from mcp_server.tools import analyze_ngo_credibility


def _render(report: dict) -> str:
    lines = []
    lines.append("=" * 56)
    lines.append(f"CharityLens — {report.get('ngo_name', 'NGO')}")
    lines.append("=" * 56)

    error = report.get("error")
    if error:
        lines.append(f"ERROR: {error}")
        return "\n".join(lines)

    score = report.get("score")
    verdict = report.get("verdict")
    bar_len = 20
    fill = round(score / 100 * bar_len)
    bar = "#" * fill + "-" * (bar_len - fill)
    lines.append(f"Score    : {score:3d}/100 [{bar}]")
    lines.append(f"Verdict  : {verdict.upper()}")
    lines.append(f"Sentiment: {report.get('sentiment', 'unknown')}")
    lines.append("")
    lines.append("Signals:")
    signals = report.get("signals") or []
    if signals:
        for s in signals:
            lines.append(f"  - {s}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("Explanation:")
    lines.append(f"  {report.get('explanation', '')}")
    lines.append("")

    news = report.get("news_results") or []
    if news:
        lines.append("Recent news:")
        for item in news[:5]:
            title = item.get("title", "")
            source = item.get("source", "")
            date = item.get("date", "")
            meta = " | ".join(x for x in [source, date] if x)
            line = f"  - {title}" + (f"  ({meta})" if meta else "")
            lines.append(line)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(prog="charitylens", description="NGO credibility lookup")
    parser.add_argument("ngo_name", nargs="+", help="NGO name to analyze")
    parser.add_argument("--state", default=None, help="Optional Indian state filter")
    parser.add_argument("--max-results", type=int, default=5, help="Results to fetch per engine")
    args = parser.parse_args()

    name = " ".join(args.ngo_name)
    report = asyncio.run(
        analyze_ngo_credibility(ngo_name=name, state=args.state, max_results=args.max_results)
    )
    print(_render(report))


if __name__ == "__main__":
    main()