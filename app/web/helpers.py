"""Small helpers shared by the page routes: templates, flash messages,
login checks and CSRF protection."""
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR
from app.database.connection import get_db
from app.repositories import user_respository as users
from app.services.auth_service import ROLE_LABELS

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

DB_FORMAT = "%Y-%m-%d %H:%M:%S"


class WebRedirect(Exception):
    """Raised inside a dependency to send the browser somewhere else."""

    def __init__(self, url: str):
        self.url = url


# ---------- template filters ----------

def _parse(value: str) -> datetime:
    return datetime.strptime(value[:19].replace("T", " "), DB_FORMAT)


def pretty_dt(value: str) -> str:
    """'2026-11-04 18:30:00' -> 'Today, 6:30 PM'"""
    when = _parse(value)
    days = (when.date() - datetime.now().date()).days
    hour = when.hour % 12 or 12
    clock = f"{hour}:{when.minute:02d} {'AM' if when.hour < 12 else 'PM'}"
    if days == 0:
        day = "Today"
    elif days == 1:
        day = "Tomorrow"
    elif days == -1:
        day = "Yesterday"
    else:
        day = f"{when.day} {when.strftime('%b')}"
    return f"{day}, {clock}"


def time_left(value: str) -> str:
    seconds = (_parse(value) - datetime.now()).total_seconds()
    if seconds <= 0:
        return "Deadline passed"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{max(minutes, 1)} min left"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes:02d}m left"
    return f"{hours // 24} days left"


def is_urgent(value: str) -> bool:
    seconds = (_parse(value) - datetime.now()).total_seconds()
    return 0 < seconds < 2 * 3600


def is_expired(value: str) -> bool:
    return _parse(value) <= datetime.now()


LISTING_STATUS = {"available": "Available", "reserved": "Reserved",
                  "picked_up": "Collected", "cancelled": "Withdrawn"}
REQUEST_STATUS = {"pending": "Awaiting response", "accepted": "Accepted",
                  "rejected": "Declined", "cancelled": "Cancelled", "picked_up": "Collected"}

templates.env.filters["pretty_dt"] = pretty_dt
templates.env.filters["time_left"] = time_left
templates.env.filters["urgent"] = is_urgent
templates.env.filters["expired"] = is_expired
templates.env.filters["listing_status"] = lambda s: LISTING_STATUS.get(s, s)
templates.env.filters["request_status"] = lambda s: REQUEST_STATUS.get(s, s)
templates.env.filters["role_label"] = lambda r: ROLE_LABELS.get(r, r)


# ---------- flash messages ----------

def flash(request: Request, message: str, kind: str = "success") -> None:
    request.session.setdefault("flash", []).append([kind, message])


def pop_flashes(request: Request) -> list[list[str]]:
    return request.session.pop("flash", [])


# ---------- CSRF ----------

def csrf_token(request: Request) -> str:
    if "csrf" not in request.session:
        request.session["csrf"] = secrets.token_urlsafe(32)
    return request.session["csrf"]


async def verify_csrf(request: Request) -> None:
    """Every form POST must carry the token we put in the page."""
    form = await request.form()
    sent = str(form.get("csrf_token", ""))
    expected = request.session.get("csrf", "")
    if not expected or not secrets.compare_digest(sent, expected):
        flash(request, "Your session expired. Please try again.", "error")
        raise WebRedirect("/dashboard")


# ---------- rendering ----------

def render(request: Request, name: str, user: dict | None, status_code: int = 200, **context):
    context.update(
        user=user,
        flashes=pop_flashes(request),
        csrf_token=csrf_token(request),
        current_path=request.url.path,
    )
    return templates.TemplateResponse(
        request=request, name=name, context=context, status_code=status_code
    )


def safe_next(target: str | None) -> str:
    """Only allow redirects to pages on this site."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return "/dashboard"


# ---------- who is logged in? ----------

def optional_user(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> dict | None:
    user_id = request.session.get("user_id")
    return users.get_by_id(conn, user_id) if user_id else None


def login_required(request: Request, user: dict | None = Depends(optional_user)) -> dict:
    if not user:
        target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        raise WebRedirect(f"/login?next={quote(target)}")
    return user


def role_required(role: str):
    def check(request: Request, user: dict = Depends(login_required)) -> dict:
        if user["role"] != role:
            who = "caterers" if role == "caterer" else "NGO accounts"
            flash(request, f"That page is only for {who}.", "error")
            raise WebRedirect("/dashboard")
        return user
    return check
