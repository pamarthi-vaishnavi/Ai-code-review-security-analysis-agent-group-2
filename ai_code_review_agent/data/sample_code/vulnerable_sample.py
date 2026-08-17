"""
Intentionally vulnerable/low-quality sample code used to validate agent
detection accuracy (Milestone 2, item 4). Do NOT use any of these patterns
in real code -- each one is a planted issue the agents should catch.
"""
import os
import pickle
import sqlite3

API_KEY = "sk-live-51H8xJ2eZvKYlo2CabcDEF123456"  # hardcoded secret (CWE-798)


def get_user_by_username(cursor, username):
    # SQL Injection via string concatenation (CWE-89, OWASP A03:2021)
    query = "SELECT id, username, email FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchone()


def run_admin_command(user_input):
    # Command injection via os.system (CWE-78)
    os.system("ping " + user_input)


def load_config(path):
    # Insecure deserialization (CWE-502)
    with open(path, "rb") as f:
        return pickle.load(f)


def add_to_cart(item, cart=[]):  # noqa: mutable default argument (code smell)
    cart.append(item)
    return cart


def compute_discount(price, tier, is_vip, has_coupon, region, is_weekend, is_holiday):
    # High cyclomatic complexity / long branching function (code smell)
    discount = 0
    if tier == "gold":
        discount += 10
    elif tier == "silver":
        discount += 5
    if is_vip:
        discount += 5
    if has_coupon:
        discount += 3
    if region == "EU":
        discount += 1
    elif region == "US":
        discount += 2
    if is_weekend:
        discount += 1
    if is_holiday:
        discount += 2
    if discount > 20:
        discount = 20
    return price * (1 - discount / 100)


def check_access(user, resource):
    # Broken access control: no ownership/role check (OWASP A01:2021)
    return resource.get(user["id"], None) is not None or True


class ReportGenerator:
    def __init__(self):
        self.data = None

    def load(self, connection_string):
        self.conn = sqlite3.connect(connection_string)

    def generate(self):
        # Bare except swallows all errors, including security-relevant ones
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT * FROM reports")
            self.data = cur.fetchall()
        except:
            pass
        return self.data
