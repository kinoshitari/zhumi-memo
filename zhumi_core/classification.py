"""Clipboard text classification without GUI or operating-system dependencies."""

import json
import re
from urllib.parse import urlparse


CATEGORIES = ("文本", "URL", "代码", "JSON", "路径", "Prompt")

_WINDOWS_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\)[^\r\n]+$")
_CODE_MARKERS = re.compile(
    r"(^|\n)\s*(?:def |class |import |from .+ import |function |const |let |var |"
    r"SELECT |INSERT |UPDATE |DELETE |CREATE TABLE|#include|public class|using namespace)",
    re.IGNORECASE,
)


def classify_content(content: str) -> str:
    stripped = content.strip()
    if not stripped:
        return "文本"
    if stripped[0:1] in ("{", "["):
        try:
            json.loads(stripped)
            return "JSON"
        except (ValueError, TypeError):
            pass
    parsed = urlparse(stripped)
    if parsed.scheme.lower() in ("http", "https") and parsed.netloc and "\n" not in stripped:
        return "URL"
    if _WINDOWS_PATH.match(stripped.strip('"\'')):
        return "路径"
    if _CODE_MARKERS.search(stripped) or (
        "\n" in stripped and any(marker in stripped for marker in ("{", "}", ";", "=>", "</"))
    ):
        return "代码"
    lowered = stripped.lower()
    prefixes = (
        "you are ", "act as ", "system:", "prompt:", "请你", "请帮我", "帮我", "任务：", "角色："
    )
    if len(stripped) >= 12 and lowered.startswith(prefixes):
        return "Prompt"
    return "文本"
