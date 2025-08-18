import cloudscraper
from html2text import html2text
from readability import Document


def create_scraper(debug=False):
    return cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'mobile': True,
        },
        debug=debug
    )


scraper = create_scraper()


def fetch(url, scraper=None):
    if scraper is None:
        scraper = globals()['scraper']

    try:
        response = scraper.get(url)
        doc = Document(response.text)
        text = html2text(doc.summary(), baseurl=url, bodywidth=0)
        return f"# {doc.title()}\n\n{text}"
    except Exception as e:
        print(f"[red]Error:[/red]: {e}")
        return None
