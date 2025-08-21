import cloudscraper
from html2text import html2text
from readability import Document
from bs4 import BeautifulSoup
import urllib.parse


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


def convert_to_markdown(html_content, url):
    """Convert HTML content to markdown using html2text."""
    try:
        doc = Document(html_content)
        text = html2text(doc.summary(), baseurl=url, bodywidth=0)
        return f"# {doc.title()}\n\n{text}"
    except Exception as e:
        print(f"[red]Error converting to markdown:[/red] {e}")
        return None


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


def fetch(url, scraper=None, favicon=False):
    """Main fetch function - either returns markdown or favicon URLs."""
    html_content, final_url = fetch_page(url, scraper)
    if html_content is None:
        return None
    
    if favicon:
        return extract_favicons(html_content, final_url or url)
    else:
        return convert_to_markdown(html_content, final_url or url)
