# Fetch

A command-line tool to fetch web pages and convert them to clean, readable text.

## Features

- Fetches web pages with proper browser headers to avoid blocking
- Extracts main content using readability algorithms
- Converts HTML to clean Markdown text
- Preserves document titles
- Handles various web page structures effectively
- Supports raw output mode for debugging

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

### Command Line Interface

After installation, you can use the `fetch` command directly:

```bash
fetch <URL>
```

**Examples:**

```bash
# Fetch a web page and display as formatted text
fetch https://example.com

# Fetch with raw output for debugging
fetch --raw https://example.com

# Show version
fetch --version
```

## How It Works

1. **Fetch**: Uses `cloudscraper` to make HTTP requests with Chrome browser headers to avoid being blocked
2. **Extract**: Uses `readability-lxml` to parse the HTML and extract the main content
3. **Convert**: Uses `html2text` to convert the cleaned HTML to clean Markdown
4. **Format**: Adds the document title as a heading and returns the formatted text
