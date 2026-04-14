"""Content extraction strategies for different types of web pages."""

import re
from html2text import html2text
from readability import Document
from bs4 import BeautifulSoup


def _extract_title(soup):
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text().strip()
        if title:
            return title
    h1_tag = soup.find("h1")
    if h1_tag:
        return h1_tag.get_text().strip()
    return None


def _build_link_map(html_content):
    """Build a mapping from link text to href from raw HTML.

    Handles common patterns where links exist but may be invisible
    (e.g. zero-font-size, absolutely positioned overlay links).
    """
    soup = BeautifulSoup(html_content, "html.parser")
    link_map = {}
    for a in soup.find_all("a", href=True):
        text = a.get_text().strip()
        if text and text not in link_map:
            link_map[text] = a["href"]
    return link_map


def _inject_links(text, link_map):
    """Replace plain text lines with markdown links where matching hrefs exist."""
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped in link_map:
            result.append(f"[{stripped}]({link_map[stripped]})")
        else:
            result.append(line)
    return "\n".join(result)


def extract_with_trafilatura(
    html_content, url, include_comments=True, output_format="markdown"
):
    """Extract content using Trafilatura library.

    Args:
        html_content: Raw HTML content
        url: Base URL for resolving relative links
        include_comments: Whether to include comments in the output
        output_format: Output format - "markdown" or "txt" (default: "markdown")

    Returns:
        Formatted markdown string with extracted content
    """
    if output_format == "html":
        return extract_with_readability(html_content, url, output_format=output_format)

    trafilatura_format = "markdown" if output_format == "markdown" else "txt"

    try:
        from trafilatura import extract

        result = extract(
            html_content,
            include_comments=include_comments,
            output_format=trafilatura_format,
            url=url,
        )

        if result:
            title = _extract_title(BeautifulSoup(html_content, "html.parser"))

            if output_format == "markdown":
                link_map = _build_link_map(html_content)
                result = _inject_links(result, link_map)
                if title and f"# {title}" not in result:
                    return f"# {title}\n\n{result}"
                return result
            else:
                if title:
                    return f"# {title}\n\n{result}"
                return result
        else:
            return extract_with_readability(
                html_content, url, output_format=output_format
            )

    except ImportError:
        print("Warning: Trafilatura not available, falling back to readability")
        return extract_with_readability(html_content, url, output_format=output_format)
    except Exception as e:
        print(
            f"Warning: Trafilatura extraction failed: {e}, falling back to readability"
        )
        return extract_with_readability(html_content, url, output_format=output_format)


def extract_with_readability(html_content, url, output_format="markdown"):
    """Fallback extraction using readability-lxml.

    Args:
        html_content: Raw HTML content
        url: Base URL for resolving relative links
        output_format: Output format - "markdown" or "txt" (default: "markdown")

    Returns:
        Formatted markdown string with extracted content
    """
    try:
        doc = Document(html_content)
        if output_format == "html":
            return doc.summary()
        elif output_format == "txt":
            text = doc.summary()
            text = BeautifulSoup(text, "html.parser").get_text(
                separator="\n", strip=True
            )
            return f"{doc.title()}\n\n{text}"
        else:
            text = html2text(doc.summary(), baseurl=url, bodywidth=0)
            return f"# {doc.title()}\n\n{text}"
    except Exception as e:
        print(f"Error extracting content with readability: {e}")
        return None


def extract_metadata(html_content, cleaned_html=None):
    """Extract metadata from HTML content.

    Args:
        html_content: Raw HTML content
        cleaned_html: Readability-cleaned HTML for links/images extraction

    Returns:
        dict with title, description, links, and images
    """
    soup = BeautifulSoup(html_content, "html.parser")

    title = None
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text().strip()
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text().strip()

    description = None
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc:
        description = meta_desc.get("content", "").strip()

    links = []
    seen_hrefs = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text().strip()
        if href not in seen_hrefs and text:
            seen_hrefs.add(href)
            links.append({"text": text, "href": href})

    images = []
    seen_srcs = set()
    source = BeautifulSoup(cleaned_html, "html.parser") if cleaned_html else soup
    for img in source.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt", "").strip()
        if src and src not in seen_srcs:
            seen_srcs.add(src)
            images.append({"alt": alt, "src": src})
    for img in soup.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt", "").strip()
        if src and src not in seen_srcs:
            seen_srcs.add(src)
            images.append({"alt": alt, "src": src})

    return {
        "title": title or "",
        "description": description or "",
        "links": links,
        "images": images,
    }


def should_exclude_comments(extracted_text):
    """Determine if comments should be excluded based on content analysis.

    Args:
        extracted_text: The extracted text content

    Returns:
        bool: True if comments should likely be excluded
    """
    if not extracted_text:
        return True

    # Heuristics to determine if comments are valuable content
    lines = extracted_text.split("\n")

    # Count lines that look like comments (short, with user-like patterns)
    comment_like_lines = 0
    total_lines = len([line for line in lines if line.strip()])

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Look for patterns typical of user comments
        if (
            (
                len(line) < 200
                and (
                    "@" in line
                    or ":" in line
                    or line.endswith("?")
                    or line.endswith("!")
                )
            )
            or (line.startswith(("Posted by", "Submitted by", "User:", "Author:")))
            or (
                len(line.split()) < 20
                and any(
                    word in line.lower()
                    for word in ["thanks", "agree", "disagree", "great", "good", "bad"]
                )
            )
        ):
            comment_like_lines += 1

    # If more than 30% of lines look like comments, they might not be valuable
    if total_lines > 0 and comment_like_lines / total_lines > 0.3:
        return True

    # If the text is very long (>5000 chars), it might include too many comments
    if len(extracted_text) > 5000:
        return True

    return False
