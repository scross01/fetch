import argparse
import logging
from .core import fetch, create_scraper
from .__version__ import __version__

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Fetch and convert web page to text")
    parser.add_argument("url", nargs="?", help="URL to fetch and convert")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--raw", action="store_true", help="include the full response data")

    args = parser.parse_args()

    if not args.url:
        parser.error("URL is required")

    logger.info(f"Fetching: {args.url}")
    scraper = create_scraper(debug=args.raw)
    text = fetch(args.url, scraper)
    print()

    if text:
        print(text)


if __name__ == "__main__":
    main()
