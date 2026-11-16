from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from .routers import auth, workers, cuts, social, reports

app = FastAPI(title="Control de Arrobas", docs_url=None, redoc_url=None)
for r in (auth, workers, cuts, social, reports):
    app.include_router(r.router)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.exception_handler(ValueError)
async def value_error(_, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.get("/api/health")
def health():
    return {"ok": True}


# Desarrollo local: sirve el frontend. En Vercel, /public se sirve como estático.
_public = Path(__file__).resolve().parents[1] / "public"
if _public.exists():
    app.mount("/", StaticFiles(directory=_public, html=True), name="public")
