"""
Code Submission Module (Milestone 1, item 3): validates pasted or uploaded
Python/Java source before it is ever sent to an agent, and detects language
from the upload's file extension (or lets the user pick it explicitly when
pasting).
"""
from __future__ import annotations

from dataclasses import dataclass

from analysis import static_java, static_python
from config import settings

EXTENSION_LANGUAGE_MAP = {
    ".py": "python",
    ".java": "java",
}


@dataclass
class ValidationResult:
    is_valid: bool
    language: str
    error: str | None = None
    char_count: int = 0


def detect_language_from_filename(filename: str) -> str | None:
    for ext, lang in EXTENSION_LANGUAGE_MAP.items():
        if filename.lower().endswith(ext):
            return lang
    return None


def validate_submission(code: str, language: str) -> ValidationResult:
    code = code or ""
    if not code.strip():
        return ValidationResult(False, language, "No source code was provided.", 0)

    if len(code) > settings.max_code_chars:
        return ValidationResult(
            False,
            language,
            f"Submission exceeds the {settings.max_code_chars:,} character limit "
            f"({len(code):,} chars). Split the file or raise MAX_CODE_CHARS in .env.",
            len(code),
        )

    if language == "python":
        ok, err = static_python.validate_syntax(code)
    elif language == "java":
        ok, err = static_java.validate_syntax(code)
    else:
        return ValidationResult(False, language, f"Unsupported language: {language}", len(code))

    return ValidationResult(ok, language, err, len(code))
