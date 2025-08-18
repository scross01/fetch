import argparse
import cloudscraper

from html2text import html2text
from readability import Document

scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'mobile': True,
    },
    debug=True
)


def fetch(url):
    try:
        response = scraper.get(url)
        doc = Document(response.text)
        text = html2text(doc.summary(), baseurl=url, bodywidth=0)
        return f"# {doc.title()}\n\n{text}"
    except Exception as e:
        print(f"[red]Error:[/red]: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Fetch and convert web page to text")
    parser.add_argument("url", help="URL to fetch and convert")

    args = parser.parse_args()

    print(f"Fetching: {args.url}")
    text = fetch(args.url)
    print()

    if text:
        print(text)


if __name__ == "__main__":
    main()
