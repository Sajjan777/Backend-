"""
Library Management System - raw Python HTTP server
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re
import uuid
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# "Database" - just in-memory Python dicts, keyed by ID.
# This is the ONLY part of this file that will be replaced later by
# PostgreSQL + the Django ORM. Everything else (routing, status codes,
# JSON shaping) carries forward conceptually into DRF views.
# ---------------------------------------------------------------------------

AUTHORS = {
    1: {"id": 1, "name": "Robert C. Martin", "bio": "Author of Clean Code", "nationality": "American"},
}

BOOKS = {
    1: {
        "id": 1,
        "title": "Clean Code",
        "author_id": 1,
        "category": "Software Engineering",
        "total_copies": 3,
        "available_copies": 3,
    },
}

USERS = {
    1: {
        "id": 1,
        "name": "Sajjan Raj Malla",
        "email": "sajjan@example.com",
        "password": "hashed_password_placeholder",  # never returned in responses
        "membership_date": "2026-01-01",
        "role": "member",
    },
}

BORROWINGS = {}

_next_id = {"authors": 2, "books": 2, "users": 2, "borrowings": 1}


def next_id(resource):
    """Simple auto-increment ID generator, mimicking what a real DB does."""
    val = _next_id[resource]
    _next_id[resource] += 1
    return val


# ---------------------------------------------------------------------------
# Small helpers - the kind of plumbing Django/DRF normally hides from you.
# ---------------------------------------------------------------------------

def author_public(author):
    """Attach a computed field (book_count) - never stored directly."""
    book_count = sum(1 for b in BOOKS.values() if b["author_id"] == author["id"])
    return {**author, "book_count": book_count}


def user_public(user):
    """Strip the password before this user is ever sent back to a client."""
    return {k: v for k, v in user.items() if k != "password"}


def book_public(book):
    author = AUTHORS.get(book["author_id"])
    return {
        "id": book["id"],
        "title": book["title"],
        "author": author["name"] if author else None,
        "category": book["category"],
        "available_copies": book["available_copies"],
    }


def borrowing_public(borrowing):
    book = BOOKS.get(borrowing["book_id"])
    return {
        "id": borrowing["id"],
        "book": {"id": book["id"], "title": book["title"]} if book else None,
        "user_id": borrowing["user_id"],
        "borrowed_at": borrowing["borrowed_at"],
        "due_date": borrowing["due_date"],
        "returned_at": borrowing["returned_at"],
        "status": borrowing["status"],
    }


# ---------------------------------------------------------------------------
# The request handler - this is the "routing layer".
# In Django, urls.py + the URL resolver does this work for you.
# Here, we do it by hand with regex so you can see what's really happening.
# ---------------------------------------------------------------------------

class LibraryHandler(BaseHTTPRequestHandler):

    # ---- generic response helpers -----------------------------------

    def send_json(self, status_code, payload):
        body = json.dumps(payload).encode()
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status_code, error, message, details=None):
        payload = {"error": error, "message": message}
        if details:
            payload["details"] = details
        self.send_json(status_code, payload)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        print(f'sajjan')
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode())
        except json.JSONDecodeError:
            return None  # signals "malformed JSON" to the caller

    def log_message(self, fmt, *args):
        # Quieter default logging; print our own structured line instead.
        print(f"{self.command} {self.path} -> handled")

    # ---- method dispatch ------------------------------------------

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_PUT(self):
        self.route("PUT")

    def do_PATCH(self):
        self.route("PATCH")

    def do_DELETE(self):
        self.route("DELETE")

    # ---- the router --------------------------------------------------
    # Real path matching using regex, so unknown paths correctly 404
    # instead of silently succeeding (the bug from Module 1.2).

    ROUTES = [
        (r"^/api/v1/authors/?$", "authors_collection"),
        (r"^/api/v1/authors/(?P<id>\d+)/?$", "authors_detail"),
        (r"^/api/v1/authors/(?P<id>\d+)/books/?$", "authors_books"),

        (r"^/api/v1/books/?$", "books_collection"),
        (r"^/api/v1/books/(?P<id>\d+)/?$", "books_detail"),

        (r"^/api/v1/users/me/?$", "users_me"),
        (r"^/api/v1/users/?$", "users_collection"),
        (r"^/api/v1/users/(?P<id>\d+)/?$", "users_detail"),

        (r"^/api/v1/borrowings/?$", "borrowings_collection"),
        (r"^/api/v1/borrowings/(?P<id>\d+)/?$", "borrowings_detail"),
        (r"^/api/v1/borrowings/(?P<id>\d+)/return/?$", "borrowings_return"),
    ]

    def route(self, method):
        path_only = self.path.split("?", 1)[0]

        for pattern, handler_name in self.ROUTES:
            match = re.match(pattern, path_only)
            if match:
                handler = getattr(self, f"h_{handler_name}", None)
                if handler is None:
                    self.send_error_json(500, "server_error", "Handler not implemented")
                    return
                handler(method, **match.groupdict())
                return

        # No route matched at all -> real 404, unlike Module 1.2's server
        self.send_error_json(404, "not_found", f"No resource matches {path_only}")

    # ---- AUTHORS -------------------------------------------------------

    def h_authors_collection(self, method):
        if method == "GET":
            self.send_json(200, [author_public(a) for a in AUTHORS.values()])
        elif method == "POST":
            data = self.read_json_body()
            if data is None:
                return self.send_error_json(400, "invalid_json", "Body is not valid JSON")
            missing = [f for f in ("name",) if not data.get(f)]
            if missing:
                return self.send_error_json(400, "validation_error", "Missing fields",
                                             {f: ["This field is required."] for f in missing})
            aid = next_id("authors")
            AUTHORS[aid] = {
                "id": aid,
                "name": data["name"],
                "bio": data.get("bio", ""),
                "nationality": data.get("nationality", ""),
            }
            self.send_json(201, author_public(AUTHORS[aid]))
        else:
            self.send_error_json(405, "method_not_allowed", f"{method} not allowed on this resource")

    def h_authors_detail(self, method, id):
        aid = int(id)
        author = AUTHORS.get(aid)
        if not author and method != "PUT":
            return self.send_error_json(404, "not_found", "Author not found")

        if method == "GET":
            self.send_json(200, author_public(author))

        elif method == "PATCH":
            data = self.read_json_body()
            if data is None:
                return self.send_error_json(400, "invalid_json", "Body is not valid JSON")
            author.update({k: v for k, v in data.items() if k in ("name", "bio", "nationality")})
            self.send_json(200, author_public(author))

        elif method == "PUT":
            data = self.read_json_body()
            required = ("name", "bio", "nationality")
            missing = [f for f in required if f not in data]
            if missing:
                return self.send_error_json(
                    400, "validation_error",
                    "PUT requires the full resource representation",
                    {f: ["This field is required for PUT."] for f in missing},
                )
            AUTHORS[aid] = {"id": aid, **{f: data[f] for f in required}}
            self.send_json(200, author_public(AUTHORS[aid]))

        elif method == "DELETE":
            del AUTHORS[aid]
            self.send_response(204)
            self.end_headers()

        else:
            self.send_error_json(405, "method_not_allowed", f"{method} not allowed on this resource")

    def h_authors_books(self, method, id):
        aid = int(id)
        if aid not in AUTHORS:
            return self.send_error_json(404, "not_found", "Author not found")
        if method != "GET":
            return self.send_error_json(405, "method_not_allowed", f"{method} not allowed on this resource")
        books = [book_public(b) for b in BOOKS.values() if b["author_id"] == aid]
        self.send_json(200, books)

    # ---- BOOKS -----------------------------------------------------------

    def h_books_collection(self, method):
        if method == "GET":
            self.send_json(200, [book_public(b) for b in BOOKS.values()])
        elif method == "POST":
            data = self.read_json_body()
            if data is None:
                return self.send_error_json(400, "invalid_json", "Body is not valid JSON")
            required = ("title", "author_id", "category", "total_copies")
            missing = [f for f in required if f not in data]
            if missing:
                return self.send_error_json(400, "validation_error", "Missing fields",
                                             {f: ["This field is required."] for f in missing})
            if data["author_id"] not in AUTHORS:
                return self.send_error_json(400, "validation_error", "Invalid author_id",
                                             {"author_id": ["No author with this ID exists."]})
            bid = next_id("books")
            BOOKS[bid] = {
                "id": bid,
                "title": data["title"],
                "author_id": data["author_id"],
                "category": data["category"],
                "total_copies": data["total_copies"],
                "available_copies": data["total_copies"],
            }
            self.send_json(201, book_public(BOOKS[bid]))
        else:
            self.send_error_json(405, "method_not_allowed", f"{method} not allowed on this resource")

    def h_books_detail(self, method, id):
        bid = int(id)
        book = BOOKS.get(bid)
        if not book and method != "PUT":
            return self.send_error_json(404, "not_found", "Book not found")

        if method == "GET":
            self.send_json(200, book_public(book))

        elif method == "PATCH":
            data = self.read_json_body()
            if data is None:
                return self.send_error_json(400, "invalid_json", "Body is not valid JSON")
            for field in ("title", "category", "total_copies"):
                if field in data:
                    book[field] = data[field]
            self.send_json(200, book_public(book))

        elif method == "PUT":
            data = self.read_json_body()
            required = ("title", "author_id", "category", "total_copies")
            missing = [f for f in required if f not in data]
            if missing:
                return self.send_error_json(
                    400, "validation_error",
                    "PUT requires the full resource representation",
                    {f: ["This field is required for PUT."] for f in missing},
                )
            BOOKS[bid] = {
                "id": bid,
                "title": data["title"],
                "author_id": data["author_id"],
                "category": data["category"],
                "total_copies": data["total_copies"],
                "available_copies": data["total_copies"],
            }
            self.send_json(200, book_public(BOOKS[bid]))

        elif method == "DELETE":
            del BOOKS[bid]
            self.send_response(204)
            self.end_headers()

        else:
            self.send_error_json(405, "method_not_allowed", f"{method} not allowed on this resource")

    # ---- USERS -----------------------------------------------------------

    def h_users_me(self, method):
        # No real auth yet (that's Module 8.1 / JWT) - hardcode "current user" as user 1.
        if method != "GET":
            return self.send_error_json(405, "method_not_allowed", f"{method} not allowed on this resource")
        user = USERS.get(1)
        if not user:
            return self.send_error_json(401, "unauthorized", "No authenticated user")
        self.send_json(200, user_public(user))

    def h_users_collection(self, method):
        if method == "GET":
            self.send_json(200, [user_public(u) for u in USERS.values()])
        elif method == "POST":
            data = self.read_json_body()
            if data is None:
                return self.send_error_json(400, "invalid_json", "Body is not valid JSON")
            required = ("name", "email", "password")
            missing = [f for f in required if not data.get(f)]
            if missing:
                return self.send_error_json(400, "validation_error", "Missing fields",
                                             {f: ["This field is required."] for f in missing})
            if any(u["email"] == data["email"] for u in USERS.values()):
                return self.send_error_json(400, "validation_error", "Email already registered",
                                             {"email": ["A user with this email already exists."]})
            uid = next_id("users")
            USERS[uid] = {
                "id": uid,
                "name": data["name"],
                "email": data["email"],
                "password": f"hashed_{data['password']}",  # pretend-hash; real hashing comes in Module 5.4
                "membership_date": datetime.utcnow().date().isoformat(),
                "role": "member",
            }
            self.send_json(201, user_public(USERS[uid]))
        else:
            self.send_error_json(405, "method_not_allowed", f"{method} not allowed on this resource")

    def h_users_detail(self, method, id):
        uid = int(id)
        user = USERS.get(uid)
        if not user and method != "PUT":
            return self.send_error_json(404, "not_found", "User not found")

        if method == "GET":
            self.send_json(200, user_public(user))

        elif method == "PATCH":
            data = self.read_json_body()
            if data is None:
                return self.send_error_json(400, "invalid_json", "Body is not valid JSON")
            for field in ("name", "email", "role"):
                if field in data:
                    user[field] = data[field]
            self.send_json(200, user_public(user))

        elif method == "PUT":
            data = self.read_json_body()
            required = ("name", "email", "role")
            missing = [f for f in required if f not in data]
            if missing:
                return self.send_error_json(
                    400, "validation_error",
                    "PUT requires the full resource representation (password excluded intentionally)",
                    {f: ["This field is required for PUT."] for f in missing},
                )
            existing_password = user["password"] if user else "hashed_placeholder"
            USERS[uid] = {
                "id": uid,
                "name": data["name"],
                "email": data["email"],
                "role": data["role"],
                "password": existing_password,
                "membership_date": user["membership_date"] if user else datetime.utcnow().date().isoformat(),
            }
            self.send_json(200, user_public(USERS[uid]))

        elif method == "DELETE":
            del USERS[uid]
            self.send_response(204)
            self.end_headers()

        else:
            self.send_error_json(405, "method_not_allowed", f"{method} not allowed on this resource")

    # ---- BORROWINGS --------------------------------------------------

    def h_borrowings_collection(self, method):
        if method == "GET":
            self.send_json(200, [borrowing_public(b) for b in BORROWINGS.values()])

        elif method == "POST":
            data = self.read_json_body()
            if data is None:
                return self.send_error_json(400, "invalid_json", "Body is not valid JSON")
            if "book_id" not in data:
                return self.send_error_json(400, "validation_error", "Missing fields",
                                             {"book_id": ["This field is required."]})
            book = BOOKS.get(data["book_id"])
            if not book:
                return self.send_error_json(400, "validation_error", "Invalid book_id",
                                             {"book_id": ["No book with this ID exists."]})
            if book["available_copies"] <= 0:
                return self.send_error_json(409, "conflict", "No available copies of this book")

            # Current user hardcoded as user 1 - real auth comes in Module 8.1
            user_id = 1
            book["available_copies"] -= 1
            bor_id = next_id("borrowings")
            now = datetime.utcnow()
            BORROWINGS[bor_id] = {
                "id": bor_id,
                "book_id": book["id"],
                "user_id": user_id,
                "borrowed_at": now.isoformat(),
                "due_date": (now + timedelta(days=14)).date().isoformat(),
                "returned_at": None,
                "status": "active",
            }
            self.send_json(201, borrowing_public(BORROWINGS[bor_id]))

        else:
            self.send_error_json(405, "method_not_allowed", f"{method} not allowed on this resource")

    def h_borrowings_detail(self, method, id):
        bor_id = int(id)
        borrowing = BORROWINGS.get(bor_id)
        if not borrowing:
            return self.send_error_json(404, "not_found", "Borrowing not found")

        if method == "GET":
            self.send_json(200, borrowing_public(borrowing))

        elif method == "PATCH":
            data = self.read_json_body()
            if data is None:
                return self.send_error_json(400, "invalid_json", "Body is not valid JSON")
            if "due_date" in data:
                borrowing["due_date"] = data["due_date"]
            self.send_json(200, borrowing_public(borrowing))

        elif method == "DELETE":
            return self.send_error_json(
                405, "method_not_allowed",
                "Borrowings cannot be deleted directly - use POST /return/ to preserve history",
            )

        else:
            self.send_error_json(405, "method_not_allowed", f"{method} not allowed on this resource")

    def h_borrowings_return(self, method, id):
        if method != "POST":
            return self.send_error_json(405, "method_not_allowed", f"{method} not allowed on this resource")

        bor_id = int(id)
        borrowing = BORROWINGS.get(bor_id)
        if not borrowing:
            return self.send_error_json(404, "not_found", "Borrowing not found")
        if borrowing["status"] == "returned":
            return self.send_error_json(409, "conflict", "This book has already been returned")

        borrowing["status"] = "returned"
        borrowing["returned_at"] = datetime.utcnow().isoformat()
        book = BOOKS.get(borrowing["book_id"])
        if book:
            book["available_copies"] += 1

        self.send_json(200, borrowing_public(borrowing))


if __name__ == "__main__":
    server = HTTPServer(("localhost", 8000), LibraryHandler)
    print("Library Management API listening on http://localhost:8000")
    print("Try: curl.exe http://localhost:8000/api/v1/books/")
    server.serve_forever()

                                