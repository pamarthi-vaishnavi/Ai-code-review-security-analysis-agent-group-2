from utils.code_validation import detect_language_from_filename, validate_submission


def test_detect_language_from_filename():
    assert detect_language_from_filename("Main.java") == "java"
    assert detect_language_from_filename("script.py") == "python"
    assert detect_language_from_filename("readme.md") is None


def test_validate_submission_rejects_empty_code():
    result = validate_submission("   ", "python")
    assert result.is_valid is False


def test_validate_submission_accepts_valid_python():
    result = validate_submission("print('hello')", "python")
    assert result.is_valid is True
    assert result.language == "python"


def test_validate_submission_rejects_invalid_python():
    result = validate_submission("def broken(:\n  pass", "python")
    assert result.is_valid is False
    assert result.error is not None
