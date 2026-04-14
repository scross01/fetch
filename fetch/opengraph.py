import json
import sys
import urllib.parse

from bs4 import BeautifulSoup

_URL_FIELDS = {"og:image", "og:image:url", "og:url", "og:audio", "og:video"}


def extract_og_metadata(html_content, base_url, output_format="markdown"):
    soup = BeautifulSoup(html_content, "html.parser")

    og_data = {}
    for meta in soup.find_all("meta", attrs={"property": True}):
        prop = meta.get("property", "")
        if prop.startswith("og:"):
            content = meta.get("content", "").strip()
            if content:
                key = prop
                if key in _URL_FIELDS:
                    content = urllib.parse.urljoin(base_url, content)
                if key in og_data:
                    existing = og_data[key]
                    if isinstance(existing, list):
                        existing.append(content)
                    else:
                        og_data[key] = [existing, content]
                else:
                    og_data[key] = content

    if not og_data:
        print("No Open Graph metadata found", file=sys.stderr)
        return None

    return _format_og(og_data, output_format)


def _format_og(data, output_format="markdown"):
    formatters = {
        "markdown": _format_og_markdown,
        "txt": _format_og_text,
        "html": _format_og_html,
        "json": _format_og_json,
    }
    formatter = formatters.get(output_format, _format_og_markdown)
    return formatter(data)


def _value_str(val):
    if isinstance(val, list):
        return val[0]
    return val


def _format_og_markdown(data):
    lines = ["# Open Graph Metadata", ""]

    title = data.get("og:title")
    if title:
        lines.append(f"**Title:** {_value_str(title)}")
        lines.append("")

    description = data.get("og:description")
    if description:
        lines.append(f"**Description:** {_value_str(description)}")
        lines.append("")

    og_type = data.get("og:type")
    if og_type:
        lines.append(f"**Type:** {_value_str(og_type)}")
        lines.append("")

    image = data.get("og:image") or data.get("og:image:url")
    if image:
        if isinstance(image, list):
            lines.append("**Images:**")
            for img in image:
                lines.append(f"  ![]({img})")
        else:
            lines.append(f"**Image:**")
            lines.append(f"  ![]({image})")
        lines.append("")

    url = data.get("og:url")
    if url:
        lines.append(f"**URL:** {_value_str(url)}")
        lines.append("")

    site_name = data.get("og:site_name")
    if site_name:
        lines.append(f"**Site:** {_value_str(site_name)}")
        lines.append("")

    extra_keys = [
        k
        for k in data
        if k
        not in (
            "og:title",
            "og:description",
            "og:type",
            "og:image",
            "og:image:url",
            "og:url",
            "og:site_name",
        )
    ]
    if extra_keys:
        lines.append("---")
        lines.append("")
        for key in sorted(extra_keys):
            val = data[key]
            nice_key = key.replace("og:", "")
            if isinstance(val, list):
                for v in val:
                    lines.append(f"**{nice_key}:** {v}")
            else:
                lines.append(f"**{nice_key}:** {val}")
        lines.append("")

    return "\n".join(lines)


def _format_og_text(data):
    lines = []
    for key, val in sorted(data.items()):
        nice_key = key.replace("og:", "")
        if isinstance(val, list):
            for v in val:
                lines.append(f"{nice_key}: {v}")
        else:
            lines.append(f"{nice_key}: {val}")
    return "\n".join(lines)


def _format_og_html(data):
    parts = ["<h1>Open Graph Metadata</h1>", "<dl>"]
    for key, val in sorted(data.items()):
        nice_key = key.replace("og:", "")
        if isinstance(val, list):
            for v in val:
                if key in _URL_FIELDS or (
                    key in ("og:image", "og:image:url") and v.startswith("http")
                ):
                    parts.append(f'<dt>{nice_key}</dt><dd><a href="{v}">{v}</a></dd>')
                else:
                    parts.append(f"<dt>{nice_key}</dt><dd>{v}</dd>")
        else:
            if key in _URL_FIELDS or (
                key in ("og:image", "og:image:url") and val.startswith("http")
            ):
                parts.append(f'<dt>{nice_key}</dt><dd><a href="{val}">{val}</a></dd>')
            else:
                parts.append(f"<dt>{nice_key}</dt><dd>{val}</dd>")
    parts.append("</dl>")
    return "\n".join(parts)


def _format_og_json(data):
    serializable = {}
    for key, val in data.items():
        serializable[key] = val
    return json.dumps(serializable, ensure_ascii=False, indent=2)
