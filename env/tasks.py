from typing import List
from env.models import FileDiff, Issue, PRMetadata


class Task:
    def __init__(
        self,
        id: str,
        files: List[FileDiff],
        expected: List[Issue],
        decision: str,
        persona: str,
        pr_metadata: PRMetadata,
    ):
        self.id = id
        self.files = files
        self.expected = expected
        self.decision = decision
        self.persona = persona
        self.pr_metadata = pr_metadata


# ═════════════════════════════════════════════════════════════════════════════
# EASY — Off-by-one bugs in utility functions
# ═════════════════════════════════════════════════════════════════════════════
easy_task = Task(
    id="easy",
    persona="You are a pragmatic reviewer focused on correctness and maintainability.",
    pr_metadata=PRMetadata(
        title="refactor: optimize list utility functions",
        description="Refactored list helpers to improve performance. Changed slicing logic and added bounds checking.",
        author_intent="Improve performance of list operations by reducing unnecessary iterations.",
    ),
    files=[
        FileDiff(
            filename="utils/list_helpers.py",
            language="python",
            lines_added=4,
            lines_removed=2,
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
            description="Off-by-one error: `len(items) - n - 1` skips the first of the last n items. Should be `len(items) - n` to correctly slice the last n elements.",
        ),
        Issue(
            file="utils/list_helpers.py",
            line=9,
            type="logic",
            severity="medium",
            description="`range(0, len(items) + 1, size)` causes IndexError on the final iteration when `i` exceeds list bounds. Should be `range(0, len(items), size)` to avoid out-of-bounds access.",
        ),
    ],
    decision="request_changes",
)


# ═════════════════════════════════════════════════════════════════════════════
# MEDIUM — Database performance anti-patterns
# ═════════════════════════════════════════════════════════════════════════════
medium_task = Task(
    id="medium",
    persona="You are a performance-focused reviewer. Prioritize database efficiency and scalability.",
    pr_metadata=PRMetadata(
        title="feat: add user export endpoint and refactor queries",
        description="Added /users/export for bulk data export. Refactored existing endpoints to use consistent query patterns.",
        author_intent="Provide admin functionality for exporting user data and standardize query logic across endpoints.",
    ),
    files=[
        FileDiff(
            filename="api/users.py",
            language="python",
            lines_added=10,
            lines_removed=4,
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
            description="N+1 query anti-pattern: fetches all users into memory then filters in Python. This causes full table scan on every request. Use `User.query.filter_by(active=True).all()` to push filtering to database with indexed WHERE clause.",
        ),
        Issue(
            file="api/users.py",
            line=15,
            type="performance",
            severity="high",
            description="Loads entire users table to find single record by primary key. This is O(n) when it should be O(1). Use `User.query.get_or_404(user_id)` which uses the primary key index for constant-time lookup.",
        ),
        Issue(
            file="api/users.py",
            line=21,
            type="code_quality",
            severity="medium",
            description="`/users/export` endpoint returns unbounded result set with no pagination, rate limiting, or authentication. This creates DoS vector and data exposure risk. Add pagination (LIMIT/OFFSET) and require admin authentication.",
        ),
    ],
    decision="request_changes",
)


# ═════════════════════════════════════════════════════════════════════════════
# HARD — Security vulnerabilities across multiple files
# ═════════════════════════════════════════════════════════════════════════════
hard_task = Task(
    id="hard",
    persona="You are a strict senior security reviewer. Flag every vulnerability, no matter how subtle.",
    pr_metadata=PRMetadata(
        title="refactor: simplify auth module and centralize config",
        description="Moved database connection logic to config module. Simplified JWT token generation by importing secret directly.",
        author_intent="Reduce code duplication by centralizing configuration. Make auth code more readable.",
    ),
    files=[
        FileDiff(
            filename="auth/login.py",
            language="python",
            lines_added=11,
            lines_removed=13,
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
            language="python",
            lines_added=5,
            lines_removed=4,
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
            description="Critical SQL injection vulnerability: user-controlled `username` and `password` are interpolated directly into query string via f-string. Attacker can inject `' OR '1'='1` to bypass authentication. Use parameterized query: `cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))`.",
        ),
        Issue(
            file="auth/config.py",
            line=7,
            type="security",
            severity="high",
            description="Hardcoded JWT secret `supersecret123` used as fallback when `JWT_SECRET` environment variable is unset. This allows trivial token forgery in any deployment where env var is missing. Remove fallback entirely and raise exception if JWT_SECRET is not configured.",
        ),
        Issue(
            file="auth/login.py",
            line=4,
            type="security",
            severity="medium",
            description="`SECRET_KEY` is imported at module load time from config.py. Combined with the hardcoded fallback in config.py, this means tokens will be signed with the known secret `supersecret123` in any environment where `JWT_SECRET` is not explicitly set, creating a silent security failure.",
        ),
    ],
    decision="request_changes",
)


# ═════════════════════════════════════════════════════════════════════════════
# EXPERT — Cross-file data flow vulnerability (requires deep reasoning)
# ═════════════════════════════════════════════════════════════════════════════
expert_task = Task(
    id="expert",
    persona="You are a strict senior security reviewer. Flag every vulnerability, no matter how subtle.",
    pr_metadata=PRMetadata(
        title="feat: add product search and refactor order queries",
        description="Added new product search endpoint. Refactored order queries to use f-strings for better readability. Removed unnecessary type casting in routes.",
        author_intent="Improve code readability by using modern Python f-strings. Add product search feature requested by product team.",
    ),
    files=[
        FileDiff(
            filename="api/routes.py",
            language="python",
            lines_added=6,
            lines_removed=2,
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
            language="python",
            lines_added=13,
            lines_removed=4,
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
            description="SQL injection in `get_orders_for_user`: `user_id` parameter is interpolated directly into query via f-string. Attacker can inject SQL like `1 OR 1=1` to access all orders. Use parameterized query: `cur.execute('SELECT * FROM orders WHERE user_id = ?', (user_id,))`.",
        ),
        Issue(
            file="db/queries.py",
            line=15,
            type="security",
            severity="high",
            description="SQL injection in `get_product_by_name`: `name` parameter is interpolated into query string. Attacker can inject `' OR '1'='1` to dump entire products table or use UNION attacks. Use parameterized query: `cur.execute('SELECT * FROM products WHERE name = ?', (name,))`.",
        ),
        Issue(
            file="api/routes.py",
            line=7,
            type="security",
            severity="medium",
            description="Removed input validation: `user_id` is now passed as raw string from query params without `int()` cast. This allows non-numeric input to reach the SQL layer unchecked. Combined with the SQL injection in db/queries.py line 9, this creates an exploitable attack surface. Restore `int()` cast and add error handling.",
        ),
    ],
    decision="request_changes",
)


TASKS: List[Task] = [easy_task, medium_task, hard_task, expert_task]
