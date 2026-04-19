"""
FastAPI Application - Chatbot Service
Migrated from Flask monolith for native async support and better performance.
"""
import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware

# Ensure paths
CHATBOT_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = CHATBOT_DIR.parent.parent

if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(1, str(ROOT_DIR))

from core.config import IMAGE_STORAGE_DIR, MEMORY_DIR
from core.extensions import MONGODB_ENABLED, logger

# Import routers
from fastapi_app.routers import (
    chat,
    council_stream,
    xai_native_stream,
    stream,
    conversations,
    memory,
    images,
    video,
    rag,
    skills,
    last30days,
    hermes,
    admin,
    image_gen,
    mcp,
    main_extras,
    stable_diffusion,
    anime_pipeline,
)

logger = logging.getLogger("chatbot.fastapi")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 FastAPI Chatbot starting up...")

    # Ensure storage directories
    IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    if MONGODB_ENABLED:
        logger.info("✅ MongoDB connection available")
    else:
        logger.warning("⚠️ MongoDB not available — some features disabled")

    yield

    logger.info("🛑 FastAPI Chatbot shutting down...")


def create_app() -> FastAPI:
    """Application factory"""
    app = FastAPI(
        title="AI Assistant Chatbot",
        description="Multi-model AI chatbot with streaming, video generation, and more",
        version="2.0.0",
        lifespan=lifespan,
    )

    # --- Middleware ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    secret = os.getenv("SESSION_SECRET", os.urandom(32).hex())
    app.add_middleware(SessionMiddleware, secret_key=secret)

    # --- Static files ---
    static_dir = CHATBOT_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    storage_dir = IMAGE_STORAGE_DIR
    if storage_dir.exists():
        app.mount(
            "/storage/images",
            StaticFiles(directory=str(storage_dir)),
            name="image_storage",
        )

    # --- Templates ---
    templates_dir = CHATBOT_DIR / "templates"
    templates = Jinja2Templates(directory=str(templates_dir)) if templates_dir.exists() else None

    # Inject a Flask-compatible url_for into Jinja2 globals so that
    # {{ url_for('static', filename='css/app.css') }} works unchanged.
    if templates:
        def _url_for(name: str, **kwargs) -> str:
            if name == 'static':
                path = kwargs.get('filename', kwargs.get('path', ''))
                return f"/static/{path}"
            # Other named routes: best-effort path construction
            path = kwargs.get('filename', kwargs.get('path', ''))
            return f"/{name}/{path}" if path else f"/{name}"
        templates.env.globals['url_for'] = _url_for

    # --- Page routes ---
    @app.post("/", include_in_schema=False)
    async def root_post_probe():
        """Silently absorb POST / probes from tools like Open WebUI, LM Studio, etc."""
        from fastapi.responses import JSONResponse
        return JSONResponse({"status": "ok"})

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        if templates:
            import json as _json
            _firebase_config = _json.dumps({
                "apiKey": os.getenv("FIREBASE_API_KEY", ""),
                "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
                "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
                "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", ""),
                "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
                "appId": os.getenv("FIREBASE_APP_ID", ""),
                "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID", ""),
            })
            return templates.TemplateResponse("index.html", {
                "request": request,
                "session": request.session,
                "firebase_config": _firebase_config,
            })
        return HTMLResponse("<h1>AI Chatbot (FastAPI)</h1><p>Templates directory not found.</p>")

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        """Render login page. If already authenticated, redirect to home."""
        if request.session.get("authenticated"):
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/", status_code=302)
        if templates:
            return templates.TemplateResponse("login.html", {"request": request})
        return HTMLResponse("<h1>Login</h1><p>login.html template not found.</p>", status_code=200)

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        ico = CHATBOT_DIR / "static" / "favicon.ico"
        if ico.exists():
            return FileResponse(str(ico))
        return HTMLResponse("", status_code=204)

    @app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
    async def chrome_devtools_json():
        """Silence Chrome DevTools automatic probe — return empty JSON 200."""
        return {}

    # --- Auth endpoints ---
    @app.get("/logout")
    async def logout(request: Request):
        """Clear session and redirect to login."""
        from fastapi.responses import RedirectResponse
        username = request.session.get("username", "unknown")
        request.session.clear()
        import logging as _log
        _log.getLogger(__name__).info(f"[Auth] Logout: {username}")
        response = RedirectResponse(url="/login", status_code=302)
        response.delete_cookie("display_name")
        return response

    @app.get("/api/auth/me")
    async def auth_me(request: Request):
        """Return current session user info (FastAPI/session-middleware path)."""
        sess = request.session
        if not sess.get("authenticated"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"authenticated": False}, status_code=401)
        return {
            "authenticated": True,
            "user": {
                "user_id": sess.get("user_id"),
                "username": sess.get("username"),
                "role": sess.get("user_role"),
                "display_name": sess.get("display_name"),
            },
        }

    @app.post("/api/auth/login")
    async def auth_login(request: Request):
        """Authenticate user and create session."""
        from fastapi.responses import JSONResponse, Response
        import uuid as _uuid
        try:
            body = await request.json()
        except Exception:
            body = {}
        username = (body.get("username") or "").strip()
        password = body.get("password") or ""
        if not username or not password:
            return JSONResponse({"success": False, "message": "Vui lòng nhập đầy đủ thông tin"}, status_code=400)
        try:
            from core.user_auth import authenticate_user
            db = None
            try:
                from core.extensions import get_db
                db = get_db()
            except Exception:
                try:
                    from config.mongodb_config import mongodb_client
                    db = mongodb_client.db
                except Exception:
                    pass
            user = authenticate_user(db, username, password) if db is not None else None
        except Exception as e:
            logger.warning(f"[Auth] Login DB error: {e}")
            user = None
        if user:
            request.session.clear()
            request.session["authenticated"] = True
            request.session["user_id"] = user["user_id"]
            request.session["username"] = user["username"]
            request.session["user_role"] = user["role"]
            request.session["display_name"] = user["display_name"]
            request.session["session_id"] = str(_uuid.uuid4())
            logger.info(f"[Auth] Login success: {username} (role={user['role']})")
            redirect_url = "/admin" if user["role"] == "admin" else "/"
            resp = JSONResponse({"success": True, "redirect": redirect_url, "user": user})
            resp.set_cookie("display_name", user["display_name"], max_age=86400 * 30, httponly=False, samesite="lax")
            return resp
        logger.warning(f"[Auth] Login failed: {username}")
        return JSONResponse({"success": False, "message": "Sai tên đăng nhập hoặc mật khẩu"}, status_code=401)

    # --- Misc API stubs (non-critical, polled by frontend on load) ---
    @app.get("/api/local-models-status")
    async def local_models_status():
        """Report whether local transformer models are available."""
        try:
            from core.model_loader import model_loader  # type: ignore
            return {"available": True, "models": model_loader.get_available_models()}
        except ImportError:
            return {
                "available": False,
                "error": "Local models not available. Install: pip install torch transformers accelerate",
            }

    _NEGATIVE_PRESETS_DATA = [
        {"id": "quality", "label": "Quality Fix", "prompt": "worst quality, low quality, normal quality, lowres, blurry, jpeg artifacts, watermark, text, signature, cropped, out of frame, duplicate, mutation, deformed"},
        {"id": "anatomy", "label": "Anatomy Fix", "prompt": "bad anatomy, bad hands, missing fingers, extra fingers, fused fingers, too many fingers, missing limbs, extra limbs, malformed limbs, floating limbs, disconnected limbs"},
        {"id": "face", "label": "Face Fix", "prompt": "bad face, disfigured face, mutated face, blurry face, extra face, cloned face, deformed eyes, crossed eyes, asymmetrical eyes"},
        {"id": "nsfw", "label": "SFW Filter", "prompt": "nsfw, nude, naked, sexual, explicit, pornographic, lewd, erotic, suggestive, revealing clothing, underwear, bikini, lingerie"},
    ]

    @app.get("/api/sd-negative-presets")
    async def sd_negative_presets():
        """Return stable diffusion negative prompt presets."""
        return {"success": True, "presets": _NEGATIVE_PRESETS_DATA}

    @app.get("/api/features")
    async def get_features():
        """Return public feature flag states for frontend UI decisions."""
        try:
            from core.feature_flags import features
            features.reload()
            return {
                "quota": features.quota_enabled,
                "video": features.video_enabled,
                "video_requires_payment": features.video_requires_payment,
                "payment": features.payment_enabled,
                "qr": features.qr_enabled,
                "registration": features.allow_registration,
            }
        except Exception as e:
            logger.warning(f"[features] Could not load feature flags: {e}")
            return {
                "quota": False, "video": False, "video_requires_payment": False,
                "payment": False, "qr": False, "registration": True,
            }

    @app.get("/admin", response_class=HTMLResponse)
    async def admin_page(request: Request):
        """Render admin dashboard (requires admin role)."""
        from fastapi.responses import RedirectResponse
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/login", status_code=302)
        if request.session.get("user_role") != "admin":
            return RedirectResponse(url="/", status_code=302)
        if templates:
            return templates.TemplateResponse("admin.html", {"request": request})
        return HTMLResponse("<h1>Admin</h1><p>admin.html template not found.</p>")

    @app.post("/api/generate-title")
    async def generate_title(request: Request):
        """Generate a short conversation title (tries Ollama, falls back to truncation)."""
        import httpx as _httpx
        body = await request.json()
        raw_message = str(body.get("message", "")).strip()[:200]
        language = str(body.get("language", "vi")).strip()
        if not raw_message:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "message is required"}, status_code=400)

        if language == "en":
            prompt = (
                "Generate a concise 3-5 word English title for this conversation. "
                "Return ONLY the title text, no quotes, no explanation:\n"
                f'"{raw_message}"'
            )
        else:
            prompt = (
                "Tạo tiêu đề ngắn gọn 3-7 từ tiếng Việt cho cuộc trò chuyện này. "
                "Chỉ trả về tiêu đề, không giải thích, không ngoặc kép:\n"
                f'"{raw_message}"'
            )
        try:
            async with _httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "qwen2.5:0.5b", "prompt": prompt, "stream": False,
                          "options": {"temperature": 0.7, "num_predict": 20}},
                )
                resp.raise_for_status()
                title = resp.json().get("response", "").strip().replace('"', "").replace("'", "").strip()
                if title:
                    return {"title": title}
        except Exception as e:
            logger.debug(f"[generate-title] Ollama unavailable: {e}")

        fallback = raw_message[:40] + ("..." if len(raw_message) > 40 else "")
        return {"title": fallback}

    # --- Routers ---
    app.include_router(chat.router, tags=["Chat"])
    app.include_router(council_stream.router, tags=["Council Streaming"])
    app.include_router(xai_native_stream.router, tags=["xAI Native Streaming"])
    app.include_router(stream.router, tags=["Streaming"])
    app.include_router(conversations.router, prefix="/api", tags=["Conversations"])
    app.include_router(memory.router, prefix="/api/memory", tags=["Memory"])
    app.include_router(images.router, tags=["Images"])
    app.include_router(video.router, prefix="/api/video", tags=["Video Generation"])
    app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])
    app.include_router(skills.router, tags=["Skills"])
    app.include_router(last30days.router, tags=["Tools"])
    app.include_router(hermes.router, tags=["Tools"])
    app.include_router(admin.router, tags=["Admin"])
    app.include_router(image_gen.router, tags=["Image Generation"])
    app.include_router(mcp.router)
    app.include_router(main_extras.router)
    app.include_router(stable_diffusion.router, tags=["Stable Diffusion"])
    app.include_router(anime_pipeline.router, tags=["Anime Pipeline"])

    # --- Root health check ---
    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "chatbot",
            "framework": "fastapi",
            "mongodb": MONGODB_ENABLED,
        }

    return app
