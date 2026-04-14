# Fetch

A command-line tool to fetch web pages and convert them to clean, readable text. Supports smart handling for GitHub and YouTube URLs.

## Features

- Fetches web pages with proper browser headers to avoid blocking
- Smart content extraction using `trafilatura` with `readability` fallback
- Converts HTML to Markdown, plain text, or HTML
- JSON output with metadata (title, description, links, images)
- GitHub URLs: fetch READMEs, raw files, issues, and pull requests
- YouTube URLs: extract video transcripts (no API key needed)
- RSS/Atom feeds: auto-detect feeds or discover them from page metadata
- Open Graph metadata: extract og: tags from any web page
- Configurable timeout, output to file, quiet mode for piping
- Extract favicon URLs from web pages

## Installation

### Using uv tool (Recommended)

```bash
uv tool install https://github.com/scross01/fetch
```

### Development Installation

```bash
git clone https://github.com/scross01/fetch
cd fetch
uv sync
```

## Usage

```bash
fetch <URL>
```

**Basic examples:**

```bash
# Fetch a web page as Markdown
fetch https://example.com

# Output as plain text
fetch --format txt https://example.com

# Output as JSON with metadata
fetch --format json https://example.com

# Save to file
fetch -o page.md https://example.com

# Quiet mode (no status messages) — useful for piping
fetch -q https://example.com | less

# Limit output size
fetch --max-size 5000 https://example.com

# Set a longer timeout for slow sites
fetch --timeout 60 https://slow-site.com

# Extract favicon URLs
fetch --favicon https://example.com

# Debug with raw output
fetch --raw https://example.com

# Show version
fetch --version
```

### GitHub URLs

No API key required for public repos.

```bash
# Repo root — fetches the README
fetch https://github.com/user/repo

# Raw file via blob URL
fetch https://github.com/user/repo/blob/main/src/main.py

# Issue with comments
fetch https://github.com/user/repo/issues/42

# Pull request with review and issue comments
fetch https://github.com/user/repo/pull/42
```

### YouTube Transcripts

Extracts transcript text using `youtube-transcript-api`. No API key needed.

```bash
# Standard watch URL
fetch https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Short URL
fetch https://youtu.be/dQw4w9WgXcQ

# Shorts
fetch https://www.youtube.com/shorts/abc123
```

Falls back to any available language and auto-translates to English when needed.

### RSS/Atom Feeds

Feeds are auto-detected when you fetch a feed URL directly. Use `--rss` to discover and fetch a feed from a regular web page.

```bash
# Auto-detected — URL is a feed
fetch https://example.com/blog/feed.xml

# Discover feed from a page's metadata
fetch --rss https://example.com/blog

# JSON output of feed entries
fetch --format json https://example.com/feed.xml

# Plain text
fetch --format txt https://example.com/feed.xml
```

### Open Graph Metadata

Extract Open Graph (`og:*`) metadata tags from any web page. Useful for getting link previews, social sharing info, and structured page data.

```bash
# Extract OG metadata as markdown
fetch --og https://example.com

# As JSON
fetch --og --format json https://example.com

# As plain text
fetch --og --format txt https://example.com
```

Extracts tags like `og:title`, `og:description`, `og:image`, `og:type`, `og:url`, `og:site_name`, and any other `og:*` properties present on the page.

## Command Line Options

| Option | Description |
|--------|-------------|
| `URL` | URL to fetch |
| `--format` | Output format: `markdown`, `txt`, `html`, `json` (default: `markdown`) |
| `--output`, `-o` | Write output to FILE instead of stdout |
| `--quiet`, `-q` | Suppress status messages |
| `--timeout` | HTTP request timeout in seconds (default: 30) |
| `--max-size` | Truncate output to N characters |
| `--favicon` | Extract favicon URLs instead of content |
| `--rss` | Look for RSS/Atom feed in page metadata and fetch it |
| `--og` | Extract Open Graph metadata from the page |
| `--raw` | Include full response data (debugging) |
| `--version` | Show version |

### Content Extraction Options

| Option | Description |
|--------|-------------|
| `--include-comments` | Force inclusion of comments (overrides auto-detection) |
| `--exclude-comments` | Force exclusion of comments (overrides auto-detection) |
| `--page-type` | Manually specify page type: `article`, `forum`, `qa`, `unknown` |

## How It Works

### Web Pages

1. **Fetch** — Uses `cloudscraper` with Chrome headers to avoid blocking
2. **Extract** — Extracts main content with `trafilatura`; falls back to `readability-lxml`
3. **Convert** — Converts cleaned HTML to the requested output format
4. **Format** — Returns the formatted result with title heading

### GitHub URLs

Detected before fetching HTML. Uses the GitHub API to fetch structured data:

- **Repo root** — Fetches README via the GitHub API
- **Blob paths** — Fetches raw file content from `raw.githubusercontent.com`
- **Issues** — Fetches issue body and all comments via the GitHub API
- **Pull requests** — Fetches PR details plus both review and issue comments

### YouTube URLs

Detected before fetching HTML. Uses `youtube-transcript-api` to fetch the video transcript and formats it as readable paragraphs.

### RSS/Atom Feeds

Two modes of operation:

- **Auto-detect** — When the fetched content is an RSS or Atom feed (XML), it is parsed and formatted automatically, bypassing normal HTML extraction
- **`--rss` flag** — Fetches a regular web page, discovers feed URLs from `<link rel="alternate">` tags in the HTML `<head>`, then fetches and formats the first valid feed

Supports RSS 2.0, Atom, and RDF feeds. Output respects the `--format` flag (markdown, txt, html, json).

### Open Graph Metadata

Fetches the page HTML and extracts all `<meta property="og:*">` tags. Relative URLs in fields like `og:image` and `og:url` are resolved to absolute URLs. Output respects the `--format` flag (markdown, txt, html, json).
