import os

# Proje kök dizinini __file__ bazlı hesapla (Render gibi ortamlarda CWD farklı olabilir)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
import json
import asyncio
import sys
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import FileResponse
# (En üstteki import satırlarından birine ekleyebilirsin)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# ==========================================
# 1. KONFİGÜRASYON (Config) YÖNETİMİ
# ==========================================

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'addon-config.json')
addon_config = {}

def load_config():
    global addon_config
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            addon_config = json.load(f)
        print('✅ Addon config loaded')
    except Exception as e:
        print('⚠️ Addon config bulunamadı, yeni bir tane oluşturuluyor...')
        addon_config = {'adminPassword': 'admin123', 'addons': {}}
        save_config() # Dosya yoksa hemen varsayılan değerlerle kaydet

def save_config():
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(addon_config, f, indent=2, ensure_ascii=False)
        print('✅ Addon config saved')
    except Exception as e:
        print(f'❌ Error saving config: {str(e)}')

load_config()

# ==========================================
# 2. EKLENTİ (ADDON) MODÜLLERİ
# ==========================================
# Not: Eklentilerini import ederken kendi yazdığın Python sınıflarını kullanacaksın.
# Şimdilik örnek olması açısından boş veya varsayılan bir obje kullanıyoruz.

class DummyAddon:
    """Henüz Python'a çevrilmemiş eklentiler için yer tutucu."""
    def __init__(self, name):
        self.manifest = {"name": name, "description": "Python port is pending."}
    def getManifest(self):
        return self.manifest

try:
    # Önceki adımdaki Crawl4AI eklentisini buraya import edebilirsin
    from addons.cizgivedizi import CizgiveDiziScraper
    cizgivedizi_addon = CizgiveDiziScraper()
except ImportError:
    cizgivedizi_addon = DummyAddon("CizgiveDizi")

try:
    from addons.inatbox import InatBoxScraper
    inatbox_addon = InatBoxScraper()
except ImportError:
    inatbox_addon = DummyAddon("InatBox")

try:
    from addons.selcuk import SelcukScraper
    selcuk_addon = SelcukScraper()
except ImportError:
    selcuk_addon = DummyAddon("SelcukSports")

try:
    from addons.sporcafe import SporCafeScraper
    sporcafe_addon = SporCafeScraper()
except ImportError:
    sporcafe_addon = DummyAddon("SporCafe")

try:
    from addons.hdfilmcehennemi import HDFilmCehennemiScraper
    hdfilmcehennemi_addon = HDFilmCehennemiScraper()
except ImportError:
    hdfilmcehennemi_addon = DummyAddon("HDFilmCehennemi")

try:
    from addons.webspor import WebsporScraper
    webspor_addon = WebsporScraper()
except ImportError:
    webspor_addon = DummyAddon("Webspor")

try:
    from addons.selcukflix import SelcukFlixScraper
    selcukflix_addon = SelcukFlixScraper()
except ImportError:
    selcukflix_addon = DummyAddon("SelcukFlix")

try:
    from addons.dizipal import DiziPalScraper
    dizipal_addon = DiziPalScraper()
except ImportError:
    dizipal_addon = DummyAddon("DiziPal")

try:
    from addons.dizimag import DiziMagScraper
    dizimag_addon = DiziMagScraper()
except ImportError:
    dizimag_addon = DummyAddon("DiziMag")

try:
    from addons.dizibox import DiziBoxScraper
    dizibox_addon = DiziBoxScraper()
except ImportError:
    dizibox_addon = DummyAddon("DiziBox")

try:
    from addons.ai_addon import GeminiAIFinderScraper
    ai_addon = GeminiAIFinderScraper()
except ImportError as e:
    print(f"Error loading AI Addon: {e}")
    ai_addon = DummyAddon("GeminiAIFinder")

try:
    from addons.youtube import YouTubeScraper
    youtube_addon = YouTubeScraper()
except ImportError:
    youtube_addon = DummyAddon("YouTube")

