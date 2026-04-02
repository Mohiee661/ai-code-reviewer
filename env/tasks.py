from typing import List
from env.models import FileDiff, Issue


class Task:
    def __init__(self, id: str, files: List[FileDiff], expected: List[Issue], decision: str):
        self.id = id
        self.files = files
        self.expected = expected
        self.decision = decision


# ─────────────────────────────────────────────
# EASY: Off-by-one bug in a simple utility function
# ─────────────────────────────────────────────
easy_task = Task(
    id="easy",
    files=[
        FileDiff(
            filename="utils/list_helpers.py",
            diff="""\
--- a/utils/list_helpers.py
+++ b/utils/list_helpers.py
@@ -1,12 +1,14 @@
 def get_last_n_items(items, n):
-    \"\"\"Return the last n items from a list.\"\"\"
-    return items[len(items) - n:]
+    \"\"\"Return the last n items from a list.\"\"\"
+    return items[len(items) - n - 1:]
 
 def chunk_list(items, size):
     \"\"\"Split list into chunks of given size.\"\"\"
     result = []
-    for i in range(0, len(items), size):
+    for i in range(0, len(items) + 1, size):
         result.append(items[i:i + size])
     return result
+
+def first_item(items):
+    return items[0]
"""
        )
    ],
    expected=[
        Issue(
            file="utils/list_helpers.py",
            line=4,
            type="logic",
            severity="medium",
            description="Off-by-one error: `len(items) - n - 1` skips the first of the last n items. Should be `len(items) - n`."
        ),
        Issue(
            file="utils/list_helpers.py",
            line=9,
            type="logic",
            severity="medium",
            description="`range(0, len(items) + 1, size)` causes an out-of-bounds iteration. Should be `range(0, len(items), size)`."
        ),
    ],
    decision="request_changes"
)


# ─────────────────────────────────────────────
# MEDIUM: Inefficient DB query + missing pagination
# ─────────────────────────────────────────────
medium_task = Task(
    id="medium",
    files=[
        FileDiff(
            filename="api/users.py",
            diff="""\
--- a/api/users.py
+++ b/api/users.py
@@ -1,18 +1,24 @@
 from flask import Blueprint, jsonify
 from models import User
 
 users_bp = Blueprint("users", __name__)
 
 @users_bp.route("/users", methods=["GET"])
 def list_users():
-    users = User.query.filter_by(active=True).all()
-    return jsonify([u.to_dict() for u in users])
+    all_users = User.query.all()
+    active = [u for u in all_users if u.active]
+    return jsonify([u.to_dict() for u in active])
 
 @users_bp.route("/users/<int:user_id>", methods=["GET"])
 def get_user(user_id):
-    user = User.query.get_or_404(user_id)
+    users = User.query.all()
+    user = next((u for u in users if u.id == user_id), None)
+    if user is None:
+        return jsonify({"error": "not found"}), 404
     return jsonify(user.to_dict())
+
+@users_bp.route("/users/export", methods=["GET"])
+def export_users():
+    users = User.query.all()
+    return jsonify([u.to_dict() for u in users])
"""
        )
    ],
    expected=[
        Issue(
            file="api/users.py",
            line=9,
            type="performance",
            severity="high",
            description="Fetches all users from DB then filters in Python. Should use `User.query.filter_by(active=True).all()` to push filtering to the database."
        ),
        Issue(
            file="api/users.py",
            line=15,
            type="performance",
            severity="high",
            description="Loads entire users table to find a single record by ID. Should use `User.query.get_or_404(user_id)` for an indexed lookup."
        ),
        Issue(
            file="api/users.py",
            line=21,
            type="code_quality",
            severity="medium",
            description="`/users/export` returns all users with no pagination or auth guard, which is a data exposure and scalability risk."
        ),
    ],
    decision="request_changes"
)


# ─────────────────────────────────────────────
# HARD: SQL injection + secret leak across two files
# ─────────────────────────────────────────────
hard_task = Task(
    id="hard",
    files=[
        FileDiff(
            filename="auth/login.py",
            diff="""\
--- a/auth/login.py
+++ b/auth/login.py
@@ -1,20 +1,26 @@
 import sqlite3
-from auth.config import get_db_connection
+from auth.config import DB_PATH, SECRET_KEY
 
 def authenticate_user(username, password):
-    conn = get_db_connection()
-    cursor = conn.cursor()
-    cursor.execute(
-        "SELECT * FROM users WHERE username = ? AND password = ?",
-        (username, password)
-    )
-    user = cursor.fetchone()
-    conn.close()
-    return user is not None
+    conn = sqlite3.connect(DB_PATH)
+    cursor = conn.cursor()
+    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
+    cursor.execute(query)
+    user = cursor.fetchone()
+    conn.close()
+    return user is not None
 
 def generate_token(user_id):
-    import jwt, os
-    secret = os.environ.get("JWT_SECRET")
-    return jwt.encode({"user_id": user_id}, secret, algorithm="HS256")
+    import jwt
+    return jwt.encode({"user_id": user_id}, SECRET_KEY, algorithm="HS256")
"""
        ),
        FileDiff(
            filename="auth/config.py",
            diff="""\
--- a/auth/config.py
+++ b/auth/config.py
@@ -1,8 +1,10 @@
 import os
 
-def get_db_connection():
-    import sqlite3
-    return sqlite3.connect(os.environ.get("DB_PATH", "app.db"))
+# Database path
+DB_PATH = os.environ.get("DB_PATH", "app.db")
 
-JWT_SECRET = os.environ.get("JWT_SECRET")
+# Hardcoded fallback secret — do not use in production
+SECRET_KEY = os.environ.get("JWT_SECRET", "supersecret123")
"""
        ),
    ],
    expected=[
        Issue(
            file="auth/login.py",
            line=11,
            type="security",
            severity="high",
            description="SQL injection vulnerability: user input is interpolated directly into the query string. Use parameterized queries with `?` placeholders instead."
        ),
        Issue(
            file="auth/config.py",
            line=7,
            type="security",
            severity="high",
            description="Hardcoded fallback secret `supersecret123` will be used if `JWT_SECRET` env var is unset. This exposes JWT signing to trivial forgery. Remove the fallback and raise an error if the secret is missing."
        ),
        Issue(
            file="auth/login.py",
            line=4,
            type="security",
            severity="medium",
            description="`SECRET_KEY` is imported directly from config rather than read from the environment at call time. Combined with the hardcoded fallback in config.py, tokens may be signed with a known secret in any environment where `JWT_SECRET` is not explicitly set."
        ),
    ],
    decision="request_changes"
)


TASKS: List[Task] = [easy_task, medium_task, hard_task]
