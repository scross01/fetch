import re
import sys
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi


YOUTUBE_URL_RE = re.compile(
    r"^https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch|shorts)|youtu\.be/)"
)


def _extract_video_id(url):
    parsed = urlparse(url)
    host = parsed.hostname or ""

    if host in ("youtu.be", "www.youtu.be"):
        return parsed.path.lstrip("/")

    if parsed.path == "/watch":
        qs = parse_qs(parsed.query)
        ids = qs.get("v")
        if ids:
            return ids[0]

    if parsed.path.startswith("/shorts/"):
        return parsed.path.split("/")[2]

    return None


def _fetch_transcript(video_id):
    try:
        ytt_api = YouTubeTranscriptApi()

        try:
            segments = ytt_api.fetch(video_id, languages=["en"])
        except Exception:
            try:
                transcript_list = ytt_api.list(video_id)
                transcript = None
                for t in transcript_list:
                    transcript = t
                    break
                if transcript is None:
                    print("No transcript available for this video", file=sys.stderr)
                    return None
                try:
                    segments = transcript.translate("en").fetch()
                except Exception:
                    segments = transcript.fetch()
            except Exception:
                print("No transcript available for this video", file=sys.stderr)
                return None

        return _format_transcript(segments, video_id)
    except Exception as e:
        print(f"Error fetching transcript: {e}", file=sys.stderr)
        return None


def _format_transcript(segments, video_id):
    lines = []
    lines.append(f"# YouTube Transcript")
    lines.append(f"https://youtube.com/watch?v={video_id}")
    lines.append("")

    text_parts = []
    for snippet in segments:
        text = snippet.text.strip()
        if text:
            text_parts.append(text)

    full_text = " ".join(text_parts)
    sentences = re.split(r"(?<=[.!?])\s+", full_text)

    paragraph = []
    for sentence in sentences:
        paragraph.append(sentence)
        if len(paragraph) >= 3:
            lines.append(" ".join(paragraph))
            lines.append("")
            paragraph = []

    if paragraph:
        lines.append(" ".join(paragraph))
        lines.append("")

    return "\n".join(lines)


def handle_youtube_url(url):
    if not YOUTUBE_URL_RE.match(url):
        return None

    video_id = _extract_video_id(url)
    if not video_id:
        return None

    return _fetch_transcript(video_id)
