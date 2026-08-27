"""File type rules shared by clipboard capture and settings validation."""

import re
from pathlib import Path


# These suffixes are handled as image history when copied from Explorer or
# another program as local files. Qt decodes the image before it is stored.
COMMON_IMAGE_EXTENSIONS = frozenset({
    ".apng", ".avif", ".bmp", ".dib", ".gif", ".heic", ".heif", ".icns",
    ".ico", ".jfif", ".jpe", ".jpeg", ".jpg", ".pbm", ".pgm", ".png",
    ".pnm", ".ppm", ".svg", ".svgz", ".tga", ".tif", ".tiff", ".webp",
    ".xbm", ".xpm",
})
DEFAULT_FILE_CACHE_EXTENSIONS = "*"
_EXTENSION_PATTERN = re.compile(r"[a-z0-9][a-z0-9._+-]{0,63}")


def normalize_file_cache_extensions(value: str) -> str:
    """Return the canonical cache-extension setting or raise ValueError.

    An asterisk means every non-image file. An empty value intentionally
    disables file caching. Multi-part suffixes such as ``tar.gz`` are allowed.
    """
    parts = [part.strip().lower() for part in re.split(r"[\s,;，；]+", str(value)) if part.strip()]
    if not parts:
        return ""
    if "*" in parts:
        if len(parts) != 1:
            raise ValueError("“*”不能与其他文件格式同时使用")
        return DEFAULT_FILE_CACHE_EXTENSIONS
    normalized = []
    for part in parts:
        extension = part.lstrip(".")
        if not _EXTENSION_PATTERN.fullmatch(extension):
            raise ValueError("文件格式应为扩展名，例如 .pdf、docx 或 .tar.gz")
        formatted = "." + extension
        if formatted not in normalized:
            normalized.append(formatted)
    return ", ".join(normalized)


def is_common_image_file(path: Path) -> bool:
    return Path(path).suffix.lower() in COMMON_IMAGE_EXTENSIONS


def file_matches_cache_extensions(path: Path, extensions: str) -> bool:
    """Whether a non-image local file matches the configured cache formats."""
    normalized = normalize_file_cache_extensions(extensions)
    if normalized == DEFAULT_FILE_CACHE_EXTENSIONS:
        return True
    name = Path(path).name.lower()
    return any(name.endswith(extension) for extension in normalized.split(", ") if extension)
