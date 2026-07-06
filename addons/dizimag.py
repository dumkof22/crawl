import base64
import json
import urllib.parse
import time
import re
from bs4 import BeautifulSoup

def base64_encode_safe(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8').replace('=', '')

def fix_url(url):
    if not url: return None
    BASE_URL = 'https://dizimag.eu'
    if url.startswith('//'): return 'https:' + url
    if not url.startswith('http'): return BASE_URL + ('' if url.startswith('/') else '/') + url
    return url

class DiziMagScraper:
    def __init__(self):
        self.BASE_URL = 'https://dizimag.eu'
        self.manifest = {
            'id': 'community.dizimag',
            'version': '2.0.0',
            'name': 'DiziMag',
            'description': 'Türkçe dizi ve film izleme platformu - DiziMag için Stremio eklentisi',
            'resources': ['catalog', 'meta', 'stream'],
            'types': ['movie', 'series'],
            'catalogs': [
                {'type': 'series', 'id': 'dizimag_new_episodes', 'name': 'Yeni Eklenenler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizimag_search', 'name': 'Arama', 'extra': [{'name': 'search', 'isRequired': True}]},
                {'type': 'movie', 'id': 'dizimag_search', 'name': 'Arama', 'extra': [{'name': 'search', 'isRequired': True}]},
                {'type': 'series', 'id': 'dizimag_dizi_aile', 'name': 'Aile', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizimag_dizi_aksiyon', 'name': 'Aksiyon-Macera', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizimag_dizi_animasyon', 'name': 'Animasyon', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizimag_dizi_belgesel', 'name': 'Belgesel', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizimag_dizi_bilimkurgu', 'name': 'Bilim Kurgu', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizimag_dizi_dram', 'name': 'Dram', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizimag_dizi_gizem', 'name': 'Gizem', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizimag_dizi_komedi', 'name': 'Komedi', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizimag_dizi_savas', 'name': 'Savaş Politik', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizimag_dizi_suc', 'name': 'Suç', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'dizimag_film_yeni', 'name': 'Yeni Filmler', 'extra': [{'name': 'skip', 'isRequired': False}]}
            ],
            'idPrefixes': ['dizimag']
        }

    def get_headers(self, referer=None):
        if not referer: referer = self.BASE_URL
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0',
            'Referer': referer
        }

    def getManifest(self):
        return self.manifest

    async def handleCatalog(self, args):
        catalogId = args.get('id')
        extra = args.get('extra', {})
        skip = int(extra.get('skip', 0))
        page = (skip // 20) + 1  # 20 items per page usually
        searchQuery = extra.get('search')
        
        if catalogId == 'dizimag_search' and searchQuery:
            # /?s=query
            url = f"{self.BASE_URL}/page/{page}?s={urllib.parse.quote(searchQuery)}" if page > 1 else f"{self.BASE_URL}/?s={urllib.parse.quote(searchQuery)}"
            return {
                'instructions': [{
                    'requestId': f"dizimag-search-{int(time.time()*1000)}",
                    'purpose': 'catalog',
                    'url': url,
                    'method': 'GET',
                    'headers': self.get_headers(),
                    'metadata': {'hiddenweb': True}
                }]
            }

        if catalogId == 'dizimag_new_episodes':
            url = f"{self.BASE_URL}/dizi/page/{page}" if page > 1 else f"{self.BASE_URL}/dizi"
            return {
                'instructions': [{
                    'requestId': f"dizimag-new-{int(time.time()*1000)}",
                    'purpose': 'catalog',
                    'url': url,
                    'method': 'GET',
                    'headers': self.get_headers(),
                    'metadata': {'hiddenweb': True}
                }]
            }
            
        if catalogId == 'dizimag_film_yeni':
            url = f"{self.BASE_URL}/film/page/{page}" if page > 1 else f"{self.BASE_URL}/film"
            return {
                'instructions': [{
                    'requestId': f"dizimag-film-{int(time.time()*1000)}",
                    'purpose': 'catalog',
                    'url': url,
                    'method': 'GET',
                    'headers': self.get_headers(),
                    'metadata': {'hiddenweb': True}
                }]
            }

        genre_map = {
            'dizimag_dizi_aile': 'aile',
            'dizimag_dizi_aksiyon': 'aksiyon-macera',
            'dizimag_dizi_animasyon': 'animasyon',
            'dizimag_dizi_belgesel': 'belgesel',
            'dizimag_dizi_bilimkurgu': 'bilim-kurgu-fantazi',
            'dizimag_dizi_dram': 'dram',
            'dizimag_dizi_gizem': 'gizem',
            'dizimag_dizi_komedi': 'comedy',
            'dizimag_dizi_savas': 'savas',
            'dizimag_dizi_suc': 'suc',
        }

        if catalogId in genre_map:
            genre_slug = genre_map[catalogId]
            base_genre_url = f"{self.BASE_URL}/kategori/{genre_slug}"
            url = f"{base_genre_url}/page/{page}" if page > 1 else base_genre_url
            return {
                'instructions': [{
                    'requestId': f"dizimag-genre-{int(time.time()*1000)}",
                    'purpose': 'catalog',
                    'url': url,
                    'method': 'GET',
                    'headers': self.get_headers(),
                    'metadata': {'hiddenweb': True}
                }]
            }

        return {'metas': []}

    async def handleMeta(self, args):
        urlBase64 = args.get('id', '').replace('dizimag:', '')
        urlBase64 += '=' * (-len(urlBase64) % 4)
        url = base64.b64decode(urlBase64).decode('utf-8')
        
        return {
            'instructions': [{
                'requestId': f"dizimag-meta-{int(time.time()*1000)}",
                'purpose': 'meta',
                'url': url,
                'method': 'GET',
                'headers': self.get_headers(),
                'metadata': {'originalUrl': url, 'hiddenweb': True}
            }]
        }

    async def handleStream(self, args):
        urlBase64 = args.get('id', '').replace('dizimag:', '')
        urlBase64 += '=' * (-len(urlBase64) % 4)
        url = base64.b64decode(urlBase64).decode('utf-8')
        
        # In this new logic, the id is already the episode/movie URL
        return {
            'instructions': [{
                'requestId': f"dizimag-stream-init-{int(time.time()*1000)}",
                'purpose': 'stream-page',
                'url': url,
                'method': 'GET',
                'headers': self.get_headers(),
                'metadata': {'targetUrl': url, 'hiddenweb': True}
            }]
        }

    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body', '')
        url = fetchResult.get('url', '')
        metadata = fetchResult.get('metadata', {})

        if purpose == 'catalog':
            soup = BeautifulSoup(body, 'html.parser')
            metas = []
            
            for elem in soup.select('div.poster') + soup.select('article.item') + soup.select('div.result-item article'):
                if 'class' in elem.attrs and 'item' in elem.attrs['class'] and elem.name == 'article':
                    poster_div = elem.select_one('.posterf') or elem.select_one('.poster')
                    a_tag = elem.select_one('a')
                    img = elem.select_one('img')
                elif elem.parent and 'result-item' in elem.parent.get('class', []):
                    poster_div = elem.select_one('.image')
                    a_tag = elem.select_one('a')
                    img = elem.select_one('img')
                else:
                    poster_div = elem
                    a_tag = elem.parent if elem.parent.name == 'a' else (elem.parent.parent if elem.parent.parent.name == 'a' else elem.find('a'))
                    img = elem.find('img')
                
                if not a_tag or not img:
                    continue
                    
                href = a_tag.get('href')
                title = img.get('alt')
                if not title and a_tag.get('title'): title = a_tag.get('title')
                if not title:
                    title_el = elem.parent.parent.select_one('h3 a') or elem.select_one('.nf-logo')
                    if title_el: title = title_el.text.strip()
                
                posterUrl = img.get('data-src') or img.get('src')
                
                if title and href and 'wp-content/themes' not in posterUrl:
                    fullUrl = fix_url(href)
                    m_type = 'series' if '/dizi/' in href else 'movie'
                    meta_id = 'dizimag:' + base64_encode_safe(fullUrl)
                    metas.append({'id': meta_id, 'type': m_type, 'name': title, 'poster': fix_url(posterUrl)})
            
            # Deduplicate by id
            seen = set()
            unique_metas = []
            for m in metas:
                if m['id'] not in seen:
                    seen.add(m['id'])
                    unique_metas.append(m)
                    
            return {'metas': unique_metas}

        if purpose == 'meta':
            soup = BeautifulSoup(body, 'html.parser')
            
            title_el = soup.select_one('h1') or soup.select_one('.sbox h1')
            fullTitle = title_el.text.strip() if title_el else ''
            
            poster_img = soup.select_one('.sheader .poster img')
            poster = poster_img.get('data-src') or poster_img.get('src') if poster_img else None
            
            year_match = re.search(r'(\d{4})', fullTitle)
            year = year_match.group(1) if year_match else None
            
            desc_el = soup.select_one('div.wp-content p')
            description = desc_el.text.strip() if desc_el else ''
            
            tags = [el.text.strip() for el in soup.select('.sgeneros a')]
            actors = [el.text.strip() for el in soup.select('.person .name a')]
            
            videos = []
            m_type = 'series' if '/dizi/' in url else 'movie'
            
            if m_type == 'series':
                for epElem in soup.select('ul.episodios li'):
                    ep_a = epElem.find('a')
                    epName = epElem.select_one('.episodiotitle').contents[0].strip() if epElem.select_one('.episodiotitle') else None
                    epHref = ep_a.get('href') if ep_a else None
                    num_text = epElem.select_one('.numerando')
                    
                    seasonNo = 1
                    episodeNo = 1
                    if num_text:
                        s_match = re.search(r'S-(\d+)\s*-\s*E-(\d+)', num_text.text)
                        if s_match:
                            seasonNo = int(s_match.group(1))
                            episodeNo = int(s_match.group(2))
                    
                    if epName and epHref:
                        videoId = 'dizimag:' + base64_encode_safe(fix_url(epHref))
                        videos.append({
                            'id': videoId,
                            'title': epName,
                            'season': seasonNo,
                            'episode': episodeNo
                        })
            else:
                # Movie, the stream url is the movie url
                videos.append({
                    'id': 'dizimag:' + base64_encode_safe(url),
                    'title': fullTitle,
                    'season': 1,
                    'episode': 1
                })
            
            meta = {
                'id': 'dizimag:' + base64_encode_safe(url),
                'type': m_type,
                'name': fullTitle,
                'poster': fix_url(poster),
                'background': fix_url(poster),
                'description': description,
                'releaseInfo': year,
                'genres': tags if tags else None,
                'cast': actors if actors else None,
                'videos': videos if videos else None
            }
            return {'meta': meta}

        if purpose == 'stream-page':
            soup = BeautifulSoup(body, 'html.parser')
            sources = soup.select('.kaynakname')
            print(f"🎬 [DiziMag] Found {len(sources)} sources from DOM")
            
            instructions = []
            for src in sources:
                onclick = src.get('onclick', '')
                match = re.search(r"Change_Source\('([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)'\)", onclick)
                if match:
                    postid = match.group(1)
                    source_name = match.group(2)
                    lang_code = match.group(4)
                    partno = match.group(5)
                    lang = "Türkçe Altyazı" if "sub" in lang_code else "Türkçe Dublaj"
                    
                    randomId = str(int(time.time() * 1000000))[-8:]
                    instructions.append({
                        'requestId': f"dizimag-part-{int(time.time()*1000)}-{randomId}",
                        'purpose': 'part-getir',
                        'url': 'https://dizimag.eu/partgetirply.php',
                        'method': 'POST',
                        'headers': {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'Referer': url,
                            'Accept': '*/*'
                        },
                        'body': f"data={postid}%2C{partno}",
                        'metadata': {
                            'hiddenweb': True,
                            'sourceName': source_name,
                            'lang': lang,
                            'originalUrl': url
                        }
                    })
            
            return {'instructions': instructions}

        if purpose == 'part-getir':
            m = re.search(r'(https?://[^\s<>"\'\\]+)', body)
            iframe_url = m.group(1).replace('\\/', '/') if m else body.strip()
            
            if iframe_url and iframe_url.startswith('http'):
                if iframe_url.endswith('.m3u8') or iframe_url.endswith('.mp4'):
                    return {'streams': [{
                        'name': f"DiziMag\n{metadata.get('sourceName')}",
                        'title': f"{metadata.get('sourceName')} ({metadata.get('lang')})\nAuto",
                        'url': iframe_url,
                        'type': 'm3u8' if iframe_url.endswith('.m3u8') else 'mp4',
                        'behaviorHints': {'notWebReady': False}
                    }]}
                else:
                    randomId = str(int(time.time() * 1000000))[-8:]
                    return {'instructions': [{
                        'requestId': f"dizimag-extract-{int(time.time()*1000)}-{randomId}",
                        'purpose': 'video-extractor',
                        'url': iframe_url,
                        'method': 'GET',
                        'headers': {
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Referer': self.BASE_URL + '/'
                        },
                        'metadata': {
                            'hiddenweb': True,
                            'sourceName': metadata.get('sourceName'),
                            'lang': metadata.get('lang'),
                            'originalUrl': metadata.get('originalUrl'),
                            'iframeUrl': iframe_url
                        }
                    }]}
            return {'streams': []}

        if purpose == 'video-extractor':
            try:
                m3uMatch = re.search(r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
                if not m3uMatch: m3uMatch = re.search(r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"', body)
                if not m3uMatch: m3uMatch = re.search(r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
                if not m3uMatch: m3uMatch = re.search(r'sources:\s*\[\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
                if not m3uMatch: m3uMatch = re.search(r'(https?://[^\s"\'<>()]+\.m3u8[^\s"\'<>()]*)', body)
                
                mp4Match = None
                if not m3uMatch:
                    mp4Match = re.search(r'file:\s*["\']([^"\']+\.mp4[^"\']*)["\']', body)
                    if not mp4Match: mp4Match = re.search(r'"file"\s*:\s*"([^"]+\.mp4[^"]*)"', body)
                    if not mp4Match: mp4Match = re.search(r'(https?://[^\s"\'<>()]+\.mp4[^\s"\'<>()]*)', body)

                source_name = metadata.get('sourceName', 'Extractor')
                lang = metadata.get('lang', 'Bilinmiyor')
                
                iframeUrl = metadata.get('iframeUrl') or 'https://dizimag.eu/'
                parsed_url = urllib.parse.urlparse(iframeUrl)
                origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
                
                proxyHeaders = {
                    'request': {
                        'Referer': iframeUrl,
                        'Origin': origin,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                }
                
                if m3uMatch:
                    return {'streams': [{
                        'name': f"DiziMag\n{source_name}",
                        'title': f"{source_name} ({lang})\nAuto",
                        'url': m3uMatch.group(1),
                        'type': 'm3u8',
                        'behaviorHints': {
                            'notWebReady': False,
                            'proxyHeaders': proxyHeaders
                        }
                    }]}
                elif mp4Match:
                    return {'streams': [{
                        'name': f"DiziMag\n{source_name}",
                        'title': f"{source_name} ({lang})\nAuto",
                        'url': mp4Match.group(1),
                        'type': 'mp4',
                        'behaviorHints': {
                            'notWebReady': False,
                            'proxyHeaders': proxyHeaders
                        }
                    }]}
                    
                return {'streams': []}
            except Exception as e:
                print(f"❌ Extractor error: {e}")
                return {'streams': []}

        return {'ok': True}
