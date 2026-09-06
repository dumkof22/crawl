"""
catalog_cache.py — Faz 2: backend paylaşımlı katalog sayfa cache'i + arama indeksi.

`main.py` bunun etrafına şeffaf bir read-through / write-through katman koyar;
`addons/*.py` dosyaları DEĞİŞMEZ. Zaten `{metas}` döndüren eklentiler otomatik
cache'lenir; talimat (`instructions`) döndürenler için `main.py` talimata bir
`__cache` anahtarı enjekte eder ve `/api/fetch-result` dönüşünde parse edilmiş
metaları o anahtarla saklar.

Günün ilk kullanıcısı gerçek fetch yapar ("öder"), aynı gün aynı sayfayı isteyen
herkes doğrudan `{metas}` alır → N×fetch ≈ 1×fetch. Birikmiş metalardan
sunucu-taraflı arama (`search`) sunulur.

Depolama tamamen in-memory (tek uvicorn worker — Render free). Spindown'da
(~15 dk boşta) RAM temizlenir; ilk istekte yeniden ısınır (kabul edilebilir).
Kalıcılık / çok worker için `REDIS_URL` yolu — # TODO (aynı API'yi Redis'e yaz).
"""

from __future__ import annotations

import os
import time
from collections import OrderedDict
from datetime import datetime, timezone

# ── Ayarlar (env ile override edilebilir) ───────────────────────────────────
CATALOG_CACHE_TTL = int(os.environ.get("CATALOG_CACHE_TTL", 6 * 3600))          # 6 sa, kayan
CATALOG_CACHE_MAX_PAGES = int(os.environ.get("CATALOG_CACHE_MAX_PAGES", 5000))  # LRU tavan
SEARCH_INDEX_MAX_PER_ADDON = int(os.environ.get("SEARCH_INDEX_MAX_PER_ADDON", 20000))
CATALOG_CACHE_MAX_SKIP = int(os.environ.get("CATALOG_CACHE_MAX_SKIP", 50000))   # üstünü cache'leme

# Çok-talimatlı katalog fetch'i (bir sayfa = birkaç URL) sırasında aynı sayfaya
# kısa sürede gelen parçalar birleştirilir; bu pencereden sonra gelen yazı
# sayfayı tamamen değiştirir (re-crawl).
_MERGE_WINDOW = 120

# ── Depolar ─────────────────────────────────────────────────────────────────
# _PAGES: LRU — (addon_id, catalog_id, skip) -> {"ts": float, "metas": list}
_PAGES: "OrderedDict[tuple, dict]" = OrderedDict()
# _INDEX: addon_id -> OrderedDict(meta_id -> meta)  (tüm put_page'lerden birikir)
_INDEX: "dict[str, OrderedDict]" = {}


# ── Türkçe normalize (Flutter TextUtils.normalizeForSearch ile aynı mantık) ──
_TR_MAP = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u",
    "ş": "s", "Ş": "s", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def normalize(s) -> str:
    """küçük harf + Türkçe karakter katlama + harf/rakam dışını (boşluk, tire,
    noktalama) at. Substring eşleşmesi bunun üzerinde yapılır."""
    if not s:
        return ""
    s = str(s).translate(_TR_MAP).lower()
    return "".join(ch for ch in s if ch.isalnum())


def _now_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


# ── Sayfa cache ─────────────────────────────────────────────────────────────
def get_page(addon_id, catalog_id, skip):
    """TTL kontrollü, kayan-süreli sayfa okuması. Miss / expire → None."""
    if not addon_id or not catalog_id:
        return None
    try:
        key = (addon_id, catalog_id, int(skip or 0))
    except (TypeError, ValueError):
        return None
    e = _PAGES.get(key)
    if not e:
        return None
    if time.time() - e["ts"] >= CATALOG_CACHE_TTL:
        _PAGES.pop(key, None)
        return None
    e["ts"] = time.time()          # kayan süre: aktif tarama cache'i canlı tutar
    _PAGES.move_to_end(key)        # LRU tazele
    return e["metas"]


