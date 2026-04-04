from typing import List
from env.models import FileDiff, Issue


class Task:
    def __init__(
        self,
        id: str,
        files: List[FileDiff],
        expected: List[Issue],
        decision: str,
        persona: str,
    ):
        self.id = id
        self.files = files
        self.expected = expected
        self.decision = decision
        self.persona = persona


# ─────────────────────────────────────────────────────────────────────────────
# EASY — off-by-one bugs in a utility function
# Persona: pragmatic maintainability reviewer
# ─────────────────────────────────────────────────────────────────────────────
easy_task = Task(
    id="easy",
    persona="You are a pragmatic reviewer focused on correctness and maintainability.",
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
            description="Off-by-one: `len(items) - n - 1` skips one item. Should be `len(items) - n`.",
        ),
        Issue(
            file="utils/list_helpers.py",
            line=9,
            type="logic",
            severity="medium",
            description="`range(0, len(items) + 1, size)` causes out-of-bounds iteration. Should be `range(0, len(items), size)`.",
        ),
    ],
    decision="request_changes",
)


# ─────────────────────────────────────────────────────────────────────────────
# MEDIUM — full-table-scan queries + unguarded export endpoint
# Persona: performance-focused reviewer
# ─────────────────────────────────────────────────────────────────────────────
medium_task = Task(
    id="medium",
    persona="You are a performance-focused reviewer. Prioritise database efficiency and scalability.",
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
            description="Fetches all users then filters in Python. Use `User.query.filter_by(active=True).all()` to push filtering to the DB.",
        ),
        Issue(
            file="api/users.py",
            line=15,
            type="performance",
            severity="high",
            description="Loads entire users table to find one record. Use `User.query.get_or_404(user_id)` for an indexed lookup.",
        ),
        Issue(
            file="api/users.py",
            line=21,
            type="code_quality",
            severity="medium",
            description="`/users/export` returns all users with no pagination or auth guard — data exposure and scalability risk.",
        ),
    ],
    decision="request_changes",
)


# ─────────────────────────────────────────────────────────────────────────────
# HARD — SQL injection + hardcoded JWT secret across two files
# Persona: strict senior security reviewer
# ─────────────────────────────────────────────────────────────────────────────
hard_task = Task(
    id="hard",
    persona="You are a strict senior security reviewer. Flag every vulnerability, no matter how subtle.",
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
            description="SQL injection: user input interpolated directly into query. Use parameterized queries with `?` placeholders.",
        ),
        Issue(
            file="auth/config.py",
            line=7,
            type="security",
            severity="high",
            description="Hardcoded fallback secret `supersecret123` used when `JWT_SECRET` env var is unset — trivial JWT forgery. Remove fallback and raise on missing secret.",
        ),
        Issue(
            file="auth/login.py",
            line=4,
            type="security",
            severity="medium",
            description="`SECRET_KEY` imported from config at module load time. Combined with the hardcoded fallback, tokens may be signed with a known secret in any env where `JWT_SECRET` is not set.",
        ),
    ],
    decision="request_changes",
)


# ─────────────────────────────────────────────────────────────────────────────
# EXPERT — missing validation in API layer exploited by unsafe DB query
# Persona: strict senior security reviewer
# Requires cross-file reasoning: unvalidated input in routes.py flows into
# a raw SQL call in db/queries.py
# ─────────────────────────────────────────────────────────────────────────────
expert_task = Task(
    id="expert",
    persona="You are a strict senior security reviewer. Flag every vulnerability, no matter how subtle.",
    files=[
        FileDiff(
            filename="api/routes.py",
            diff="""\
--- a/api/routes.py
+++ b/api/routes.py
@@ -1,14 +1,16 @@
 from flask import Blueprint, request, jsonify
-from db.queries import get_orders_for_user
+from db.queries import get_orders_for_user, get_product_by_name
 
 api_bp = Blueprint("api", __name__)
 
 @api_bp.route("/orders", methods=["GET"])
 def orders():
-    user_id = int(request.args.get("user_id", 0))
+    user_id = request.args.get("user_id", "0")
     return jsonify(get_orders_for_user(user_id))
 
+@api_bp.route("/products/search", methods=["GET"])
+def search_product():
+    name = request.args.get("name", "")
+    return jsonify(get_product_by_name(name))
"""
        ),
        FileDiff(
            filename="db/queries.py",
            diff="""\
--- a/db/queries.py
+++ b/db/queries.py
@@ -1,12 +1,20 @@
 import sqlite3
 
 DB = "app.db"
 
 def get_orders_for_user(user_id):
-    conn = sqlite3.connect(DB)
-    cur = conn.cursor()
-    cur.execute("SELECT * FROM orders WHERE user_id = ?", (user_id,))
-    return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
+    conn = sqlite3.connect(DB)
+    cur = conn.cursor()
+    cur.execute(f"SELECT * FROM orders WHERE user_id = {user_id}")
+    return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
+
+def get_product_by_name(name):
+    conn = sqlite3.connect(DB)
+    cur = conn.cursor()
+    cur.execute(f"SELECT * FROM products WHERE name = '{name}'")
+    rows = cur.fetchall()
+    if not rows:
+        return []
+    return [dict(zip([c[0] for c in cur.description], row)) for row in rows]
"""
        ),
    ],
    expected=[
        Issue(
            file="db/queries.py",
            line=9,
            type="security",
            severity="high",
            description="SQL injection in `get_orders_for_user`: `user_id` is interpolated directly. Use parameterized query `(user_id,)`.",
        ),
        Issue(
            file="db/queries.py",
            line=15,
            type="security",
            severity="high",
            description="SQL injection in `get_product_by_name`: `name` is interpolated into the query string. Use `WHERE name = ?` with `(name,)`.",
        ),
        Issue(
            file="api/routes.py",
            line=7,
            type="security",
            severity="medium",
            description="`user_id` is passed as a raw string from query params without type validation. The missing `int()` cast means non-numeric input reaches the SQL layer unchecked.",
        ),
    ],
    decision="request_changes",
)


TASKS: List[Task] = [easy_task, medium_task, hard_task, expert_task]
