import re
import sys
import time
from typing import Any

import cloudscraper

GITHUB_URL_RE = re.compile(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+)(/.*)?$")


class GithubResult(str):
    def __new__(
        cls,
        content: str,
        title: str = "",
        description: str = "",
        links: list[dict[str, str]] | None = None,
        images: list[dict[str, str]] | None = None,
    ):
        obj = super().__new__(cls, content)
        obj.title = title
        obj.description = description
        obj.links = links or []
        obj.images = images or []
        return obj


_LINK_RE = re.compile(r"(?:^|[^!])\[([^\]]+)\]\(([^)]+)\)", re.MULTILINE)
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _extract_links(md: str) -> list[dict[str, str]]:
    if not md:
        return []
    seen = set()
    links = []
    for m in _LINK_RE.finditer(md):
        text, href = m.group(1).strip(), m.group(2).strip()
        if href not in seen:
            seen.add(href)
            links.append({"text": text, "href": href})
    return links


def _extract_images(md: str) -> list[dict[str, str]]:
    if not md:
        return []
    seen = set()
    images = []
    for m in _IMAGE_RE.finditer(md):
        alt, src = m.group(1).strip(), m.group(2).strip()
        if src not in seen:
            seen.add(src)
            images.append({"alt": alt, "src": src})
    return images


def _parse(url: str) -> tuple[str, str, str] | None:
    m = GITHUB_URL_RE.match(url)
    if not m:
        return None
    owner = m.group(1)
    repo = m.group(2).removesuffix(".git")
    path = (m.group(3) or "").strip("/")
    return owner, repo, path


def _api_get(
    scraper: cloudscraper.CloudScraper, url: str, timeout: int
) -> dict[str, Any]:
    response = scraper.get(
        url,
        timeout=timeout,
        headers={"Accept": "application/vnd.github.v3+json"},
    )
    remaining = response.headers.get("X-RateLimit-Remaining", "")
    reset_time = response.headers.get("X-RateLimit-Reset", "")
    if remaining == "0" and reset_time:
        wait_seconds = int(reset_time) - int(time.time()) + 1
        if wait_seconds > 0:
            print(
                f"GitHub API rate limited. Waiting {wait_seconds}s...", file=sys.stderr
            )
            time.sleep(wait_seconds)
            response = scraper.get(
                url,
                timeout=timeout,
                headers={"Accept": "application/vnd.github.v3+json"},
            )
    response.raise_for_status()
    return response.json()


def _fetch_raw(scraper: cloudscraper.CloudScraper, url: str, timeout: int) -> str:
    response = scraper.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def _fetch_readme(
    owner: str,
    repo: str,
    scraper: cloudscraper.CloudScraper,
    timeout: int,
) -> GithubResult | None:
    try:
        data = _api_get(
            scraper,
            f"https://api.github.com/repos/{owner}/{repo}/readme",
            timeout,
        )
        content = _fetch_raw(scraper, data["download_url"], timeout)

        repo_data = _api_get(
            scraper,
            f"https://api.github.com/repos/{owner}/{repo}",
            timeout,
        )
        return GithubResult(
            content,
            title=repo_data.get("name", ""),
            description=repo_data.get("description", "") or "",
            links=_extract_links(content),
            images=_extract_images(content),
        )
    except Exception as e:
        print(f"Error fetching README: {e}", file=sys.stderr)
        return None


def _fetch_raw_file(
    owner: str,
    repo: str,
    ref_path: str,
    scraper: cloudscraper.CloudScraper,
    timeout: int,
) -> str | None:
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref_path}"
    try:
        return _fetch_raw(scraper, raw_url, timeout)
    except Exception as e:
        print(f"Error fetching raw file: {e}", file=sys.stderr)
        return None


