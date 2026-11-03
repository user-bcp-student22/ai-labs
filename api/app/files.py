import re
from pathlib import PurePosixPath, PureWindowsPath

ALLOWED_EXTENSIONS = frozenset({".txt", ".md", ".pdf"})
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_FILE_NAME_LENGTH = 120
RESERVED_WINDOWS_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", *(f"COM{number}" for number in range(1, 10)), *(f"LPT{number}" for number in range(1, 10))}
)
UNSAFE_NAME_CHARACTERS = re.compile(r"[^A-Za-z0-9._-]")


def safe_file_name(raw_name: str) -> str:
    base_name = PureWindowsPath(PurePosixPath(raw_name).name).name
    return UNSAFE_NAME_CHARACTERS.sub("_", base_name).lstrip(".")


def has_allowed_extension(file_name: str) -> bool:
    return PurePosixPath(file_name).suffix.lower() in ALLOWED_EXTENSIONS


def is_acceptable_name(file_name: str) -> bool:
    stem = PurePosixPath(file_name).stem.upper()
    return (
        bool(file_name)
        and len(file_name) <= MAX_FILE_NAME_LENGTH
        and has_allowed_extension(file_name)
        and stem not in RESERVED_WINDOWS_NAMES
    )
