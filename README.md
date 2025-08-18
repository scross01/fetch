# Fetch

A command-line tool to fetch web pages and convert them to clean, readable text.

## Features

- Fetches web pages with proper browser headers to avoid blocking
- Extracts main content using readability algorithms
- Converts HTML to clean Markdown text
- Preserves document titles
- Handles various web page structures effectively

## Installation

```bash
uv sync
```

## Usage

### Command Line Interface

The tool can be used directly with Python:

```bash
python main.py <URL>
```

**Examples:**

```bash
# Fetch a web page and display as formatted text
python main.py https://example.com


## How It Works

1. **Fetch**: Uses `cloudscraper` to make HTTP requests with Chrome browser headers to avoid being blocked
2. **Extract**: Uses `readability-lxml` to parse the HTML and extract the main content
3. **Convert**: Uses `html2text` to convert the cleaned HTML to clean Markdown
4. **Format**: Adds the document title as a heading and returns the formatted text

