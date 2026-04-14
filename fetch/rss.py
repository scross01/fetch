import json
import sys
import urllib.parse
from datetime import datetime, timezone
from html import unescape

import feedparser
from bs4 import BeautifulSoup

_FEED_TYPES = {
    "rss",
    "atom",
    "rdf",
    "jsonfeed",
}


def _find_feed_urls(html_content, base_url):
    soup = BeautifulSoup(html_content, "html.parser")
    feed_urls = []

    for link in soup.find_all("link", rel="alternate"):
        href = link.get("href")
        link_type = (link.get("type") or "").lower()
        if href and (
            "rss" in link_type
            or "atom" in link_type
            or "feed" in link_type
            or href.lower().endswith((".rss", ".xml", ".atom"))
        ):
            feed_urls.append(urllib.parse.urljoin(base_url, href))

    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if href.endswith((".rss", ".xml", "/rss", "/feed", "/atom.xml")):
            feed_urls.append(urllib.parse.urljoin(base_url, a["href"]))

    seen = set()
    unique = []
    for url in feed_urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def _is_feed_content(content):
    if not content or not content.strip():
        return False
    stripped = content.strip().lower()
    if (
        stripped.startswith("<?xml")
        or stripped.startswith("<rss")
        or stripped.startswith("<feed")
    ):
        parsed = feedparser.parse(content)
        return bool(parsed.entries) or bool(parsed.feed.get("title"))
    if stripped.startswith("{") or stripped.startswith("["):
        parsed = feedparser.parse(content)
        return bool(parsed.entries)
    return False


def _clean_html(text):
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ").strip()


def _format_date(entry):
    for attr in ("published", "updated"):
        raw = entry.get(attr)
        if raw:
            try:
                from email.utils import parsedate_to_datetime

                dt = parsedate_to_datetime(raw)
                return dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                return raw
    return None


def _format_feed_markdown(feed):
    lines = []
    meta = feed.feed if hasattr(feed, "feed") else {}

    title = meta.get("title", "")
    if title:
        lines.append(f"# {title}")
        lines.append("")

    description = meta.get("subtitle") or meta.get("description") or meta.get("summary")
    if description:
        cleaned = _clean_html(description)
        if cleaned:
            lines.append(cleaned)
            lines.append("")

    link = meta.get("link")
    if link:
        lines.append(f"[Website]({link})")
        lines.append("")

    lines.append(f"---")
    lines.append(f"{len(feed.entries)} entries")
    lines.append("")

    for entry in feed.entries:
        entry_title = entry.get("title", "Untitled")
        lines.append(f"## {unescape(entry_title)}")

        date = _format_date(entry)
        if date:
            lines.append(f"**{date}**")

        authors = entry.get("authors", [])
        if authors:
            author_names = ", ".join(
                a.get("name", "") for a in authors if a.get("name")
            )
            if author_names:
                lines.append(f"By {author_names}")

        summary = entry.get("summary") or entry.get("description")
        if summary:
            cleaned = _clean_html(summary)
            if cleaned:
                lines.append("")
                lines.append(cleaned)

        entry_link = entry.get("link")
        if entry_link:
            lines.append("")
            lines.append(f"[Read more]({entry_link})")

        lines.append("")

    return "\n".join(lines)


def _format_feed_text(feed):
    lines = []
    meta = feed.feed if hasattr(feed, "feed") else {}

    title = meta.get("title", "")
    if title:
        lines.append(title)
        lines.append("=" * len(title))
        lines.append("")

    description = meta.get("subtitle") or meta.get("description") or meta.get("summary")
    if description:
        cleaned = _clean_html(description)
        if cleaned:
            lines.append(cleaned)
            lines.append("")

    link = meta.get("link")
    if link:
        lines.append(link)
        lines.append("")

    lines.append(f"---")
    lines.append(f"{len(feed.entries)} entries")
    lines.append("")

    for entry in feed.entries:
        entry_title = entry.get("title", "Untitled")
        lines.append(unescape(entry_title))

        date = _format_date(entry)
        if date:
            lines.append(date)

        authors = entry.get("authors", [])
        if authors:
            author_names = ", ".join(
                a.get("name", "") for a in authors if a.get("name")
            )
            if author_names:
                lines.append(f"By {author_names}")

        summary = entry.get("summary") or entry.get("description")
        if summary:
            cleaned = _clean_html(summary)
            if cleaned:
                lines.append("")
                lines.append(cleaned)

        entry_link = entry.get("link")
        if entry_link:
            lines.append("")
            lines.append(entry_link)

        lines.append("")
        lines.append("-" * 40)
        lines.append("")

    return "\n".join(lines)


