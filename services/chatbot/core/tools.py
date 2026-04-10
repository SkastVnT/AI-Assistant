"""
Tool functions for chatbot
"""
import sys
import logging
import requests
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import GOOGLE_SEARCH_API_KEY_1, GOOGLE_SEARCH_API_KEY_2, GOOGLE_CSE_ID, GITHUB_TOKEN, SAUCENAO_API_KEY, SERPAPI_API_KEY

logger = logging.getLogger(__name__)


def google_search_tool(query):
    """Google Custom Search API with improved error handling"""
    try:
        if not GOOGLE_SEARCH_API_KEY_1 or not GOOGLE_CSE_ID:
            return "âŒ Google Search API chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh. Vui lÃ²ng thÃªm GOOGLE_SEARCH_API_KEY vÃ  GOOGLE_CSE_ID vÃ o file .env"
        
        logger.info(f"[GOOGLE SEARCH] Query: {query}")
        
        url = "https://www.googleapis.com/customsearch/v1"
        
        # Create session with retry strategy
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Try with first API key
        params = {
            'key': GOOGLE_SEARCH_API_KEY_1,
            'cx': GOOGLE_CSE_ID,
            'q': query,
            'num': 5
        }
        
        response = session.get(url, params=params, timeout=30)
        
        logger.info(f"[GOOGLE SEARCH] Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            if 'items' in data:
                for item in data['items'][:5]:
                    title = item.get('title', 'No title')
                    link = item.get('link', '')
                    snippet = item.get('snippet', 'No description')
                    results.append(f"**{title}**\n{snippet}\nðŸ”— {link}")
                
                return "ðŸ” **Káº¿t quáº£ tÃ¬m kiáº¿m:**\n\n" + "\n\n---\n\n".join(results)
            else:
                return "KhÃ´ng tÃ¬m tháº¥y káº¿t quáº£ nÃ o."
                
        elif response.status_code == 429:
            # Quota exceeded, try second key
            if GOOGLE_SEARCH_API_KEY_2:
                params['key'] = GOOGLE_SEARCH_API_KEY_2
                response = session.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    if 'items' in data:
                        for item in data['items'][:5]:
                            title = item.get('title', 'No title')
                            link = item.get('link', '')
                            snippet = item.get('snippet', 'No description')
                            results.append(f"**{title}**\n{snippet}\nðŸ”— {link}")
                        return "ðŸ” **Káº¿t quáº£ tÃ¬m kiáº¿m:**\n\n" + "\n\n---\n\n".join(results)
            return "âŒ ÄÃ£ háº¿t quota Google Search API. Vui lÃ²ng thá»­ láº¡i sau."
        else:
            return f"âŒ Lá»—i Google Search API: {response.status_code}"
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[GOOGLE SEARCH] Connection Error: {e}")
        return "âŒ Lá»—i káº¿t ná»‘i Ä‘áº¿n Google Search API"
    except requests.exceptions.Timeout as e:
        logger.error(f"[GOOGLE SEARCH] Timeout Error: {e}")
        return "âŒ Timeout khi káº¿t ná»‘i Ä‘áº¿n Google Search API"
    except Exception as e:
        logger.error(f"[GOOGLE SEARCH] Unexpected Error: {e}")
        return f"âŒ Lá»—i: {str(e)}"


def github_search_tool(query):
    """GitHub Repository Search"""
    try:
        if not GITHUB_TOKEN:
            return "âŒ GitHub Token chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh. Vui lÃ²ng thÃªm GITHUB_TOKEN vÃ o file .env"
        
        url = "https://api.github.com/search/repositories"
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': 5
        }
        
        cleaned_query = query.replace('\n', ' ').replace('\r', '')
        logger.info(f"[GITHUB SEARCH] Query: {cleaned_query}")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            if 'items' in data and len(data['items']) > 0:
                for repo in data['items']:
                    name = repo.get('full_name', 'Unknown')
                    desc = repo.get('description', 'No description')
                    stars = repo.get('stargazers_count', 0)
                    html_url = repo.get('html_url', '')
                    language = repo.get('language', 'N/A')
                    
                    results.append(f"**{name}** â­ {stars}\n{desc}\nðŸ’» {language} | ðŸ”— {html_url}")
                
                return "ðŸ™ **GitHub Repositories:**\n\n" + "\n\n---\n\n".join(results)
            else:
                return "KhÃ´ng tÃ¬m tháº¥y repository nÃ o."
        else:
            return f"âŒ Lá»—i GitHub API: {response.status_code}"
    
    except Exception as e:
        logger.error(f"[GITHUB SEARCH] Error: {e}")
        return f"❌ Lỗi: {str(e)}"


