import base64
import json
import re
import urllib.parse
import random
import time
from bs4 import BeautifulSoup


def base64_decode_safe(s):
    s = (s or '').strip()
    s += '=' * (-len(s) % 4)
    try:
        return base64.b64decode(s).decode('utf-8')
    except Exception:
        try:
            return base64.b64decode(s).decode('latin1')
        except Exception:
            return ''


def base64_encode_safe(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8').replace('=', '')


def _b64_bytes(s):
    s = (s or '').strip()
    s += '=' * (-len(s) % 4)
    return base64.b64decode(s)


def get_and_unpack(packed_js):
    """Dean Edwards p,a,c,k,e,d unpacker (rapidvid / king / benzeri player'lar)."""
    try:
        if not re.search(r'eval\(function\(p,a,c,k,e,(?:r|d)\)', packed_js):
            return packed_js
        m = re.search(r"}\('(.*)',(\d+),(\d+),'(.*)'\.", packed_js)
        if not m:
            return packed_js
        p = m.group(1).replace("\\'", "'")
        a = int(m.group(2))
        c = int(m.group(3))
        k = m.group(4).split('|')

        def to_base(num, radix):
            chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
            if num == 0:
                return '0'
            res = ''
            while num > 0:
                res = chars[num % radix] + res
                num //= radix
            return res

        result = p
        for i in range(c - 1, -1, -1):
            if i < len(k) and k[i]:
                result = re.sub(r'\b' + re.escape(to_base(i, a)) + r'\b', k[i], result)
        return result
    except Exception as e:
        print(f"⚠️  Unpack error: {e}")
        return packed_js


def decode_rapidvid_av(input_str):
    """rapidvid.net  ->  file: av('...')  şifre çözücü (K9L key)."""
    try:
        first = base64.b64decode(input_str[::-1])
        key = 'K9L'
        adjusted = bytearray(len(first))
        for i in range(len(first)):
            adjusted[i] = (first[i] - ((ord(key[i % 3]) % 5) + 1)) & 0xFF
        return base64.b64decode(adjusted).decode('utf-8')
    except Exception as e:
        print(f"⚠️  decode_rapidvid_av error: {e}")
        return ''


def decode_ee(encoded):
    """vidmoxy / benzeri  ->  file: EE.dd("...")  (base64 + rot13 + reverse)."""
    try:
        s = encoded.replace('-', '+').replace('_', '/')
        s += '=' * (-len(s) % 4)
        a = base64.b64decode(s).decode('utf-8')
        import codecs
        return codecs.encode(a, 'rot_13')[::-1]
    except Exception as e:
        print(f"⚠️  decode_ee error: {e}")
        return ''


def _extract_js_object(text, start_key):
    """`scx = { ... }` gibi bir JS objesini süslü parantez sayarak çıkar."""
    idx = text.find(start_key)
    if idx == -1:
        return None
    idx = text.find('{', idx)
    if idx == -1:
        return None
    depth = 0
    for i in range(idx, len(text)):
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[idx:i + 1]
    return None


def _decode_scx_source(s):
    """scx içindeki `sources` değerini gerçek embed/iframe URL'sine çevir.
    Site sürümüne göre; düz base64, ters base64, çift base64 olabiliyor."""
    s = (s or '').strip().strip('"\'')
    if not s:
        return None
    if s.startswith('http') or s.startswith('//'):
        return s

    candidates = []
    for variant in (s, s[::-1]):
        try:
            candidates.append(_b64_bytes(variant).decode('utf-8', 'ignore'))
        except Exception:
            pass
    # çift base64 denemeleri
    for c in list(candidates):
        for variant in (c, c[::-1]):
            try:
                candidates.append(_b64_bytes(variant).decode('utf-8', 'ignore'))
            except Exception:
                pass

    for c in candidates:
        if c and ('http' in c or c.lstrip().startswith('//')):
            m = re.search(r'(https?:)?//[^\s"\'<>\\]+', c)
            if m:
                return m.group(0)
    return None


def _norm_lang(label):
    l = (label or '').strip()
    low = l.lower()
    if 'forced' in low:
        return 'Turkish Forced'
    if any(k in low for k in ('tur', 'tr', 'türk', 'turk')):
        return 'Turkish'
    if any(k in low for k in ('eng', 'en', 'ingiliz')):
        return 'English'
    return l or 'Türkçe'


def extract_player_tracks(content, base_origin=''):
    """Player iframe içeriğinden altyazı + ses (audio) track'lerini çıkar.
    `tracks:[{file,label,kind}]` veya `"file":"..","label":".."` kalıpları."""
    subtitles, audio_tracks = [], []
    seen_sub, seen_aud = set(), set()

    def _abs(u):
        u = (u or '').replace('\\/', '/').replace('\\u0026', '&').replace('\\', '')
        if not u:
            return u
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/') and base_origin:
            return base_origin + u
        return u

    def _attr(obj, name):
        m = re.search(r'["\']?' + name + r'["\']?\s*:\s*["\']([^"\']+)["\']', obj)
        return m.group(1) if m else ''

    blocks = re.findall(r'\btracks\s*:\s*(\[[\s\S]*?\])', content) + re.findall(r'"tracks"\s*:\s*(\[[\s\S]*?\])', content)
    for raw in blocks:
        objs = re.findall(r'\{[^{}]*\}', raw)
        for obj in objs:
            f = _abs(_attr(obj, 'file') or _attr(obj, 'src'))
            if not f:
                continue
            kind = (_attr(obj, 'kind') or '').lower()
            label = _attr(obj, 'label') or _attr(obj, 'language') or ''
            if kind in ('captions', 'subtitles') or (not kind and f.lower().split('?')[0].endswith(('.vtt', '.srt'))):
                if f not in seen_sub:
                    seen_sub.add(f)
                    lang = _norm_lang(label)
                    subtitles.append({'id': lang.lower().replace(' ', '_'), 'url': f, 'lang': lang})
            elif kind in ('audio', 'audiotrack'):
                if f not in seen_aud:
                    seen_aud.add(f)
                    lang = label or 'Orijinal'
                    audio_tracks.append({'id': lang.lower().replace(' ', '_'), 'url': f, 'lang': lang})

    if not subtitles:
        for m in re.finditer(r'["\']?file["\']?\s*:\s*["\']([^"\']+?\.(?:vtt|srt)[^"\']*)["\'][^{}]*?["\']?label["\']?\s*:\s*["\']([^"\']+)["\']', content):
            f = _abs(m.group(1))
            if f in seen_sub:
                continue
            seen_sub.add(f)
            lang = _norm_lang(m.group(2))
            subtitles.append({'id': lang.lower().replace(' ', '_'), 'url': f, 'lang': lang})

    return subtitles, audio_tracks


UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'


class FullHDFilmIzleseneScraper:
    def __init__(self):
        self.BASE_URL = 'https://www.fullhdfilmizlesene.now'
        self.manifest = {
            'id': 'community.fullhdfilmizlesene',
            'version': '1.0.0',
            'name': 'FullHDFilmizlesene',
            'description': 'Full HD yerli ve yabancı film izleme platformu - FullHDFilmizlesene için Stremio eklentisi (Instruction Mode)',
            'logo': 'https://www.fullhdfilmizlesene.now/apple-touch-icon.png',
            'resources': ['catalog', 'meta', 'stream'],
            'types': ['movie'],
            'catalogs': [
                {'type': 'movie', 'id': 'fhd_search', 'name': 'Arama', 'extra': [{'name': 'search', 'isRequired': True}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_yeni', 'name': 'Yeni Filmler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_encok', 'name': 'En Çok İzlenenler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_trend', 'name': 'Trend Filmler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_populer', 'name': 'Popüler Filmler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_imdb', 'name': 'IMDb Puanı Yüksek', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_dublaj', 'name': 'Türkçe Dublaj', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_altyazi', 'name': 'Türkçe Altyazılı', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_4k', 'name': '4K Filmler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_2026', 'name': '2026 Filmleri', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_2025', 'name': '2025 Filmleri', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_aksiyon', 'name': 'Aksiyon', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_komedi', 'name': 'Komedi', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_bilimkurgu', 'name': 'Bilim Kurgu', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_korku', 'name': 'Korku', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_gerilim', 'name': 'Gerilim', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_romantik', 'name': 'Romantik', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_animasyon', 'name': 'Animasyon', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_dram', 'name': 'Dram', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'fhd_yerli', 'name': 'Yerli Filmler', 'extra': [{'name': 'skip', 'isRequired': False}]},
            ],
            'idPrefixes': ['fhd']
        }

        # Katalog id -> site yolu (sayfa numarası "/{n}" eklenerek gezilir)
        self.CATALOG_PATHS = {
            'fhd_yeni': '/yeni-filmler',
            'fhd_encok': '/en-cok-izlenen-filmler',
            'fhd_trend': '/trend-filmler',
            'fhd_populer': '/populer-filmler',
            'fhd_imdb': '/filmizle/imdb-puani-yuksek-filmler',
            'fhd_dublaj': '/filmizle/turkce-dublaj-filmler-1',
            'fhd_altyazi': '/filmizle/turkce-altyazili-filmler-1',
            'fhd_4k': '/filmizle/4k-filmler',
            'fhd_2026': '/yil/2026-filmleri-izle',
            'fhd_2025': '/yil/2025-filmler-izle',
            'fhd_aksiyon': '/filmizle/aksiyon-filmleri',
            'fhd_komedi': '/filmizle/komedi-filmleri',
            'fhd_bilimkurgu': '/filmizle/bilim-kurgu-filmleri',
            'fhd_korku': '/filmizle/korku-filmleri',
            'fhd_gerilim': '/filmizle/gerilim-filmleri',
            'fhd_romantik': '/filmizle/romantik-filmler',
            'fhd_animasyon': '/filmizle/animasyon-filmleri',
            'fhd_dram': '/filmizle/dram-filmler-izle',
            'fhd_yerli': '/filmizle/yerli-filmler',
        }

    def getManifest(self):
        return self.manifest

    def _headers(self, referer=None):
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'User-Agent': UA,
            'Referer': referer or (self.BASE_URL + '/'),
        }

    def _abs(self, u):
        if not u:
            return u
        if u.startswith('http'):
            return u
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.BASE_URL + u
        return self.BASE_URL + '/' + u

    # ---------------------------------------------------------------- catalog
    async def handleCatalog(self, args):
        catalog_id = args.get('id')
        extra = args.get('extra', {}) or {}
        search_query = extra.get('search')
        skip = int(extra.get('skip', 0) or 0)
        page = (skip // 20) + 1
        rand = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))

        print(f"\n🎯 [FullHDFilmizlesene Catalog] id={catalog_id} page={page} search={search_query}")

        if catalog_id == 'fhd_search':
            if not search_query:
                return {'instructions': []}
            url = f"{self.BASE_URL}/arama/{urllib.parse.quote(search_query)}"
            return {
                'instructions': [{
                    'requestId': f"fhd-search-{int(time.time()*1000)}-{rand}",
                    'purpose': 'catalog',
                    'url': url,
                    'method': 'GET',
                    'headers': self._headers(),
                    'metadata': {'hiddenweb': True, 'catalogId': catalog_id}
                }]
            }

        path = self.CATALOG_PATHS.get(catalog_id)
        if not path:
            return {'instructions': []}

        url = self.BASE_URL + path
        if page > 1:
            url = f"{url}/{page}"

        return {
            'instructions': [{
                'requestId': f"fhd-catalog-{catalog_id}-{page}-{int(time.time()*1000)}-{rand}",
                'purpose': 'catalog',
                'url': url,
                'method': 'GET',
                'headers': self._headers(),
                'metadata': {'hiddenweb': True, 'catalogId': catalog_id}
            }]
        }

    # ------------------------------------------------------------------- meta
    async def handleMeta(self, args):
        url = base64_decode_safe(args.get('id', '').replace('fhd:', ''))
        url = self._abs(url)
        rand = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        return {
            'instructions': [{
                'requestId': f"fhd-meta-{int(time.time()*1000)}-{rand}",
                'purpose': 'meta',
                'url': url,
                'method': 'GET',
                'headers': self._headers(),
                'metadata': {'hiddenweb': True}
            }]
        }

    # ----------------------------------------------------------------- stream
    async def handleStream(self, args):
        url = base64_decode_safe(args.get('id', '').replace('fhd:', ''))
        url = self._abs(url)
        rand = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        return {
            'instructions': [{
                'requestId': f"fhd-stream-{int(time.time()*1000)}-{rand}",
                'purpose': 'stream',
                'url': url,
                'method': 'GET',
                'headers': self._headers(),
                'metadata': {'hiddenweb': True, 'pageUrl': url}
            }]
        }

    # -------------------------------------------------------- shared parsing
    def _parse_film_list(self, soup):
        metas = []
        seen = set()
        for film in soup.select('.film, li.film, div.film'):
            a = film.select_one('a.tt') or film.select_one('a[href*="/film/"]') or film.find('a')
            if not a:
                continue
            href = self._abs(a.get('href'))
            if not href or '/film/' not in href or href in seen:
                continue

            title_el = film.select_one('.film-title') or film.select_one('h2.film-tt') or a
            title = (title_el.get_text(' ', strip=True) if title_el else '').replace(' izle', '').strip()
            if not title:
                title = (a.get('title') or a.get_text(strip=True) or '').replace(' izle', '').strip()
            if not title:
                continue

            year_el = film.select_one('.film-yil')
            year = year_el.get_text(strip=True) if year_el else None

            poster = None
            img = film.find('img')
            if img:
                poster = img.get('data-src') or img.get('src')
                if poster and poster.startswith('data:'):
                    poster = img.get('data-src')
            if not poster:
                src = film.find('source')
                if src:
                    raw = src.get('data-srcset') or src.get('srcset') or ''
                    poster = raw.split(' ')[0] if raw else None
            poster = self._abs(poster) if poster else None

            seen.add(href)
            metas.append({
                'id': 'fhd:' + base64_encode_safe(href),
                'type': 'movie',
                'name': f"{title} ({year})" if year else title,
                'poster': poster,
            })
        return metas

    def _find_scx_script(self, soup, body):
        for sc in soup.find_all('script'):
            data = sc.string or sc.get_text() or ''
            if re.search(r'\bscx\s*=\s*\{', data):
                return data
        m = re.search(r'\bscx\s*=\s*\{.*', body, re.DOTALL)
        return m.group(0) if m else ''

    def _collect_scx_sources(self, scx_obj):
        """scx yapısı:  {"atom":{"tt":"<b64 isim>","sx":{"p":[...],"t":[...]},"order":1}, ...}
        Eski yapı:      {"atom":{"sources":["<b64>"],"tracks":[...]}}
        Döndürür: [(kaynak_adı, embed_url), ...] ve altyazı listesi."""
        found, subs = [], []
        parsed = None
        try:
            parsed = json.loads(scx_obj)
        except Exception:
            try:
                parsed = json.loads(re.sub(r"'", '"', scx_obj.replace('\\/', '/')))
            except Exception:
                parsed = None

        if isinstance(parsed, dict):
            ordered = sorted(parsed.items(), key=lambda kv: (kv[1].get('order', 99) if isinstance(kv[1], dict) else 99))
            for key, val in ordered:
                if not isinstance(val, dict):
                    continue
                name = key
                if val.get('tt'):
                    dec = base64_decode_safe(val['tt'])
                    if dec:
                        name = dec
                candidates = []
                raw_sources = val.get('sources') or []
                if isinstance(raw_sources, str):
                    raw_sources = [raw_sources]
                candidates += raw_sources
                sx = val.get('sx') or {}
                if isinstance(sx, dict):
                    for arrkey in ('t', 'p', 'u', 'l'):
                        arr = sx.get(arrkey) or []
                        if isinstance(arr, str):
                            arr = [arr]
                        candidates += [x for x in arr if isinstance(x, str)]
                for rs in candidates:
                    if isinstance(rs, dict):
                        rs = rs.get('file') or rs.get('src') or ''
                    embed = _decode_scx_source(rs)
                    if embed:
                        found.append((name, self._abs(embed)))
                for tr in (val.get('tracks') or []):
                    if isinstance(tr, dict) and tr.get('file'):
                        lang = _norm_lang(tr.get('label') or tr.get('language'))
                        su = self._abs(tr['file'].replace('\\/', '/'))
                        if not any(s['url'] == su for s in subs):
                            subs.append({'id': lang.lower().replace(' ', '_'), 'url': su, 'lang': lang})
        else:
            for m in re.finditer(r'"(?:sources|t|p)"\s*:\s*\[\s*"([^"]+)"', scx_obj):
                embed = _decode_scx_source(m.group(1))
                if embed:
                    found.append(('kaynak', self._abs(embed)))
        return found, subs

    # ---------------------------------------------------- processFetchResult
    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body', '') or ''
        url = fetchResult.get('url', '') or ''
        metadata = fetchResult.get('metadata') or {}

        print(f"\n⚙️ [FullHDFilmizlesene] purpose={purpose} url={url[:90]}")

        if purpose == 'catalog':
            try:
                soup = BeautifulSoup(body, 'html.parser')
                metas = self._parse_film_list(soup)
                print(f"✅ {len(metas)} film bulundu")
                return {'metas': metas}
            except Exception as e:
                print(f"⚠️  Catalog parse error: {e}")
                return {'metas': []}

        if purpose == 'meta':
            try:
                soup = BeautifulSoup(body, 'html.parser')

                title = None
                ld = None
                for sc in soup.find_all('script', type='application/ld+json'):
                    try:
                        parsed = json.loads(sc.string or '{}')
                        items = parsed if isinstance(parsed, list) else [parsed]
                        for it in items:
                            if isinstance(it, dict) and it.get('@type') in ('Movie', 'CreativeWork', 'VideoObject'):
                                ld = it
                                break
                    except Exception:
                        continue
                    if ld:
                        break

                def _og(prop):
                    el = soup.select_one(f'meta[property="{prop}"]') or soup.select_one(f'meta[name="{prop}"]')
                    return el.get('content') if el and el.get('content') else None

                if ld:
                    title = ld.get('name')
                if not title:
                    h1 = soup.select_one('div.izle-titles h1') or soup.select_one('h1')
                    if h1:
                        title = h1.get_text(strip=True)
                title = (title or _og('og:title') or 'Bilinmeyen').replace(' izle', '').strip()

                poster = None
                if ld and ld.get('image'):
                    poster = ld['image'] if isinstance(ld['image'], str) else (ld['image'][0] if isinstance(ld['image'], list) else None)
                poster = poster or _og('og:image')
                if not poster:
                    pimg = soup.select_one('div.film-afis img, div.poster img, aside img')
                    if pimg:
                        poster = pimg.get('data-src') or pimg.get('src')
                poster = self._abs(poster) if poster else None

                description = (ld.get('description') if ld else None) or _og('og:description')
                if not description:
                    d = soup.select_one('div.ozet-ic p, div.ozet-ic, div.film-aciklama')
                    description = d.get_text(' ', strip=True) if d else 'Açıklama mevcut değil'

                year = None
                if ld and ld.get('datePublished'):
                    year = str(ld['datePublished'])[:4]
                if not year:
                    y = soup.select_one('div.release a, div.date, span.yil')
                    if y:
                        ym = re.search(r'\d{4}', y.get_text())
                        year = ym.group(0) if ym else None

                rating = None
                if ld and isinstance(ld.get('aggregateRating'), dict):
                    rating = str(ld['aggregateRating'].get('ratingValue') or '').strip() or None
                if not rating:
                    r = soup.select_one('div.imdb-count, span.imdb, div.rating')
                    if r:
                        rm = re.search(r'\d+[.,]?\d*', r.get_text())
                        rating = rm.group(0).replace(',', '.') if rm else None

                # film-info satırları:  <li><span class="dt">Tür</span><div class="dd">...</div></li>
                info_rows = {}
                for li in soup.select('div.film-info li'):
                    dt = li.select_one('.dt')
                    dd = li.select_one('.dd')
                    if dt and dd:
                        info_rows[dt.get_text(strip=True)] = dd

                genres = []
                if ld and ld.get('genre'):
                    genres = ld['genre'] if isinstance(ld['genre'], list) else [ld['genre']]
                if not genres and 'Tür' in info_rows:
                    genres = [a.get_text(strip=True).replace(' Filmleri', '') for a in info_rows['Tür'].select('a') if a.get_text(strip=True)]
                if not genres:
                    genres = [a.get_text(strip=True) for a in soup.select('div.turler a, div.category a, p.tur a') if a.get_text(strip=True)]

                lang_row = info_rows.get('Dil')
                page_lang = lang_row.get_text(' ', strip=True).strip(' -') if lang_row else None

                cast = []
                if ld and ld.get('actor'):
                    actors = ld['actor'] if isinstance(ld['actor'], list) else [ld['actor']]
                    for ac in actors:
                        if isinstance(ac, dict) and ac.get('name'):
                            cast.append(ac['name'])
                        elif isinstance(ac, str):
                            cast.append(ac)
                if not cast and 'Oyuncular' in info_rows:
                    cast = [a.get_text(strip=True) for a in info_rows['Oyuncular'].select('a') if a.get_text(strip=True)]
                if not cast:
                    cast = [a.get_text(strip=True) for a in soup.select('div.oyuncular a, div.cast a') if a.get_text(strip=True)]
                # çöp değerleri ele ('-', site adı)
                cast = [c for c in cast if c and c != '-' and 'fullhdfilm' not in c.lower()]

                director = None
                if ld and isinstance(ld.get('director'), dict):
                    dn = ld['director'].get('name')
                    if dn and 'fullhdfilm' not in dn.lower() and dn != '-':
                        director = dn
                if not director and 'Yönetmen' in info_rows:
                    dn = info_rows['Yönetmen'].get_text(' ', strip=True).strip(' -')
                    director = dn or None

                if page_lang and page_lang not in (description or ''):
                    description = f"{description}\n\n🎧 Dil: {page_lang}"

                recommendations = []
                for film in soup.select('div.film-strip .film, div.benzer .film, div.related .film'):
                    ra = film.find('a')
                    rimg = film.find('img')
                    if ra and ra.get('href'):
                        rhref = self._abs(ra.get('href'))
                        if '/film/' not in rhref:
                            continue
                        recommendations.append({
                            'id': 'fhd:' + base64_encode_safe(rhref),
                            'type': 'movie',
                            'name': (ra.get('title') or ra.get_text(strip=True) or '').replace(' izle', '').strip(),
                            'poster': self._abs(rimg.get('data-src') or rimg.get('src')) if rimg else None,
                        })

                meta = {
                    'id': 'fhd:' + base64_encode_safe(url),
                    'type': 'movie',
                    'name': title,
                    'poster': poster,
                    'background': poster,
                    'description': description,
                    'releaseInfo': year,
                    'imdbRating': rating,
                    'genres': genres or None,
                    'cast': cast[:15] or None,
                    'director': [director] if director else None,
                    'recommendations': recommendations[:20] or None,
                }
                print(f"✅ Meta: {title} ({year}) rating={rating}")
                return {'meta': meta}
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"⚠️  Meta parse error: {e}")
                return {'meta': None}

        if purpose == 'stream':
            try:
                soup = BeautifulSoup(body, 'html.parser')
                instructions = []
                page_url = metadata.get('pageUrl') or url

                # dil bilgisi (film-info "Dil" satırı)
                page_lang = None
                for li in soup.select('div.film-info li'):
                    dt = li.select_one('.dt')
                    if dt and 'Dil' in dt.get_text():
                        dd = li.select_one('.dd')
                        if dd:
                            page_lang = dd.get_text(' ', strip=True).strip(' -')
                        break

                # 1) scx = {"atom":{"tt":..,"sx":{"p":[],"t":[..]},"order":1}, ...}
                script_data = self._find_scx_script(soup, body)
                scx_obj = _extract_js_object(script_data, 'scx') if script_data else None
                subtitles = []
                sources_found = []

                if scx_obj:
                    sf, sb = self._collect_scx_sources(scx_obj)
                    sources_found += sf
                    subtitles += sb

                # 2) Webview tarafından render edilen player iframe'leri
                _iframe_blocklist = ('youtube.com', 'youtu.be', 'google.', 'gstatic', 'disqus.com',
                                     'facebook.com', 'twitter.com', 'doubleclick', 'googlesyndication',
                                     '/trailer', 'imgz.me')
                for ifr in soup.select('section.player-alan iframe, figure.ply iframe, #plx iframe, '
                                       '.part-source-sec iframe, .part-btns iframe, div#singlePlay iframe, '
                                       'div.video-content iframe, div#player iframe, iframe'):
                    src = ifr.get('data-src') or ifr.get('src')
                    if src and ('http' in src or src.startswith('//')) and not any(b in src.lower() for b in _iframe_blocklist):
                        sources_found.append(('iframe', self._abs(src)))

                # 3) Alternatif kaynak butonlarındaki data-* ipuçları
                for btn in soup.select('.part-btns button, .part-btns a, .part-source-sec [data-src], .part-source-sec [data-embed]'):
                    for attr in ('data-src', 'data-embed', 'data-frame', 'data-url', 'data-iframe'):
                        v = btn.get(attr)
                        if v and ('http' in v or v.startswith('//')):
                            sources_found.append((btn.get_text(strip=True) or 'kaynak', self._abs(v)))

                # tekilleştir
                uniq = []
                seen_u = set()
                for name, u in sources_found:
                    if u and u not in seen_u and 'about:blank' not in u:
                        seen_u.add(u)
                        uniq.append((name, u))

                for name, embed_url in uniq:
                    rand = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                    instructions.append({
                        'requestId': f"fhd-extract-{int(time.time()*1000)}-{rand}",
                        'purpose': 'stream_extract',
                        'url': embed_url,
                        'method': 'GET',
                        'headers': {
                            'User-Agent': UA,
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Referer': self.BASE_URL + '/',
                        },
                        'metadata': {
                            'hiddenweb': True,
                            'sourceName': name,
                            'pageUrl': page_url,
                            'pageLang': page_lang,
                            'subtitles': subtitles,
                        }
                    })

                print(f"✅ {len(instructions)} video kaynağı bulundu")
                if instructions:
                    return {'instructions': instructions}
                return {'streams': []}
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"⚠️  Stream parse error: {e}")
                return {'streams': []}

        if purpose == 'stream_extract':
            streams = []
            meta = fetchResult.get('metadata') or {}
            source_name = (meta.get('sourceName') or 'FullHD').strip()
            page_lang = meta.get('pageLang')
            subtitles = list(meta.get('subtitles') or [])
            audio_tracks = list(meta.get('audioTracks') or [])
            page_url = meta.get('pageUrl') or url
            hop = int(meta.get('hop', 0) or 0)
            p = urllib.parse.urlparse(url)
            origin = f"{p.scheme}://{p.netloc}"
            low = url.lower()

            try:
                # tüm script'leri topla + packed olanları aç
                combined = body
                for sc in re.findall(r'<script[^>]*>(.*?)</script>', body, re.DOTALL):
                    if 'eval(function(p,a,c,k,e' in sc:
                        combined += '\n' + get_and_unpack(sc)

                # --- altyazı + ses track'leri ---
                s2, a2 = extract_player_tracks(combined, origin)
                for s in s2:
                    if not any(x['url'] == s['url'] for x in subtitles):
                        subtitles.append(s)
                for a in a2:
                    if not any(x['url'] == a['url'] for x in audio_tracks):
                        audio_tracks.append(a)

                final_url = None
                stype = 'm3u8'

                # rapidvid.net player: window._p8  (reverse -> atob -> "-K9L" -> atob -> JSON)
                #   cm = temel HLS, tm = tier/premium HLS, ct = altyazı listesi
                mp8 = re.search(r"""window\._p8\s*=\s*['"]([A-Za-z0-9+/=]+)['"]""", combined)
                if mp8:
                    try:
                        pj = json.loads(decode_rapidvid_av(mp8.group(1)))
                        for tr in (pj.get('ct') or []):
                            if isinstance(tr, dict) and tr.get('file'):
                                fu = tr['file']
                                fu = 'https:' + fu if fu.startswith('//') else fu
                                lang = _norm_lang(tr.get('label') or tr.get('language'))
                                if not any(s['url'] == fu for s in subtitles):
                                    subtitles.append({'id': lang.lower().replace(' ', '_'), 'url': fu, 'lang': lang})

                        lang_tag = f" [{page_lang}]" if page_lang else ''
                        rv_ref = f"{p.scheme}://{p.netloc}/"
                        variants = []
                        if pj.get('tr') and pj.get('tm'):
                            variants.append((pj['tm'], 'Tier'))
                        if pj.get('cm'):
                            variants.append((pj['cm'], 'HD'))
                        rv_origin = f"{p.scheme}://{p.netloc}"
                        for vurl, vlabel in variants:
                            if vurl.startswith('//'):
                                vurl = 'https:' + vurl
                            nm = f"FullHD · {source_name} {vlabel}{lang_tag}"
                            st = {
                                'name': nm,
                                'title': nm,
                                'url': vurl,
                                'type': 'm3u8',
                                'behaviorHints': {
                                    'notWebReady': False,
                                    'bingeGroup': 'fullhdfilmizlesene',
                                    'proxyHeaders': {'request': {
                                        'User-Agent': UA,
                                        'Referer': rv_ref,
                                        'Origin': rv_origin,
                                    }},
                                },
                            }
                            if subtitles:
                                st['subtitles'] = subtitles
                            streams.append(st)
                        if streams:
                            streams.append({
                                'name': 'Tarayıcıda Aç',
                                'title': 'Tarayıcıda Oynat',
                                'externalUrl': url,
                                'behaviorHints': {'notWebReady': True},
                            })
                            print(f"✅ _p8 çözüldü: {len(variants)} kaynak, {len(subtitles)} altyazı")
                            return {'streams': streams}
                    except Exception as e:
                        print(f"⚠️  _p8 decode error: {e}")

                # rapidvid: file: av('...')
                if 'rapidvid' in low or "av('" in combined or 'av("' in combined:
                    m = re.search(r"""file:\s*av\(['"]([^'"]+)['"]\)""", combined)
                    if m:
                        final_url = decode_rapidvid_av(m.group(1))

                # vidmoxy / EE.dd
                if not final_url and ('vidmoxy' in low or 'EE.dd' in combined):
                    m = re.search(r'file\s*:\s*EE\.dd\("([^"]+)"', combined)
                    if m:
                        final_url = decode_ee(m.group(1))

                # JWPlayer sources:[{file:"..."}]
                if not final_url:
                    m = re.search(r'sources\s*:\s*\[\s*\{[^}]*?["\']?file["\']?\s*:\s*["\']([^"\']+)["\']', combined, re.IGNORECASE)
                    if m:
                        final_url = m.group(1)

                # atob("...") içinde m3u8
                if not final_url:
                    for m in re.finditer(r'atob\(\s*["\']([A-Za-z0-9+/=]+)["\']\s*\)', combined):
                        try:
                            dec = base64.b64decode(m.group(1) + '===').decode('utf-8', 'ignore')
                            mm = re.search(r'https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*', dec)
                            if mm:
                                final_url = mm.group(0)
                                break
                        except Exception:
                            pass

                # düz file:/source:/src: "...m3u8"
                if not final_url:
                    m = re.search(r'["\']?(?:file|source|src|url)["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', combined, re.IGNORECASE)
                    if m:
                        final_url = m.group(1)

                # herhangi bir .m3u8 / .mp4
                if not final_url:
                    m = re.search(r'(https?:\\?/\\?/[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', combined, re.IGNORECASE)
                    if m:
                        final_url = m.group(1)
                if not final_url:
                    m = re.search(r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)', combined, re.IGNORECASE)
                    if m:
                        final_url = m.group(1)
                        stype = 'mp4'

                # embed sayfası içinde GERÇEKTEN farklı bir iframe/redirect varsa zincirle (max 2 hop)
                if not final_url and hop < 2:
                    soup2 = BeautifulSoup(body, 'html.parser')
                    nested = None
                    for ifr in soup2.find_all('iframe'):
                        cand = ifr.get('data-src') or ifr.get('src')
                        if cand and ('http' in cand or cand.startswith('//')) and 'about:blank' not in cand:
                            nested = cand
                            break
                    if not nested:
                        mm = re.search(r'''(?:location\.href|window\.location(?:\.href)?|top\.location)\s*=\s*["']([^"']+)["']''', combined)
                        if mm and 'http' in mm.group(1):
                            nested = mm.group(1)
                    if nested:
                        nested = self._abs(nested.replace('\\/', '/'))
                        _same_host = urllib.parse.urlparse(nested).netloc == p.netloc
                        if nested and nested != url and not (_same_host and 'rapidvid' in low):
                            rand = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                            return {
                                'instructions': [{
                                    'requestId': f"fhd-extract-{int(time.time()*1000)}-{rand}",
                                    'purpose': 'stream_extract',
                                    'url': nested,
                                    'method': 'GET',
                                    'headers': {'User-Agent': UA, 'Referer': url},
                                    'metadata': {'hiddenweb': True, 'sourceName': source_name, 'pageUrl': page_url,
                                                 'pageLang': page_lang, 'subtitles': subtitles, 'audioTracks': audio_tracks,
                                                 'hop': hop + 1}
                                }]
                            }

                # etiket
                lang_tag = f" [{page_lang}]" if page_lang else ''
                label = f"FullHD · {source_name}{lang_tag}"

                if final_url and final_url.startswith(('http', '//')):
                    final_url = final_url.replace('\\/', '/').replace('\\', '')
                    if final_url.startswith('//'):
                        final_url = 'https:' + final_url
                    is_hls = '.m3u8' in final_url or stype == 'm3u8'
                    stream = {
                        'name': label,
                        'title': label,
                        'url': final_url,
                        'type': 'm3u8' if is_hls else 'mp4',
                        'behaviorHints': {
                            'notWebReady': False,
                            'bingeGroup': 'fullhdfilmizlesene',
                            'proxyHeaders': {'request': {'User-Agent': UA, 'Referer': url, 'Origin': origin}},
                        }
                    }
                    if subtitles:
                        stream['subtitles'] = subtitles
                    if audio_tracks:
                        stream['audioTracks'] = audio_tracks
                    streams.append(stream)
                    print(f"✅ Stream ({label}): {final_url[:90]}  subs={len(subtitles)} audio={len(audio_tracks)}")
                else:
                    stream = {
                        'name': f"{label} (iframe)",
                        'title': f"{label} - Player",
                        'url': url,
                        'behaviorHints': {
                            'notWebReady': True,
                            'bingeGroup': 'fullhdfilmizlesene',
                            'proxyHeaders': {'request': {'User-Agent': UA, 'Referer': self.BASE_URL + '/'}},
                        },
                    }
                    if subtitles:
                        stream['subtitles'] = subtitles
                    streams.append(stream)
                    print(f"⚠️  m3u8 çözülemedi, iframe stream döndürülüyor: {url[:90]}")
                    try:
                        dbg = f"debug_fhd_extract_{int(time.time())}.html"
                        with open(dbg, 'w', encoding='utf-8') as _f:
                            _f.write(f"<!-- {url} -->\n{body}")
                        print(f"🐛 [stream_extract] Debug dump: {dbg} ({len(body)} bytes)")
                    except Exception as _e:
                        print(f"🐛 dump hatası: {_e}")

                streams.append({
                    'name': 'Tarayıcıda Aç',
                    'title': 'Tarayıcıda Oynat',
                    'externalUrl': url,
                    'behaviorHints': {'notWebReady': True},
                })
                return {'streams': streams}
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"⚠️  stream_extract error: {e}")
                return {'streams': streams}

        return {'ok': True}
