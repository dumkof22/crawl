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
        self.BASE_URL = 'https://dizipal1578.com'
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
        randomId = str(int(time.time() * 1000000))[-8:]

        if catalogId in ['dizipal_search', 'dizipal_search_series'] and searchQuery:
            return {
                'instructions': [{
                    'requestId': f"dizipal-search-{catalogId}-{int(time.time()*1000)}-{randomId}",
                    'purpose': 'catalog-search-ajax',
                    'url': f"{self.BASE_URL}/bg/searchcontent",
                    'method': 'POST',
                    'body': f"searchterm={urllib.parse.quote(searchQuery)}",
                    'headers': {'Content-Type': 'application/x-www-form-urlencoded'},
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
        randomId = str(int(time.time() * 1000000))[-8:]
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
        randomId = str(int(time.time() * 1000000))[-8:]
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
            m_type = 'series' if '/dizi/' in fullUrl or '/series/' in fullUrl else 'movie'

            return {'id': meta_id, 'type': m_type, 'name': title, 'poster': posterUrl}
        except: return None

    async def processFetchResult(self, fetchResult):
        import random
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
                with open('/home/hakan/Belgeler/crawl/debug_dizipal_search.html', 'w', encoding='utf-8') as f:
                    f.write(body)
                soup = BeautifulSoup(body, 'html.parser')
                metas = []
                catalogId = metadata.get('catalogId')
                
                for a_tag in soup.find_all('a'):
                    href = a_tag.get('href')
                    if not href: continue
                    
                    title = a_tag.text.strip()
                    if not title:
                        title_el = a_tag.find(['span', 'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', '.title'])
                        if title_el: title = title_el.text.strip()
                        
                    if not title: continue
                        
                    img = a_tag.find('img')
                    posterUrl = (img.get('src') or img.get('data-src')) if img else None
                    
                    fullUrl = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                    m_type = 'series' if '/dizi/' in fullUrl or '/series/' in fullUrl else 'movie'
                    
                    if catalogId == 'dizipal_search' and m_type != 'movie': continue
                    if catalogId == 'dizipal_search_series' and m_type != 'series': continue
                    
                    meta_id = 'dizipal:' + base64_encode_safe(fullUrl)
                    if not any(m['id'] == meta_id for m in metas):
                        metas.append({'id': meta_id, 'type': m_type, 'name': title, 'poster': posterUrl})
                
                print(f"📋 [DiziPal] Search metas found: {len(metas)}")
                return {'metas': metas}
            except Exception as e:
                print(f"❌ Search parsing error: {e}")
                return {'metas': []}

        if purpose == 'catalog-search-ajax':
            try:
                import re, json
                json_match = re.search(r'({.*})', body, re.DOTALL)
                if not json_match:
                    return {'metas': []}
                
                resp = json.loads(json_match.group(1))
                if 'data' in resp and isinstance(resp['data'], dict):
                    inner_data = resp['data']
                else:
                    inner_data = resp
                    
                results = inner_data.get('result', [])
                metas = []
                catalogId = metadata.get('catalogId')
                
                for item in results:
                    slug = item.get('used_slug')
                    if not slug: continue
                    title = item.get('object_name') or item.get('object_detail_name')
                    poster = item.get('object_poster_url')
                    o_type = item.get('used_type', '')
                    
                    m_type = 'movie' if 'movie' in str(o_type).lower() else 'series'
                    if catalogId == 'dizipal_search' and m_type != 'movie': continue
                    if catalogId == 'dizipal_search_series' and m_type != 'series': continue
                    
                    fixedSlug = slug if slug.startswith('/') else f"/{slug}"
                    href = fixedSlug if fixedSlug.startswith('http') else f"{self.BASE_URL}{fixedSlug}"
                    meta_id = 'dizipal:' + base64_encode_safe(href)
                    
                    if not any(m['id'] == meta_id for m in metas):
                        metas.append({
                            'id': meta_id,
                            'type': m_type,
                            'name': title,
                            'poster': poster
                        })
                        
                print(f"📋 [DiziPal] AJAX Search metas found: {len(metas)}")
                return {'metas': metas}
            except Exception as e:
                print(f"❌ AJAX Search parsing error: {e}")
                return {'metas': []}

        if purpose == 'catalog':
            soup = BeautifulSoup(body, 'html.parser')
            metas = []
            catalogId = metadata.get('catalogId')
            print(f"[DEBUG - Dizipal] Catalog parsing for {catalogId} | URL: {url} | Body Length: {len(body)}")
            if soup.title:
                print(f"[DEBUG - Dizipal] Page Title: {soup.title.string}")

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
                            m_type = 'series' if '/dizi/' in fullUrl or '/series/' in fullUrl else 'movie'
                            metas.append({'id': meta_id, 'type': m_type, 'name': title, 'poster': posterUrl})
                            
                if not metas:
                    for elem in soup.select('ul li'):
                        title_el = elem.select_one('span.title') or elem.select_one('.title') or elem.select_one('span')
                        title = title_el.text.strip() if title_el else None
                        a_tag = elem.find('a')
                        href = a_tag.get('href') if a_tag else None
                        img = elem.find('img')
                        posterUrl = (img.get('src') or img.get('data-src')) if img else None

                        if title and href and ('/dizi/' in href or '/series/' in href):
                            fullUrl = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                            meta_id = 'dizipal:' + base64_encode_safe(fullUrl)
                            metas.append({'id': meta_id, 'type': 'series', 'name': title, 'poster': posterUrl})

                if not metas:
                    for a_tag in soup.select('a[href*="/series/"], a[href*="/dizi/"], a[href*="/movie/"], a[href*="/film/"]'):
                        title = a_tag.get('title')
                        if title and title.endswith(' izle'):
                            title = title[:-5]
                        href = a_tag.get('href')
                        if title and href:
                            img = a_tag.find('img')
                            posterUrl = (img.get('src') or img.get('data-src')) if img else None
                            fullUrl = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                            meta_id = 'dizipal:' + base64_encode_safe(fullUrl)
                            m_type = 'movie' if '/movie/' in href or '/film/' in href else 'series'
                            if not any(m['id'] == meta_id for m in metas):
                                metas.append({'id': meta_id, 'type': m_type, 'name': title, 'poster': posterUrl})

            print(f"[DEBUG - Dizipal] Extracted {len(metas)} items for catalog {catalogId}")
            if len(metas) == 0:
                print(f"[DEBUG - Dizipal] Body snippet: {body[:500]}")
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
            import json
            meta_json = None
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') in ['TVSeries', 'Movie']:
                        meta_json = data
                        break
                except:
                    pass

            if isinstance(meta_json, dict):
                title = meta_json.get('name') if isinstance(meta_json, dict) else ''
                description = meta_json.get('description', '') if isinstance(meta_json, dict) else ''
                poster = meta_json.get('image') if isinstance(meta_json, dict) else None
                year = meta_json.get('datePublished', '')[:4] if isinstance(meta_json, dict) and meta_json.get('datePublished') else ''
                agg = meta_json.get('aggregateRating', {}) if isinstance(meta_json, dict) else {}
                imdbRating = str(agg.get('ratingValue', '')) if isinstance(agg, dict) else str(agg)
                
                videos = []
                if 'containsSeason' in meta_json and isinstance(meta_json['containsSeason'], list):
                    for season in meta_json['containsSeason']:
                        if not isinstance(season, dict): continue
                        s_num = season.get('seasonNumber')
                        episodes = season.get('episode', [])
                        if not isinstance(episodes, list): continue
                        for ep in episodes:
                            if not isinstance(ep, dict): continue
                            ep_num = ep.get('episodeNumber')
                            ep_url = ep.get('url')
                            ep_name = ep.get('name')
                            if ep_url:
                                videoId = 'dizipal:' + base64_encode_safe(ep_url)
                                videos.append({
                                    'id': videoId,
                                    'title': ep_name or f"{s_num}. Sezon {ep_num}. Bölüm",
                                    'season': s_num,
                                    'episode': ep_num
                                })
                
                meta = {
                    'id': 'dizipal:' + base64_encode_safe(url),
                    'type': 'series' if 'containsSeason' in meta_json else 'movie',
                    'name': title,
                    'poster': poster,
                    'background': poster,
                    'description': description,
                    'releaseInfo': year,
                    'imdbRating': imdbRating,
                    'videos': videos if videos else None
                }
                return {'meta': meta}
            else:
                title_el = soup.select_one('div.cover h5') or soup.select_one('meta[property="og:title"]')
                title = ''
                if title_el:
                    if title_el.name == 'meta' and hasattr(title_el, 'get'):
                        title = title_el.get('content', '').replace(' izle', '')
                    else:
                        title = title_el.text.strip()
                else:
                    title = 'Dizi'
                    
                poster_el = soup.select_one('div.cover img') or soup.select_one('meta[property="og:image"]')
                poster = None
                if poster_el and hasattr(poster_el, 'get'):
                    poster = poster_el.get('content') if poster_el.name == 'meta' else poster_el.get('src')
                
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

                m_type = 'series' if '/dizi/' in url or '/series/' in url else 'movie'
                videos = []
                if m_type == 'series':
                    import re
                    for a_tag in soup.select('a[href*="/bolum/"]'):
                        epHref = a_tag.get('href')
                        if epHref:
                            m = re.search(r'-(\d+)x(\d+)', epHref)
                            if m:
                                season = int(m.group(1))
                                episode = int(m.group(2))
                                fullUrl = epHref if epHref.startswith('http') else f"{self.BASE_URL}{epHref}"
                                videoId = 'dizipal:' + base64_encode_safe(fullUrl)
                                if not any(v['id'] == videoId for v in videos):
                                    videos.append({
                                        'id': videoId,
                                        'title': f"{season}. Sezon {episode}. Bölüm",
                                        'season': season,
                                        'episode': episode
                                    })
                
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
                
        if purpose == 'source2-stream':
            print(f"\n[DEBUG - Dizipal] purpose=source2-stream. URL: {url}")
            streamName = metadata.get('streamName', 'DiziPal')
            import json
            try:
                data = json.loads(body)
                if data and 'playlist' in data:
                    streams = []
                    for p in data['playlist']:
                        if 'sources' in p:
                            for s in p['sources']:
                                if 'file' in s:
                                    stream_url = s['file'].replace('m.php', 'master.m3u8').replace('\\/', '/')
                                    streams.append({
                                        'name': streamName,
                                        'title': s.get('title', streamName),
                                        'url': stream_url,
                                        'type': 'm3u8' if '.m3u8' in stream_url else 'mp4',
                                        'behaviorHints': {'notWebReady': False}
                                    })
                    if streams:
                        print(f"[DEBUG - Dizipal] Successfully parsed source2 playlist: {len(streams)} streams found")
                        return {'streams': streams}
                print(f"[DEBUG - Dizipal] No playlist found in source2 response: {body[:100]}")
            except Exception as e:
                print(f"[DEBUG - Dizipal] Failed to parse source2 response: {e}")
            return {'streams': []}

        if purpose == 'stream':
            print(f"\n[DEBUG - Dizipal] purpose=stream. URL: {url}")
            soup = BeautifulSoup(body, 'html.parser')
            iframeSources = []
            
            for selector, attr in [
                ('#vast_new iframe', 'src'), ('#vast_new iframe', 'data-src'),
                ('.pre-player iframe', 'src'), (('.pre-player iframe', 'data-src')),
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

            iframeSources = list(dict.fromkeys([s for s in iframeSources if s and s.strip() != ''])) # unique and non-empty
            print(f"[DEBUG - Dizipal] Found iframeSources from DOM: {iframeSources}")

            if not iframeSources:
                print(f"[DEBUG - Dizipal] No iframes found in DOM. Using original URL as iframe source.")
                iframeSources.append(url)

            if iframeSources:
                instructions = []
                for i in range(min(len(iframeSources), 5)):
                    iframeSrc = iframeSources[i]
                    iframeUrl = iframeSrc if iframeSrc.startswith('http') else f"https:{iframeSrc}"
                    randomId = str(int(time.time() * 1000000))[-8:]
                    
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
                randomId = str(int(time.time() * 1000000))[-8:]
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
            print(f"\n[DEBUG - Dizipal] purpose={purpose}. URL: {url}")
            streamName = metadata.get('streamName', 'DiziPal')
            
            # If Flutter intercepted the m3u8 directly and sent it in the URL or metadata
            intercepted_url = url
            if 'resolvedUrl' in metadata: intercepted_url = metadata['resolvedUrl']
            elif 'targetUrl' in metadata: intercepted_url = metadata['targetUrl']
            
            print(f"[DEBUG - Dizipal] intercepted_url evaluated as: {intercepted_url}")
            if intercepted_url and ('.m3u8' in intercepted_url.lower() or '.mp4' in intercepted_url.lower()):
                print(f"[DEBUG - Dizipal] intercepted_url is a video! Returning stream.")
                stream_type = 'mp4' if '.mp4' in intercepted_url.lower() else 'm3u8'
                return {'streams': [{
                    'name': streamName, 'title': streamName, 'url': intercepted_url, 'type': stream_type,
                    'behaviorHints': {'notWebReady': False}
                }]}

            print(f"[DEBUG - Dizipal] intercepted_url is not video. Searching body for m3u8 or openPlayer...")
            import re
            
            openPlayerMatch = re.search(r'window\.openPlayer\s*\(\s*[\'"]([^\'"]+)[\'"]', body)
            if openPlayerMatch:
                print(f"[DEBUG - Dizipal] Found openPlayer match! Delegating to source2.php")
                with open('/home/hakan/Belgeler/crawl/iframe_dump.html', 'w', encoding='utf-8') as f:
                    f.write(body)
                encrypted_base64 = openPlayerMatch.group(1).replace('\n', '').replace('\r', '')
                
                from urllib.parse import urlparse, quote
                import json
                
                # Altyazıları HTML body içinden çıkar
                subtitles_list = []
                subMatch = re.search(r'(\[\{.*?"label".*?\}\])\s*\)', body)
                if subMatch:
                    try:
                        subs = json.loads(subMatch.group(1))
                        for sub in subs:
                            file_url = sub.get('file')
                            if file_url:
                                file_url = file_url.replace('\\/', '/')
                                label = sub.get('label', 'Türkçe')
                                subtitles_list.append({
                                    'id': label.lower().replace(' ', '_'),
                                    'url': file_url,
                                    'lang': label
                                })
                        print(f"[DEBUG - Dizipal] Extracted {len(subtitles_list)} subtitles")
                    except Exception as e:
                        print(f"[DEBUG - Dizipal] Subtitle parse error: {e}")
                
                parsed_url = urlparse(url)
                source2_url = f"{parsed_url.scheme}://{parsed_url.netloc}/source2.php?v={quote(encrypted_base64, safe='')}"
                
                headers = self.get_enhanced_headers(url, True)
                headers['Origin'] = f"{parsed_url.scheme}://{parsed_url.netloc}"
                
                return {
                    'instructions': [{
                        'requestId': f"dizipal-source2-{int(time.time()*1000)}-{randomId if 'randomId' in locals() else 'x'}",
                        'purpose': 'source2-resolve',
                        'url': source2_url,
                        'method': 'GET',
                        'headers': headers,
                        'metadata': {
                            'streamName': streamName, 
                            'subtitles': subtitles_list,
                            'originalUrl': url,
                            'hiddenweb': True
                        }
                    }]
                }

            m3uMatch = re.search(r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"', body)
            if not m3uMatch: m3uMatch = re.search(r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'sources:\s*\[\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'(https?://[^\s"\'<>()]+\.m3u8[^\s"\'<>()]*)', body)
            
            if m3uMatch:
                print(f"[DEBUG - Dizipal] Found m3u8 in body: {m3uMatch.group(1)}")
                return {'streams': [{
                    'name': streamName, 'title': streamName, 'url': m3uMatch.group(1), 'type': 'm3u8',
                    'behaviorHints': {'notWebReady': False, 'proxyHeaders': {'request': {'Referer': url}}}
                }]}
            
            print(f"[DEBUG - Dizipal] No m3u8 found in body!")
            return {'streams': []}

        if purpose == 'source2-resolve':
            body_text = fetchResult.get('body', '')
            metadata = fetchResult.get('metadata', {})
            streamName = metadata.get('streamName', 'DiziPal')
            subtitles_list = metadata.get('subtitles', [])
            url = metadata.get('originalUrl', '')
            
            try:
                import json
                import urllib.parse
                parsed_url = urllib.parse.urlparse(url) if url else None
                
                clean_body = body_text
                if clean_body.strip().startswith('<'):
                    import re
                    # Extract from <pre> if WebView wrapped it
                    pre_match = re.search(r'<pre[^>]*>(.*?)</pre>', clean_body, re.DOTALL | re.IGNORECASE)
                    if pre_match:
                        clean_body = pre_match.group(1)
                    else:
                        # Fallback to extract between first { and last }
                        json_match = re.search(r'(\{.*\})', clean_body, re.DOTALL)
                        if json_match:
                            clean_body = json_match.group(1)
                            
                data = json.loads(clean_body)
                if data and 'playlist' in data:
                    streams = []
                    for p in data['playlist']:
                        if 'sources' in p:
                            for s in p['sources']:
                                if 'file' in s:
                                    stream_url = s['file'].replace('m.php', 'master.m3u8').replace('\\/', '/')
                                    stream_obj = {
                                        'name': streamName,
                                        'title': s.get('title', streamName),
                                        'url': stream_url,
                                        'type': 'm3u8' if '.m3u8' in stream_url else 'mp4',
                                        'behaviorHints': {
                                            'notWebReady': False,
                                            'proxyHeaders': {
                                                'request': {
                                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
                                                    'Referer': url,
                                                    'Origin': f"{parsed_url.scheme}://{parsed_url.netloc}" if parsed_url else ""
                                                }
                                            }
                                        }
                                    }
                                    if subtitles_list:
                                        stream_obj['subtitles'] = subtitles_list
                                    streams.append(stream_obj)
                    if streams:
                        print(f"[DEBUG - Dizipal] Successfully parsed source2 playlist via instruction: {len(streams)} streams found")
                        return {'streams': streams}
                print(f"[DEBUG - Dizipal] No playlist found in instruction fetch: {body_text[:100]}")
            except Exception as e:
                print(f"[DEBUG - Dizipal] Instruction fetch parse failed: {e}. Body len: {len(body_text)} Snippet: {repr(body_text[:200])}")
                
            import re
            m3uMatch = re.search(r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body_text)
            if not m3uMatch: m3uMatch = re.search(r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"', body_text)
            if not m3uMatch: m3uMatch = re.search(r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body_text)
            if not m3uMatch: m3uMatch = re.search(r'sources:\s*\[\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body_text)
            if not m3uMatch: m3uMatch = re.search(r'(https?://[^\s"\'<>()]+\.m3u8[^\s"\'<>()]*)', body_text)
            
            if m3uMatch:
                stream_url = m3uMatch.group(1).replace('\\/', '/')
                stream_obj = {
                    'name': streamName,
                    'title': streamName,
                    'url': stream_url,
                    'type': 'm3u8',
                    'behaviorHints': {
                        'notWebReady': False,
                        'proxyHeaders': {
                            'request': {
                                'Referer': url,
                                'Origin': f"{parsed_url.scheme}://{parsed_url.netloc}" if parsed_url else ""
                            }
                        }
                    }
                }
                if subtitles_list:
                    stream_obj['subtitles'] = subtitles_list
                print(f"[DEBUG - Dizipal] Found m3u8 via regex in source2-resolve: {stream_url}")
                return {'streams': [stream_obj]}
            
            return {'streams': []}

        return {'ok': True}
