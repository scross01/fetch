# Change Log

## 0.3.2

- Fixed AttributeError when using `--format json` with YouTube URLs

## 0.3.1

- Fixed error when calling fetch from a subprocess without piped input

## 0.3.0

- Added `--format` option for markdown, txt, html, or json output
- Added `--output` / `-o` to write output to a file
- Added `--quiet` / `-q` to suppress status messages
- Added `--timeout` flag for HTTP request timeout (default: 30s)
- Added `--html` flag to convert piped HTML from stdin
- Added stdin piping support for URLs and raw HTML
- Errors now print to stderr instead of stdout
- Smart page classification with automatic extraction strategy
- Added `--include-comments` / `--exclude-comments` flags
- Added `--page-type` flag to manually specify page type
- GitHub URLs: fetch READMEs, raw files, issues, and pull requests
- YouTube URLs: extract video transcripts (no API key needed)
- RSS/Atom feeds: auto-detect or discover via `--rss` flag
- Added `--opengraph` flag to extract Open Graph metadata

## 0.2.0

- Added `--favicon` option to extract and list the sites favicons

## 0.1.0

- Intiial release to fetch and extract main page content from a URL and output as markdown