def saucenao_search_tool(image_url: str = "", image_data: bytes = None) -> str:
    """
    Reverse image search using SauceNAO API.
    Accepts an image URL or raw image bytes.
    Returns formatted results with source info, similarity, and links.
    """
    try:
        if not SAUCENAO_API_KEY:
            return "❌ SauceNAO API Key chưa được cấu hình. Thêm SAUCENAO_API_KEY vào .env"

        from saucenao_api import SauceNao

        logger.info(f"[SAUCENAO] Searching: {image_url[:80] if image_url else 'uploaded image'}")

        sauce = SauceNao(api_key=SAUCENAO_API_KEY, numres=8)

        if image_url:
            results = sauce.from_url(image_url)
        elif image_data:
            import tempfile, os
            ext = ".png"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            tmp.write(image_data)
            tmp.close()
            try:
                results = sauce.from_file(tmp.name)
            finally:
                os.unlink(tmp.name)
        else:
            return "❌ Cần cung cấp URL ảnh hoặc file ảnh để tìm kiếm."

        if not results:
            return "🔍 Không tìm thấy kết quả nào trên SauceNAO."

        parts = []
        for i, res in enumerate(results[:6]):
            sim = f"{res.similarity:.1f}%"
            title = res.title or "Không rõ"
            author = res.author or "N/A"
            urls = res.urls or []
            url_str = "\n".join(f"  🔗 {u}" for u in urls[:3]) if urls else "  (không có link)"

            parts.append(
                f"**#{i+1}** — {sim} tương đồng\n"
                f"📌 **{title}**\n"
                f"🎨 Tác giả: {author}\n"
                f"{url_str}"
            )

        header = f"🔍 **SauceNAO — Kết quả tìm kiếm ảnh** ({len(results)} nguồn)\n"
        remaining = f"\n⏳ Còn lại: {results.short_remaining}/30s · {results.long_remaining}/ngày"

        return header + "\n\n---\n\n".join(parts) + remaining

    except Exception as e:
        logger.error(f"[SAUCENAO] Error: {e}")
        return f"❌ Lỗi SauceNAO: {str(e)}"


# ── SerpAPI tools ─────────────────────────────────────────────────────

_SERPAPI_URL = "https://serpapi.com/search.json"


