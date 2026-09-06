import base64
import json
import re
import hashlib
import hmac
import urllib.parse
import random
import time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

def base64_encode_safe(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8').replace('=', '')

def decrypt_aes(encrypted_data_with_iv, key_str):
    try:
        key = key_str.encode('utf8')
        iv = key_str.encode('utf8')
        
        encrypted_part1 = encrypted_data_with_iv.split(':')[0]
        cipher1 = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor1 = cipher1.decryptor()
        
        pad1 = encrypted_part1 + '=' * (-len(encrypted_part1) % 4)
        dec1_padded = decryptor1.update(base64.b64decode(pad1)) + decryptor1.finalize()
        unpadder1 = padding.PKCS7(128).unpadder()
        dec1 = unpadder1.update(dec1_padded) + unpadder1.finalize()
        decrypted1 = dec1.decode('utf8')
        
        encrypted_part2 = decrypted1.split(':')[0]
        cipher2 = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor2 = cipher2.decryptor()
        
        pad2 = encrypted_part2 + '=' * (-len(encrypted_part2) % 4)
        dec2_padded = decryptor2.update(base64.b64decode(pad2)) + decryptor2.finalize()
        unpadder2 = padding.PKCS7(128).unpadder()
        dec2 = unpadder2.update(dec2_padded) + unpadder2.finalize()
        
        print(f"🐛 [InatBox Debug] Decrypted data successfully. Length: {len(dec2)}")
        return dec2.decode('utf8')
    except Exception as e:
        print(f"❌ Decryption error: {e}")
        return None

def _aes_cbc_seg(key_str, data_with_iv):
    """One AES/CBC/PKCS7 layer as the app's f63.p() does it:
    key = key string padded/trimmed to 16 bytes, IV = base64(second ':' segment)."""
    k = (key_str + '0' * 16)[:16] if len(key_str) < 16 else key_str[:16]
    parts = data_with_iv.split(':')
    if len(parts) < 2:
        raise ValueError("missing iv segment")
    iv = base64.b64decode(parts[1] + '=' * (-len(parts[1]) % 4))
    ct = base64.b64decode(parts[0] + '=' * (-len(parts[0]) % 4))
    dec = Cipher(algorithms.AES(k.encode('utf-8')), modes.CBC(iv), backend=default_backend()).decryptor()
    raw = dec.update(ct) + dec.finalize()
    unpad = padding.PKCS7(128).unpadder()
    return (unpad.update(raw) + unpad.finalize()).decode('utf-8', 'replace')

def decrypt_lb_sh_3(body, regex1, regex2):
    """tekli_regex_lb_sh_3 player payload: two AES layers (Regex1 then Regex2),
    result is JSON {chUrl, playHost, playSH1} with a trailing integrity hash."""
    layer1 = _aes_cbc_seg(regex1, body)
    layer2 = _aes_cbc_seg(regex2, layer1)
    m = re.search(r'\{.*\}', layer2, re.DOTALL)
    return json.loads(m.group(0) if m else layer2)

def vk_source_fix(url):
    if url and url.startswith('act'):
        return f"https://vk.com/al_video.php?{url}"
    return url

# InatBox chHeaders use dash-less keys (UserAgent, XRequestedWith, Referer).
# Players / CDNs only honour real HTTP header names, so map them before use.
_INAT_HEADER_KEYMAP = {
    'useragent': 'User-Agent',
    'user-agent': 'User-Agent',
    'referer': 'Referer',
    'referrer': 'Referer',
    'xrequestedwith': 'X-Requested-With',
    'x-requested-with': 'X-Requested-With',
    'origin': 'Origin',
    'cookie': 'Cookie',
}

_LIVE_FALLBACK_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                     '(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36')

def _build_live_stream_headers(default_ua, item):
    """Playback headers for a direct live_url stream.

    Mirrors what the InatBox APK's ExoPlayer sends (verified against
    PlayerActivity / wi.smali): only User-Agent / Referer / X-Requested-With
    from the channel's own chHeaders, plus a fixed 'Cache-Control: no-cache'.
    The 'speedrestapi' UA and 'com.bp.box' X-Requested-With belong only to
    InatBox's own API — CDNs (e.g. mediatriple.net) reject them with 403 — so
    they are never forwarded to the media request.
    """
    ch = normalize_ch_headers(item.get('chHeaders'))
    headers = {'Cache-Control': 'no-cache'}
    ua = ch.get('User-Agent')
    if not ua or ua == 'speedrestapi':
        ua = default_ua if (default_ua and default_ua != 'speedrestapi') else _LIVE_FALLBACK_UA
    headers['User-Agent'] = ua
    for k in ('Referer', 'X-Requested-With', 'Origin', 'Cookie'):
        if ch.get(k):
            headers[k] = ch[k]
    try:
        reg = item.get('chReg')
        if isinstance(reg, str) and reg and reg not in ('null', 'NULL'):
            reg = json.loads(reg)
        if isinstance(reg, list) and reg and isinstance(reg[0], dict) and reg[0].get('playSH2'):
            headers['Cookie'] = reg[0]['playSH2']
    except Exception as e:
        print(f"⚠️  _build_live_stream_headers chReg: {e}")
    return headers

def normalize_ch_headers(raw):
    """Return a dict with real HTTP header names from an InatBox chHeaders entry.
    Accepts a dict, a JSON string, or a list (first element is used)."""
    try:
        if isinstance(raw, str):
            raw = json.loads(raw) if raw and raw != 'null' else None
        if isinstance(raw, list):
            raw = raw[0] if raw else None
        if not isinstance(raw, dict):
            return {}
        out = {}
        for k, v in raw.items():
            if v is None:
                continue
            sv = str(v).strip()
            # InatBox stores absent header values as the literal string "null"
            if not sv or sv.lower() in ('null', 'none', 'undefined'):
                continue
            out[_INAT_HEADER_KEYMAP.get(str(k).strip().lower(), str(k))] = sv
        return out
    except Exception as e:
        print(f"⚠️  normalize_ch_headers: {e}")
        return {}

# Catalog ids that are live-TV channel lists (metas -> type 'tv', square poster)
TV_CATALOGS = {
    'spor', 'list1', 'list2', 'list3', 'sinema', 'belgesel',
    'ulusal', 'haber', 'cocuk', 'eba', 'dini',
}

def _strip_mode(t):
    t = t or ''
    return t[:-5] if t.endswith('_mode') else t

def determine_content_type(item, catalog_id):
    dt = _strip_mode(item.get('diziType'))
    if dt == 'dizi': return 'series'
    if dt == 'film': return 'movie'
    if catalog_id in ['yabanci-dizi', 'yerli-dizi']: return 'series'
    ct = _strip_mode(item.get('chType'))
    if ct in ['live_url', 'live', 'tekli_regex_lb_sh_3', 'cable_sh']: return 'tv'
    if catalog_id in TV_CATALOGS: return 'tv'
    if ct: return 'movie'
    return 'movie'


# ── Katalog listesi cache ────────────────────────────────────────────────────
# 4K (~18k öğe) ve list2 (~12k öğe) gibi dev listeler her sayfa isteğinde 16 MB'lık
# gövdeyi yeniden indirip çözüyordu (skip=4200 => ~40 kez). Artık ilk sayfa (skip=0)
# tek gerçek fetch yapar ve çözülmüş TAM listeyi burada tutar; skip>0 sayfaları
# handleCatalog'tan doğrudan {'metas': dilim} olarak döner — fetch yok.
# NOT: Bu, eşleşen istemci yamasını gerektirir (katalog yanıtında 'instructions'
# yok, 'metas' var). Eski istemci bunu "boş sayfa" sanar; birlikte yayınla.
_CATALOG_CACHE = {}          # catalogId -> {'ts': float, 'items': list}
_CATALOG_CACHE_TTL = 1800    # 30 dk — kayan (her erişimde tazelenir)
_CATALOG_CACHE_MAX = 3       # aynı anda en fazla bu kadar dev katalog RAM'de


def _catalog_cache_get(cid):
    e = _CATALOG_CACHE.get(cid)
    if not e:
        return None
    if time.time() - e['ts'] >= _CATALOG_CACHE_TTL:
        _CATALOG_CACHE.pop(cid, None)
        return None
    e['ts'] = time.time()          # kayan süre: aktif tarama cache'i canlı tutar
    return e['items']


def _catalog_cache_put(cid, items):
    _CATALOG_CACHE[cid] = {'ts': time.time(), 'items': items}
    while len(_CATALOG_CACHE) > _CATALOG_CACHE_MAX:
        oldest = min(_CATALOG_CACHE, key=lambda k: _CATALOG_CACHE[k]['ts'])
        _CATALOG_CACHE.pop(oldest, None)


