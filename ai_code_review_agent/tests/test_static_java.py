from analysis import static_java

VALID_JAVA = """
public class Sample {
    public int add(int a, int b) {
        return a + b;
    }
}
"""

BROKEN_JAVA = "public class Sample { public int add(int a, int b) { return a + b; "  # missing closing braces


def test_validate_syntax_accepts_valid_java():
    ok, err = static_java.validate_syntax(VALID_JAVA)
    assert ok is True
    assert err is None


def test_validate_syntax_rejects_unbalanced_braces():
    ok, err = static_java.validate_syntax(BROKEN_JAVA)
    assert ok is False
    assert err is not None


def test_fallback_brace_check_directly():
    ok, err = static_java._fallback_brace_check("{ ( ) }")
    assert ok is True
    ok2, err2 = static_java._fallback_brace_check("{ ( } )")
    assert ok2 is False