addon_modules = {
    'cizgivedizi': cizgivedizi_addon,
    'fullhdfilmizlesene': DummyAddon("FullHDFilmIzlesene"),
    'hdfilmcehennemi': hdfilmcehennemi_addon,
    'inatbox': inatbox_addon,
    'selcuksports': selcuk_addon,
    'sporcafe': sporcafe_addon,
    'webspor': webspor_addon,
    'selcukflix': selcukflix_addon,
    'dizipal': dizipal_addon,
    'dizimag': dizimag_addon,
    'dizibox': dizibox_addon,
    'ai.gemini.finder': ai_addon,
    'youtube': youtube_addon,
    # ... Diğer eklentilerin buraya eklenecek
}

# ==========================================
# 3. FASTAPI KURULUMU & MİDDLEWARE
# ==========================================

app = FastAPI(title="Mind IPTV Backend", version="1.0.0")

# CORS Ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Statik dosyalar (public klasörü varsa)
if not os.path.exists(PUBLIC_DIR):
    os.makedirs(PUBLIC_DIR)
app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")

# Admin Yetkilendirme Dependency
async def check_auth(
    x_admin_password: str = Header(None),
    password: str = None  # Query'den gelebilir
):
    admin_pass = addon_config.get('adminPassword')
    # Header veya Query parametresini kontrol et
    if x_admin_password == admin_pass or password == admin_pass:
        return True
    raise HTTPException(status_code=401, detail={"error": "Unauthorized", "message": "Geçersiz şifre"})

# ==========================================
# 4. KONSOL BİLGİLENDİRMESİ
# ==========================================

print(f"\n🚀 Mind IPTV Backend Server (Instruction/Crawl4AI Hybrid Architecture)")
print(f"📦 Loaded {len(addon_modules)} addon(s):\n")

addon_categories = {
    '🤖 AI Araçları': ['ai.gemini.finder'],
    '🎬 Film & Dizi': ['fullhdfilmizlesene', 'hdfilmcehennemi', 'dizibox', 'dizipal', 'selcukflix', 'dizigom', 'dizimag', '4kfilmizlesene', 'sinefy', 'webteizle'],
    '📺 Dizi': ['dizist', 'dizigom', 'dizimag'],
    '🎌 Anime': ['animecix'],
    '🎨 Çizgi Film': ['cizgimax', 'cizgivedizi'],
    '📚 Belgesel': ['belgeselx'],
    '📺 Canlı TV & Programlar': ['inatbox', 'canlitv', 'tv8', 'kicktr'],
    '⚽ Spor': ['selcuksports', 'sporcafe', 'webspor'],
    '🌐 Platformlar': ['youtube']
}

for category, ids in addon_categories.items():
    loaded_addons = [aid for aid in ids if aid in addon_modules]
    if loaded_addons:
        print(f"   {category}: {', '.join(loaded_addons)}")

# ==========================================
# 5. PUBLIC ENDPOINTLER
# ==========================================
@app.api_route("/", methods=["GET", "HEAD"])
async def serve_index():
    # Siteye ilk girildiğinde public klasöründeki index.html'i göster
    index_path = os.path.join(PUBLIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "index.html public klasöründe bulunamadı."}

