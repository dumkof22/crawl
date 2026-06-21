import base64
import json
import urllib.parse
import random
import time
from bs4 import BeautifulSoup

def base64_encode_safe(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8').replace('=', '')

def base64_decode_safe(s):
    s = s.strip()
    s += '=' * (-len(s) % 4)
    try:
        return base64.b64decode(s).decode('utf-8')
    except:
        return ''

class DiziPalScraper:
    def __init__(self):
        self.BASE_URL = 'https://dizipal1551.com'
        self.manifest = {
            'id': 'community.dizipal',
            'version': '2.0.0',
            'name': 'DiziPal',
            'description': 'Türkçe dizi ve film izleme platformu - DiziPal için Stremio eklentisi (Instruction Mode)',
            'logo': 'https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://dizipal953.com&size=128',
            'resources': ['catalog', 'meta', 'stream'],
            'types': ['movie', 'series'],
            'catalogs': [
                {'type': 'series', 'id': 'dizipal_latest_episodes', 'name': 'Son Bölümler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizipal_series', 'name': 'Yeni Diziler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'dizipal_movies', 'name': 'Yeni Filmler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizipal_netflix', 'name': 'Netflix Dizileri', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizipal_exxen', 'name': 'Exxen Dizileri', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizipal_blutv', 'name': 'BluTV Dizileri', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizipal_disney', 'name': 'Disney+ Dizileri', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizipal_prime', 'name': 'Amazon Prime Dizileri', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizipal_anime', 'name': 'Anime', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizipal_scifi_series', 'name': 'Bilimkurgu Dizileri', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'dizipal_scifi_movies', 'name': 'Bilimkurgu Filmleri', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizipal_comedy_series', 'name': 'Komedi Dizileri', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'dizipal_comedy_movies', 'name': 'Komedi Filmleri', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'dizipal_search', 'name': 'Film Ara', 'extra': [{'name': 'search', 'isRequired': True}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizipal_search_series', 'name': 'Dizi Ara', 'extra': [{'name': 'search', 'isRequired': True}, {'name': 'skip', 'isRequired': False}]}
            ],
            'idPrefixes': ['dizipal']
        }
        self.CATALOG_URLS = {
            'dizipal_latest_episodes': f"{self.BASE_URL}/diziler/son-bolumler",
            'dizipal_series': f"{self.BASE_URL}/diziler",
            'dizipal_movies': f"{self.BASE_URL}/filmler",
            'dizipal_netflix': f"{self.BASE_URL}/koleksiyon/netflix",
            'dizipal_exxen': f"{self.BASE_URL}/koleksiyon/exxen",
            'dizipal_blutv': f"{self.BASE_URL}/koleksiyon/blutv",
            'dizipal_disney': f"{self.BASE_URL}/koleksiyon/disney",
            'dizipal_prime': f"{self.BASE_URL}/koleksiyon/amazon-prime",
            'dizipal_anime': f"{self.BASE_URL}/diziler?kelime=&durum=&tur=26&type=&siralama=",
            'dizipal_scifi_series': f"{self.BASE_URL}/diziler?kelime=&durum=&tur=5&type=&siralama=",
            'dizipal_scifi_movies': f"{self.BASE_URL}/tur/bilimkurgu",
            'dizipal_comedy_series': f"{self.BASE_URL}/diziler?kelime=&durum=&tur=11&type=&siralama=",
            'dizipal_comedy_movies': f"{self.BASE_URL}/tur/komedi"
        }

    def get_enhanced_headers(self, referer=None, is_ajax=False, include_cookie_hint=True):
        if not referer: referer = self.BASE_URL
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01' if is_ajax else 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Sec-Ch-Ua': '"Chromium";v="134", "Not)A;Brand";v="24", "Google Chrome";v="134"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty' if is_ajax else 'document',
            'Sec-Fetch-Mode': 'cors' if is_ajax else 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Priority': 'u=0, i'
        }
        if referer: headers['Referer'] = referer
        if is_ajax:
            headers['X-Requested-With'] = 'XMLHttpRequest'
            headers['Origin'] = self.BASE_URL
        if include_cookie_hint:
            headers['__COOKIE_HINT__'] = 'FLUTTER_INJECT_WEBVIEW_COOKIES'
        return headers

    def getManifest(self):
        return self.manifest

    async def handleCatalog(self, args):
        catalogId = args.get('id')
        extra = args.get('extra', {})
        searchQuery = extra.get('search')
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))

        if catalogId in ['dizipal_search', 'dizipal_search_series'] and searchQuery:
            headers = self.get_enhanced_headers(self.BASE_URL, True)
            headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
            return {
                'instructions': [{
                    'requestId': f"dizipal-search-{catalogId}-{int(time.time()*1000)}-{randomId}",
                    'purpose': 'catalog-search',
                    'url': f"{self.BASE_URL}/api/search-autocomplete",
                    'method': 'POST',
                    'headers': headers,
                    'body': f"query={urllib.parse.quote(searchQuery)}",
                    'metadata': {'catalogId': catalogId, 'hiddenweb': True}
                }]
            }

        url = self.CATALOG_URLS.get(catalogId)
        if not url: return {'instructions': []}

        return {
            'instructions': [{
                'requestId': f"dizipal-catalog-{catalogId}-{int(time.time()*1000)}-{randomId}",
                'purpose': 'catalog',
                'url': url,
                'method': 'GET',
                'headers': self.get_enhanced_headers(self.BASE_URL, False),
                'metadata': {'catalogId': catalogId, 'hiddenweb': True}
            }]
        }

    async def handleMeta(self, args):
        urlBase64 = args.get('id', '').replace('dizipal:', '')
        url = base64_decode_safe(urlBase64)
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        return {
            'instructions': [{
                'requestId': f"dizipal-meta-{int(time.time()*1000)}-{randomId}",
                'purpose': 'meta',
                'url': url,
                'method': 'GET',
                'headers': self.get_enhanced_headers(self.BASE_URL, False),
                'metadata': {'hiddenweb': True}
            }]
        }

    async def handleStream(self, args):
        urlBase64 = args.get('id', '').replace('dizipal:', '')
        url = base64_decode_safe(urlBase64)
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        return {
            'instructions': [{
                'requestId': f"dizipal-stream-{int(time.time()*1000)}-{randomId}",
                'purpose': 'stream',
                'url': url,
                'method': 'GET',
                'headers': self.get_enhanced_headers(self.BASE_URL, False),
                'metadata': {'hiddenweb': True}
            }]
        }

    def parse_son_bolumler(self, soup, elem):
        try:
            name_div = elem.select_one('div.name')
            if not name_div: return None
            name = name_div.text.strip()
            if not name: return None

            ep_div = elem.select_one('div.episode')
            episode = ep_div.text.strip().replace('. Sezon ', 'x').replace('. Bölüm', '') if ep_div else ''
            
            title = f"{name} {episode}".strip()
            a_tag = elem.find('a')
            if not a_tag or not a_tag.get('href'): return None
            href = a_tag['href']

            fullUrl = href if href.startswith('http') else f"{self.BASE_URL}{href}"
            img = elem.find('img')
            posterUrl = img.get('src') if img else None

            seriesUrl = fullUrl.split('/sezon')[0]
            meta_id = 'dizipal:' + base64_encode_safe(seriesUrl)

            return {'id': meta_id, 'type': 'series', 'name': title, 'poster': posterUrl}
        except: return None

    def parse_diziler(self, soup, elem):
        try:
            title_span = elem.select_one('span.title')
            if not title_span: return None
            title = title_span.text.strip()
            if not title: return None

            a_tag = elem.find('a')
            if not a_tag or not a_tag.get('href'): return None
            href = a_tag['href']

            fullUrl = href if href.startswith('http') else f"{self.BASE_URL}{href}"
            img = elem.find('img')
            posterUrl = img.get('src') if img else None

            meta_id = 'dizipal:' + base64_encode_safe(fullUrl)
            m_type = 'series' if '/dizi/' in fullUrl else 'movie'

            return {'id': meta_id, 'type': m_type, 'name': title, 'poster': posterUrl}
        except: return None

    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body', '')
        url = fetchResult.get('url', '')
        metadata = fetchResult.get('metadata', {})

        if isinstance(body, str):
            if any(x in body for x in ['Just a moment', 'cf-browser-verification', 'Checking your browser', 'DDoS protection by Cloudflare', 'cf_clearance']) \
               or any(x in body for x in ['Access denied', '403 Forbidden', 'Bot detected', 'Please enable JavaScript']) or len(body) < 500:
                if purpose in ['catalog', 'catalog-search']: return {'metas': []}
                if purpose == 'meta': return {'meta': None}
                if purpose in ['stream', 'iframe-stream', 'series-player-stream']: return {'streams': []}

        if purpose == 'catalog-search':
            try:
                searchResults = json.loads(body)
                metas = []
                catalogId = metadata.get('catalogId')
                
                if isinstance(searchResults, dict):
                    for key, item in searchResults.items():
                        if isinstance(item, dict) and item.get('title') and item.get('url'):
                            fullUrl = f"{self.BASE_URL}{item['url']}"
                            m_type = 'series' if item.get('type') == 'series' else 'movie'
                            
                            if catalogId == 'dizipal_search' and m_type != 'movie': continue
                            if catalogId == 'dizipal_search_series' and m_type != 'series': continue
                            
                            meta_id = 'dizipal:' + base64_encode_safe(fullUrl)
                            metas.append({'id': meta_id, 'type': m_type, 'name': item['title'], 'poster': item.get('poster')})
                return {'metas': metas}
            except Exception as e:
                print(f"❌ Search parsing error: {e}")
                return {'metas': []}

        if purpose == 'catalog':
            soup = BeautifulSoup(body, 'html.parser')
            metas = []
            catalogId = metadata.get('catalogId')

            if catalogId == 'dizipal_latest_episodes':
                for elem in soup.select('div.episode-item'):
                    meta = self.parse_son_bolumler(soup, elem)
                    if meta: metas.append(meta)
            else:
                for elem in soup.select('article.type2 ul li'):
                    meta = self.parse_diziler(soup, elem)
                    if meta: metas.append(meta)

                if not metas:
                    for elem in soup.select('li.film'):
                        title_el = elem.select_one('span.film-title') or elem.select_one('span.title') or elem.select_one('.title')
                        title = title_el.text.strip() if title_el else None
                        a_tag = elem.find('a')
                        href = a_tag.get('href') if a_tag else None
                        img = elem.find('img')
                        posterUrl = (img.get('src') or img.get('data-src')) if img else None
                        
                        if title and href:
                            fullUrl = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                            meta_id = 'dizipal:' + base64_encode_safe(fullUrl)
                            m_type = 'series' if '/dizi/' in fullUrl else 'movie'
                            metas.append({'id': meta_id, 'type': m_type, 'name': title, 'poster': posterUrl})
                            
                if not metas:
                    for elem in soup.select('ul li'):
                        title_el = elem.select_one('span.title') or elem.select_one('.title') or elem.select_one('span')
                        title = title_el.text.strip() if title_el else None
                        a_tag = elem.find('a')
                        href = a_tag.get('href') if a_tag else None
                        img = elem.find('img')
                        posterUrl = (img.get('src') or img.get('data-src')) if img else None

                        if title and href and '/dizi/' in href:
                            fullUrl = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                            meta_id = 'dizipal:' + base64_encode_safe(fullUrl)
                            metas.append({'id': meta_id, 'type': 'series', 'name': title, 'poster': posterUrl})

            return {'metas': metas}

        if purpose == 'meta':
            soup = BeautifulSoup(body, 'html.parser')
            poster_el = soup.select_one('[property="og:image"]')
            poster = poster_el.get('content') if poster_el else None
            desc_el = soup.select_one('div.summary p')
            description = desc_el.text.strip() if desc_el else 'Açıklama mevcut değil'

            year = None
            tags = []
            imdbRating = None
            runtime = None
            
            for elem in soup.select('div.col-md-6'):
                divs = elem.find_all('div')
                if len(divs) >= 2:
                    label = divs[0].text.strip()
                    val = divs[-1].text.strip()
                    if label == 'Yapım Yılı': year = val
                    elif label == 'Türler': tags.extend([t.strip() for t in val.split(' ') if t.strip()])
                    elif label == 'IMDB Puanı': imdbRating = val
                    elif label == 'Ortalama Süre':
                        import re
                        match = re.search(r'(\d+)', val)
                        if match: runtime = f"{match.group(1)} dk"

            if '/dizi/' in url:
                title_el = soup.select_one('div.cover h5')
                title = title_el.text.strip() if title_el else 'Dizi'
                
                videos = []
                for elem in soup.select('div.episode-item'):
                    epName_el = elem.select_one('div.name')
                    epName = epName_el.text.strip() if epName_el else ''
                    a_tag = elem.find('a')
                    epHref = a_tag.get('href') if a_tag else None
                    epText_el = elem.select_one('div.episode')
                    epText = epText_el.text.strip() if epText_el else ''
                    
                    if epHref and epText:
                        parts = epText.split(' ')
                        season = int(parts[0].replace('.', '')) if len(parts) > 0 and parts[0] else None
                        episode = int(parts[2].replace('.', '')) if len(parts) > 2 and parts[2] else None
                        
                        fullUrl = epHref if epHref.startswith('http') else f"{self.BASE_URL}{epHref}"
                        videoId = 'dizipal:' + base64_encode_safe(fullUrl)
                        videos.append({
                            'id': videoId,
                            'title': epName or f"{season}. Sezon {episode}. Bölüm",
                            'season': season,
                            'episode': episode
                        })

                meta = {
                    'id': 'dizipal:' + base64_encode_safe(url),
                    'type': 'series',
                    'name': title,
                    'poster': poster,
                    'background': poster,
                    'description': description,
                    'releaseInfo': year,
                    'imdbRating': imdbRating,
                    'genres': tags if tags else None,
                    'runtime': runtime,
                    'videos': videos
                }
                return {'meta': meta}
            else:
                title_el = soup.select('div.g-title')
                title = ''
                if len(title_el) > 1 and title_el[1].find('div'):
                    title = title_el[1].find('div').text.strip()
                if not title:
                    og_title = soup.select_one('[property="og:title"]')
                    title = og_title.get('content') if og_title else 'Film'
                
                meta = {
                    'id': 'dizipal:' + base64_encode_safe(url),
                    'type': 'movie',
                    'name': title,
                    'poster': poster,
                    'background': poster,
                    'description': description,
                    'releaseInfo': year,
                    'imdbRating': imdbRating,
                    'genres': tags if tags else None,
                    'runtime': runtime
                }
                return {'meta': meta}

        if purpose == 'stream':
            soup = BeautifulSoup(body, 'html.parser')
            iframeSources = []
            
            for selector, attr in [
                ('#vast_new iframe', 'src'), ('#vast_new iframe', 'data-src'),
                ('.pre-player iframe', 'src'), ('.pre-player iframe', 'data-src'),
                ('.series-player-container iframe', 'src'), ('.series-player-container iframe', 'data-src')
            ]:
                el = soup.select_one(selector)
                if el and el.get(attr): iframeSources.append(el.get(attr))
                
            for el in soup.find_all('iframe'):
                src = el.get('src')
                data_src = el.get('data-src')
                if src and 'embed' in src: iframeSources.append(src)
                if data_src and 'embed' in data_src: iframeSources.append(data_src)
                if src: iframeSources.append(src)
                if data_src: iframeSources.append(data_src)

            iframeSources = list(dict.fromkeys([s for s in iframeSources if s])) # unique and non-empty

            if iframeSources:
                instructions = []
                for i in range(min(len(iframeSources), 5)):
                    iframeSrc = iframeSources[i]
                    iframeUrl = iframeSrc if iframeSrc.startswith('http') else f"https:{iframeSrc}"
                    randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                    
                    iframeHeaders = self.get_enhanced_headers(url, False)
                    iframeHeaders['Sec-Fetch-Dest'] = 'iframe'
                    iframeHeaders['Sec-Fetch-Site'] = 'cross-site'
                    
                    instructions.append({
                        'requestId': f"dizipal-iframe-extract-{int(time.time()*1000)}-{randomId}",
                        'purpose': 'iframe-stream',
                        'url': iframeUrl,
                        'method': 'GET',
                        'headers': iframeHeaders,
                        'metadata': {'streamName': f"DiziPal Server {i + 1}", 'hiddenweb': True}
                    })
                return {'instructions': instructions}

            import re
            seriesPlayerMatch = re.search(r'file:\s*["\']?(/series-player/[^"\'\s,]+)["\']?', body)
            if not seriesPlayerMatch:
                for script in soup.find_all('script'):
                    content = script.string or ''
                    if 'series-player' in content:
                        m = re.search(r'["\'](/series-player/[^"\']+)["\']', content)
                        if m:
                            seriesPlayerMatch = m
                            break
                            
            if not seriesPlayerMatch:
                for elem in soup.select('[onclick*="series-player"], [data-url*="series-player"]'):
                    val = (elem.get('onclick') or '') + (elem.get('data-url') or '')
                    m = re.search(r'/series-player/[^\s"\']+', val)
                    if m:
                        seriesPlayerMatch = m
                        break

            if seriesPlayerMatch:
                seriesPlayerUrl = f"{self.BASE_URL}{seriesPlayerMatch.group(1) if len(seriesPlayerMatch.groups())>0 else seriesPlayerMatch.group(0)}"
                randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                seriesPlayerHeaders = self.get_enhanced_headers(url, True)
                seriesPlayerHeaders['Accept'] = '*/*'
                return {
                    'instructions': [{
                        'requestId': f"dizipal-series-player-{int(time.time()*1000)}-{randomId}",
                        'purpose': 'series-player-stream',
                        'url': seriesPlayerUrl,
                        'method': 'GET',
                        'headers': seriesPlayerHeaders,
                        'metadata': {'originalUrl': url, 'streamName': 'DiziPal Series Player', 'hiddenweb': True}
                    }]
                }

            # Direct m3u8
            m3uMatch = re.search(r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"', body)
            if not m3uMatch: m3uMatch = re.search(r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'sources:\s*\[\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'(https?://[^\s"\'<>()]+\.m3u8[^\s"\'<>()]*)', body)
            
            if m3uMatch:
                return {'streams': [{
                    'name': 'DiziPal', 'title': 'DiziPal', 'url': m3uMatch.group(1), 'type': 'm3u8',
                    'behaviorHints': {'notWebReady': False}
                }]}
            
            return {'streams': []}

        if purpose in ['iframe-stream', 'series-player-stream']:
            streamName = metadata.get('streamName', 'DiziPal')
            import re
            
            m3uMatch = re.search(r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"', body)
            if not m3uMatch: m3uMatch = re.search(r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'sources:\s*\[\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'(https?://[^\s"\'<>()]+\.m3u8[^\s"\'<>()]*)', body)
            
            if m3uMatch:
                return {'streams': [{
                    'name': streamName, 'title': streamName, 'url': m3uMatch.group(1), 'type': 'm3u8',
                    'behaviorHints': {'notWebReady': False, 'proxyHeaders': {'request': {'Referer': url}}}
                }]}
                
            return {'streams': []}

        return {'ok': True}
