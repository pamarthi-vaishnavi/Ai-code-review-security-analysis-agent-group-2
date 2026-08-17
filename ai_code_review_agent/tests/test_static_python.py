from analysis import static_python

VULNERABLE_SNIPPET = '''
def get_user(cursor, username):
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchone()
'''

BROKEN_SYNTAX = "def foo(:\n    pass"


def test_validate_syntax_accepts_valid_code():
    ok, err = static_python.validate_syntax("x = 1 + 2\nprint(x)")
    assert ok is True
    assert err is None


def test_validate_syntax_rejects_broken_code():
    ok, err = static_python.validate_syntax(BROKEN_SYNTAX)
    assert ok is False
    assert err is not None


def test_bandit_flags_sql_injection_pattern():
    findings = static_python.run_bandit(VULNERABLE_SNIPPET, "sample.py")
    # bandit's B608 (hardcoded_sql_expressions) should fire on string-built SQL
    assert any("sql" in f.title.lower() or "sql" in f.description.lower() for f in findings)


def test_radon_flags_high_complexity_function():
    branchy = "def f(a):\n" + "\n".join(
        f"    if a == {i}:\n        return {i}" for i in range(20)
    )
    findings = static_python.run_radon_complexity(branchy, "sample.py")
    assert len(findings) >= 1
