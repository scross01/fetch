import argparse
import logging
from .core import fetch, create_scraper
from .__version__ import __version__
from .types import PageType

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Fetch and convert web page to text")
    parser.add_argument("url", nargs="?", help="URL to fetch and convert")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--raw", action="store_true", help="include the full response data"
    )
    parser.add_argument(
        "--favicon",
        action="store_true",
        help="extract favicon URLs instead of converting to markdown",
    )
    parser.add_argument(
        "--max-size", type=int, metavar="N", help="truncate output to N characters"
    )

    # Content extraction options
    content_group = parser.add_argument_group("Content Extraction Options")
    content_group.add_argument(
        "--include-comments",
        action="store_true",
        help="force inclusion of comments (overrides auto-detection)",
    )
    content_group.add_argument(
        "--exclude-comments",
        action="store_true",
        help="force exclusion of comments (overrides auto-detection)",
    )
    content_group.add_argument(
        "--page-type",
        choices=[t.value for t in PageType],
        help="manually specify page type (for debugging)",
    )
    content_group.add_argument(
        "--format",
        choices=["txt", "markdown", "html", "json"],
        default="markdown",
        help="output format for extracted content (default: markdown)",
    )

    args = parser.parse_args()

    if not args.url:
        parser.error("URL is required")

    # Validate conflicting options
    if args.include_comments and args.exclude_comments:
        parser.error("Cannot specify both --include-comments and --exclude-comments")

    logger.info(f"Fetching: {args.url}")
    scraper = create_scraper(debug=args.raw)

    # Parse page type if specified
    page_type = None
    if args.page_type:
        page_type = PageType(args.page_type)

    # Determine comment preference
    include_comments = None
    if args.include_comments:
        include_comments = True
    elif args.exclude_comments:
        include_comments = False

    result = fetch(
        args.url,
        scraper,
        favicon=args.favicon,
        include_comments=include_comments,
        page_type=page_type,
        output_format=args.format,
    )
    print()

    if result:
        if args.favicon:
            print("Found favicon URLs:")
            for i, favicon_url in enumerate(result, 1):
                print(f"{i}. {favicon_url}")
        else:
            if args.max_size is not None and len(result) > args.max_size:
                result = result[: args.max_size]
            print(result)


if __name__ == "__main__":
    main()
