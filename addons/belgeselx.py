import base64
import json
import re
import time
import urllib.parse
from bs4 import BeautifulSoup

BASE_URL = 'https://belgeselx.com'

# site JS: var srcMap = { '0':'new5','2':'new1','5':'new4','3':'new2','4':'new3' };
SRC_MAP = {'0': 'new5', '2': 'new1', '5': 'new4', '3': 'new2', '4': 'new3'}

# Kanal (belgesel kanalları) — görünen ad -> slug
CHANNELS = {
    'National Geographic': 'national-geographic',
    'National Geographic HD': 'national-geographic-hd',
    'National Geographic Wild': 'national-geographic-wild',
    'Discovery Channel': 'discovery-channel',
    'Discovery Science': 'discovery-science',
    'Discovery ID': 'discovery-id',
    'History Channel': 'history-channel',
    'History HD': 'history-hd',
    'History Viasat': 'history-viasat',
    'BBC': 'bbc',
    'Science Vie': 'science-vie',
    'Da Vinci Learning': 'da-vinci-learning',
    'Diğer Belgeseller': 'diger-belgeseller',
    'TRT Belgesel': 'trt-belgesel',
    'Eğitim Setleri': 'egitim-setleri',
}

# Konu (belgesel türleri) — görünen ad -> slug
TOPICS = {
    'Türk Tarihi Belgeselleri': 'turk-tarihi-belgeselleri',
    'Tarih Belgeselleri': 'tarih-belgeselleri',
    'Seyahat Belgeselleri': 'seyehat-belgeselleri',
    'Seri Belgeseller': 'seri-belgeseller',
    'Savaş Belgeselleri': 'savas-belgeselleri',
    'Sanat Belgeselleri': 'sanat-belgeselleri',
    'Psikoloji Belgeselleri': 'psikoloji-belgeselleri',
    'Polisiye Belgeselleri': 'polisiye-belgeselleri',
    'Otomobil Belgeselleri': 'otomobil-belgeselleri',
    'Nazi Belgeselleri': 'nazi-belgeselleri',
    'Mühendislik Belgeselleri': 'muhendislik-belgeselleri',
    'Kültür Din Belgeselleri': 'kultur-din-belgeselleri',
    'Kozmik Belgeseller': 'kozmik-belgeseller',
    'Hayvan Belgeselleri': 'hayvan-belgeselleri',
    'Eski Tarih Belgeselleri': 'eski-tarih-belgeselleri',
    'Eğitim Belgeselleri': 'egitim-belgeselleri',
    'Dünya Belgeselleri': 'dunya-belgeselleri',
    'Doğa Belgeselleri': 'doga-belgeselleri',
    'Çizgi Film': 'cizgi-film',
    'Bilim Belgeselleri': 'bilim-belgeselleri',
}

# Sitemap'ten çıkarılan (slug, başlık) listesi — client'ın döndürdüğü body ile doldurulur.
_SITEMAP_CACHE = {'ts': 0.0, 'items': []}
_SITEMAP_TTL = 1800  # 30 dk


def base64_encode_safe(s):
    return base64.urlsafe_b64encode(s.encode('utf-8')).decode('utf-8').replace('=', '')


def base64_decode_safe(s):
    s += '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode('utf-8')).decode('utf-8')


_TR_MAP = str.maketrans({
    'ı': 'i', 'İ': 'i', 'ş': 's', 'Ş': 's', 'ç': 'c', 'Ç': 'c',
    'ğ': 'g', 'Ğ': 'g', 'ü': 'u', 'Ü': 'u', 'ö': 'o', 'Ö': 'o',
})


def _norm(s):
    return (s or '').translate(_TR_MAP).lower()


def _slug_to_title(slug):
    return re.sub(r'\s+', ' ', slug.replace('-', ' ')).strip().title()


def _fix_url(u):
    if not u:
        return None
    if u.startswith('//'):
        return 'https:' + u
    if u.startswith('/'):
        return BASE_URL + u
    return u


def _slug_from_href(href):
    m = re.search(r'/belgesel(?:dizi)?/([A-Za-z0-9-]+)', href or '')
    return m.group(1) if m else None