class InatBoxScraper:
    def __init__(self):
        self.CONFIG = {
            'contentUrl': 'https://diziboxen.help/CDN/001/002/dizibox/v2',
            'aesKey': 'GxGQWghI0aSiADee',
            'userAgent': 'speedrestapi',
            # HmacSHA256 key for the X-Sg request signature (baseUrl.HMK() in the app)
            'hmacKey': 'x7kkk0qmqz63kj68tla5i7u26192v7zqnnddhjgm'
        }
        # Server checks X-Ts against its own clock (self-corrects via the X-St
        # response header in the app). Bump this if the host clock drifts.
        self.TIME_OFFSET = 0

        cu = self.CONFIG['contentUrl']
        spr = 'https://sprboxs.bar/CDN/001/SPR/v2'
        # Mirrors the app's master menu (dizilab v2 ct.php). link_mode / destek /
        # "Hata Bildir" entries are intentionally left out.
        self.CATALOG_URLS = {
            # Canlı TV listeleri
            'list1': f"{cu}/tv/list1.php",
            'list2': f"{cu}/tv/list2.php",
            'list3': f"{cu}/tv/list3.php",
            'spor': f"{spr}/spor_v3.php",
            'sinema': f"{cu}/tv/sinema.php",
            'belgesel': f"{cu}/tv/belgesel.php",
            'ulusal': f"{cu}/tv/ulusal.php",
            'haber': f"{cu}/tv/haber.php",
            'eba': f"{cu}/tv/eba.php",
            'cocuk': f"{cu}/tv/cocuk.php",
            'dini': f"{cu}/tv/dini.php",
            # Spor VOD
            'derbiler': f"{spr}/derbiler.php",
            'tod': f"{spr}/ccc/a/index.php",
            # Platformlar
            'exxen': f"{cu}/ex/index.php",
            'gain': f"{cu}/ga/index.php",
            'netflix': f"{cu}/nf/index.php",
            'hbo': f"{cu}/hb/index.php",
            'disney': f"{cu}/dsny/index.php",
            'amazon': f"{cu}/amz/index.php",
            'tabii': f"{cu}/tbi/index.php",
            'mubi': f"{cu}/film/mubi.php",
            # Film / dizi
            'yerli-filmler': f"{cu}/film/yerli-filmler.php",
            'yabanci-dizi': f"{cu}/yabanci-dizi/index.php",
            'yerli-dizi': f"{cu}/yerli-dizi/index.php",
            # 4K Film — app 10 ayrı sayfa listeliyor; her biri ~17-18k öğelik
            # bağımsız dev liste, o yüzden sayfa/varyant başına ayrı katalog id.
            '4k01web': 'https://4k.filmizleeeee.cfd/4k/01/public/catalog-web.php',
            '4k01exo': 'https://4k.filmizleeeee.cfd/4k/01/public/catalog-exo.php',
            '4k02web': 'https://4k.filmizleeeee.cfd/4k/02/public/catalog-web.php',
            '4k03web': 'https://4k.filmizleeeee.cfd/4k/03/public/catalog-web.php',
            '4k03exo': 'https://4k.filmizleeeee.cfd/4k/03/public/catalog-exo.php',
            '4k04web': 'https://4k.filmizleeeee.cfd/4k/04/public/catalog-web.php',
            '4k04exo': 'https://4k.filmizleeeee.cfd/4k/04/public/catalog-exo.php',
            '4k06web': 'https://4k.filmizleeeee.cfd/4k/06/public/catalog-web.php',
            '4k06exo': 'https://4k.filmizleeeee.cfd/4k/06/public/catalog-exo.php',
            '4k07web': 'https://4k.filmizleeeee.cfd/4k/07/public/catalog-web.php',
        }

        # Catalogs fetched with GET + a fixed (non per-request) AES key.
        self.GET_CATALOGS = {'list3': 'a4osa8x1yl4w3vrk'}

        self.manifest = {
            'id': 'com.keyiflerolsun.inatbox',
            'version': '3.0.12',
            'name': 'InatBox',
            'description': 'Turkish TV channels, movies and series streaming (Python Port)',
            'logo': 'https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEh3vCp6N1K4bECoYRQD-cisJF2_6V_Hk01ZhDmoPR2JuM8O5qr4MqrPO1munM9cRlleBBSK6odYhLtDBWv4E3vhPhynlmS5hVVtJZShHoGA5REQ8_3v8SIlccTEqzVQu2UJyNYQdJNrKIfWy66RQeT0D-CcmFCbHPz5023H6p2v5fv4NVloZ5Rqo_yGrIY/s320/iNat-Box-App.png',
            'resources': ['catalog', 'meta', 'stream'],
            'types': ['movie', 'series', 'tv'],
            'catalogs': [
                {'type': 'tv', 'id': 'list1', 'name': '📺 Liste 1 - TR', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'tv', 'id': 'list2', 'name': '📺 Liste 2 - GLB', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'tv', 'id': 'list3', 'name': '📺 Liste 3 - TR', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'tv', 'id': 'spor', 'name': '⚽ Spor Kanalları', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'tv', 'id': 'sinema', 'name': '🎬 Sinema Kanalları', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'tv', 'id': 'belgesel', 'name': '🌍 Belgesel Kanalları', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'tv', 'id': 'ulusal', 'name': '📡 Ulusal Kanallar', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'tv', 'id': 'haber', 'name': '📰 Haber Kanalları', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'tv', 'id': 'eba', 'name': '🎓 EBA TV', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'tv', 'id': 'cocuk', 'name': '🧸 Çocuk Kanalları', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'tv', 'id': 'dini', 'name': '🕌 Dini Kanallar', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},

                {'type': 'movie', 'id': 'derbiler', 'name': '⚽ Derbiler', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'tod', 'name': '🎬 TOD', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},

                {'type': 'movie', 'id': 'exxen', 'name': '🎬 Exxen', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'gain', 'name': '🎬 Gain', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'netflix', 'name': '🎬 Netflix', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'hbo', 'name': '🎬 HBO Max (BluTV)', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'disney', 'name': '🎬 Disney+', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'amazon', 'name': '🎬 Amazon Prime', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'tabii', 'name': '🎬 Tabii', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'mubi', 'name': '🎬 MUBI', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'yerli-filmler', 'name': '🎬 Yerli Filmler', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},

                {'type': 'series', 'id': 'yabanci-dizi', 'name': '📺 Yabancı Diziler', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'yerli-dizi', 'name': '📺 Yerli Diziler', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},

                # 4K Film listeleri en sonda: her biri ~17-18k öğe, uzun sayfalama
                # yaptığı için diğer katalogları (canlı TV, platformlar) bekletmesin.
                {'type': 'movie', 'id': '4k01web', 'name': '🎬 4K Film 01 | Web', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': '4k01exo', 'name': '🎬 4K Film 01 | Exo', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': '4k02web', 'name': '🎬 4K Film 02 | Web', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': '4k03web', 'name': '🎬 4K Film 03 | Web', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': '4k03exo', 'name': '🎬 4K Film 03 | Exo', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': '4k04web', 'name': '🎬 4K Film 04 | Web', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': '4k04exo', 'name': '🎬 4K Film 04 | Exo', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': '4k06web', 'name': '🎬 4K Film 06 | Web', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': '4k06exo', 'name': '🎬 4K Film 06 | Exo', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': '4k07web', 'name': '🎬 4K Film 07 | Web', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},

                {'type': 'movie', 'id': 'inat_search', 'name': '🔍 Tümünde Ara', 'extra': [{'name': 'search', 'isRequired': True}, {'name': 'skip', 'isRequired': False}]}
            ],
            'idPrefixes': ['inatbox']
        }

    def getManifest(self):
        return self.manifest

    def _extract_tracks(self, content, sourceUrl, subtitles, audioTracks):
        """HTML/JS içeriğinden subtitle ve audio track çıkar"""
        tracks_patterns = [
            r'tracks\s*:\s*(\[[\s\S]*?\])\s*[,}]',
            r'tracks\s*:\s*(\[[\s\S]*?\])',
            r'"tracks"\s*:\s*(\[[\s\S]*?\])',
        ]
        
        for pattern in tracks_patterns:
            tracks_match = re.search(pattern, content)
            if tracks_match:
                try:
                    raw = tracks_match.group(1)
                    raw = re.sub(r',\s*\]', ']', raw)
                    tracksData = json.loads(raw)
                    
                    for track in tracksData:
                        kind = track.get('kind', '').lower()
                        file_url = track.get('file', '')
                        
                        if not file_url:
                            continue
                        
                        if not file_url.startswith('http'):
                            file_url = urllib.parse.urljoin(sourceUrl, file_url)
                        
                        label = track.get('label') or track.get('language') or ''
                        
                        if kind in ['captions', 'subtitles']:
                            sub_id = label.lower().replace(' ', '_') if label else 'tr'
                            if not any(s['url'] == file_url for s in subtitles):
                                subtitles.append({'id': sub_id, 'url': file_url, 'lang': label or 'Türkçe'})
                        elif kind in ['audio', 'audiotrack']:
                            audio_id = label.lower().replace(' ', '_') if label else 'default'
                            if not any(a['url'] == file_url for a in audioTracks):
                                audioTracks.append({'id': audio_id, 'url': file_url, 'lang': label or 'Orijinal'})
                    
                    if subtitles or audioTracks:
                        break
                except:
                    continue

    def _extract_item_subtitles(self, item, subtitles):
        try:
            chReg = item.get('chReg')
            if chReg and isinstance(chReg, str) and chReg.strip().lower() not in ('null', ''):
                chReg = json.loads(chReg)
            if chReg and not isinstance(chReg, str):
                if isinstance(chReg, list):
                    for regItem in chReg:
                        if regItem.get('Subtitle'):
                            for part in regItem['Subtitle'].split(','):
                                m = re.search(r'\[([^\]]+)\]', part)
                                if m:
                                    lang = m.group(1)
                                    subUrl = part.replace(f"[{lang}]", '').strip()
                                    if subUrl:
                                        sub_id = lang.lower().replace(' ', '_')
                                        if not any(s['url'] == subUrl for s in subtitles):
                                            subtitles.append({'id': sub_id, 'url': subUrl, 'lang': lang})
                        if regItem.get('SubtitleUrl'):
                            lang = regItem.get('SubtitleLang') or regItem.get('SubtitleName') or 'Türkçe'
                            sub_id = lang.lower().replace(' ', '_')
                            if not any(s['url'] == regItem['SubtitleUrl'] for s in subtitles):
                                subtitles.append({'id': sub_id, 'url': regItem['SubtitleUrl'], 'lang': lang})
        except Exception as e: print("EXCEPTION IN LOOP:", e)
        
        try:
            if item.get('SubtitleUrl'):
                lang = item.get('SubtitleLang') or item.get('SubtitleName') or 'Türkçe'
                sub_id = lang.lower().replace(' ', '_')
                if not any(s['url'] == item['SubtitleUrl'] for s in subtitles):
                    subtitles.append({'id': sub_id, 'url': item['SubtitleUrl'], 'lang': lang})
            if item.get('diziSubUrl'):
                lang = 'Türkçe'
                sub_id = 'tr'
                if not any(s['url'] == item['diziSubUrl'] for s in subtitles):
                    subtitles.append({'id': sub_id, 'url': item['diziSubUrl'], 'lang': lang})
        except Exception as e: print("EXCEPTION IN LOOP:", e)

    def get_aes_key(self, url):
        import string
        # Every endpoint (incl. speedrestapi /rest/api/) now takes a fresh random
        # 16-char key; the server encrypts its response with the key we send.
        letters_and_digits = string.ascii_letters + string.digits
        random_key = ''.join(random.choice(letters_and_digits) for i in range(16))

        print(f"🔑 [Key Generator] {url} için üretilen yeni AES: {random_key}")
        return random_key

    def buildRequestBody(self, extraFields=None, aesKey=None):
        key = aesKey or self.CONFIG['aesKey']
        base = {'1': key, '0': key}
        if extraFields and extraFields.get('q'):
            base['q'] = extraFields['q']
        parts = [f"{urllib.parse.quote(str(k))}={urllib.parse.quote(str(v))}" for k, v in base.items()]
        return "&".join(parts)

    def _sign_headers(self, url, body, method='POST'):
        """X-Ts / X-Nc / X-Sg request signature (app class n41.c).

        msg = METHOD + "\\n" + encodedPath + "\\n" + ts + "\\n" + nonce + "\\n" + sha256hex(body)
        X-Sg = HMAC_SHA256(hmacKey, msg)  (lowercase hex).  GET => body is "".
        """
        try:
            ts = str(int(time.time()) + self.TIME_OFFSET)
            nonce = '%032x' % random.getrandbits(128)
            path = urllib.parse.urlparse(url).path or '/'
            body_sha = hashlib.sha256((body or '').encode('utf-8')).hexdigest()
            msg = f"{method}\n{path}\n{ts}\n{nonce}\n{body_sha}"
            sig = hmac.new(self.CONFIG['hmacKey'].encode('utf-8'),
                           msg.encode('utf-8'), hashlib.sha256).hexdigest()
            return {'X-Ts': ts, 'X-Nc': nonce, 'X-Sg': sig}
        except Exception as e:
            print(f"❌ [InatBox] Signing error: {e}")
            return {}

    def _api_headers(self, url, body, method='POST'):
        headers = {
            'Cache-Control': 'no-cache',
            'Referer': 'https://speedrestapi.com/',
            'X-Requested-With': 'com.bp.box',
            'User-Agent': self.CONFIG['userAgent']
        }
        if method == 'POST':
            headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        headers.update(self._sign_headers(url, body if method == 'POST' else '', method))
        return headers

    def _resolve_lb_sh_3(self, item, body, addonManifestUrl=None):
        """tekli_regex_lb_sh_3(_mode): decrypt the player payload (Regex1 -> Regex2)
        and return the direct stream from its chUrl."""
        chReg = item.get('chReg') or []
        if isinstance(chReg, str):
            try: chReg = json.loads(chReg)
            except Exception: chReg = []
        reg = chReg[0] if isinstance(chReg, list) and chReg else (chReg if isinstance(chReg, dict) else {})
        r1 = reg.get('Regex1')
        r2 = reg.get('Regex2') or reg.get('Regex2p')
        if not (body and r1 and r2):
            return {'streams': []}
        try:
            play = decrypt_lb_sh_3(body, r1, r2)
        except Exception as e:
            print(f"❌ [InatBox] lb_sh_3 decrypt failed: {e}")
            return {'streams': []}

        streamUrl = play.get('chUrl') or play.get('url')
        if not streamUrl:
            return {'streams': []}

        name = item.get('chName') or item.get('diziName') or 'InatBox'
        headers = _build_live_stream_headers(self.CONFIG['userAgent'], item)

        stream = {
            'url': streamUrl,
            'name': f"InatBox\n{name}",
            'title': name,
            'behaviorHints': {'notWebReady': False, 'httpHeaders': headers},
            'addonName': 'inatbox',
            'addonManifestUrl': addonManifestUrl
        }
        subtitles = []
        self._extract_item_subtitles(item, subtitles)
        if subtitles:
            stream['subtitles'] = subtitles
        print(f"🐛 [InatBox Debug] lb_sh_3 resolved: {streamUrl}")
        return {'streams': [stream]}

    def _build_ch_headers(self, item, base=None):
        headers = dict(base or {})
        try:
            ch = item.get('chHeaders')
            if isinstance(ch, str) and ch not in ('null', 'NULL'):
                ch = json.loads(ch)
            if isinstance(ch, list) and ch:
                ch = ch[0]
            if isinstance(ch, dict):
                if ch.get('UserAgent'): headers['User-Agent'] = ch['UserAgent']
                if ch.get('Referer'): headers['Referer'] = ch['Referer']
        except Exception as e:
            print("EXCEPTION IN LOOP:", e)
        return headers

    _MAX_TRY = 4

    def _resolve_4k(self, metadata, body, addonManifestUrl=None):
        """4K Film (web_mode / tekli_regex_mode): exo.php returned a plaintext,
        ready-to-play stream URL (a headerless 4k.filmizleeeee.cfd/stream.m3u8
        wrapper, or a direct .m3u8 / .mp4). exo.php is flaky (502 / rate limits),
        so retry a few times before giving up."""
        item = metadata.get('originalItem') or {}
        text = (body or '').strip()
        first = text.splitlines()[0].strip() if text else ''
        is_media = first.startswith('http') and (
            '.m3u8' in first.lower() or '.mp4' in first.lower()
            or '/stream.m3u8?' in first.lower() or '/hls' in first.lower())

        if not is_media:
            tries = int(metadata.get('try', 1))
            if tries < self._MAX_TRY and metadata.get('exoUrl'):
                print(f"⚠️ [InatBox] 4K exo.php bad body (try {tries}): {text[:80]!r} — retrying")
                md = dict(metadata); md['try'] = tries + 1
                return {'instructions': [{
                    'requestId': f"inat-4k-{int(time.time()*1000)}-{random.randint(1000,9999)}",
                    'purpose': 'stream_4k_exo',
                    'url': metadata['exoUrl'],
                    'method': 'GET',
                    'headers': {'Accept': '*/*', 'Cache-Control': 'no-cache',
                                'User-Agent': metadata.get('ua') or self.CONFIG['userAgent'],
                                'Referer': metadata.get('referer') or '',
                                'X-Requested-With': 'XMLHttpRequest'},
                    'metadata': md,
                }]}
            # exo.php exhausted — offer the web.php proxy as a webview fallback
            # (that page renders a self-contained player, same as the app's
            # web_mode WebActivity).
            web_url = (metadata.get('exoUrl') or '').replace('/exo.php?', '/web.php?')
            if web_url:
                name = item.get('chName') or item.get('diziName') or 'InatBox 4K'
                print(f"⚠️ [InatBox] 4K exo.php failed — webview fallback: {web_url}")
                return {'streams': [{
                    'name': f"InatBox 4K (Web)\n{name}",
                    'title': 'Tarayıcıda Oynat',
                    'externalUrl': web_url,
                    'behaviorHints': {'notWebReady': True},
                    'addonName': 'inatbox',
                    'addonManifestUrl': addonManifestUrl,
                }]}
            print(f"❌ [InatBox] 4K exo.php gave no media url: {text[:160]!r}")
            return {'streams': []}

        low = first.lower()
        name = item.get('chName') or item.get('diziName') or 'InatBox 4K'
        is_mp4 = '.mp4' in low and '.m3u8' not in low
        headers = self._build_ch_headers(item, {'User-Agent': self.CONFIG['userAgent']})
        stream = {
            'url': first,
            'name': f"InatBox 4K\n{name}",
            'title': name,
            'type': 'mp4' if is_mp4 else 'hls',
            'behaviorHints': {'notWebReady': False, 'httpHeaders': headers},
            'addonName': 'inatbox',
            'addonManifestUrl': addonManifestUrl,
        }
        subtitles = []
        self._extract_item_subtitles(item, subtitles)
        if subtitles:
            stream['subtitles'] = subtitles

        # HLS ise master playlist'i bir kez çekip #EXT-X-MEDIA:TYPE=SUBTITLES
        # parçalarını ayrı altyazı olarak çıkar. `stream.m3u8?url=` wrapper'ı
        # (4k03/04/07 imagestoo kaynakları) harici .vtt altyazı taşıyor; oynatıcı
        # HLS altyazısını otomatik almazsa bunlar kaybolurdu.
        if not is_mp4 and '.m3u8' in low and not metadata.get('subsPass'):
            md = dict(metadata)
            md['pendingStream'] = stream
            md['subsPass'] = True
            return {'instructions': [{
                'requestId': f"inat-4ksub-{int(time.time()*1000)}-{random.randint(1000,9999)}",
                'purpose': 'stream_4k_m3u8',
                'url': first,
                'method': 'GET',
                'headers': {'Accept': '*/*',
                            'User-Agent': headers.get('User-Agent') or self.CONFIG['userAgent'],
                            'Referer': metadata.get('referer') or headers.get('Referer') or ''},
                'metadata': md,
            }]}

        print(f"🐛 [InatBox Debug] 4K resolved: {first}")
        return {'streams': [stream]}

    @staticmethod
    def _hls_subtitle_tracks(m3u8_text, base_url):
        """HLS master playlist'teki #EXT-X-MEDIA:TYPE=SUBTITLES satırlarını
        {id,url,lang} altyazı listesine çevir."""
        out = []
        for line in (m3u8_text or '').splitlines():
            if not line.startswith('#EXT-X-MEDIA:') or 'TYPE=SUBTITLES' not in line:
                continue
            mu = re.search(r'URI="([^"]+)"', line)
            if not mu:
                continue
            u = mu.group(1)
            if not u.startswith('http'):
                u = urllib.parse.urljoin(base_url, u)
            mn = re.search(r'NAME="([^"]*)"', line)
            ml = re.search(r'LANGUAGE="([^"]*)"', line)
            label = (mn.group(1) if mn else '') or (ml.group(1) if ml else '') or 'Altyazı'
            sid = ((ml.group(1) if ml else label) or 'sub').lower().replace(' ', '_')
            out.append({'id': sid, 'url': u, 'lang': label})
        return out

    def _resolve_4k_subs(self, metadata, body, addonManifestUrl=None):
        """4K HLS master playlist'ten harici altyazıları çekip pendingStream'e ekler.
        m3u8 boş/hatalı dönerse stream altyazısız (mevcut hâliyle) döner."""
        stream = dict(metadata.get('pendingStream') or {})
        if not stream:
            return {'streams': []}
        subs = list(stream.get('subtitles') or [])
        try:
            for t in self._hls_subtitle_tracks(body, stream.get('url', '')):
                if not any(x['url'] == t['url'] for x in subs):
                    subs.append(t)
        except Exception as e:
            print(f"⚠️ [InatBox] 4K m3u8 altyazı ayrıştırma: {e}")
        if subs:
            stream['subtitles'] = subs
        print(f"🐛 [InatBox Debug] 4K resolved: {stream.get('url')}  (+{len(subs)} altyazı)")
        return {'streams': [stream]}

    @staticmethod
    def _vk_ext_url(raw):
        """nok5 chUrl (`act=show&...&video=<oid>_<id>` or a full url) -> the
        video_ext.php embed page, which is far less bot-hostile than al_video.php."""
        m = re.search(r'video=(-?\d+)_(\d+)', raw or '')
        if m:
            return f"https://vk.com/video_ext.php?oid={m.group(1)}&id={m.group(2)}&hd=2"
        if raw and raw.startswith('http'):
            return raw
        return 'https://vk.com/al_video.php?' + (raw or '')

    def _nok5_instruction(self, item, vk_url, vk_ua, tries):
        headers = {'Accept': '*/*', 'User-Agent': vk_ua, 'Referer': 'https://vk.com/',
                   'Origin': 'https://vk.com', 'X-Requested-With': 'XMLHttpRequest',
                   'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8'}
        # First try a plain fetch; escalate to the webview once VK starts serving
        # its JS/anti-bot ("badbrowser") stub.
        hiddenweb = tries >= 2
        return {
            'requestId': f"inat-nok5-{int(time.time()*1000)}-{random.randint(1000,9999)}",
            'purpose': 'stream_nok5',
            'url': vk_url,
            'method': 'GET',
            'headers': headers,
            'metadata': {'originalItem': item, 'vkUrl': vk_url, 'vkUa': vk_ua,
                         'try': tries, 'hiddenweb': hiddenweb},
        }

    def _nok5_webview_fallback(self, item, vk_url, addonManifestUrl=None):
        if not vk_url:
            return {'streams': []}
        name = item.get('chName') or item.get('diziName') or 'InatBox'
        print(f"⚠️ [InatBox] nok5 — webview fallback: {vk_url}")
        return {'streams': [{
            'name': f"InatBox MUBI (Web)\n{name}",
            'title': 'Tarayıcıda Oynat',
            'externalUrl': vk_url,
            'behaviorHints': {'notWebReady': True},
            'addonName': 'inatbox',
            'addonManifestUrl': addonManifestUrl,
        }]}

    def _resolve_nok5(self, metadata, body, addonManifestUrl=None):
        """MUBI (nok5_mode): VK video_ext.php HTML -> chReg[0].Regex1 hls url.
        The okcdn.ru playlist needs the vk.com Referer + a desktop UA to play.
        VK intermittently answers with a `badbrowser.php` stub, so retry
        (escalating to the webview)."""
        item = metadata.get('originalItem') or {}
        blocked = bool(body) and 'badbrowser' in body
        if not body or blocked:
            tries = int(metadata.get('try', 1))
            if tries < self._MAX_TRY and metadata.get('vkUrl'):
                print(f"⚠️ [InatBox] nok5 VK blocked (try {tries}) — retrying")
                return {'instructions': [self._nok5_instruction(
                    item, metadata['vkUrl'], metadata.get('vkUa') or '', tries + 1)]}
            print("❌ [InatBox] nok5: VK still blocked after retries")
            return self._nok5_webview_fallback(item, metadata.get('vkUrl'), addonManifestUrl)

        rx = r'"hls[^"]*"\s*:\s*"\s*(.*?)\s*"'
        try:
            chReg = item.get('chReg')
            if isinstance(chReg, str) and chReg not in ('null', 'NULL'):
                chReg = json.loads(chReg)
            if isinstance(chReg, list) and chReg and chReg[0].get('Regex1'):
                rx = chReg[0]['Regex1']
        except Exception as e:
            print("EXCEPTION IN LOOP:", e)

        streamUrl = None
        try:
            m = re.search(rx, body)
            if m:
                streamUrl = m.group(1) if m.groups() else m.group(0)
        except Exception as e:
            print(f"❌ [InatBox] nok5 regex error: {e}")
        if not streamUrl:
            m2 = re.search(r'"hls(?:_[a-z0-9]+)?"\s*:\s*"(https:[^"]+)"', body)
            if m2:
                streamUrl = m2.group(1)
        if not streamUrl:
            tries = int(metadata.get('try', 1))
            if tries < self._MAX_TRY and metadata.get('vkUrl'):
                print(f"⚠️ [InatBox] nok5: no hls in VK response (try {tries}) — retrying")
                return {'instructions': [self._nok5_instruction(
                    item, metadata['vkUrl'], metadata.get('vkUa') or '', tries + 1)]}
            print("❌ [InatBox] nok5: no hls url in VK response")
            return self._nok5_webview_fallback(item, metadata.get('vkUrl'), addonManifestUrl)

        streamUrl = streamUrl.replace('\\/', '/').replace('\\u0026', '&').strip()

        vk_ua = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                 '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
        try:
            ch = item.get('chHeaders')
            if isinstance(ch, str) and ch not in ('null', 'NULL'):
                ch = json.loads(ch)
            if isinstance(ch, list) and ch and isinstance(ch[0], dict) and ch[0].get('UserAgent'):
                vk_ua = ch[0]['UserAgent']
        except Exception as e:
            print("EXCEPTION IN LOOP:", e)

        name = item.get('chName') or item.get('diziName') or 'InatBox'
        stream = {
            'url': streamUrl,
            'name': f"InatBox MUBI\n{name}",
            'title': name,
            'type': 'hls',
            'behaviorHints': {'notWebReady': False,
                              'httpHeaders': {'User-Agent': vk_ua, 'Referer': 'https://vk.com/'}},
            'addonName': 'inatbox',
            'addonManifestUrl': addonManifestUrl,
        }
        subtitles = []
        self._extract_item_subtitles(item, subtitles)
        if subtitles:
            stream['subtitles'] = subtitles
        print(f"🐛 [InatBox Debug] nok5 resolved: {streamUrl}")
        return {'streams': [stream]}

    def _catalog_slice_to_metas(self, items, metadata, addonManifestUrl):
        """Katalog item listesi -> ara-filtre -> skip dilimi (100'lük) -> Stremio meta.
        Canlı fetch yolu da (processFetchResult), handleCatalog cache-hit yolu da
        bunu kullanır ki meta üretimi tek yerde kalsın."""
        searchQuery = (metadata.get('searchQuery') or '').strip().lower()
        catalogId = metadata.get('catalogId', '')
        if searchQuery:
            def _nm(it):
                return (it.get('diziName') or it.get('chName') or it.get('name')
                        or it.get('title') or it.get('catName') or '')
            items = [it for it in items if isinstance(it, dict) and searchQuery in _nm(it).lower()]
            print(f"🐛 [InatBox Debug] Search '{searchQuery}': {len(items)} matches", flush=True)

        skip = int(metadata.get('skip', 0))
        # İstemci `extra.limit` ile büyük dilim isteyebilir (toplu arka plan
        # senkronu). Tavan 5000 — tek yanıtı makul tut. Varsayılan 100.
        try:
            limit = max(1, min(5000, int(metadata.get('limit', 100) or 100)))
        except (TypeError, ValueError):
            limit = 100
        page = items[skip:skip + limit]
        print(f"🐛 [InatBox Debug] After pagination (skip={skip}, limit={limit}): {len(page)} items", flush=True)

        metas = []
        for item in page:
            try:
                ctype = item.get('diziType') or item.get('chType') or ''
                # nav / non-content rows (keep web_mode: those are real webview movies)
                if ctype in ['link', 'web', 'link_mode', 'destek_mode', 'destek']: continue

                name = item.get('diziName') or item.get('chName') or item.get('name') or item.get('title') or 'Unknown'
                poster = item.get('diziImg') or item.get('chImg') or item.get('img') or item.get('poster')
                meta_id = 'inatbox:' + base64_encode_safe(json.dumps(item))

                type_val = determine_content_type(item, catalogId)
                posterShape = 'square' if type_val == 'tv' else 'poster'

                metas.append({
                    'id': meta_id,
                    'type': type_val,
                    'name': name,
                    'poster': poster,
                    'posterShape': posterShape,
                    'description': item.get('diziDetay') or item.get('description') or '',
                    'releaseInfo': item.get('diziYear') or item.get('year') or '',
                    'addonName': 'inatbox',
                    'addonManifestUrl': addonManifestUrl
                })
            except Exception as e:
                print(f"Error processing item: {e}")
        return {'metas': metas}

    async def handleCatalog(self, args):
        catalogId = args.get('id')
        extra = args.get('extra', {})
        searchQuery = extra.get('search')
        skip = int(extra.get('skip', 0))
        try:
            limit = max(1, min(5000, int(extra.get('limit', 100) or 100)))
        except (TypeError, ValueError):
            limit = 100

        print(f"📋 [InatBox Catalog] Catalog ID: {catalogId}, Search: {searchQuery}, Skip: {skip}, Limit: {limit}")

        # Dev listeler (4K ~18k, list2 ~12k): ilk sayfada (skip=0) doldurulan RAM
        # cache'ten doğrudan {'metas': dilim} dön — 16 MB'lık yeniden fetch yok.
        # inat_search (çok katalog tek key) ve GET_CATALOGS hariç. Cache
        # soğuk/expire ise aşağıdaki gerçek-talimat yoluna düşer; processFetchResult
        # onu yeniden doldurur, sonraki istek yine cache-hit alır.
        # NOT: limit>100 (toplu senkron) ise skip=0 da cache-hit olabilir.
        if (skip > 0 or limit > 100) and catalogId != 'inat_search' \
                and catalogId not in self.GET_CATALOGS:
            cached = _catalog_cache_get(catalogId)
            if cached is not None:
                print(f"⚡ [InatBox Catalog] cache HIT {catalogId} skip={skip} limit={limit} ({len(cached)} öğe)", flush=True)
                return self._catalog_slice_to_metas(
                    cached,
                    {'catalogId': catalogId, 'skip': skip, 'limit': limit,
                     'searchQuery': searchQuery or ''},
                    args.get('addonManifestUrl'),
                )

        # GET catalogs: signed GET request, response decrypted with a fixed key.
        if catalogId in self.GET_CATALOGS:
            u = self.CATALOG_URLS[catalogId]
            return {'instructions': [{
                'requestId': f"inat-catalog-{catalogId}-{int(time.time()*1000)}",
                'purpose': 'catalog',
                'url': u,
                'method': 'GET',
                'headers': self._api_headers(u, '', method='GET'),
                'metadata': {'catalogId': catalogId, 'aesKey': self.GET_CATALOGS[catalogId],
                             'skip': skip, 'limit': limit, 'searchQuery': searchQuery or ''}
            }]}

        # InatBox has no server-side search endpoint anymore. "🔍 Tümünde Ara"
        # scans a handful of broad catalogs; a per-catalog search filters that
        # catalog's own list. Both are done locally in processFetchResult.
        if catalogId == 'inat_search':
            if not searchQuery:
                return {'instructions': []}
            search_ids = ['yabanci-dizi', 'yerli-dizi', 'yerli-filmler', 'netflix', 'mubi']
            urls = [self.CATALOG_URLS[i] for i in search_ids if isinstance(self.CATALOG_URLS.get(i), str)]
        else:
            baseUrl = self.CATALOG_URLS.get(catalogId)
            if not baseUrl:
                print(f"❌ [InatBox Catalog] No URL mapped for {catalogId}")
                return {'instructions': []}
            # A catalog id may map to one URL or several (e.g. 4K web + exo lists).
            urls = baseUrl if isinstance(baseUrl, list) else [baseUrl]

        instructions = []
        for idx, u in enumerate(urls):
            aesKey = self.get_aes_key(u)
            requestBody = self.buildRequestBody(aesKey=aesKey)
            instructions.append({
                'requestId': f"inat-catalog-{catalogId}-{idx}-{int(time.time()*1000)}",
                'purpose': 'catalog',
                'url': u,
                'method': 'POST',
                'headers': self._api_headers(u, requestBody),
                'body': requestBody,
                'metadata': {'catalogId': catalogId, 'aesKey': aesKey, 'skip': skip,
                             'limit': limit, 'searchQuery': searchQuery or ''}
            })

        return {'instructions': instructions}

    async def handleMeta(self, args):
        try:
            padded = args.get('id', '').replace('inatbox:', '')
            padded += '=' * (-len(padded) % 4)
            itemData = base64.b64decode(padded).decode('utf8')
            item = json.loads(itemData)
        except Exception as e:
            print(f"Error parsing meta id: {e}")
            return {'instructions': []}
            
        print('📺 [InatBox Meta] for', item.get('diziName') or item.get('chName'))
        
        if item.get('diziType') and item.get('diziUrl'):
            requestId = f"inat-meta-{int(time.time()*1000)}"
            parsed = urllib.parse.urlparse(item.get('diziUrl'))
            aesKey = self.get_aes_key(item.get('diziUrl'))
            body = self.buildRequestBody(aesKey=aesKey)
            return {
                'instructions': [{
                    'requestId': requestId,
                    'purpose': 'meta_series_seasons' if item.get('diziType') in ['dizi', 'dizi_mode'] else 'meta',
                    'url': item.get('diziUrl'),
                    'method': 'POST',
                    'headers': self._api_headers(item.get('diziUrl'), body),
                    'body': body,
                    'metadata': {'originalItem': item, 'aesKey': aesKey}
                }],
                'metadata': {'originalItem': item, 'aesKey': aesKey}
            }
            
        if item.get('chUrl') and item.get('chType'):
            return {'instructions': [], 'metadata': {'originalItem': item, 'isChannel': True}}
            
        return {'instructions': [], 'metadata': {'originalItem': item}}

    async def handleStream(self, args):
        try:
            padded = args.get('id', '').replace('inatbox:', '')
            padded += '=' * (-len(padded) % 4)
            itemData = base64.b64decode(padded).decode('utf8')
            item = json.loads(itemData)
        except:
            return {'instructions': []}
            
        fetchUrl = None
        needsExtraction = False
        
        chType = item.get('chType')
        diziType = item.get('diziType')
        chUrl0 = item.get('chUrl') or item.get('url') or ''

        # --- 4K Film (web_mode / tekli_regex_mode on 4k.filmizleeeee.cfd) ---
        # The web.php and exo.php proxies point at the same movie; exo.php runs the
        # extraction server-side and returns a ready, usually headerless, HLS/MP4
        # URL as text/plain. Always route both variants through exo.php.
        if 'filmizleeeee.cfd' in chUrl0 and ('/web.php?' in chUrl0 or '/exo.php?' in chUrl0):
            exo_url = chUrl0.replace('/web.php?', '/exo.php?')
            ua = self.CONFIG['userAgent']
            referer = ''
            try:
                ch0 = item.get('chHeaders')
                if isinstance(ch0, str) and ch0 not in ('null', 'NULL'):
                    ch0 = json.loads(ch0)
                if isinstance(ch0, list) and ch0 and isinstance(ch0[0], dict):
                    ua = ch0[0].get('UserAgent') or ua
                    referer = ch0[0].get('Referer') or referer
            except Exception as e:
                print("EXCEPTION IN LOOP:", e)
            return {
                'instructions': [{
                    'requestId': f"inat-4k-{int(time.time()*1000)}",
                    'purpose': 'stream_4k_exo',
                    'url': exo_url,
                    'method': 'GET',
                    'headers': {'Accept': '*/*', 'User-Agent': ua, 'Referer': referer,
                                'X-Requested-With': 'XMLHttpRequest'},
                    'metadata': {'originalItem': item, 'exoUrl': exo_url, 'try': 1,
                                 'ua': ua, 'referer': referer}
                }],
                'metadata': {'originalItem': item}
            }

        # --- MUBI / VK (nok5_mode): vk.com video_ext.php -> Regex1 hls url ---
        if chType and _strip_mode(chType) == 'nok5':
            vk_url = self._vk_ext_url(chUrl0)
            vk_ua = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                     '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
            try:
                ch0 = item.get('chHeaders')
                if isinstance(ch0, str) and ch0 not in ('null', 'NULL'):
                    ch0 = json.loads(ch0)
                if isinstance(ch0, list) and ch0 and isinstance(ch0[0], dict):
                    vk_ua = ch0[0].get('UserAgent') or vk_ua
            except Exception as e:
                print("EXCEPTION IN LOOP:", e)
            return {
                'instructions': [self._nok5_instruction(item, vk_url, vk_ua, 1)],
                'metadata': {'originalItem': item}
            }

        if diziType in ['film', 'film_mode']:
            fetchUrl = item.get('diziUrl')
            needsExtraction = True
        elif chType in ['tekli_regex_lb_sh_3', 'tekli_regex_lb_sh_3_mode']:
            fetchUrl = item.get('chUrl')
            needsExtraction = True
        elif chType and ('tekli_regex' in chType or chType == 'cable_sh'):
            extractUrl = vk_source_fix(item.get('chUrl') or item.get('url'))
            
            referer = 'https://speedrestapi.com/'
            ua = self.CONFIG['userAgent']
            
            try:
                chHeaders = item.get('chHeaders', [])
                if isinstance(chHeaders, list) and len(chHeaders) > 0 and isinstance(chHeaders[0], dict):
                    referer = chHeaders[0].get('Referer', referer)
                    ua = chHeaders[0].get('UserAgent', ua)
            except Exception as e: print("EXCEPTION IN LOOP:", e)
            
            if 'vk.com' in extractUrl:
                ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
            
            if '.m3u8' in extractUrl or '.mpd' in extractUrl:
                print(f"🐛 [InatBox Debug] Returning direct stream link: {extractUrl}")
                return await self.processFetchResult({
                    'purpose': 'stream_extract',
                    'body': '',
                    'metadata': {'originalItem': item}
                })
            
            return {
                'instructions': [{
                    'requestId': f"inat-extract-{int(time.time()*1000)}",
                    'purpose': 'stream_extract',
                    'url': extractUrl,
                    'method': 'GET',
                    'headers': {
                        'Accept': '*/*',
                        'Referer': referer,
                        'User-Agent': ua,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    'metadata': {'originalItem': item, 'extractorNeeded': True}
                }],
                'metadata': {'originalItem': item, 'extractorNeeded': True}
            }
        elif chType in ['live_url', 'live_mode', 'live_url_mode'] and (item.get('chUrl') or item.get('url')):
            # Direct stream, no fetch needed. The Flutter client's getStreams()
            # ignores a top-level `streams` key on the /stream response — it only
            # picks up direct streams by round-tripping `metadata.directItem`
            # through processFetchResult (empty body). Match the reference JS
            # plugin: return no instructions + metadata.directItem.
            if not (item.get('chUrl') or item.get('url')):
                return {'streams': []}
            return {'instructions': [], 'metadata': {'directItem': item}}

        if fetchUrl:
            parsed = urllib.parse.urlparse(fetchUrl)
            aesKey = self.get_aes_key(fetchUrl)
            body = self.buildRequestBody(aesKey=aesKey)
            requestId = f"inat-stream-{int(time.time()*1000)}"
            return {
                'instructions': [{
                    'requestId': requestId,
                    'purpose': 'stream_fetch_for_extract' if needsExtraction else 'stream',
                    'url': fetchUrl,
                    'method': 'POST',
                    'headers': self._api_headers(fetchUrl, body),
                    'body': body,
                    'metadata': {'originalItem': item, 'needsExtraction': needsExtraction, 'aesKey': aesKey}
                }],
                'metadata': {'originalItem': item, 'needsExtraction': needsExtraction, 'aesKey': aesKey}
            }
            
        return {'streams': []}

    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body')
        metadata = fetchResult.get('metadata', {})
        url = fetchResult.get('url')
        addonManifestUrl = fetchResult.get('addonManifestUrl')
        
        print(f"🐛 [InatBox Debug] processFetchResult started. Purpose: {purpose}, Body length: {len(str(body))}", flush=True)
        if isinstance(body, str):
            print(f"🐛 [InatBox Debug] Body start: {repr(body[:100])}", flush=True)
        
        if not body and metadata:
            if metadata.get('directItem'):
                item = metadata['directItem']
                if item.get('chType') not in ['live_url', 'live_mode', 'live_url_mode']:
                    return {'streams': []}
                
                streamUrl = vk_source_fix(item.get('chUrl') or item.get('url'))
                if not streamUrl:
                    return {'streams': []}
                    
                headersObject = _build_live_stream_headers(self.CONFIG['userAgent'], item)

                streams = [{
                    'url': streamUrl,
                    'name': item.get('diziName') or item.get('chName') or 'InatBox Stream',
                    'title': item.get('diziName') or item.get('chName') or 'InatBox Stream',
                    'behaviorHints': {
                        'notWebReady': False,
                        'httpHeaders': headersObject
                    },
                    'addonName': 'inatbox',
                    'addonManifestUrl': addonManifestUrl
                }]
                
                subtitles = []
                self._extract_item_subtitles(item, subtitles)
                if subtitles:
                    streams[0]['subtitles'] = subtitles
                    
                print(f"🐛 [InatBox Debug] Extracted direct stream: {streamUrl}")
                return {'streams': streams}
                
        isHTML = isinstance(body, str) and (body.strip().startswith('<!DOCTYPE') or body.strip().startswith('<html'))
        is_bad_body = not body or isHTML
        
        if is_bad_body and url and purpose in ['catalog', 'catalog_search', 'meta_series_seasons', 'meta_series_episodes', 'stream_fetch_for_extract']:
            print("⚠️ Bad body received from Flutter. Attempting domain rotation...", flush=True)
            parsed = urllib.parse.urlparse(url)
            body_data = self.buildRequestBody({'q': metadata.get('searchQuery', '')}, aesKey=metadata.get('aesKey')) if purpose == 'catalog_search' else self.buildRequestBody(aesKey=metadata.get('aesKey'))

            domains = ['diziboxen.help', 'foxlab.cfd', 'bozspra.cfd', 'dizilabmedia.click']
            current_domain = parsed.netloc
            if current_domain in domains:
                current_idx = domains.index(current_domain)
                next_idx = current_idx + 1
                if next_idx < len(domains):
                    next_domain = domains[next_idx]
                    new_url = url.replace(current_domain, next_domain)
                    new_parsed = urllib.parse.urlparse(new_url)

                    requestId = f"inat-retry-{int(time.time()*1000)}-{random.randint(1000,9999)}"
                    print(f"🔄 Rotating to new domain: {next_domain}", flush=True)
                    return {
                        'instructions': [{
                            'requestId': requestId,
                            'purpose': purpose,
                            'url': new_url,
                            'method': 'POST',
                            'headers': self._api_headers(new_url, body_data),
                            'body': body_data,
                            'metadata': metadata
                        }]
                    }

        _lb_item = metadata.get('originalItem') or {}
        if (purpose in ['stream', 'stream_fetch_for_extract']
                and _strip_mode(_lb_item.get('chType')) == 'tekli_regex_lb_sh_3'):
            return self._resolve_lb_sh_3(_lb_item, body, addonManifestUrl)

        if purpose == 'stream_4k_exo':
            return self._resolve_4k(metadata, body, addonManifestUrl)
        if purpose == 'stream_4k_m3u8':
            return self._resolve_4k_subs(metadata, body, addonManifestUrl)
        if purpose == 'stream_nok5':
            return self._resolve_nok5(metadata, body, addonManifestUrl)

        if purpose in ['stream_extract', 'meta']:
            pass
        else:
            if not body or (isinstance(body, str) and (body.strip().startswith('<!DOCTYPE') or body.strip().startswith('<html'))):
                return {'metas': []} if purpose in ['catalog', 'catalog_search'] else {'streams': []}
                
        data = None
        if purpose not in ['stream_extract', 'meta']:
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict) and 'response' in parsed and isinstance(parsed['response'], str):
                    body_to_decrypt = parsed['response']
                else:
                    data = parsed
                    body_to_decrypt = None
            except:
                body_to_decrypt = body
                
            if not data and body_to_decrypt:
                aesKey = metadata.get('aesKey', self.CONFIG['aesKey'])
                
                item_for_aes = metadata.get('originalItem', {})
                if item_for_aes.get('chType') in ['tekli_regex_lb_sh_3', 'tekli_regex_lb_sh_3_mode']:
                    ch_reg = item_for_aes.get('chReg')
                    if ch_reg and isinstance(ch_reg, list) and len(ch_reg) > 0:
                        regex1 = ch_reg[0].get('Regex1')
                        if regex1 and regex1 != 'null':
                            aesKey = regex1
                            
                try:
                    decrypted = decrypt_aes(body_to_decrypt, aesKey)
                    if decrypted:
                        try:
                            data = json.loads(decrypted)
                        except Exception as json_err:
                            print(f"❌ [InatBox Debug] JSON Parse error after decryption: {json_err}")
                            print(f"🐛 [InatBox Debug] First 100 chars of decrypted: {repr(decrypted[:100])}")
                except Exception as e:
                    print(f"❌ [InatBox Debug] Outer decrypt error: {e}")
                    return {'metas': []} if purpose in ['catalog', 'catalog_search'] else {'streams': []}
            
            if not data:
                return {'metas': []} if purpose in ['catalog', 'catalog_search'] else {'streams': []}

        if purpose in ['catalog', 'catalog_search']:
            items = []
            if isinstance(data, list): items = data
            elif isinstance(data, dict):
                if 'results' in data and isinstance(data['results'], list): items = data['results']
                elif 'channels' in data and isinstance(data['channels'], list): items = data['channels']
                elif 'items' in data and isinstance(data['items'], list): items = data['items']
                elif 'data' in data and isinstance(data['data'], list): items = data['data']
                elif 'response' in data and isinstance(data['response'], list): items = data['response']
                else:
                    items = [v for k,v in data.items() if isinstance(v, dict)]
            
            print(f"🐛 [InatBox Debug] Parsed Data keys: {data.keys() if isinstance(data, dict) else type(data)}", flush=True)
            print(f"🐛 [InatBox Debug] Extracted {len(items)} items from payload", flush=True)

            # Dev liste cache'i: TAM (filtrelenmemiş) listeyi RAM'e al ki handleCatalog
            # skip>0 sayfalarını 16 MB yeniden-fetch olmadan dilimleyebilsin.
            # inat_search (çok katalog tek key altında) hariç.
            cid = metadata.get('catalogId', '')
            if cid and cid != 'inat_search' and items:
                _catalog_cache_put(cid, items)
                print(f"💾 [InatBox Debug] cached {cid}: {len(items)} öğe", flush=True)

            return self._catalog_slice_to_metas(items, metadata, addonManifestUrl)

        if purpose == 'stream_extract':
            item = metadata.get('originalItem')
            if not item: return {'streams': []}
            
            ch_name_str = item.get('chName') or item.get('diziName') or ''
            lang_tag = 'TR' if ' TR' in ch_name_str or '-TR' in ch_name_str or '- TR' in ch_name_str else 'EN' if ' EN' in ch_name_str or '-EN' in ch_name_str or '- EN' in ch_name_str else ''
            base_name = f"InatBox {lang_tag}".strip()
            
            sourceUrl = item.get('chUrl') or item.get('url')
            streams = []
            subtitles = []
            audioTracks = []
            
            self._extract_item_subtitles(item, subtitles)
            if body and isinstance(body, str):
                self._extract_tracks(body, sourceUrl, subtitles, audioTracks)
                
            if '.m3u8' in sourceUrl or '.mpd' in sourceUrl:
                headersObject = {'User-Agent': self.CONFIG['userAgent'], 'Referer': ''}
                try:
                    chHeaders = item.get('chHeaders')
                    if chHeaders and chHeaders != 'null':
                        if isinstance(chHeaders, str):
                            parsed = json.loads(chHeaders)
                            if isinstance(parsed, list) and len(parsed)>0: headersObject.update(parsed[0])
                            elif isinstance(parsed, dict): headersObject.update(parsed)
                        elif isinstance(chHeaders, list) and len(chHeaders)>0: headersObject.update(chHeaders[0])
                        elif isinstance(chHeaders, dict): headersObject.update(chHeaders)
                except Exception as e: print("EXCEPTION IN LOOP:", e)
                
                try:
                    chReg = item.get('chReg')
                    if chReg and chReg != 'null':
                        if isinstance(chReg, str):
                            parsed = json.loads(chReg)
                            if isinstance(parsed, list) and len(parsed)>0 and parsed[0].get('playSH2'):
                                headersObject['Cookie'] = parsed[0]['playSH2']
                        elif isinstance(chReg, list) and len(chReg)>0 and chReg[0].get('playSH2'):
                            headersObject['Cookie'] = chReg[0]['playSH2']
                except Exception as e: print("EXCEPTION IN LOOP:", e)
                
                stream = {
                    'url': sourceUrl,
                    'name': f"{base_name} (Direct)",
                    'title': ch_name_str or 'Direct Stream',
                    'behaviorHints': {'notWebReady': False, 'httpHeaders': headersObject},
                    'addonName': 'inatbox',
                    'addonManifestUrl': addonManifestUrl
                }
                print(f"🐛 [InatBox Debug] Extracted direct stream: {sourceUrl}")
                streams.append(stream)
                
            elif 'dzen.ru' in sourceUrl:
                for match in re.finditer(r'\{"url":"([^"]*)","type":"([^"]*)"\}', body, re.IGNORECASE):
                    videoUrl = match.group(1)
                    qMatch = re.search(r'=(\w+)$', videoUrl)
                    qualityMap = {'tiny':'256p','lowest':'426p','low':'640p','medium':'852p','high':'1280p','fullhd':'1920p'}
                    quality = qualityMap.get(qMatch.group(1)) if qMatch else 'Unknown'
                    streams.append({
                        'url': videoUrl,
                        'name': f"{base_name}\n{quality}",
                        'title': ch_name_str or 'Dzen Stream',
                        'behaviorHints': {'notWebReady': False, 'httpHeaders': {'Referer': 'https://dzen.ru/'}},
                        'addonName': 'inatbox',
                        'addonManifestUrl': addonManifestUrl
                    })
                    print(f"🐛 [InatBox Debug] Extracted Dzen stream: {videoUrl}")
            elif 'vk.com' in sourceUrl:
                match = re.search(r'"([^"]*m3u8[^"]*)"', body)
                if match:
                    videoUrl = match.group(1).replace('\\/', '/')
                    streams.append({
                        'url': videoUrl,
                        'name': f"{base_name} (VK)",
                        'title': ch_name_str or 'VK Stream',
                        'behaviorHints': {'notWebReady': False, 'httpHeaders': {'Referer': 'https://vk.com/'}},
                        'addonName': 'inatbox',
                        'addonManifestUrl': addonManifestUrl
                    })
                    print(f"🐛 [InatBox Debug] Extracted VK stream: {videoUrl}")
            elif 'disk.yandex.com' in sourceUrl:
                match = re.search(r'https?:\/\/[^\s"]*?master-playlist\.m3u8', body)
                if match:
                    streams.append({
                        'url': match.group(0),
                        'name': f"{base_name} (Yandex)",
                        'title': ch_name_str or 'Yandex Disk',
                        'behaviorHints': {'notWebReady': False, 'httpHeaders': {'Referer': ''}},
                        'addonName': 'inatbox',
                        'addonManifestUrl': addonManifestUrl
                    })
                    print(f"🐛 [InatBox Debug] Extracted Yandex stream: {match.group(0)}")
            elif 'cdn.dzen.ru' in sourceUrl:
                if '.m3u8' in sourceUrl or '.mpd' in sourceUrl:
                    streams.append({
                        'url': sourceUrl,
                        'name': f"{base_name} (CDN)",
                        'title': ch_name_str or 'Dzen CDN',
                        'behaviorHints': {'notWebReady': False, 'httpHeaders': {'Referer': ''}},
                        'addonName': 'inatbox',
                        'addonManifestUrl': addonManifestUrl
                    })
                    print(f"🐛 [InatBox Debug] Extracted Dzen CDN stream: {sourceUrl}")
            elif 'cdn.jwplayer.com' in sourceUrl or '.m3u8' in sourceUrl:
                streams.append({
                    'url': sourceUrl,
                    'name': f"{base_name} (CDN)",
                    'title': ch_name_str or 'CDN Stream',
                    'behaviorHints': {'notWebReady': False, 'httpHeaders': {'Referer': ''}},
                    'addonName': 'inatbox',
                    'addonManifestUrl': addonManifestUrl
                })
                print(f"🐛 [InatBox Debug] Extracted CDN stream: {sourceUrl}")
                
            if not streams:
                chReg = item.get('chReg')
                extractedUrl = None
                if chReg and isinstance(chReg, list) and len(chReg)>0:
                    regexPattern = chReg[0].get('Regex1')
                    if regexPattern and regexPattern != 'null':
                        # First try AES decryption (if Regex1 is actually an AES key)
                        try:
                            decrypted = decrypt_aes(body, regexPattern)
                            if decrypted:
                                parsed_json = json.loads(decrypted)
                                extractedUrl = parsed_json.get('chUrl')
                        except Exception as e: print("EXCEPTION IN LOOP:", e)
                        
                        # Fallback to standard regex search if decryption failed or didn't yield a URL
                        if not extractedUrl:
                            try:
                                match = re.search(regexPattern, body, re.IGNORECASE)
                                if match and match.group(1):
                                    extractedUrl = match.group(1)
                            except Exception as e: print("EXCEPTION IN LOOP:", e)
                
                finalUrl = extractedUrl or sourceUrl
                headersArray = item.get('chHeaders') or {'Referer': '', 'User-Agent': self.CONFIG['userAgent']}
                if isinstance(headersArray, str) and headersArray != 'null':
                    try: headersArray = json.loads(headersArray)
                    except: headersArray = {'Referer': '', 'User-Agent': self.CONFIG['userAgent']}
                if isinstance(headersArray, list) and len(headersArray) > 0: headersArray = headersArray[0]
                if not headersArray: headersArray = {'Referer': '', 'User-Agent': self.CONFIG['userAgent']}
                
                genericStream = {
                    'url': finalUrl,
                    'name': base_name,
                    'title': ch_name_str or 'Generic Stream',
                    'behaviorHints': {'notWebReady': False, 'httpHeaders': headersArray},
                    'addonName': 'inatbox',
                    'addonManifestUrl': addonManifestUrl
                }
                print(f"🐛 [InatBox Debug] Extracted generic stream: {finalUrl}")
                streams.append(genericStream)
                
            for s in streams:
                if subtitles and 'subtitles' not in s:
                    s['subtitles'] = subtitles
                if audioTracks and 'audioTracks' not in s:
                    s['audioTracks'] = audioTracks
                    
            return {'streams': streams}

        if purpose == 'stream_fetch_for_extract':
            item = metadata.get('originalItem')
            if not item or not data: return {'streams': []}
            items_to_process = data if isinstance(data, list) else [data]
            
            instructions = []
            
            for d in items_to_process:
                if not isinstance(d, dict) or not d.get('chUrl'): continue
                
                chHeaders = d.get('chHeaders') or item.get('chHeaders') or []
                ext_item = item.copy()
                ext_item.update(d)
                
                ext_item['chUrl'] = vk_source_fix(d.get('chUrl'))
                ext_item['chName'] = d.get('chName') or d.get('diziName') or item.get('chName') or item.get('diziName')
                ext_item['chImg'] = d.get('chImg') or d.get('diziImg') or item.get('chImg') or item.get('diziImg')
                ext_item['chHeaders'] = chHeaders
                
                if not ext_item.get('chReg'): ext_item['chReg'] = item.get('chReg')
                if not ext_item.get('chType'): ext_item['chType'] = item.get('chType') or item.get('diziType')
                
                source_url = ext_item['chUrl']
                
                referer = 'https://speedrestapi.com/'
                ua = self.CONFIG['userAgent']
                if isinstance(chHeaders, list) and len(chHeaders)>0 and isinstance(chHeaders[0], dict):
                    referer = chHeaders[0].get('Referer', referer)
                    ua = chHeaders[0].get('UserAgent', ua)
                    
                instructions.append({
                    'requestId': f"inat-extract-{int(time.time()*1000)}-{random.randint(1000,9999)}",
                    'purpose': 'stream_extract',
                    'url': source_url,
                    'method': 'GET',
                    'headers': {
                        'Accept': '*/*',
                        'Referer': referer,
                        'User-Agent': ua,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    'metadata': {'originalItem': ext_item, 'extractorNeeded': True},
                    'addonManifestUrl': addonManifestUrl
                })
            
            if instructions:
                return {'instructions': instructions}
            return {'streams': []}

        if purpose in ['meta', 'meta_series_seasons', 'meta_series_episodes']:
            item = metadata.get('originalItem')
            if not item: return {'meta': None}
            
            if metadata.get('isChannel'):
                meta_id = 'inatbox:' + base64_encode_safe(json.dumps(item))
                _ct = _strip_mode(item.get('chType'))
                is_live = _ct in ['live_url', 'live', 'tekli_regex_lb_sh_3', 'cable_sh']
                # web_mode / tekli_regex_mode (4K Film) and nok5_mode (MUBI) are
                # VOD movies, not channels — give them a proper movie meta so the
                # Stremio movie play flow reaches handleStream.
                ch_meta = {
                    'id': meta_id, 'type': 'tv' if is_live else 'movie',
                    'name': item.get('chName') or item.get('diziName') or 'Unknown',
                    'poster': item.get('chImg') or item.get('diziImg'),
                    'posterShape': 'square' if is_live else 'poster',
                    'description': item.get('diziDetay') or item.get('description') or '',
                    'releaseInfo': item.get('diziYear') or item.get('year') or '',
                    'addonName': 'inatbox', 'addonManifestUrl': addonManifestUrl
                }
                if not is_live:
                    ch_meta['videos'] = [{
                        'id': meta_id, 'title': ch_meta['name'],
                        'released': item.get('diziYear') or item.get('year') or ''
                    }]
                return {'meta': ch_meta}
                
            meta_id = 'inatbox:' + base64_encode_safe(json.dumps(item))
            
            type_val = 'movie'
            _dt = _strip_mode(item.get('diziType'))
            _ct = _strip_mode(item.get('chType'))
            if _dt == 'dizi': type_val = 'series'
            elif _dt == 'film': type_val = 'movie'
            elif _ct:
                if _ct in ['live_url', 'live', 'tekli_regex_lb_sh_3', 'cable_sh']: type_val = 'tv'
                else: type_val = 'movie'
                
            if purpose in ['meta_series_seasons', 'meta_series_episodes']:
                type_val = 'series'
                
            meta = {
                'id': meta_id, 'type': type_val, 'name': item.get('diziName') or item.get('chName') or 'Unknown',
                'poster': item.get('diziImg') or item.get('chImg'), 'description': item.get('diziDetay') or '',
                'releaseInfo': item.get('diziYear') or '', 'addonName': 'inatbox', 'addonManifestUrl': addonManifestUrl
            }
            
            if purpose == 'meta_series_seasons' and type_val == 'series' and isinstance(data, list):
                episodeInstructions = []
                for idx, season in enumerate(data):
                    if season.get('diziUrl'):
                        try:
                            parsed = urllib.parse.urlparse(season.get('diziUrl'))
                            season_body = self.buildRequestBody(aesKey=metadata.get('aesKey'))
                            episodeInstructions.append({
                                'requestId': f"inat-season-{idx+1}-{int(time.time()*1000)}",
                                'purpose': 'meta_series_episodes',
                                'url': season.get('diziUrl'),
                                'method': 'POST',
                                'headers': self._api_headers(season.get('diziUrl'), season_body),
                                'body': season_body,
                                'metadata': {'originalItem': item, 'seasonNumber': idx+1, 'seasonName': season.get('diziName'), 'aesKey': metadata.get('aesKey')}
                            })
                        except Exception as e: print("EXCEPTION IN LOOP:", e)
                if data and data[0].get('diziImg'):
                    meta['poster'] = data[0]['diziImg']
                if not episodeInstructions: return {'meta': meta}
                return {'instructions': episodeInstructions, 'partialMeta': meta}
                
            if purpose == 'meta_series_episodes' and isinstance(data, list):
                seasonNumber = metadata.get('seasonNumber', 1)
                videos = []
                for idx, ep in enumerate(data):
                    if ep.get('chName') or ep.get('diziName'):
                        ep_id = 'inatbox:' + base64_encode_safe(json.dumps(ep))
                        videos.append({
                            'id': ep_id,
                            'title': ep.get('chName') or ep.get('diziName'),
                            'thumbnail': ep.get('chImg') or ep.get('diziImg'),
                            'season': seasonNumber,
                            'episode': idx + 1
                        })
                return {'partialMeta': {'videos': videos}}
                
            if type_val == 'movie' and item.get('diziType') in ['film', 'film_mode']:
                if isinstance(data, list) and len(data)>0:
                    firstItem = data[0]
                    vid_id = 'inatbox:' + base64_encode_safe(json.dumps(firstItem))
                    meta['videos'] = [{
                        'id': vid_id, 'title': item.get('diziName') or 'Film',
                        'thumbnail': firstItem.get('chImg') or item.get('diziImg'),
                        'released': item.get('diziYear') or ''
                    }]
                else:
                    vid_id = 'inatbox:' + base64_encode_safe(json.dumps(item))
                    meta['videos'] = [{
                        'id': vid_id, 'title': item.get('diziName') or 'Film',
                        'thumbnail': item.get('diziImg'),
                        'released': item.get('diziYear') or ''
                    }]
                return {'meta': meta}
                
            return {'meta': meta}

        return {'ok': True}
