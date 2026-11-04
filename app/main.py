from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.api.router import router as api_router
from app.config import BASE_DIR, SECRET_KEY
from app.database.connection import get_connection
from app.database.init_db import initialize_database
from app.database.seed import seed_demo_data
from app.repositories import user_respository as users
from app.web.helpers import WebRedirect, render
from app.web.pages import router as pages_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    conn = get_connection()
    try:
        seed_demo_data(conn)  # adds demo accounts/listings only if missing
    finally:
        conn.close()
    yield


app = FastAPI(
    title="SoulService",
    version="1.0.0",
    lifespan=lifespan,
)

# Keeps the user logged in using a signed cookie.
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    max_age=8 * 60 * 60,
    session_cookie="soulservice_session",
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "app" / "static")),
    name="static",
)


@app.exception_handler(WebRedirect)
async def handle_web_redirect(request: Request, exc: WebRedirect):
    return RedirectResponse(exc.url, status_code=303)


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(request: Request, exc: StarletteHTTPException):
    # API clients get the default JSON/XML errors; browsers get a friendly page.
    if request.url.path.startswith("/api") or exc.status_code not in (404, 405):
        from fastapi.exception_handlers import http_exception_handler
        return await http_exception_handler(request, exc)
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        conn = get_connection()
        try:
            user = users.get_by_id(conn, user_id)
        finally:
            conn.close()
    return render(request, "404.html", user, status_code=404)


app.include_router(pages_router)
app.include_router(api_router)
