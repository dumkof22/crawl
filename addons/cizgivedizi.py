import base64
import json
import re
import time
import random
import urllib.parse
from bs4 import BeautifulSoup

BASE_URL = 'https://cizgivedizi.com'

# Katalog id -> filtre tanımı.
#   types  : kabul edilen data-type değerleri (kart üzerindeki)
#   genre  : (opsiyonel) data-genresraw içinde aranan tür adı
#   metatype: Stremio meta tipi
CATALOG_DEFS = {
    'cizgivedizi_cizgi_diziler': {'types': ['cizgi'], 'metatype': 'series'},
    'cizgivedizi_animeler':      {'types': ['anime'], 'metatype': 'series'},
    'cizgivedizi_diziler':       {'types': ['dizi'], 'metatype': 'series'},
    'cizgivedizi_filmler':       {'types': ['film'], 'metatype': 'movie'},
    'cizgivedizi_komedi':        {'types': ['cizgi', 'anime', 'dizi'], 'genre': 'Komedi', 'metatype': 'series'},
    'cizgivedizi_macera':        {'types': ['cizgi', 'anime', 'dizi'], 'genre': 'Macera', 'metatype': 'series'},
    'cizgivedizi_fantastik':     {'types': ['cizgi', 'anime', 'dizi'], 'genre': 'Fantastik', 'metatype': 'series'},
    'cizgivedizi_aksiyon':       {'types': ['cizgi', 'anime', 'dizi'], 'genre': 'Aksiyon', 'metatype': 'series'},
    'cizgivedizi_bilim_kurgu':   {'types': ['cizgi', 'anime', 'dizi'], 'genre': 'Bilim Kurgu', 'metatype': 'series'},
    'cizgivedizi_korku':         {'types': ['cizgi', 'anime', 'dizi'], 'genre': 'Korku', 'metatype': 'series'},
}

PAGE_SIZE = 100

# Bölüm/film sayfasındaki tür rozetleri (/diziyeni/turresim/<kod>.png) için kod -> ad.
GENRE_CODE_MAP = {
    'kom': 'Komedi', 'mac': 'Macera', 'fant': 'Fantastik', 'aks': 'Aksiyon',
    'bilkur': 'Bilim Kurgu', 'dra': 'Dram', 'müz': 'Müzik/Müzikal', 'muz': 'Müzik/Müzikal',
    'eği': 'Eğitici/Öğretici', 'egi': 'Eğitici/Öğretici', 'gh': 'Günlük Hayattan',
    'giz': 'Gizem', 'kor': 'Korku', 'doğ': 'Doğa ve Hayvanlar', 'dog': 'Doğa ve Hayvanlar',
    'spo': 'Spor', 'rom': 'Romantik', 'suç': 'Suç/Polisiye', 'suc': 'Suç/Polisiye',
    'abs': 'Absürt', 'dedek': 'Dedektif', 'romkom': 'Romantik Komedi', 'yem': 'Yemek',
    'tar': 'Tarihi', 'özel': 'Özel', 'ozel': 'Özel', 'lgbt': 'LGBT', 'tıp': 'Tıp', 'tip': 'Tıp',
    'sav': 'Savaş', 'sih': 'Sihir', 'mini': 'Mini Seriler', 'kuş': 'Kuşaklar', 'kus': 'Kuşaklar',
}
_NON_GENRE_CODES = {'film', 'cd', 'çd', 'ani', 'diz', 'dizi', 'anime', 'cizgi', 'yans'}


def get_enhanced_headers(referer=BASE_URL):
    return {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Referer': referer
    }


def normalize_string(text):
    text = (text or '').lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = text.replace('İ', 'i').replace('Ğ', 'g').replace('Ü', 'u').replace('Ş', 's').replace('Ö', 'o').replace('Ç', 'c')
    text = re.sub(r'[-_.]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def b64_encode(url):
    return 'cizgivedizi:' + base64.b64encode(url.encode('utf-8')).decode('utf-8').replace('=', '')


def b64_decode(video_id):
    b64 = video_id.replace('cizgivedizi:', '')
    b64 += '=' * (-len(b64) % 4)
    return base64.b64decode(b64).decode('utf-8')


def abs_url(u):
    if not u:
        return u
    if u.startswith('//'):
        return 'https:' + u
    if u.startswith('http'):
        return u
    return BASE_URL + (u if u.startswith('/') else '/' + u)


def _encode_url(u):
    """URL içindeki ASCII olmayan karakterleri (ör. resim adlarındaki İ) yüzde-kodla."""
    if not u:
        return u
    try:
        parts = urllib.parse.urlsplit(u)
        path = urllib.parse.quote(parts.path, safe="/%:@&=+$,;~")
        return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
    except Exception:
        return u


def rand_id(n=8):
    return ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=n))


