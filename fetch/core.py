import cloudscraper
from html2text import html2text
from readability import Document
from bs4 import BeautifulSoup
import urllib.parse
from .extractors import extract_with_trafilatura, extract_with_readability, should_exclude_comments
from .classifier import classify_page
from .types import PageType


def create_scraper(debug=False):
    return cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'mobile': True,
        },
        debug=debug
    )


scraper = create_scraper()


def fetch_page(url, scraper=None):
    """Fetch the raw HTML content from a URL."""
    if scraper is None:
        scraper = globals()['scraper']

    try:
        response = scraper.get(url)
        response.raise_for_status()
        return response.text, response.url
    except Exception as e:
        print(f"[red]Error fetching page:[/red] {e}")
        return None, None


def convert_to_markdown(html_content, url, include_comments=None, page_type=None):
    """Convert HTML content to markdown using intelligent extraction.
    
    Args:
        html_content: Raw HTML content
        url: Base URL for resolving relative links
        include_comments: Override for comment inclusion (None = auto-detect)
        page_type: Manually specified page type (None = auto-detect)
        
    Returns:
        Formatted markdown string with extracted content
    """
    try:
        # Determine page type if not provided
        if page_type is None:
            page_type = classify_page(html_content, url)
        
        # Choose extraction strategy based on page type and user preference
        if include_comments is not None:
            # User explicitly specified comment preference
            result = extract_with_trafilatura(
                html_content, url, include_comments=include_comments
            )
        elif page_type == PageType.ARTICLE:
            # Articles typically don't need comments
            result = extract_with_trafilatura(
                html_content, url, include_comments=False
            )
        elif page_type in (PageType.FORUM, PageType.QA):
            # Forums and Q&A pages need comments for completeness
            result = extract_with_trafilatura(
                html_content, url, include_comments=True
            )
        else:
            # Unknown page type - try with comments first
            result = extract_with_trafilatura(
                html_content, url, include_comments=True
            )
            
            # If result seems too long or contains too much noise, retry without comments
            if should_exclude_comments(result):
                result = extract_with_trafilatura(
                    html_content, url, include_comments=False
                )
        
        return result
        
    except Exception as e:
        print(f"[red]Error converting to markdown:[/red] {e}")
        # Fallback to original readability-based extraction
        return extract_with_readability(html_content, url)


def extract_favicons(html_content, base_url):
    """Extract favicon URLs from HTML content."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        base_domain = urllib.parse.urlparse(base_url)
        base_scheme = base_domain.scheme
        base_netloc = base_domain.netloc
        
        favicons = []
        
        # Look for link rel="icon" and rel="shortcut icon"
        icon_links = soup.find_all('link', attrs={'rel': lambda x: x and 'icon' in x.lower()})
        
        for link in icon_links:
            href = link.get('href')
            if href:
                # Convert relative URLs to absolute
                if href.startswith('//'):
                    # Protocol-relative URL
                    favicon_url = f"{base_scheme}:{href}"
                elif href.startswith('/'):
                    # Root-relative URL
                    favicon_url = f"{base_scheme}://{base_netloc}{href}"
                elif href.startswith('http'):
                    # Absolute URL
                    favicon_url = href
                else:
                    # Relative URL
                    favicon_url = f"{base_scheme}://{base_netloc}/{href.lstrip('/')}"
                
                favicons.append(favicon_url)
        
        # Look for meta content with favicon info
        meta_favicons = soup.find_all('meta', attrs={'name': 'msapplication-TileImage'})
        for meta in meta_favicons:
            href = meta.get('content')
            if href:
                if href.startswith('//'):
                    favicon_url = f"{base_scheme}:{href}"
                elif href.startswith('/'):
                    favicon_url = f"{base_scheme}://{base_netloc}{href}"
                elif href.startswith('http'):
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
        print(f"[red]Error extracting favicons:[/red] {e}")
        return []


def fetch(url, scraper=None, favicon=False, include_comments=None, page_type=None):
    """Main fetch function - either returns markdown or favicon URLs.
    
    Args:
        url: URL to fetch
        scraper: Custom scraper instance (optional)
        favicon: If True, extract favicon URLs instead of content
        include_comments: Override for comment inclusion (None = auto-detect)
        page_type: Manually specified page type (None = auto-detect)
        
    Returns:
        Extracted content or favicon URLs
    """
    html_content, final_url = fetch_page(url, scraper)
    if html_content is None:
        return None
    
    if favicon:
        return extract_favicons(html_content, final_url or url)
    else:
        return convert_to_markdown(
            html_content,
            final_url or url,
            include_comments=include_comments,
            page_type=page_type
        )