def serpapi_web_search(query: str, engine: str = "google") -> str:
    """
    Web search via SerpAPI. Supports engine: google (default), bing, baidu.
    Returns formatted organic results.
    """
    try:
        if not SERPAPI_API_KEY:
            return "❌ SERPAPI_API_KEY chưa được cấu hình. Thêm vào file .env"

        logger.info(f"[SERPAPI:{engine.upper()}] Query: {query[:80]}")

        params = {
            "engine": engine,
            "q": query,
            "api_key": SERPAPI_API_KEY,
            "num": 5,
        }
        resp = requests.get(_SERPAPI_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("organic_results", [])
        if not items:
            return f"🔍 Không tìm thấy kết quả từ {engine.title()}."

        engine_label = {"google": "Google", "bing": "Bing", "baidu": "Baidu"}.get(engine, engine.title())
        parts = []
        for item in items[:5]:
            title = item.get("title", "")
            snippet = item.get("snippet", item.get("description", ""))
            link = item.get("link", "")
            parts.append(f"**{title}**\n{snippet}\n🔗 {link}")

        return f"🔍 **{engine_label} Search — Kết quả:**\n\n" + "\n\n---\n\n".join(parts)

    except Exception as e:
        logger.error(f"[SERPAPI:{engine}] Error: {e}")
        return f"❌ Lỗi SerpAPI ({engine}): {str(e)}"


def serpapi_reverse_image(image_url: str) -> str:
    """
    Reverse image search via SerpAPI.
    Strategy: Google Lens (best) → Google Reverse Image → Yandex Images.
    Returns visual matches or image results.
    """
    if not SERPAPI_API_KEY:
        return "❌ SERPAPI_API_KEY chưa được cấu hình."

    if not image_url or not image_url.startswith("http"):
        return "❌ Cần cung cấp URL ảnh hợp lệ (http/https)."

    logger.info(f"[SERPAPI:REVERSE_IMAGE] URL: {image_url[:80]}")

    # --- Attempt 1: Google Lens ---
    try:
        resp = requests.get(_SERPAPI_URL, params={
            "engine": "google_lens",
            "url": image_url,
            "api_key": SERPAPI_API_KEY,
        }, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            matches = data.get("visual_matches", [])
            if matches:
                parts = []
                for i, m in enumerate(matches[:6]):
                    title = m.get("title", "Không rõ")
                    source = m.get("source", "")
                    link = m.get("link", "")
                    price = m.get("price", {})
                    price_str = f" — 💰 {price.get('value', '')}" if price else ""
                    parts.append(f"**#{i+1}** [{source}] {title}{price_str}\n🔗 {link}")
                return (
                    f"🔍 **Google Lens — Visual Matches** ({len(matches)} kết quả):\n\n"
                    + "\n\n".join(parts)
                )
    except Exception as e:
        logger.warning(f"[SERPAPI:GOOGLE_LENS] Failed: {e}")

    # --- Attempt 2: Google Reverse Image ---
    try:
        resp = requests.get(_SERPAPI_URL, params={
            "engine": "google_reverse_image",
            "image_url": image_url,
            "api_key": SERPAPI_API_KEY,
        }, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            kg = data.get("knowledge_graph", {})
            items = data.get("image_results", data.get("inline_images", []))
            parts = []
            if kg:
                parts.append(f"**🧠 Knowledge Graph:** {kg.get('title', '')} — {kg.get('description', '')[:200]}")
            for i, item in enumerate(items[:5]):
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", item.get("original", ""))
                parts.append(f"**#{i+1}** {title}\n{snippet}\n🔗 {link}")
            if parts:
                return "🔍 **Google Reverse Image:**\n\n" + "\n\n---\n\n".join(parts)
    except Exception as e:
        logger.warning(f"[SERPAPI:GOOGLE_REVERSE_IMAGE] Failed: {e}")

    # --- Attempt 3: Yandex Images ---
    try:
        resp = requests.get(_SERPAPI_URL, params={
            "engine": "yandex_images",
            "url": image_url,
            "api_key": SERPAPI_API_KEY,
        }, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("images_results", [])
            if items:
                parts = []
                for i, item in enumerate(items[:5]):
                    title = item.get("title", "")
                    source = item.get("source", "")
                    link = item.get("link", item.get("original", ""))
                    parts.append(f"**#{i+1}** {title} ({source})\n🔗 {link}")
                return "🔍 **Yandex Images Reverse:**\n\n" + "\n\n".join(parts)
    except Exception as e:
        logger.warning(f"[SERPAPI:YANDEX_IMAGES] Failed: {e}")

    return "🔍 Không tìm thấy kết quả reverse image từ bất kỳ nguồn nào."


def serpapi_image_search(query: str, engine: str = "google_images_light") -> str:
    """
    Image search via SerpAPI. engine: google_images_light (default), bing_images, google_images.
    Returns list of image links and titles.
    """
    try:
        if not SERPAPI_API_KEY:
            return "❌ SERPAPI_API_KEY chưa được cấu hình."

        logger.info(f"[SERPAPI:IMG_SEARCH] Query: {query[:80]}, engine={engine}")

        params = {
            "engine": engine,
            "q": query,
            "api_key": SERPAPI_API_KEY,
        }
        resp = requests.get(_SERPAPI_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("images_results", [])
        if not items:
            return f"🖼️ Không tìm thấy ảnh cho: {query}"

        engine_label = {"google_images_light": "Google Images", "bing_images": "Bing Images",
                        "google_images": "Google Images (Full)"}.get(engine, engine)
        parts = []
        for i, item in enumerate(items[:6]):
            title = item.get("title", "")
            thumbnail = item.get("thumbnail", "")
            original = item.get("original", item.get("link", ""))
            source = item.get("source", "")
            parts.append(f"**#{i+1}** {title} ({source})\n📎 {original}")

        return f"🖼️ **{engine_label} — '{query}'** ({len(items)} kết quả):\n\n" + "\n\n".join(parts)

    except Exception as e:
        logger.error(f"[SERPAPI:IMAGE_SEARCH] Error: {e}")
        return f"❌ Lỗi image search: {str(e)}"


# ── Comprehensive reverse image search ────────────────────────────────

def reverse_image_search(image_data_url: str = "", image_url: str = "") -> dict:
    """
    Comprehensive reverse image search pipeline.

    Accepts a base64 data-URL *or* a public URL.  When only a data-URL is
    provided the image is uploaded to ImgBB first to obtain a public URL
    that SerpAPI/SauceNAO can accept.

    Returns a dict with structured results::

        {
            "sources": [
                {
                    "title": str,
                    "author": str | None,
                    "url": str,
                    "thumbnail": str | None,
                    "similarity": float | None,  # 0-100
                    "source_engine": str,         # "saucenao" | "google_lens" | ...
                }
            ],
            "similar": [ ... same schema ... ],
            "knowledge": str | None,   # Knowledge-graph blurb
            "summary": str,            # Human-readable markdown summary
        }
    """
    result = {
        "sources": [],
        "similar": [],
        "knowledge": None,
        "summary": "",
    }

    # ── Resolve a public URL ──────────────────────────────────────
    public_url = image_url
    if not public_url and image_data_url:
        try:
            from core.image_storage import upload_to_imgbb
            public_url = upload_to_imgbb(image_data_url) or ""
            if public_url:
                logger.info(f"[ReverseImg] Uploaded to ImgBB: {public_url[:80]}")
        except Exception as e:
            logger.warning(f"[ReverseImg] ImgBB upload failed: {e}")

    # ── 1. SauceNAO (best for anime/art) ─────────────────────────
    try:
        if SAUCENAO_API_KEY:
            from saucenao_api import SauceNao
            sauce = SauceNao(api_key=SAUCENAO_API_KEY, numres=8)
            if public_url:
                sauce_results = sauce.from_url(public_url)
            elif image_data_url:
                import tempfile, os, base64 as _b64
                raw = image_data_url
                if ',' in raw:
                    raw = raw.split(',', 1)[1]
                img_bytes = _b64.b64decode(raw)
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                tmp.write(img_bytes)
                tmp.close()
                try:
                    sauce_results = sauce.from_file(tmp.name)
                finally:
                    os.unlink(tmp.name)
            else:
                sauce_results = None

            if sauce_results:
                for res in sauce_results[:6]:
                    result["sources"].append({
                        "title": res.title or "Unknown",
                        "author": res.author or None,
                        "url": (res.urls[0] if res.urls else ""),
                        "thumbnail": None,
                        "similarity": float(res.similarity) if res.similarity else None,
                        "source_engine": "saucenao",
                    })
    except ImportError:
        logger.debug("[ReverseImg] saucenao_api not installed — skipping")
    except Exception as e:
        logger.warning(f"[ReverseImg] SauceNAO failed: {e}")

    # ── 2. Google Lens (best for real-world objects) ──────────────
    if public_url and SERPAPI_API_KEY:
        try:
            resp = requests.get(_SERPAPI_URL, params={
                "engine": "google_lens",
                "url": public_url,
                "api_key": SERPAPI_API_KEY,
            }, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                # Knowledge graph
                kg = data.get("knowledge_graph", {})
                if kg:
                    result["knowledge"] = f"{kg.get('title', '')} — {kg.get('description', '')[:300]}"

                # Visual matches → sources (exact/near-exact)
                for m in data.get("visual_matches", [])[:8]:
                    result["sources"].append({
                        "title": m.get("title", ""),
                        "author": m.get("source", None),
                        "url": m.get("link", ""),
                        "thumbnail": m.get("thumbnail", None),
                        "similarity": None,
                        "source_engine": "google_lens",
                    })
        except Exception as e:
            logger.warning(f"[ReverseImg] Google Lens failed: {e}")

    # ── 3. Google Reverse Image ───────────────────────────────────
    if public_url and SERPAPI_API_KEY and len(result["sources"]) < 3:
        try:
            resp = requests.get(_SERPAPI_URL, params={
                "engine": "google_reverse_image",
                "image_url": public_url,
                "api_key": SERPAPI_API_KEY,
            }, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("image_results", data.get("inline_images", []))[:5]:
                    result["similar"].append({
                        "title": item.get("title", ""),
                        "author": item.get("source", None),
                        "url": item.get("link", item.get("original", "")),
                        "thumbnail": item.get("thumbnail", None),
                        "similarity": None,
                        "source_engine": "google_reverse_image",
                    })
        except Exception as e:
            logger.warning(f"[ReverseImg] Google Reverse Image failed: {e}")

    # ── 4. Yandex Images (good for non-English sources) ───────────
    if public_url and SERPAPI_API_KEY and len(result["sources"]) < 3:
        try:
            resp = requests.get(_SERPAPI_URL, params={
                "engine": "yandex_images",
                "url": public_url,
                "api_key": SERPAPI_API_KEY,
            }, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("images_results", [])[:5]:
                    result["similar"].append({
                        "title": item.get("title", ""),
                        "author": item.get("source", None),
                        "url": item.get("link", item.get("original", "")),
                        "thumbnail": item.get("thumbnail", None),
                        "similarity": None,
                        "source_engine": "yandex",
                    })
        except Exception as e:
            logger.warning(f"[ReverseImg] Yandex failed: {e}")

    # ── Build summary ─────────────────────────────────────────────
    parts = []
    if result["knowledge"]:
        parts.append(f"🧠 **Knowledge Graph:** {result['knowledge']}")

    if result["sources"]:
        parts.append(f"\n🔍 **Nguồn tìm thấy** ({len(result['sources'])} kết quả):\n")
        for i, s in enumerate(result["sources"][:8], 1):
            sim_str = f" — {s['similarity']:.1f}% match" if s.get("similarity") else ""
            author_str = f" | 🎨 {s['author']}" if s.get("author") else ""
            engine = s.get("source_engine", "")
            parts.append(
                f"**#{i}** [{engine}]{sim_str}{author_str}\n"
                f"📌 **{s['title']}**\n"
                f"🔗 {s['url']}"
            )

    if result["similar"]:
        parts.append(f"\n🖼️ **Ảnh tương tự** ({len(result['similar'])} kết quả):\n")
        for i, s in enumerate(result["similar"][:5], 1):
            parts.append(f"**#{i}** {s['title']}\n🔗 {s['url']}")

    if not parts:
        result["summary"] = "🔍 Không tìm thấy kết quả reverse image từ bất kỳ nguồn nào."
    else:
        result["summary"] = "\n\n".join(parts)

    return result