def crypto_aes_handler(data_b64, passphrase_str, encrypt=False):
    try:
        from Crypto.Cipher import AES
        if encrypt:
            return None
        data = base64.b64decode(data_b64)
        passphrase = passphrase_str.encode('utf-8')

        import hashlib
        key_iv = b''
        prev = b''
        while len(key_iv) < 48:
            prev = hashlib.md5(prev + passphrase).digest()
            key_iv += prev

        key = key_iv[:32]
        iv = key_iv[32:48]

        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(data)
        pad_len = decrypted[-1]
        return decrypted[:-pad_len].decode('utf-8')
    except Exception as e:
        print(f"❌ AES decrypt error: {e}")
        return None


def _detect_extractor(embed_url):
    host = urllib.parse.urlparse(embed_url).netloc.lower()
    if 'sibnet' in host:
        return 'sibnet', 'SibNet'
    if 'cizgiduo' in host:
        return 'cizgiduo', 'CizgiDuo'
    if 'cizgipass' in host or 'cizgipas' in host:
        return 'cizgipass', 'CizgiPass'
    if 'drive.google' in host:
        return 'googledrive', 'GDrive'
    if 'mp4upload' in host:
        return 'mp4upload', 'Mp4Upload'
    if 'abyss' in host:
        return 'generic', 'Abyss'
    if 'mail.ru' in host:
        return 'generic', 'MailRu'
    return 'generic', (host.split(':')[0] or 'CizgiveDizi')


