# Progress So Far

## module1 — basic HTTP server (module1/module1_1_2.py)
Raw `http.server` based server. No routing, no 404 handling.
- `do_GET` — returns `{"message": "hello, Master", "path_you_hit": <path>}`, 200 always.
- `do_POST` — reads body, returns 201 `{"status": "created", "you_sent": ...}`.
- `do_PATCH` — reads body, returns 200 `{"status": "updated"}`.
- `do_DELETE` — returns 204, no body.
- `my_name()` dummy helper function (prints "sajjan").
- Runs on `localhost:8000`.

## module1_3 — Library Management API (module1_3/library.py)
Bigger raw-Python HTTP server simulating a real REST API (precursor to Django/DRF version). In-memory dict "DB" — `AUTHORS`, `BOOKS`, `USERS`, `BORROWINGS` — with auto-increment IDs via `next_id()`.

Real regex-based router (`ROUTES` list + `route()`), so unmatched paths correctly 404 (fixes module1's bug of silently succeeding on any path).

### Endpoints
- **Authors**: `GET/POST /api/v1/authors/`, `GET/PATCH/PUT/DELETE /api/v1/authors/{id}/`, `GET /api/v1/authors/{id}/books/`
- **Books**: `GET/POST /api/v1/books/`, `GET/PATCH/PUT/DELETE /api/v1/books/{id}/`
- **Users**: `GET /api/v1/users/me/` (hardcoded as user 1, no real auth yet), `GET/POST /api/v1/users/`, `GET/PATCH/PUT/DELETE /api/v1/users/{id}/`
- **Borrowings**: `GET/POST /api/v1/borrowings/`, `GET/PATCH /api/v1/borrowings/{id}/` (DELETE blocked — must use return endpoint), `POST /api/v1/borrowings/{id}/return/`

### Behavior notes
- Passwords never returned (`user_public` strips them); stored as fake-hashed `hashed_<pw>`.
- Author responses include computed `book_count`.
- Book creation validates `author_id` exists; borrowing creation validates `book_id` exists and `available_copies > 0` (409 if none left).
- Borrowing due date = borrowed_at + 14 days; return endpoint increments `available_copies` back and blocks double-return (409).
- PUT requires full resource representation (400 + field-level details if missing); PATCH is partial update.
- Consistent JSON error shape: `{"error", "message", "details"?}`.
- Runs on `localhost:8000`.

## Git history
1. `feat: basic HTTP server with GET and POST handlers` — module1 initial server
2. `feat: dummy function` — added `my_name()`
3. PR #1 merged (feat/branch)
4. `feat: APIs for the Library management system` — module1_3/library.py created (523 lines)
5. PR #2 merged (feat/mod1_3)
6. `docs: update project description on staging` — removed 13 lines (docstring/description trimmed)
7. `feat/conflict creation`, `feat/conflict origin`, `fix: conflict resolve` x2 — conflict practice commits touching module1_3/library.py
8. `feat: add gitignore` — added `.gitignore`

## Current state
Clean working tree on `main`. Only 2 Python files tracked: `module1/module1_1_2.py`, `module1_3/library.py`, plus `.gitignore`.
