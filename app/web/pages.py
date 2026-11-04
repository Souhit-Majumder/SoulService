"""All the HTML pages and form actions of the website.

Posting a listing is the one exception: the browser sends it as XML to
/api/v1/listings (see app/api/routes/listings.py and static/js/app.js).
"""
import sqlite3
import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.database.connection import get_db
from app.repositories import listing_respository as listings
from app.repositories import request_respository as requests_repo
from app.services import auth_service, listing_service, request_service
from app.services.errors import ServiceError
from app.web.helpers import (
    flash, login_required, optional_user, render, role_required, safe_next, verify_csrf,
)

router = APIRouter()


def redirect(url: str) -> RedirectResponse:
    # 303 makes the browser follow with GET after a form POST.
    return RedirectResponse(url, status_code=303)


# ---------------- public pages ----------------

@router.get("/")
def home(request: Request, user=Depends(optional_user), conn: sqlite3.Connection = Depends(get_db)):
    return render(request, "index.html", user, stats=listings.public_stats(conn))


@router.get("/login")
def login_page(request: Request, user=Depends(optional_user), next: str = "/dashboard"):
    if user:
        return redirect("/dashboard")
    return render(request, "login.html", None, next=safe_next(next), email="", error=None)


@router.post("/login", dependencies=[Depends(verify_csrf)])
def login_submit(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    next: str = Form("/dashboard"),
    conn: sqlite3.Connection = Depends(get_db),
):
    user = auth_service.authenticate(conn, email, password)
    if not user:
        return render(
            request, "login.html", None, status_code=401,
            next=safe_next(next), email=email,
            error="That email and password don't match. Please check and try again.",
        )
    request.session.clear()  # fresh session after login
    request.session["user_id"] = user["user_id"]
    flash(request, f"Welcome back, {user['name']}!")
    return redirect(safe_next(next))


@router.post("/logout", dependencies=[Depends(verify_csrf)])
def logout(request: Request):
    request.session.clear()
    flash(request, "You have been logged out.")
    return redirect("/")


# ---------------- browsing food ----------------

@router.get("/food")
def browse_food(
    request: Request,
    q: str = "",
    diet: str = "",
    user=Depends(optional_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    q = q.strip()[:100]
    if diet not in listing_service.DIETARY_OPTIONS:
        diet = ""
    items = listings.list_available(conn, q, diet)
    requested = requests_repo.active_food_ids(conn, user["user_id"]) if user and user["role"] == "recipient" else set()
    return render(
        request, "food_list.html", user,
        items=items, q=q, diet=diet, requested=requested,
        dietary_options=listing_service.DIETARY_OPTIONS,
    )


@router.get("/food/new")
def new_food_page(request: Request, user=Depends(role_required("caterer"))):
    return render(
        request, "food_new.html", user,
        dietary_options=listing_service.DIETARY_OPTIONS,
        allergen_options=listing_service.ALLERGEN_OPTIONS,
        unit_options=listing_service.UNIT_OPTIONS,
    )


# ---------------- dashboard ----------------

@router.get("/dashboard")
def dashboard(request: Request, user=Depends(login_required), conn: sqlite3.Connection = Depends(get_db)):
    if user["role"] == "caterer":
        my_listings = listings.list_by_caterer(conn, user["user_id"])
        incoming = requests_repo.list_for_caterer(conn, user["user_id"])
        pending = [r for r in incoming if r["status"] == "pending" and r["food_status"] == "available"]
        accepted = [r for r in incoming if r["status"] == "accepted"]
        stats = {
            "active": sum(1 for l in my_listings if l["status"] in ("available", "reserved")),
            "pending": len(pending),
            "collected": sum(1 for l in my_listings if l["status"] == "picked_up"),
        }
        return render(request, "dashboard.html", user, listings=my_listings,
                      pending=pending, accepted=accepted, stats=stats)

    my_requests = requests_repo.list_for_recipient(conn, user["user_id"])
    stats = {
        "waiting": sum(1 for r in my_requests if r["status"] == "pending"),
        "accepted": sum(1 for r in my_requests if r["status"] == "accepted"),
        "collected": sum(1 for r in my_requests if r["status"] == "picked_up"),
    }
    return render(request, "dashboard.html", user, my_requests=my_requests, stats=stats)


# Contact details are controlled by the caterer and shown to the NGO only
# after acceptance, never on public food listings or pending requests.
@router.post("/profile/contact", dependencies=[Depends(verify_csrf)])
def update_contact(request: Request, phone: str = Form(""),
                   user=Depends(role_required("caterer")),
                   conn: sqlite3.Connection = Depends(get_db)):
    phone = phone.strip()
    if phone and not re.fullmatch(r"\+?[0-9][0-9 ()-]{6,19}", phone):
        flash(request, "Enter a valid contact number (7–20 characters, digits and optional +, spaces or hyphens).", "error")
    else:
        conn.execute("UPDATE users SET contact_phone = ? WHERE user_id = ?", (phone, user["user_id"]))
        conn.commit()
        flash(request, "Pickup contact number updated.")
    return redirect("/dashboard")


# ---------------- actions (all POST, all need the CSRF token) ----------------

def _run(request: Request, action, success: str, back: str):
    try:
        action()
    except ServiceError as exc:
        flash(request, exc.message, "error")
    else:
        flash(request, success)
    return redirect(safe_next(back))


@router.post("/food/{food_id}/request", dependencies=[Depends(verify_csrf)])
def request_food(request: Request, food_id: int, next: str = Form("/food"),
                 user=Depends(login_required), conn: sqlite3.Connection = Depends(get_db)):
    return _run(request, lambda: request_service.request_food(conn, user, food_id),
                "Request sent! The caterer will review it.", next)


@router.post("/food/{food_id}/withdraw", dependencies=[Depends(verify_csrf)])
def withdraw_food(request: Request, food_id: int, next: str = Form("/dashboard"),
                  user=Depends(login_required), conn: sqlite3.Connection = Depends(get_db)):
    return _run(request, lambda: listing_service.withdraw_listing(conn, user, food_id),
                "Listing withdrawn.", next)


@router.post("/requests/{request_id}/accept", dependencies=[Depends(verify_csrf)])
def accept(request: Request, request_id: int, next: str = Form("/dashboard"),
           user=Depends(login_required), conn: sqlite3.Connection = Depends(get_db)):
    return _run(request, lambda: request_service.accept_request(conn, user, request_id),
                "Request accepted. The food is now reserved for that NGO.", next)


@router.post("/requests/{request_id}/reject", dependencies=[Depends(verify_csrf)])
def reject(request: Request, request_id: int, next: str = Form("/dashboard"),
           user=Depends(login_required), conn: sqlite3.Connection = Depends(get_db)):
    return _run(request, lambda: request_service.reject_request(conn, user, request_id),
                "Request declined.", next)


@router.post("/requests/{request_id}/cancel", dependencies=[Depends(verify_csrf)])
def cancel(request: Request, request_id: int, next: str = Form("/dashboard"),
           user=Depends(login_required), conn: sqlite3.Connection = Depends(get_db)):
    return _run(request, lambda: request_service.cancel_request(conn, user, request_id),
                "Request cancelled.", next)


@router.post("/requests/{request_id}/collect", dependencies=[Depends(verify_csrf)])
def collect(request: Request, request_id: int, next: str = Form("/dashboard"),
            user=Depends(login_required), conn: sqlite3.Connection = Depends(get_db)):
    return _run(request, lambda: request_service.confirm_collection(conn, user, request_id),
                "Collection confirmed. Thank you for sharing food!", next)