def _fetch_issue(
    owner: str,
    repo: str,
    number: int,
    scraper: cloudscraper.CloudScraper,
    timeout: int,
) -> GithubResult | None:
    try:
        issue = _api_get(
            scraper,
            f"https://api.github.com/repos/{owner}/{repo}/issues/{number}",
            timeout,
        )

        comments = []
        if issue.get("comments", 0) > 0:
            comments = _api_get(
                scraper,
                f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments",
                timeout,
            )

        return GithubResult(
            _format_item(issue, comments, kind="Issue"),
            title=issue.get("title", ""),
            description=(issue.get("body") or "")[:500],
            links=_extract_links(issue.get("body") or ""),
            images=_extract_images(issue.get("body") or ""),
        )
    except Exception as e:
        print(f"Error fetching issue: {e}", file=sys.stderr)
        return None


def _fetch_pr(
    owner: str,
    repo: str,
    number: int,
    scraper: cloudscraper.CloudScraper,
    timeout: int,
) -> GithubResult | None:
    try:
        pr = _api_get(
            scraper,
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}",
            timeout,
        )

        comments = []
        review_comments = _api_get(
            scraper,
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}/comments",
            timeout,
        )
        if review_comments:
            comments.extend(review_comments)

        issue_comments = _api_get(
            scraper,
            f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments",
            timeout,
        )
        if issue_comments:
            comments.extend(issue_comments)

        return GithubResult(
            _format_item(pr, comments, kind="PR"),
            title=pr.get("title", ""),
            description=(pr.get("body") or "")[:500],
            links=_extract_links(pr.get("body") or ""),
            images=_extract_images(pr.get("body") or ""),
        )
    except Exception as e:
        if "404" in str(e):
            print(f"PR #{number} not found, fetching as issue...", file=sys.stderr)
            return _fetch_issue(owner, repo, number, scraper, timeout)
        print(f"Error fetching pull request: {e}", file=sys.stderr)
        return None


def _format_item(
    item: dict[str, Any], comments: list[dict[str, Any]], kind: str = "Issue"
) -> str:
    lines = []
    lines.append(f"# {item['title']}")
    lines.append("")

    meta_parts = [
        f"**{kind} #{item['number']}**",
        item["state"],
        f"opened by {item['user']['login']}",
    ]
    lines.append(" | ".join(meta_parts))

    labels = [label["name"] for label in item.get("labels", [])]
    if labels:
        lines.append(f"Labels: {', '.join(labels)}")

    if item.get("milestone"):
        lines.append(f"Milestone: {item['milestone']['title']}")

    if kind == "PR":
        pr = item
        lines.append(
            f"Branch: {pr['head']['ref']} → {pr['base']['ref']}"
            + (f" (+{pr['additions']} -{pr['deletions']})" if "additions" in pr else "")
        )
        if pr.get("merged"):
            lines.append(f"Merged by {pr['merged_by']['login']}")
        elif pr.get("draft"):
            lines.append("Draft")

    lines.append("")

    if item.get("body"):
        lines.append(item["body"])
        lines.append("")

    if comments:
        lines.append("---")
        lines.append(f"## Comments ({len(comments)})")
        lines.append("")
        for comment in comments:
            lines.append(
                f"**@{comment['user']['login']}** ({comment['created_at'][:10]})"
            )
            lines.append("")
            if comment.get("body"):
                lines.append(comment["body"])
            lines.append("")

    return "\n".join(lines)


def handle_github_url(
    url: str, scraper: cloudscraper.CloudScraper, timeout: int = 30
) -> GithubResult | None:
    parsed = _parse(url)
    if not parsed:
        return None

    owner, repo, path = parsed

    issue_match = re.match(r"issues/(\d+)", path)
    if issue_match:
        return _fetch_issue(owner, repo, int(issue_match.group(1)), scraper, timeout)

    pr_match = re.match(r"pulls?/(\d+)", path)
    if pr_match:
        return _fetch_pr(owner, repo, int(pr_match.group(1)), scraper, timeout)

    blob_match = re.match(r"blob/(.+)", path)
    if blob_match:
        return _fetch_raw_file(owner, repo, blob_match.group(1), scraper, timeout)

    if not path:
        return _fetch_readme(owner, repo, scraper, timeout)

    return None