def _format_feed_html(feed):
    parts = []
    meta = feed.feed if hasattr(feed, "feed") else {}

    title = meta.get("title", "Feed")
    parts.append(f"<h1>{title}</h1>")

    description = meta.get("subtitle") or meta.get("description") or meta.get("summary")
    if description:
        parts.append(f"<p>{description}</p>")

    link = meta.get("link")
    if link:
        parts.append(f'<p><a href="{link}">Website</a></p>')

    parts.append(f"<p>{len(feed.entries)} entries</p>")
    parts.append("<hr>")

    for entry in feed.entries:
        entry_title = unescape(entry.get("title", "Untitled"))
        entry_link = entry.get("link", "")
        if entry_link:
            parts.append(f'<article><h2><a href="{entry_link}">{entry_title}</a></h2>')
        else:
            parts.append(f"<article><h2>{entry_title}</h2>")

        date = _format_date(entry)
        if date:
            parts.append(f"<time>{date}</time>")

        authors = entry.get("authors", [])
        if authors:
            author_names = ", ".join(
                a.get("name", "") for a in authors if a.get("name")
            )
            if author_names:
                parts.append(f"<p>By {author_names}</p>")

        summary = entry.get("summary") or entry.get("description")
        if summary:
            parts.append(f"<div>{summary}</div>")

        parts.append("</article>")

    return "\n".join(parts)


def _format_feed_json(feed):
    meta = feed.feed if hasattr(feed, "feed") else {}

    feed_data = {
        "title": meta.get("title", ""),
        "description": meta.get("subtitle")
        or meta.get("description")
        or meta.get("summary", ""),
        "link": meta.get("link", ""),
        "entries": [],
    }

    for entry in feed.entries:
        entry_data = {
            "title": unescape(entry.get("title", "")),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "updated": entry.get("updated", ""),
            "summary": _clean_html(
                entry.get("summary") or entry.get("description", "")
            ),
            "authors": [
                a.get("name", "") for a in entry.get("authors", []) if a.get("name")
            ],
        }
        feed_data["entries"].append(entry_data)

    return json.dumps(feed_data, ensure_ascii=False, indent=2)


def _format_feed(feed, output_format="markdown"):
    formatters = {
        "markdown": _format_feed_markdown,
        "txt": _format_feed_text,
        "html": _format_feed_html,
        "json": _format_feed_json,
    }
    formatter = formatters.get(output_format, _format_feed_markdown)
    return formatter(feed)


def handle_rss_content(content, output_format="markdown"):
    if not _is_feed_content(content):
        return None
    try:
        parsed = feedparser.parse(content)
        return _format_feed(parsed, output_format)
    except Exception as e:
        print(f"Error parsing feed: {e}", file=sys.stderr)
        return None


def fetch_feed_from_html(
    html_content, url, scraper, timeout=30, output_format="markdown"
):
    feed_urls = _find_feed_urls(html_content, url)
    if not feed_urls:
        print("No RSS/Atom feed found in page metadata", file=sys.stderr)
        return None

    for feed_url in feed_urls:
        try:
            response = scraper.get(feed_url, timeout=timeout)
            response.raise_for_status()
            parsed = feedparser.parse(response.text)
            if parsed.entries:
                return _format_feed(parsed, output_format)
        except Exception as e:
            print(f"Error fetching feed {feed_url}: {e}", file=sys.stderr)
            continue

    print("Could not fetch a valid feed from discovered URLs", file=sys.stderr)
    return None
