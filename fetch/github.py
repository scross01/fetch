import re
import sys

GITHUB_URL_RE = re.compile(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+)(/.*)?$")


def _parse(url):
    m = GITHUB_URL_RE.match(url)
    if not m:
        return None
    owner = m.group(1)
    repo = m.group(2).removesuffix(".git")
    path = (m.group(3) or "").strip("/")
    return owner, repo, path


def _api_get(scraper, url, timeout):
    response = scraper.get(
        url,
        timeout=timeout,
        headers={"Accept": "application/vnd.github.v3+json"},
    )
    response.raise_for_status()
    return response.json()


def _fetch_raw(scraper, url, timeout):
    response = scraper.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def _fetch_readme(owner, repo, scraper, timeout):
    try:
        data = _api_get(
            scraper,
            f"https://api.github.com/repos/{owner}/{repo}/readme",
            timeout,
        )
        return _fetch_raw(scraper, data["download_url"], timeout)
    except Exception as e:
        print(f"Error fetching README: {e}", file=sys.stderr)
        return None


def _fetch_raw_file(owner, repo, ref_path, scraper, timeout):
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref_path}"
    try:
        return _fetch_raw(scraper, raw_url, timeout)
    except Exception as e:
        print(f"Error fetching raw file: {e}", file=sys.stderr)
        return None


def _fetch_issue(owner, repo, number, scraper, timeout):
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

        return _format_item(issue, comments, kind="Issue")
    except Exception as e:
        print(f"Error fetching issue: {e}", file=sys.stderr)
        return None


def _fetch_pr(owner, repo, number, scraper, timeout):
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

        return _format_item(pr, comments, kind="PR")
    except Exception as e:
        print(f"Error fetching pull request: {e}", file=sys.stderr)
        return None


def _format_item(item, comments, kind="Issue"):
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


def handle_github_url(url, scraper, timeout=30):
    parsed = _parse(url)
    if not parsed:
        return None

    owner, repo, path = parsed

    issue_match = re.match(r"issues/(\d+)", path)
    if issue_match:
        return _fetch_issue(owner, repo, int(issue_match.group(1)), scraper, timeout)

    pr_match = re.match(r"pull/(\d+)", path)
    if pr_match:
        return _fetch_pr(owner, repo, int(pr_match.group(1)), scraper, timeout)

    blob_match = re.match(r"blob/(.+)", path)
    if blob_match:
        return _fetch_raw_file(owner, repo, blob_match.group(1), scraper, timeout)

    if not path:
        return _fetch_readme(owner, repo, scraper, timeout)

    return None