class BelgeselXScraper:
    def __init__(self):
        self.BASE_URL = BASE_URL
        catalog_extra_genre_kanal = [
            {'name': 'genre', 'options': list(CHANNELS.keys()), 'isRequired': False},
            {'name': 'skip', 'isRequired': False},
        ]
        catalog_extra_genre_konu = [
            {'name': 'genre', 'options': list(TOPICS.keys()), 'isRequired': False},
            {'name': 'skip', 'isRequired': False},
        ]
        self.manifest = {
            'id': 'community.belgeselx',
            'version': '1.0.0',
            'name': 'BelgeselX',
            'description': 'BelgeselX - Türkçe dublaj ve altyazılı HD belgesel izleme platformu için Stremio eklentisi',
            'logo': 'https://belgeselx.com/images/logo5.png',
            'resources': ['catalog', 'meta', 'stream'],
            'types': ['series'],
            'catalogs': [
                {'type': 'series', 'id': 'belgeselx_trend', 'name': 'BelgeselX - Haftanın Trendleri',
                 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'belgeselx_son', 'name': 'BelgeselX - Son Eklenenler',
                 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'belgeselx_pop', 'name': 'BelgeselX - En Çok İzlenenler',
                 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'belgeselx_kanal', 'name': 'BelgeselX - Kanallar',
                 'extra': catalog_extra_genre_kanal},
                {'type': 'series', 'id': 'belgeselx_konu', 'name': 'BelgeselX - Türler',
                 'extra': catalog_extra_genre_konu},
                {'type': 'series', 'id': 'belgeselx_search', 'name': 'BelgeselX',
                 'extra': [{'name': 'search', 'isRequired': True}]},
            ],
            'idPrefixes': ['belgeselx'],
        }

    def getManifest(self):
        return self.manifest

    def _headers(self, referer=None):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': referer or (BASE_URL + '/'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

    def _req_id(self, phase):
        return f"belgeselx-{phase}-{int(time.time() * 1000)}-{int(time.time() * 1000000) % 100000000}"

    # ---------------------------------------------------------------- CATALOG
    async def handleCatalog(self, args):
        catalog_id = args.get('id')
        extra = args.get('extra', {}) or {}
        skip = int(extra.get('skip', 0) or 0)
        search = extra.get('search')
        genre = extra.get('genre')

        if catalog_id == 'belgeselx_search':
            if not search:
                return {'metas': []}
            # Taze cache varsa hiç fetch etmeden dön
            if _SITEMAP_CACHE['items'] and (time.time() - _SITEMAP_CACHE['ts'] < _SITEMAP_TTL):
                return {'metas': self._search_in_cache(search)}
            return {'instructions': [{
                'requestId': self._req_id('search'),
                'purpose': 'search',
                'url': f"{BASE_URL}/sitemap.php",
                'method': 'GET',
                'headers': self._headers(),
                'metadata': {'hiddenweb': False, 'query': search},
            }]}

        if skip > 0:
            # Bu listelerin sayfalaması yok
            return {'metas': []}

        if catalog_id == 'belgeselx_trend':
            url = f"{BASE_URL}/haftanin-trendleri"
        elif catalog_id == 'belgeselx_son':
            url = f"{BASE_URL}/son-eklenenler"
        elif catalog_id == 'belgeselx_pop':
            url = f"{BASE_URL}/en-cok-izlenen-belgeseller"
        elif catalog_id == 'belgeselx_kanal':
            slug = CHANNELS.get(genre)
            if not slug:
                return {'metas': []}
            url = f"{BASE_URL}/belgeselkanali/{slug}"
        elif catalog_id == 'belgeselx_konu':
            slug = TOPICS.get(genre)
            if not slug:
                return {'metas': []}
            url = f"{BASE_URL}/konu/{slug}"
        else:
            return {'metas': []}

        return {'instructions': [{
            'requestId': self._req_id('catalog'),
            'purpose': 'catalog',
            'url': url,
            'method': 'GET',
            'headers': self._headers(),
            'metadata': {'hiddenweb': False},
        }]}

    def _search_in_cache(self, query):
        qwords = [w for w in _norm(query).split() if w]
        out = []
        seen = set()
        for slug, title in _SITEMAP_CACHE['items']:
            hay = _norm(slug.replace('-', ' ') + ' ' + title)
            if all(w in hay for w in qwords):
                if slug in seen:
                    continue
                seen.add(slug)
                out.append({
                    'id': 'belgeselx:' + base64_encode_safe(slug),
                    'type': 'series',
                    'name': title,
                    'poster': None,
                })
            if len(out) >= 50:
                break
        return out

    # ------------------------------------------------------------------- META
    async def handleMeta(self, args):
        raw = args.get('id', '')
        slug = base64_decode_safe(raw.split(':', 1)[1]) if ':' in raw else raw
        url = f"{BASE_URL}/belgesel/{slug}"
        return {'instructions': [{
            'requestId': self._req_id('meta'),
            'purpose': 'meta',
            'url': url,
            'method': 'GET',
            'headers': self._headers(),
            'metadata': {'hiddenweb': False, 'slug': slug},
        }]}

    # ----------------------------------------------------------------- STREAM
    async def handleStream(self, args):
        raw = args.get('id', '')
        payload = raw.split(':e:', 1)[1] if ':e:' in raw else raw.split(':', 1)[-1]
        data = json.loads(base64_decode_safe(payload))
        slug = data.get('s', '')
        vid = str(data.get('v', ''))
        ics = data.get('i', []) or []
        referer = f"{BASE_URL}/belgesel/{slug}"

        instructions = []
        for slot, ic in enumerate(ics[:3], start=1):
            php = SRC_MAP.get(str(ic), 'default')
            src_url = f"{BASE_URL}/video/data/{php}.php?id={vid}&sira={slot}"
            instructions.append({
                'requestId': self._req_id(f'stream{slot}'),
                'purpose': 'stream',
                'url': src_url,
                'method': 'GET',
                'headers': self._headers(referer),
                'metadata': {'hiddenweb': False, 'slot': slot, 'slug': slug},
            })
        if not instructions:
            return {'streams': []}
        return {'instructions': instructions}

    # -------------------------------------------------------- FETCH RESULT
    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body', '') or ''
        metadata = fetchResult.get('metadata', {}) or {}

        if purpose == 'catalog':
            return {'metas': self._parse_catalog(body)}

        if purpose == 'search':
            slugs = []
            seen = set()
            for m in re.finditer(r'/belgesel/([a-z0-9][a-z0-9-]*)', body):
                s = m.group(1)
                if s not in seen:
                    seen.add(s)
                    slugs.append(s)
            _SITEMAP_CACHE['items'] = [(s, _slug_to_title(s)) for s in slugs]
            _SITEMAP_CACHE['ts'] = time.time()
            return {'metas': self._search_in_cache(metadata.get('query', ''))}

        if purpose == 'meta':
            return {'meta': self._parse_meta(body, metadata.get('slug', ''))}

        if purpose == 'stream':
            return {'streams': self._parse_streams(body, metadata)}

        return {'ok': True}

    # -------------------------------------------------------------- parsers
    def _parse_catalog(self, body):
        soup = BeautifulSoup(body, 'html.parser')
        cards = soup.select(
            'a.px-ep-card, a.px-rank-item, a.px-trend-card, a.px-card, '
            'a.px-notable-card, a.px-today-card, a.px-today-hero'
        )
        metas = []
        seen = set()
        for a in cards:
            slug = _slug_from_href(a.get('href', ''))
            if not slug or slug in seen:
                continue
            img = a.find('img')
            name = None
            if img and img.get('alt'):
                name = img.get('alt').strip()
            if not name:
                t = a.select_one(
                    '.px-card-title, .px-trend-title, .px-today-card-title, '
                    '.px-notable-title, .px-rank-meta, .px-ep-series'
                )
                if t:
                    name = t.get_text(strip=True)
            if not name:
                continue
            poster = None
            if img:
                poster = img.get('data-src') or img.get('src')
                if poster and 'noimage' in poster:
                    poster = None
            seen.add(slug)
            metas.append({
                'id': 'belgeselx:' + base64_encode_safe(slug),
                'type': 'series',
                'name': name,
                'poster': _fix_url(poster),
            })
        return metas

    def _parse_meta(self, body, slug):
        soup = BeautifulSoup(body, 'html.parser')

        def og(prop):
            el = soup.find('meta', attrs={'property': prop})
            return el.get('content').strip() if el and el.get('content') else None

        canonical = slug
        ogurl = og('og:url')
        if ogurl:
            cs = _slug_from_href(ogurl)
            if cs:
                canonical = cs

        title = og('og:title') or ''
        title = re.sub(r'\s*[—\-]\s*belgeselx\.com\s*$', '', title, flags=re.I).strip()
        if not title:
            h1 = soup.select_one('h1')
            title = h1.get_text(strip=True) if h1 else _slug_to_title(canonical)

        poster = og('og:image')
        desc_el = soup.find('meta', attrs={'name': 'description'})
        description = desc_el.get('content').strip() if desc_el and desc_el.get('content') else ''

        genres = []
        ch = soup.select_one('.px-stat a[href*="/belgeselkanali/"], .px-hero-channel span, .px-channel-bottom span')
        if ch:
            href = ch.get('href') if ch.name == 'a' else ''
            cslug = _slug_from_href(href) or ch.get_text(strip=True).lower().replace(' ', '-')
            for name, slug in CHANNELS.items():
                if slug == cslug:
                    genres.append(name)
                    break
            else:
                g = ch.get_text(strip=True)
                if g:
                    genres.append(g)

        videos = []
        for idx, call in enumerate(re.finditer(r"diziGetir\((.*?)\)\s*;\s*return\s+false", body), start=1):
            argstr = call.group(1)
            parts = re.findall(r"'((?:[^'\\]|\\.)*)'", argstr)
            if len(parts) < 10:
                continue
            vid = parts[0]
            ic1, ic2, ic3 = parts[1], parts[2], parts[3]
            baslik = re.sub(r'\s+', ' ', parts[4].replace('\\', '')).strip()
            sezon = parts[7]
            bolum = parts[8]
            label = baslik or f"Bölüm {idx}"
            if sezon.isdigit() and int(sezon) > 0:
                label = f"S{sezon}B{bolum} · {baslik}" if baslik else f"S{sezon}B{bolum}"
            vpayload = base64_encode_safe(json.dumps({
                's': canonical, 'v': vid, 'i': [ic1, ic2, ic3], 't': baslik,
            }, ensure_ascii=False))
            videos.append({
                'id': f"belgeselx:e:{vpayload}",
                'title': label,
                'season': 1,
                'episode': idx,
            })

        meta = {
            'id': 'belgeselx:' + base64_encode_safe(canonical),
            'type': 'series',
            'name': title,
            'poster': _fix_url(poster),
            'background': _fix_url(poster),
            'description': description,
            'genres': genres or None,
            'videos': videos or None,
        }
        return meta

    def _parse_streams(self, body, metadata):
        slot = metadata.get('slot', 1)
        streams = []
        seen = set()

        def add(url, quality=None, host=None, external=False):
            if not url or url in seen:
                return
            seen.add(url)
            is_m3u8 = '.m3u8' in url
            title_bits = [f"Kaynak {slot}"]
            if quality:
                title_bits.append(quality)
            if host:
                title_bits.append(host)
            s = {
                'name': 'BelgeselX',
                'title': ' • '.join(title_bits),
                'behaviorHints': {
                    'notWebReady': True,
                    'bingeGroup': f'belgeselx-{slot}',
                },
            }
            if external:
                s['externalUrl'] = url
                s['url'] = url
            else:
                s['url'] = url
                s['type'] = 'm3u8' if is_m3u8 else 'mp4'
                if 'belgeselx.com' in url:
                    s['behaviorHints']['proxyHeaders'] = {
                        'request': {
                            'Referer': BASE_URL + '/',
                            'Origin': BASE_URL,
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        }
                    }
            streams.append(s)

        # 1) jwplayer sources: [{file:"...", label:"720p", ...}, ...]
        for fm in re.finditer(r'\{\s*file\s*:\s*"([^"]*)"\s*(?:,\s*label\s*:\s*"([^"]*)")?', body):
            furl = fm.group(1).replace('\\/', '/').strip()
            if furl.startswith('http'):
                add(furl, quality=fm.group(2) or None)

        # 2) iframe embeds (alt kaynaklar: dailymotion, ok.ru, yandex, vk ...)
        for im in re.finditer(r'<iframe[^>]+src="([^"]+)"', body):
            iu = im.group(1).replace('\\/', '/').strip()
            if iu.startswith('//'):
                iu = 'https:' + iu
            if not iu.startswith('http'):
                continue
            if '.m3u8' in iu or '.mp4' in iu:
                add(iu)
                continue
            host = urllib.parse.urlparse(iu).netloc.replace('www.', '')
            if any(k in host for k in ('dailymotion', 'odnoklassniki', 'ok.ru', 'yandex', 'yadi.sk',
                                       'vk.com', 'vkvideo', 'youtube', 'sibnet', 'mail.ru')):
                add(iu, host=host, external=True)

        # 3) generic düz linkler
        for gm in re.finditer(r'https?://[^\s"\'<>()]+\.(?:m3u8|mp4)[^\s"\'<>()]*', body):
            add(gm.group(0).replace('\\/', '/'))

        return streams
