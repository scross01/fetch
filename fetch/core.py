import json
import re
import sys
from datetime import datetime, timezone
import cloudscraper
from html2text import html2text
from readability import Document
from bs4 import BeautifulSoup
import urllib.parse
from .extractors import (
    extract_with_trafilatura,
    extract_with_readability,
    extract_metadata,
    should_exclude_comments,
)
from .classifier import classify_page
from .github import handle_github_url
from .youtube import handle_youtube_url
from .rss import handle_rss_content, fetch_feed_from_html
from .opengraph import extract_og_metadata
from .types import PageType


def create_scraper(debug=False):
    return cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "mobile": True,
        },
        debug=debug,
    )


scraper = create_scraper()


def fetch_page(url, scraper=None, timeout=30):
    """Fetch the raw HTML content from a URL."""
    if scraper is None:
        scraper = globals()["scraper"]

    try:
        response = scraper.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text, response.url
    except Exception as e:
        print(f"Error fetching page: {e}", file=sys.stderr)
        return None, None


def convert_to_markdown(
    html_content, url, include_comments=None, page_type=None, output_format="markdown"
):
    """Convert HTML content to markdown using intelligent extraction.

    Args:
        html_content: Raw HTML content
        url: Base URL for resolving relative links
        include_comments: Override for comment inclusion (None = auto-detect)
        page_type: Manually specified page type (None = auto-detect)
        output_format: Output format - "markdown", "txt", "html", or "json" (default: "markdown")

    Returns:
        Formatted string with extracted content, or JSON string
    """
    content_format = "markdown" if output_format == "json" else output_format

    try:
        # Determine page type if not provided
        if page_type is None:
            page_type = classify_page(html_content, url)

        # Choose extraction strategy based on page type and user preference
        if include_comments is not None:
            # User explicitly specified comment preference
            result = extract_with_trafilatura(
                html_content,
                url,
                include_comments=include_comments,
                output_format=content_format,
            )
        elif page_type == PageType.ARTICLE:
            # Articles typically don't need comments
            result = extract_with_trafilatura(
                html_content, url, include_comments=False, output_format=content_format
            )
        elif page_type in (PageType.FORUM, PageType.QA):
            # Forums and Q&A pages need comments for completeness
            result = extract_with_trafilatura(
                html_content, url, include_comments=True, output_format=content_format
            )
        else:
            # Unknown page type - try with comments first
            result = extract_with_trafilatura(
                html_content, url, include_comments=True, output_format=content_format
            )

            # If result seems too long or contains too much noise, retry without comments
            if should_exclude_comments(result):
                result = extract_with_trafilatura(
                    html_content,
                    url,
                    include_comments=False,
                    output_format=content_format,
                )

    except Exception as e:
        print(f"Error converting to markdown: {e}", file=sys.stderr)
        # Fallback to original readability-based extraction
        result = extract_with_readability(
            html_content, url, output_format=content_format
        )

    if output_format == "json":
        return _build_json(html_content, url, result, page_type)

    return result