def put_page(addon_id, catalog_id, skip, metas, *, merge=False):
    """Sayfayı yazar, arama indeksini günceller, LRU/limit uygular.
    Tamamen best-effort — geçersiz girdide sessizce çıkar."""
    if not addon_id or not catalog_id or not isinstance(metas, list):
        return
    try:
        skip = int(skip or 0)
    except (TypeError, ValueError):
        return
    if skip < 0 or skip > CATALOG_CACHE_MAX_SKIP:
        return

    key = (addon_id, catalog_id, skip)
    existing = _PAGES.get(key)

    if merge and existing and (time.time() - existing["ts"] < _MERGE_WINDOW):
        # Çok-talimatlı katalog fetch'i: parçaları id ile dedupe ederek birleştir.
        seen = set()
        stored = []
        for m in list(existing["metas"]) + metas:
            if not isinstance(m, dict):
                continue
            mid = m.get("id")
            if mid is not None and mid in seen:
                continue
            if mid is not None:
                seen.add(mid)
            stored.append(m)
    else:
        stored = [m for m in metas if isinstance(m, dict)]

    _PAGES[key] = {"ts": time.time(), "metas": stored}
    _PAGES.move_to_end(key)

    # Arama indeksi — meta'ları id ile dedupe ederek biriktir.
    idx = _INDEX.setdefault(addon_id, OrderedDict())
    for m in stored:
        mid = m.get("id")
        if not mid:
            continue
        if mid in idx:
            idx.move_to_end(mid)
        idx[mid] = m
    while len(idx) > SEARCH_INDEX_MAX_PER_ADDON:
        idx.popitem(last=False)

    # LRU tavan
    while len(_PAGES) > CATALOG_CACHE_MAX_PAGES:
        _PAGES.popitem(last=False)


def search(addon_id, query, type=None, limit=150):
    """`_INDEX[addon_id]` üzerinde normalize edilmiş substring eşleşmesi.
    En taze eklenen metalar önce döner. `type` verilirse `meta['type']` filtresi."""
    idx = _INDEX.get(addon_id)
    if not idx:
        return []
    q = normalize(query)
    if len(q) < 2:
        return []
    out = []
    for m in reversed(idx.values()):
        if type and m.get("type") != type:
            continue
        hay = m.get("name") or m.get("title") or ""
        if q in normalize(hay):
            out.append(m)
            if len(out) >= limit:
                break
    return out


def summary(addon_id):
    """{catalog_id: {"count": int, "last_crawled": iso|None, "max_skip": int}}"""
    cats = {}
    for (aid, cid, skip), e in _PAGES.items():
        if aid != addon_id:
            continue
        c = cats.setdefault(cid, {"count": 0, "_ts": 0.0, "max_skip": 0})
        c["count"] += len(e["metas"])
        c["max_skip"] = max(c["max_skip"], skip)
        c["_ts"] = max(c["_ts"], e["ts"])
    return {
        cid: {
            "count": c["count"],
            "last_crawled": _now_iso(c["_ts"]) if c["_ts"] else None,
            "max_skip": c["max_skip"],
        }
        for cid, c in cats.items()
    }


def invalidate(addon_id=None, catalog_id=None):
    """addon_id=None → tümü. catalog_id=None → o eklentinin tüm sayfaları + indeksi."""
    if addon_id is None:
        _PAGES.clear()
        _INDEX.clear()
        return
    for key in [k for k in _PAGES
                if k[0] == addon_id and (catalog_id is None or k[1] == catalog_id)]:
        _PAGES.pop(key, None)
    if catalog_id is None:
        _INDEX.pop(addon_id, None)


def stats():
    return {
        "pages": len(_PAGES),
        "index": {aid: len(idx) for aid, idx in _INDEX.items()},
        "ttl_seconds": CATALOG_CACHE_TTL,
        "max_pages": CATALOG_CACHE_MAX_PAGES,
    }