@app.get("/admin.html")
async def serve_admin():
    admin_path = os.path.join(PUBLIC_DIR, "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path, media_type="text/html")
    return {"message": "admin.html public klasöründe bulunamadı."}
    
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "architecture": "hybrid-python",
        "addons": list(addon_modules.keys()),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/api/addons")
async def get_all_addons(request: Request):
    addons = []
    for addon_id, addon in addon_modules.items():
        manifest = addon.getManifest() if hasattr(addon, 'getManifest') else getattr(addon, 'manifest', {})
        base_url = str(request.base_url).rstrip('/')
        
        addon_data = {
            "id": addon_id,
            "manifestUrl": f"{base_url}/api/addon/{addon_id}/manifest.json",
        }
        addon_data.update(manifest)
        addons.append(addon_data)
    return {"addons": addons}

@app.get("/api/addons/categories")
async def get_addons_categories():
    result = []
    for category, addon_ids in addon_categories.items():
        cat_addons = []
        for aid in addon_ids:
            addon = addon_modules.get(aid)
            if addon:
                manifest = addon.getManifest() if hasattr(addon, 'getManifest') else getattr(addon, 'manifest', {})
                if manifest and manifest.get("name"):
                    cat_addons.append({
                        "id": aid,
                        "name": manifest.get("name"),
                        "description": manifest.get("description")
                    })
        result.append({"category": category, "addons": cat_addons})
    return {"categories": result}

@app.get("/api/addon/{addon_id}/manifest.json")
async def get_addon_manifest(addon_id: str):
    addon = addon_modules.get(addon_id)
    if not addon:
        raise HTTPException(status_code=404, detail={"error": "Addon not found"})
    return addon.getManifest() if hasattr(addon, 'getManifest') else getattr(addon, 'manifest', {})

# ==========================================
# 6. INSTRUCTION ENDPOINTLERİ (Flutter ile haberleşme)
# ==========================================

@app.post("/api/addon/{addon_id}/catalog")
async def handle_catalog(addon_id: str, request: Request):
    addon = addon_modules.get(addon_id)
    if not addon or not hasattr(addon, 'handleCatalog'):
        raise HTTPException(status_code=404, detail={"error": "Addon or method not found"})
    
    body = await request.json()
    print(f"\n📋 [{addon_id}] CATALOG instruction request")
    
    try:
        result = await addon.handleCatalog(body) # Async varsayıyoruz
        return result
    except Exception as e:
        print(f"❌ [{addon_id}] Catalog error: {str(e)}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@app.post("/api/addon/{addon_id}/meta")
async def handle_meta(addon_id: str, request: Request):
    addon = addon_modules.get(addon_id)
    if not addon or not hasattr(addon, 'handleMeta'):
        raise HTTPException(status_code=404, detail={"error": "Addon or method not found"})
    
    body = await request.json()
    print(f"\n📺 [{addon_id}] META instruction request")
    
    try:
        result = await addon.handleMeta(body)
        return result
    except Exception as e:
        print(f"❌ [{addon_id}] Meta error: {str(e)}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@app.post("/api/addon/{addon_id}/stream")
async def handle_stream(addon_id: str, request: Request):
    addon = addon_modules.get(addon_id)
    if not addon or not hasattr(addon, 'handleStream'):
        raise HTTPException(status_code=404, detail={"error": "Addon or method not found"})
    
    body = await request.json()
    print(f"\n🎬 [{addon_id}] STREAM instruction request")
    
    try:
        result = await addon.handleStream(body)
        return result
    except Exception as e:
        print(f"❌ [{addon_id}] Stream error: {str(e)}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

# ==========================================
# 7. FETCH RESULT ENDPOINTİ (Flutter'dan dönen veriyi işleme)
# ==========================================

@app.post("/api/fetch-result")
async def process_fetch_result(request: Request):
    body = await request.json()
    addon_id = body.get('addonId')
    request_id = body.get('requestId')
    purpose = body.get('purpose')
    url = body.get('url', '')
    status = body.get('status')
    error = body.get('error')
    
    print(f"\n📥 [Fetch Result] Received from Flutter")
    print(f"   Addon: {addon_id} | Purpose: {purpose} | Status: {status}")
    
    if not addon_id:
        return {"success": False, "error": "addonId required"}
        
    addon = addon_modules.get(addon_id)
    if not addon or not hasattr(addon, 'processFetchResult'):
        return {"success": False, "error": "Addon does not support processFetchResult"}
        
    if error or status != 200:
        print(f"⚠️ [Fetch Result] Fetch failed: {error or f'HTTP {status}'}")
        # Hata durumunda hemen dönmek yerine addon'a iletelim ki domain rotation vs yapabilsin
        # return {"success": False, "error": error or f"HTTP {status}", "data": None}

    try:
        base_url = str(request.base_url).rstrip('/')
        addon_manifest_url = f"{base_url}/api/addon/{addon_id}/manifest.json"
        
        # Python tarafındaki metoduna ek parametreyi geçiriyoruz
        body['addonManifestUrl'] = addon_manifest_url
        
        result = await addon.processFetchResult(body)
        
        # Extractor mantığı eklenebilir (Node.js'teki videoExtractors)
        # if result.get('ok') is True and purpose.startswith('extract_'): ...

        print(f"✅ [Fetch Result] Processed successfully")
        return {"success": True, "data": result}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ [Fetch Result] Processing error: {str(e)}")
        return {"success": False, "error": str(e)}

# ==========================================
# 8. ADMIN (YÖNETİM) ENDPOINTLERİ
# ==========================================

@app.get("/api/admin/config", dependencies=[Depends(check_auth)])
async def get_admin_config():
    return {"success": True, "config": addon_config}

@app.post("/api/admin/addon/{addon_id}/config", dependencies=[Depends(check_auth)])
async def update_addon_config(addon_id: str, request: Request):
    body = await request.json()
    
    if addon_id not in addon_modules:
        raise HTTPException(status_code=404, detail="Addon not found")
        
    if addon_id not in addon_config['addons']:
        addon_config['addons'][addon_id] = {}
        
    for key in ['baseUrl', 'headers', 'cookies', 'enabled']:
        if key in body:
            addon_config['addons'][addon_id][key] = body[key]
            
    save_config()
    return {
        "success": True,
        "message": f"{addon_id} yapılandırması güncellendi",
        "config": addon_config['addons'][addon_id]
    }

@app.post("/api/admin/password", dependencies=[Depends(check_auth)])
async def update_admin_password(request: Request):
    body = await request.json()
    new_password = body.get('newPassword')
    
    if not new_password or len(new_password) < 4:
        raise HTTPException(status_code=400, detail="Şifre en az 4 karakter olmalıdır")
        
    addon_config['adminPassword'] = new_password
    save_config()
    return {"success": True, "message": "Admin şifresi güncellendi"}

@app.post("/api/admin/restart", dependencies=[Depends(check_auth)])
async def restart_server():
    print('\n🔄 Server restart requested by admin...')
    # FastAPI'yi programatik olarak sonlandırıyoruz (PM2 otomatik başlatır)
    asyncio.get_event_loop().call_later(1.0, sys.exit, 0)
    return {"success": True, "message": "Sunucu yeniden başlatılıyor..."}

@app.post("/api/admin/stop", dependencies=[Depends(check_auth)])
async def stop_all_addons():
    for aid in addon_config['addons']:
        addon_config['addons'][aid]['enabled'] = False
    save_config()
    return {"success": True, "message": "Tüm eklentiler durduruldu"}

@app.post("/api/admin/start", dependencies=[Depends(check_auth)])
async def start_all_addons():
    for aid in addon_config['addons']:
        addon_config['addons'][aid]['enabled'] = True
    save_config()
    return {"success": True, "message": "Tüm eklentiler başlatıldı"}

@app.get("/api/admin/stats", dependencies=[Depends(check_auth)])
async def get_admin_stats():
    enabled_count = sum(1 for a in addon_config['addons'].values() if a.get('enabled', True))
    disabled_count = len(addon_config['addons']) - enabled_count
    
    stats = {
        "totalAddons": len(addon_modules),
        "enabledAddons": enabled_count,
        "disabledAddons": disabled_count,
        "addons": {}
    }
    
    for aid, addon in addon_modules.items():
        manifest = addon.getManifest() if hasattr(addon, 'getManifest') else getattr(addon, 'manifest', {})
        conf = addon_config['addons'].get(aid, {})
        stats['addons'][aid] = {
            "name": manifest.get('name', aid),
            "enabled": conf.get('enabled', True),
            "baseUrl": conf.get('baseUrl', 'N/A')
        }
        
    return {"success": True, "stats": stats}

# ==========================================
# 9. SUNUCUYU BAŞLATMA
# ==========================================

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 3000))
    print(f"\n✅ Server running on port {PORT}")
    print(f"🌐 Health: http://localhost:{PORT}/health")
    print(f"📋 Addons: http://localhost:{PORT}/api/addons")
    print(f"🔐 Admin Panel: http://localhost:{PORT}/public/admin.html\n")
    
    # EĞER DOSYANIN ADI main.py İSE:
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)