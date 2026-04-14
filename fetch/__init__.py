import argparse
import logging
import sys
from .core import fetch, create_scraper
from .__version__ import __version__
from .types import PageType

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
        "--rss",
        action="store_true",
        help="look for RSS/Atom feed in page metadata and fetch it",
    )
    parser.add_argument(
        "--og",
        "--opengraph",
        action="store_true",
        help="extract Open Graph metadata from the page",
    )
    parser.add_argument(
        "--max-size", type=int, metavar="N", help="truncate output to N characters"
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="write output to FILE instead of stdout",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="suppress status messages",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30,
        metavar="SECONDS",
        help="HTTP request timeout in seconds (default: 30)",
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

    log_level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    if not args.url:
        parser.error("URL is required")

    # Validate conflicting options
    if args.include_comments and args.exclude_comments:
        parser.error("Cannot specify both --include-comments and --exclude-comments")

    if args.rss and args.favicon:
        parser.error("Cannot specify both --rss and --favicon")

    if args.og and args.favicon:
        parser.error("Cannot specify both --og and --favicon")

    if args.og and args.rss:
        parser.error("Cannot specify both --og and --rss")

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
        rss=args.rss,
        og=args.og,
        include_comments=include_comments,
        page_type=page_type,
        output_format=args.format,
        timeout=args.timeout,
    )

    if result:
        if args.favicon:
            output_lines = []
            if not args.quiet:
                output_lines.append("Found favicon URLs:")
            for i, favicon_url in enumerate(result, 1):
                output_lines.append(f"{i}. {favicon_url}")
            output_text = "\n".join(output_lines)
        else:
            if args.max_size is not None and len(result) > args.max_size:
                result = result[: args.max_size]
            output_text = result

        if args.output:
            with open(args.output, "w") as f:
                f.write(output_text)
                f.write("\n")
        else:
            print(output_text)


if __name__ == "__main__":
    main()