def _convert_result(result, url, output_format, page_type_str):
    if output_format == "markdown":
        return result
    if output_format == "txt":
        result = re.sub(r"^#{1,6}\s+", "", result, flags=re.MULTILINE)
        result = re.sub(r"\*\*([^*]+)\*\*", r"\1", result)
        return result
    if output_format == "html":
        return f"<pre>{result}</pre>"
    if output_format == "json":
        from .github import GithubResult
        from .youtube import YoutubeResult

        has_custom_attrs = isinstance(result, (GithubResult, YoutubeResult))
        title = (
            result.title if has_custom_attrs and isinstance(result.title, str) else ""
        )
        description = (
            result.description
            if has_custom_attrs and isinstance(result.description, str)
            else ""
        )
        links = (
            result.links if has_custom_attrs and isinstance(result.links, list) else []
        )
        images = (
            result.images
            if has_custom_attrs and isinstance(result.images, list)
            else []
        )
        return json.dumps(
            {
                "url": url,
                "title": title,
                "description": description,
                "content": result or "",
                "page_type": page_type_str,
                "links": links,
                "images": images,
                "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "content_length": len(result) if result else 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    return result


def _build_json(html_content, url, content, page_type):
    """Build structured JSON output with metadata."""
    try:
        doc = Document(html_content)
        cleaned_html = doc.summary()
    except Exception:
        cleaned_html = html_content

    metadata = extract_metadata(html_content, cleaned_html)

    return json.dumps(
        {
            "url": url,
            "title": metadata["title"],
            "description": metadata["description"],
            "content": content or "",
            "page_type": page_type.value if page_type else "unknown",
            "links": metadata["links"],
            "images": metadata["images"],
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "content_length": len(content) if content else 0,
        },
        ensure_ascii=False,
        indent=2,
    )


def extract_favicons(html_content, base_url):
    """Extract favicon URLs from HTML content."""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        base_domain = urllib.parse.urlparse(base_url)
        base_scheme = base_domain.scheme
        base_netloc = base_domain.netloc

        favicons = []

        # Look for link rel="icon" and rel="shortcut icon"
        icon_links = soup.find_all(
            "link", attrs={"rel": lambda x: x and "icon" in x.lower()}
        )

        for link in icon_links:
            href = link.get("href")
            if href:
                # Convert relative URLs to absolute
                if href.startswith("//"):
                    # Protocol-relative URL
                    favicon_url = f"{base_scheme}:{href}"
                elif href.startswith("/"):
                    # Root-relative URL
                    favicon_url = f"{base_scheme}://{base_netloc}{href}"
                elif href.startswith("http"):
                    # Absolute URL
                    favicon_url = href
                else:
                    # Relative URL
                    favicon_url = f"{base_scheme}://{base_netloc}/{href.lstrip('/')}"

                favicons.append(favicon_url)

        # Look for meta content with favicon info
        meta_favicons = soup.find_all("meta", attrs={"name": "msapplication-TileImage"})
        for meta in meta_favicons:
            href = meta.get("content")
            if href:
                if href.startswith("//"):
                    favicon_url = f"{base_scheme}:{href}"
                elif href.startswith("/"):
                    favicon_url = f"{base_scheme}://{base_netloc}{href}"
                elif href.startswith("http"):
                    favicon_url = href
                else:
                    favicon_url = f"{base_scheme}://{base_netloc}/{href.lstrip('/')}"
                favicons.append(favicon_url)

        # Remove duplicates while preserving order
        seen = set()
        unique_favicons = []
        for favicon in favicons:
            if favicon not in seen:
                seen.add(favicon)
                unique_favicons.append(favicon)

        return unique_favicons
    except Exception as e:
        print(f"Error extracting favicons: {e}", file=sys.stderr)
        return []


def fetch(
    url,
    scraper=None,
    favicon=False,
    rss=False,
    og=False,
    include_comments=None,
    page_type=None,
    output_format="markdown",
    timeout=30,
    html=None,
):
    """Main fetch function - either returns markdown or favicon URLs.

    Args:
        url: URL to fetch (used as base URL when html is provided)
        scraper: Custom scraper instance (optional)
        favicon: If True, extract favicon URLs instead of content
        rss: If True, look for RSS/Atom feed in page metadata and fetch it
        og: If True, extract Open Graph metadata instead of content
        include_comments: Override for comment inclusion (None = auto-detect)
        page_type: Manually specified page type (None = auto-detect)
        output_format: Output format - "markdown" or "txt" (default: "markdown")
        timeout: HTTP request timeout in seconds (default: 30)
        html: Pre-fetched HTML content; skips HTTP fetch and GitHub/YouTube dispatch

    Returns:
        Extracted content or favicon URLs
    """
    if html is not None:
        html_content = html
        final_url = url
    else:
        if not favicon and not rss and not og:
            github_result = handle_github_url(url, scraper, timeout=timeout)
            if github_result is not None:
                return _convert_result(github_result, url, output_format, "github")

            youtube_result = handle_youtube_url(url)
            if youtube_result is not None:
                return _convert_result(youtube_result, url, output_format, "youtube")

        html_content, final_url = fetch_page(url, scraper, timeout=timeout)
        if html_content is None:
            return None

    if favicon:
        return extract_favicons(html_content, final_url or url)

    if og:
        return extract_og_metadata(
            html_content, final_url or url, output_format=output_format
        )

    if rss:
        rss_result = fetch_feed_from_html(
            html_content,
            final_url or url,
            scraper,
            timeout=timeout,
            output_format=output_format,
        )
        if rss_result is not None:
            return rss_result

    rss_result = handle_rss_content(html_content, output_format=output_format)
    if rss_result is not None:
        return rss_result

    return convert_to_markdown(
        html_content,
        final_url or url,
        include_comments=include_comments,
        page_type=page_type,
        output_format=output_format,
    )
