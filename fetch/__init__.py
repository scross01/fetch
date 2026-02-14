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
    parser.add_argument("--favicon", action="store_true", help="extract favicon URLs instead of converting to markdown")
    parser.add_argument("--max-size", type=int, metavar="N", help="truncate output to N characters")

    args = parser.parse_args()

    if not args.url:
        parser.error("URL is required")

    logger.info(f"Fetching: {args.url}")
    scraper = create_scraper(debug=args.raw)
    result = fetch(args.url, scraper, favicon=args.favicon)
    print()

    if result:
        if args.favicon:
            print("Found favicon URLs:")
            for i, favicon_url in enumerate(result, 1):
                print(f"{i}. {favicon_url}")
        else:
            if args.max_size is not None and len(result) > args.max_size:
                result = result[:args.max_size]
            print(result)


if __name__ == "__main__":
    main()