class CizgiveDiziScraper:
    def __init__(self):
        catalogs = [
            {"type": "series", "id": "cizgivedizi_cizgi_diziler", "name": "Çizgi Diziler", "extra": [{"name": "skip", "isRequired": False}]},
            {"type": "series", "id": "cizgivedizi_animeler", "name": "Animeler", "extra": [{"name": "skip", "isRequired": False}]},
            {"type": "series", "id": "cizgivedizi_diziler", "name": "Diziler", "extra": [{"name": "skip", "isRequired": False}]},
            {"type": "series", "id": "cizgivedizi_komedi", "name": "Komedi", "extra": [{"name": "skip", "isRequired": False}]},
            {"type": "series", "id": "cizgivedizi_macera", "name": "Macera", "extra": [{"name": "skip", "isRequired": False}]},
            {"type": "series", "id": "cizgivedizi_fantastik", "name": "Fantastik", "extra": [{"name": "skip", "isRequired": False}]},
            {"type": "series", "id": "cizgivedizi_aksiyon", "name": "Aksiyon", "extra": [{"name": "skip", "isRequired": False}]},
            {"type": "series", "id": "cizgivedizi_bilim_kurgu", "name": "Bilim Kurgu", "extra": [{"name": "skip", "isRequired": False}]},
            {"type": "series", "id": "cizgivedizi_korku", "name": "Korku", "extra": [{"name": "skip", "isRequired": False}]},
            {"type": "series", "id": "cizgivedizi_search", "name": "Ara", "extra": [{"name": "search", "isRequired": True}, {"name": "skip", "isRequired": False}]},
            {"type": "movie", "id": "cizgivedizi_filmler", "name": "Filmler", "extra": [{"name": "skip", "isRequired": False}]},
            {"type": "movie", "id": "cizgivedizi_search", "name": "Ara", "extra": [{"name": "search", "isRequired": True}, {"name": "skip", "isRequired": False}]},
        ]
        self.manifest = {
            "id": "community.cizgivedizi",
            "version": "2.0.0",
            "name": "CizgiveDizi",
            "description": "Türkçe çizgi film, anime, dizi ve film platformu - CizgiveDizi için Stremio eklentisi (Instruction Mode)",
            "logo": "https://cizgivedizi.com/favicon.ico",
            "resources": ["catalog", "meta", "stream"],
            "types": ["series", "movie"],
            "catalogs": catalogs,
            "idPrefixes": ["cizgivedizi"]
        }

    def getManifest(self):
        return self.manifest

    # ------------------------------------------------------------------
    # INSTRUCTION ÜRETİCİLER
    # ------------------------------------------------------------------
    async def handleCatalog(self, args):
        catalog_id = args.get('id')
        req_type = args.get('type')
        extra = args.get('extra', {}) or {}
        search_query = extra.get('search')
        try:
            skip = int(extra.get('skip') or 0)
        except Exception:
            skip = 0

        if catalog_id != 'cizgivedizi_search' and catalog_id not in CATALOG_DEFS:
            return {"metas": []}

        headers = get_enhanced_headers(BASE_URL)
        headers['Accept-Charset'] = 'utf-8'
        return {
            "instructions": [{
                "requestId": f"cizgivedizi-catalog-{int(time.time()*1000)}-{rand_id()}",
                "purpose": "catalog-data",
                "url": f"{BASE_URL}/",
                "method": "GET",
                "headers": headers,
                "metadata": {
                    "hiddenweb": False,
                    "catalogId": catalog_id,
                    "reqType": req_type,
                    "searchQuery": search_query,
                    "skip": skip
                }
            }]
        }

    async def handleMeta(self, args):
        url = b64_decode(args.get('id', ''))
        is_movie = '/film/' in url
        encoded_url = urllib.parse.quote(url, safe=";/?:@&=+$,%")
        return {
            "instructions": [{
                "requestId": f"cizgivedizi-meta-{int(time.time()*1000)}-{rand_id()}",
                "purpose": "meta",
                "url": encoded_url,
                "method": "GET",
                "headers": get_enhanced_headers(BASE_URL),
                "metadata": {"hiddenweb": False, "originalUrl": url, "isMovie": is_movie}
            }]
        }

    async def handleStream(self, args):
        url = b64_decode(args.get('id', ''))
        encoded_url = urllib.parse.quote(url, safe=";/?:@&=+$,%")
        return {
            "instructions": [{
                "requestId": f"cizgivedizi-stream-{int(time.time()*1000)}-{rand_id()}",
                "purpose": "stream-page",
                "url": encoded_url,
                "method": "GET",
                "headers": get_enhanced_headers(BASE_URL),
                "metadata": {"hiddenweb": False, "originalUrl": url}
            }]
        }

    # ------------------------------------------------------------------
    # FLUTTER'DAN DÖNEN SONUÇLARI İŞLE
    # ------------------------------------------------------------------
    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body')
        url = fetchResult.get('url')
        metadata = fetchResult.get('metadata') or {}
        status = fetchResult.get('status')

        if status and status != 200:
            if purpose == 'catalog-data':
                return {"metas": []}
            if purpose == 'meta':
                return {"meta": None}
            if purpose in ('stream-page', 'extractor') or 'stream' in (purpose or '') or 'extract' in (purpose or ''):
                return {"streams": []}
            return {"ok": False, "error": f"HTTP {status}"}

        if isinstance(body, bytes):
            body = body.decode('utf-8', errors='ignore')
        body = body or ''

        if purpose == 'catalog-data':
            return self._parse_catalog(body, metadata)
        if purpose == 'meta':
            return self._parse_meta(body, metadata)
        if purpose == 'stream-page':
            return self._parse_stream_page(body, metadata)
        if purpose == 'extractor':
            return self._parse_extractor(body, url, metadata)
        if purpose == 'googledrive-api':
            return self._gdrive_api(body, metadata)
        if purpose == 'googledrive-embed':
            return self._gdrive_embed(body, metadata)
        if purpose == 'googledrive-video':
            return self._gdrive_video(body, metadata)

        return {"ok": True}

    # ------------------------------------------------------------------
    # KATALOG
    # ------------------------------------------------------------------
    def _parse_catalog(self, body, metadata):
        catalog_id = metadata.get('catalogId')
        req_type = metadata.get('reqType')
        search_query = metadata.get('searchQuery')
        skip = metadata.get('skip') or 0

        soup = BeautifulSoup(body, 'html.parser')

        if catalog_id == 'cizgivedizi_search':
            if req_type == 'movie':
                allowed_types = ['film']
                genre = None
            else:
                allowed_types = ['cizgi', 'anime', 'dizi']
                genre = None
        else:
            cdef = CATALOG_DEFS.get(catalog_id)
            if not cdef:
                return {"metas": []}
            allowed_types = cdef['types']
            genre = cdef.get('genre')

        n_query = normalize_string(search_query) if search_query else None
        metas = []
        seen = set()

        for a in soup.select('a.item'):
            href = a.get('href') or ''
            if not (href.startswith('/dizi/') or href.startswith('/film/')):
                continue
            dtype = (a.get('data-type') or '').strip()
            if dtype not in allowed_types:
                continue

            name = (a.get('aria-label') or a.get('data-name') or '').strip()
            if not name:
                continue

            genres = [g.strip() for g in (a.get('data-genresraw') or '').split('|') if g.strip()]
            if genre and genre not in genres:
                continue

            if n_query:
                haystack = normalize_string(
                    name + ' ' + (a.get('data-name') or '') + ' ' +
                    (a.get('data-hay') or '') + ' ' + (a.get('data-hay-en') or '')
                )
                if n_query not in haystack:
                    continue

            full_url = abs_url(href)
            if full_url in seen:
                continue
            seen.add(full_url)

            img = a.select_one('img.poster-img') or a.select_one('img')
            poster = _encode_url(abs_url(img.get('src'))) if img and img.get('src') else None

            metas.append({
                "id": b64_encode(full_url),
                "type": "movie" if dtype == 'film' else "series",
                "name": name,
                "poster": poster,
                "genres": genres or None
            })

        return {"metas": metas[skip:skip + PAGE_SIZE]}

    # ------------------------------------------------------------------
    # META
    # ------------------------------------------------------------------
    def _clean_title(self, raw):
        if not raw:
            return None
        t = raw.strip()
        for suf in [' Türkçe İzle', ' İzle | Çizgi ve Dizi', ' İzle', ' | Çizgi ve Dizi', ' - Çizgi ve Dizi']:
            if t.endswith(suf):
                t = t[:-len(suf)].strip()
        return t or None

    def _parse_meta(self, body, metadata):
        original_url = metadata.get('originalUrl') or ''
        is_movie = metadata.get('isMovie')
        soup = BeautifulSoup(body, 'html.parser')

        title_tag = soup.select_one('title')
        title = self._clean_title(title_tag.text if title_tag else None)
        if not title:
            h = soup.select_one('h1') or soup.select_one('h2')
            title = h.text.strip() if h else None
        if not title:
            return {"meta": None}

        description = ""
        desc_el = soup.select_one('meta[name="description"]')
        if desc_el and desc_el.get('content'):
            description = desc_el.get('content').strip()
        if not description:
            sc = soup.select_one('.summary-content') or soup.select_one('p.lead')
            if sc and sc.get_text(strip=True):
                description = sc.get_text(' ', strip=True)

        poster = None
        og_img = soup.select_one('meta[property="og:image"]')
        if og_img and og_img.get('content'):
            poster = og_img.get('content')
        if not poster:
            m = re.search(r"(https://cizgivedizi\.com/resim/[^\"'()\s]*[Pp]oster[^\"'()\s]*)", body)
            if m:
                poster = m.group(1)
        if not poster:
            bg = soup.select_one('[data-bg-url]')
            if bg and bg.get('data-bg-url'):
                poster = bg.get('data-bg-url')
        if not poster:
            pi = soup.select_one('img.poster-img')
            if pi and pi.get('src'):
                poster = pi.get('src')
        poster = _encode_url(abs_url(poster)) if poster else None

        genres = []
        for img in soup.select('img.tag-logo'):
            code = ''
            src = img.get('src') or ''
            mcode = re.search(r'/turresim/([^/.]+)\.', src)
            if mcode:
                code = urllib.parse.unquote(mcode.group(1)).strip().lower()
            label = (img.get('title') or img.get('alt') or '').strip()
            if code in _NON_GENRE_CODES:
                continue
            name = GENRE_CODE_MAP.get(code)
            if not name:
                # başlık tam ad gibi görünüyorsa (boşluk/büyük harf) onu kullan
                if label and (' ' in label or label != label.lower()) and label.lower() not in _NON_GENRE_CODES:
                    name = label
            if name and name not in genres:
                genres.append(name)

        meta = {
            "id": b64_encode(original_url),
            "type": "movie" if is_movie else "series",
            "name": title,
            "poster": poster,
            "background": poster,
            "description": description or "Açıklama mevcut değil",
            "genres": genres or None
        }

        if is_movie:
            return {"meta": meta}

        # Sezon bilgisi: #s1, #s2 ... kutularından href -> sezon eşlemesi
        season_of = {}
        for box in soup.select('div.list-box'):
            box_id = box.get('id') or ''
            if len(box_id) > 1 and box_id[0] == 's' and box_id[1:].isdigit():
                snum = int(box_id[1:])
                for a in box.select('a.row'):
                    if a.get('href'):
                        season_of[a.get('href')] = snum

        all_box = soup.select_one('#all')
        rows = all_box.select('a.row') if all_box else soup.select('a.row')

        videos = []
        seen = set()
        for a in rows:
            href = a.get('href')
            if not href or href in seen:
                continue
            seen.add(href)

            ep_raw = (a.get('data-episode-id') or a.get('data-episode-safe-id') or '').strip()
            m = re.match(r'(\d+)', ep_raw)
            episode = int(m.group(1)) if m else (len(videos) + 1)
            season = season_of.get(href, 1)

            name_el = a.select_one('.name')
            eng_el = a.select_one('.eng-name')
            sub_el = a.select_one('.sub')
            ep_name = name_el.text.strip() if name_el and name_el.text.strip() else f"{episode}. Bölüm"
            eng_name = eng_el.text.strip() if eng_el else ''
            if eng_name and eng_name.lower() != ep_name.lower():
                ep_title = f"{ep_name} ({eng_name})"
            else:
                ep_title = ep_name

            full_url = abs_url(href)
            vid = {
                "id": b64_encode(full_url),
                "title": ep_title,
                "season": season,
                "episode": episode
            }
            if sub_el and sub_el.text.strip():
                vid["overview"] = sub_el.text.strip()
            videos.append(vid)

        videos.sort(key=lambda v: (v["season"], v["episode"]))
        meta["videos"] = videos
        return {"meta": meta}

    # ------------------------------------------------------------------
    # STREAM
    # ------------------------------------------------------------------
    def _extract_embeds(self, body):
        soup = BeautifulSoup(body, 'html.parser')
        blob = None
        container = soup.select_one('#videoDataContainer')
        if container and container.get('data-embeds'):
            blob = container.get('data-embeds')
        if not blob:
            m = re.search(r"__embeds_b64\s*=\s*'([^']+)'", body)
            if m:
                blob = m.group(1)
        if not blob:
            m = re.search(r'__embeds_b64\s*=\s*"([^"]+)"', body)
            if m:
                blob = m.group(1)
        if not blob:
            return []
        try:
            decoded = base64.b64decode(blob).decode('utf-8', errors='ignore')
            data = json.loads(decoded)
            if isinstance(data, list):
                return [str(x) for x in data if x]
        except Exception as e:
            print(f"❌ embed decode error: {e}")
        return []

    def _parse_stream_page(self, body, metadata):
        original_url = metadata.get('originalUrl') or ''
        embeds = self._extract_embeds(body)
        if not embeds:
            return {"streams": []}

        instructions = []
        for i, raw in enumerate(embeds):
            embed_url = abs_url(raw)
            extractor_type, server_name = _detect_extractor(embed_url)
            encoded = urllib.parse.quote(embed_url, safe=";/?:@&=+$,%")
            instructions.append({
                "requestId": f"cizgivedizi-extract-{int(time.time()*1000)}-{rand_id()}-{i}",
                "purpose": "extractor",
                "url": encoded,
                "method": "GET",
                "headers": get_enhanced_headers(BASE_URL),
                "metadata": {
                    "hiddenweb": False,
                    "originalUrl": original_url,
                    "extractorType": extractor_type,
                    "serverName": f"{server_name} {i + 1}" if len(embeds) > 1 else server_name
                }
            })
        return {"instructions": instructions}

    def _parse_extractor(self, body, url, metadata):
        extractor_type = metadata.get('extractorType', 'generic')
        server_name = metadata.get('serverName', 'CizgiveDizi')
        referer = urllib.parse.quote(url or '', safe=";/?:@&=+$,%")

        def make_stream(stream_url, ref=None):
            return {
                "name": server_name,
                "title": server_name,
                "url": stream_url,
                "behaviorHints": {
                    "notWebReady": False,
                    "bingeGroup": "cizgivedizi-stream",
                    "proxyHeaders": {
                        "request": {
                            "User-Agent": "Mozilla/5.0",
                            "Referer": ref or referer
                        }
                    }
                }
            }

        streams = []

        if extractor_type in ('cizgiduo', 'cizgipass'):
            m = re.search(r"bePlayer\('([^']+)',\s*'(\{[^}]+\})'\);", body)
            if m:
                decrypted = crypto_aes_handler(m.group(2), m.group(1), False)
                if decrypted:
                    vm = re.search(r'video_location":"([^"]+)', decrypted)
                    if vm:
                        streams.append(make_stream(vm.group(1).replace('\\', '')))

        elif extractor_type == 'sibnet':
            m = re.search(r'player\.src\(\[\{\s*src:\s*"([^"]+)"', body)
            if m:
                src = m.group(1)
                if not src.startswith('http'):
                    src = 'https://video.sibnet.ru' + (src if src.startswith('/') else '/' + src)
                streams.append(make_stream(src, ref='https://video.sibnet.ru/'))

        elif extractor_type == 'googledrive':
            parts = (url or '').split('/d/')
            if len(parts) > 1:
                url_id = parts[1].split('/')[0]
                return {
                    "instructions": [{
                        "requestId": f"cizgivedizi-gdrive-api-{int(time.time()*1000)}-{rand_id()}",
                        "purpose": "googledrive-api",
                        "url": "https://gdplayer.vip/api/video",
                        "method": "POST",
                        "headers": {
                            "Content-Type": "application/x-www-form-urlencoded",
                            "User-Agent": "Mozilla/5.0"
                        },
                        "body": f"file_id={url_id}&subtitle=",
                        "metadata": {"hiddenweb": False, "serverName": server_name, "urlId": url_id}
                    }]
                }

        else:
            patterns = [
                r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'src:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'(https?:\/\/[^\s"\'<>()]+\.m3u8[^\s"\'<>()]*)',
                r'player\.src\(\[\{\s*src:\s*"([^"]+)"',
                r'sources:\s*\[\{\s*(?:file|src)\s*:\s*["\']([^"\']+)["\']',
                r'(https?:\/\/[^\s"\'<>()]+\.mp4[^\s"\'<>()]*)',
            ]
            for pat in patterns:
                m = re.search(pat, body)
                if m:
                    streams.append(make_stream(m.group(1)))
                    break

        return {"streams": streams}

    # ------------------------------------------------------------------
    # GOOGLE DRIVE (gdplayer.vip) ZİNCİRİ
    # ------------------------------------------------------------------
    def _gdrive_api(self, body, metadata):
        try:
            data = json.loads(body)
            if data.get('status') == 'success' and 'embedUrl' in data.get('data', {}):
                return {
                    "instructions": [{
                        "requestId": f"cizgivedizi-gdrive-embed-{int(time.time()*1000)}-{rand_id()}",
                        "purpose": "googledrive-embed",
                        "url": data['data']['embedUrl'],
                        "method": "GET",
                        "headers": get_enhanced_headers('https://gdplayer.vip/'),
                        "metadata": {"hiddenweb": False, "serverName": metadata.get('serverName')}
                    }]
                }
        except Exception:
            pass
        return {"streams": []}

    def _gdrive_embed(self, body, metadata):
        soup = BeautifulSoup(body, 'html.parser')
        body_el = soup.select_one('body[ng-init]')
        if body_el:
            m = re.search(r"init\('([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']*)'\)", body_el.get('ng-init'))
            if m:
                play_url = m.group(1)
                key_hex = m.group(2)
                return {
                    "instructions": [{
                        "requestId": f"cizgivedizi-gdrive-video-{int(time.time()*1000)}-{rand_id()}",
                        "purpose": "googledrive-video",
                        "url": f"{play_url}/?video_id={key_hex}&action=get_video",
                        "method": "GET",
                        "headers": {"User-Agent": "Mozilla/5.0", "Referer": "https://gdplayer.vip/"},
                        "metadata": {
                            "hiddenweb": False,
                            "serverName": metadata.get('serverName'),
                            "playUrl": play_url,
                            "keyHex": key_hex
                        }
                    }]
                }
        return {"streams": []}

    def _gdrive_video(self, body, metadata):
        streams = []
        try:
            data = json.loads(body)
            play_url = metadata.get('playUrl')
            key_hex = metadata.get('keyHex')
            server_name = metadata.get('serverName') or 'GDrive'
            for q in data.get('qualities', []):
                quality = q.get('quality')
                streams.append({
                    "name": f"{server_name} {quality}p",
                    "title": f"{server_name} {quality}p",
                    "url": f"{play_url}/?video_id={key_hex}&quality={quality}&action=p",
                    "behaviorHints": {
                        "notWebReady": False,
                        "bingeGroup": "cizgivedizi-stream",
                        "proxyHeaders": {"request": {"User-Agent": "Mozilla/5.0", "Referer": "https://gdplayer.vip/"}}
                    }
                })
        except Exception:
            pass
        return {"streams": streams}
