import base64
import json
import urllib.parse
import random
import time
import hashlib
from bs4 import BeautifulSoup
from Crypto.Cipher import AES

def base64_encode_safe(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8').replace('=', '')

def fix_url(url):
    if not url: return None
    BASE_URL = 'https://dizimag.onl'
    if url.startswith('//'): return 'https:' + url
    if not url.startswith('http'): return BASE_URL + ('' if url.startswith('/') else '/') + url
    return url

def evp_bytes_to_key(password, salt, key_len, iv_len):
    password_buffer = password.encode('utf-8')
    salt_buffer = bytes.fromhex(salt)
    
    derived_key = b''
    block = None
    target_len = key_len + iv_len
    
    while len(derived_key) < target_len:
        hash_obj = hashlib.md5()
        if block:
            hash_obj.update(block)
        hash_obj.update(password_buffer)
        hash_obj.update(salt_buffer)
        block = hash_obj.digest()
        derived_key += block
        
    key = derived_key[:key_len]
    iv = derived_key[key_len:key_len+iv_len]
    return key, iv

def decrypt_be_player(password, cipher_text, salt_hex):
    try:
        key, iv = evp_bytes_to_key(password, salt_hex, 32, 16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted_data = base64.b64decode(cipher_text)
        decrypted_padded = cipher.decrypt(encrypted_data)
        
        # unpad
        pad_len = decrypted_padded[-1]
        decrypted = decrypted_padded[:-pad_len]
        return decrypted.decode('utf-8')
    except Exception as e:
        print(f'Decryption error: {e}')
        return None

class DiziMagScraper:
    def __init__(self):
        self.BASE_URL = 'https://dizimag.onl'
        self.manifest = {
            'id': 'community.dizimag',
            'version': '1.0.0',
            'name': 'DiziMag',
            'description': 'Türkçe dizi ve film izleme platformu - DiziMag için Stremio eklentisi',
            'resources': ['catalog', 'meta', 'stream'],
            'types': ['movie', 'series'],
            'catalogs': [
                {'type': 'series', 'id': 'dizimag_new_episodes', 'name': 'Yeni Eklenenler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizimag_search', 'name': 'Arama', 'extra': [{'name': 'search', 'isRequired': True}]},
                {'type': 'movie', 'id': 'dizimag_search', 'name': 'Arama', 'extra': [{'name': 'search', 'isRequired': True}]},
                {'type': 'series', 'id': 'dizimag_dizi_aile', 'name': 'Aile'},
                {'type': 'series', 'id': 'dizimag_dizi_aksiyon', 'name': 'Aksiyon-Macera'},
                {'type': 'series', 'id': 'dizimag_dizi_animasyon', 'name': 'Animasyon'},
                {'type': 'series', 'id': 'dizimag_dizi_belgesel', 'name': 'Belgesel'},
                {'type': 'series', 'id': 'dizimag_dizi_bilimkurgu', 'name': 'Bilim Kurgu'},
                {'type': 'series', 'id': 'dizimag_dizi_dram', 'name': 'Dram'},
                {'type': 'series', 'id': 'dizimag_dizi_gizem', 'name': 'Gizem'},
                {'type': 'series', 'id': 'dizimag_dizi_komedi', 'name': 'Komedi'},
                {'type': 'series', 'id': 'dizimag_dizi_savas', 'name': 'Savaş Politik'},
                {'type': 'series', 'id': 'dizimag_dizi_suc', 'name': 'Suç'},
                {'type': 'movie', 'id': 'dizimag_film_aile', 'name': 'Aile Film'},
                {'type': 'movie', 'id': 'dizimag_film_animasyon', 'name': 'Animasyon Film'},
                {'type': 'movie', 'id': 'dizimag_film_bilimkurgu', 'name': 'Bilim-Kurgu Film'}
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
        page = (skip // 24) + 1
        searchQuery = extra.get('search')
        
        if catalogId == 'dizimag_search' and searchQuery:
            headers = self.get_headers()
            headers.update({
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/javascript, */*; q=0.01'
            })
            return {
                'instructions': [{
                    'requestId': f"dizimag-search-{int(time.time()*1000)}",
                    'purpose': 'catalog-search',
                    'url': f"{self.BASE_URL}/search",
                    'method': 'POST',
                    'headers': headers,
                    'body': f"query={urllib.parse.quote(searchQuery)}",
                    'metadata': {}
                }]
            }

        if catalogId == 'dizimag_new_episodes':
            return {
                'instructions': [{
                    'requestId': f"dizimag-new-{int(time.time()*1000)}",
                    'purpose': 'catalog-new',
                    'url': f"{self.BASE_URL}/kesfet/eyJ0eXBlIjoic2VyaWVzIn0=/{page}",
                    'method': 'GET',
                    'headers': self.get_headers(),
                    'metadata': {}
                }]
            }

        genre_map = {
            'dizimag_dizi_aile': '/dizi/tur/aile',
            'dizimag_dizi_aksiyon': '/dizi/tur/aksiyon-macera',
            'dizimag_dizi_animasyon': '/dizi/tur/animasyon',
            'dizimag_dizi_belgesel': '/dizi/tur/belgesel',
            'dizimag_dizi_bilimkurgu': '/dizi/tur/bilim-kurgu-fantazi',
            'dizimag_dizi_dram': '/dizi/tur/dram',
            'dizimag_dizi_gizem': '/dizi/tur/gizem',
            'dizimag_dizi_komedi': '/dizi/tur/komedi',
            'dizimag_dizi_savas': '/dizi/tur/savas-politik',
            'dizimag_dizi_suc': '/dizi/tur/suc',
            'dizimag_film_aile': '/film/tur/aile',
            'dizimag_film_animasyon': '/film/tur/animasyon',
            'dizimag_film_bilimkurgu': '/film/tur/bilim-kurgu'
        }

        if catalogId in genre_map:
            base_genre_url = f"{self.BASE_URL}{genre_map[catalogId]}"
            url = f"{base_genre_url}/{page}" if page > 1 else base_genre_url
            return {
                'instructions': [{
                    'requestId': f"dizimag-genre-{int(time.time()*1000)}",
                    'purpose': 'catalog-genre',
                    'url': url,
                    'method': 'GET',
                    'headers': self.get_headers(),
                    'metadata': {}
                }]
            }

        return {'metas': []}

    async def handleMeta(self, args):
        urlBase64 = args.get('id', '').replace('dizimag:', '')
        # Base64 pad
        urlBase64 += '=' * (-len(urlBase64) % 4)
        url = base64.b64decode(urlBase64).decode('utf-8')
        url = url.replace('dizimag.nl', 'dizimag.onl')
        
        return {
            'instructions': [{
                'requestId': f"dizimag-meta-{int(time.time()*1000)}",
                'purpose': 'meta',
                'url': url,
                'method': 'GET',
                'headers': self.get_headers(),
                'metadata': {}
            }]
        }

    async def handleStream(self, args):
        urlBase64 = args.get('id', '').replace('dizimag:', '')
        urlBase64 += '=' * (-len(urlBase64) % 4)
        url = base64.b64decode(urlBase64).decode('utf-8')
        url = url.replace('dizimag.nl', 'dizimag.onl')
        
        return {
            'instructions': [{
                'requestId': f"dizimag-init-{int(time.time()*1000)}",
                'purpose': 'init-session',
                'url': self.BASE_URL,
                'method': 'GET',
                'headers': self.get_headers(),
                'metadata': {'targetUrl': url}
            }]
        }

    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body', '')
        url = fetchResult.get('url', '').replace('dizimag.nl', 'dizimag.onl')
        metadata = fetchResult.get('metadata', {})

        if purpose in ['catalog-new', 'catalog-genre']:
            soup = BeautifulSoup(body, 'html.parser')
            metas = []
            
            if purpose == 'catalog-new':
                for elem in soup.select('div.filter-result-box'):
                    h2 = elem.select_one('h2.truncate')
                    title = h2.text.strip() if h2 else None
                    a_tag = elem.select_one('div.filter-result-box-image a')
                    href = a_tag.get('href') if a_tag else None
                    img = elem.select_one('div.filter-result-box-image img')
                    posterUrl = img.get('data-src') if img else None
                    
                    if title and href:
                        fullUrl = fix_url(href)
                        m_type = 'series' if '/dizi/' in href else 'movie'
                        meta_id = 'dizimag:' + base64_encode_safe(fullUrl)
                        metas.append({'id': meta_id, 'type': m_type, 'name': title, 'poster': fix_url(posterUrl)})
            else:
                for elem in soup.select('div.poster-long'):
                    h2 = elem.select_one('h2.truncate')
                    title = h2.text.strip() if h2 else None
                    a_tag = elem.select_one('div.poster-long-image a')
                    href = a_tag.get('href') if a_tag else None
                    img = elem.select_one('div.poster-long-image img')
                    posterUrl = img.get('data-src') if img else None
                    
                    if title and href:
                        fullUrl = fix_url(href)
                        m_type = 'series' if '/dizi/' in href else 'movie'
                        meta_id = 'dizimag:' + base64_encode_safe(fullUrl)
                        metas.append({'id': meta_id, 'type': m_type, 'name': title, 'poster': fix_url(posterUrl)})
            
            return {'metas': metas}

        if purpose == 'catalog-search':
            try:
                json_data = json.loads(body)
                if not json_data.get('success') or not json_data.get('theme'): return {'metas': []}
                
                soup = BeautifulSoup(json_data['theme'], 'html.parser')
                metas = []
                
                for elem in soup.select('.result-series'):
                    parent_a = elem.parent
                    if parent_a and parent_a.name == 'a':
                        href = parent_a.get('href')
                        title_el = elem.select_one('span.truncate')
                        title = title_el.text.strip() if title_el else None
                        img = elem.find('img')
                        posterUrl = img.get('data-src') if img else None
                        
                        if title and href:
                            fullUrl = fix_url(href)
                            meta_id = 'dizimag:' + base64_encode_safe(fullUrl)
                            metas.append({'id': meta_id, 'type': 'series', 'name': title, 'poster': fix_url(posterUrl)})
                            
                for elem in soup.select('.result-movies'):
                    title_link = elem.select_one('.result-movies-text a')
                    href = title_link.get('href') if title_link else None
                    title = title_link.text.strip() if title_link else None
                    img = elem.select_one('.result-movies-image img')
                    posterUrl = img.get('data-src') if img else None
                    
                    if title and href:
                        fullUrl = fix_url(href)
                        meta_id = 'dizimag:' + base64_encode_safe(fullUrl)
                        metas.append({'id': meta_id, 'type': 'movie', 'name': title, 'poster': fix_url(posterUrl)})
                
                return {'metas': metas}
            except Exception as e:
                print(f'Search parse error: {e}')
                return {'metas': []}

        if purpose == 'meta':
            soup = BeautifulSoup(body, 'html.parser')
            
            title_el = soup.select_one('div.page-title h1 a')
            title = title_el.text.strip() if title_el else ''
            org_title_el = soup.select_one('div.page-title p')
            orgTitle = org_title_el.text.strip() if org_title_el else ''
            fullTitle = f"{title} - {orgTitle}" if orgTitle else title
            
            img_el = soup.select_one('div.series-profile-image img')
            poster = img_el.get('src') if img_el else None
            
            h1_span = soup.select_one('h1 span')
            year = None
            if h1_span:
                try: year = h1_span.text.split('(')[1].split(')')[0]
                except: pass
                
            rating_el = soup.select_one('span.color-imdb')
            rating = rating_el.text.strip() if rating_el else None
            
            desc_el = soup.select_one('div.series-profile-summary p')
            description = desc_el.text.strip() if desc_el else ''
            
            tags = [el.text.strip() for el in soup.select('div.series-profile-type a')]
            actors = [el.text.strip() for el in soup.select('div.series-profile-cast li h5.truncate')]
            
            videos = []
            if '/dizi/' in url:
                for seasonIndex, seasonElem in enumerate(soup.select('div.series-profile-episodes-area')):
                    seasonNo = seasonIndex + 1
                    for epIndex, epElem in enumerate(seasonElem.find_all('li')):
                        ep_a = epElem.select_one('h6.truncate a')
                        epName = ep_a.text.strip() if ep_a else None
                        first_a = epElem.find('a')
                        epHref = first_a.get('href') if first_a else None
                        
                        if epName and epHref:
                            episodeNo = epIndex + 1
                            videoId = 'dizimag:' + base64_encode_safe(fix_url(epHref))
                            videos.append({
                                'id': videoId,
                                'title': epName,
                                'season': seasonNo,
                                'episode': episodeNo
                            })
                            
            m_type = 'series' if '/dizi/' in url else 'movie'
            
            meta = {
                'id': 'dizimag:' + base64_encode_safe(url),
                'type': m_type,
                'name': fullTitle,
                'poster': fix_url(poster),
                'background': fix_url(poster),
                'description': description,
                'releaseInfo': year,
                'imdbRating': rating,
                'genres': tags if tags else None,
                'cast': actors if actors else None,
                'videos': videos if videos else None
            }
            return {'meta': meta}

        if purpose == 'init-session':
            return {
                'instructions': [{
                    'requestId': f"dizimag-stream-page-{int(time.time()*1000)}",
                    'purpose': 'stream-page',
                    'url': metadata.get('targetUrl'),
                    'method': 'GET',
                    'headers': self.get_headers(),
                    'metadata': {}
                }]
            }

        if purpose == 'stream-page':
            print(f"🎬 [DiziMag] Processing stream-page for {url}")
            soup = BeautifulSoup(body, 'html.parser')
            iframe_urls = []
            
            for tab_li in soup.select('ul.alternative-group li'):
                tab_id = tab_li.get('data-number')
                if not tab_id: continue
                
                lang_a = tab_li.find('a')
                lang = lang_a.text.strip() if lang_a else 'Auto'
                
                tab_div = soup.select_one(f'div#{tab_id}')
                if tab_div:
                    for btn in tab_div.select('button[data-frame]'):
                        frame_url = btn.get('data-frame')
                        title = btn.get('title', 'DiziMag')
                        if frame_url:
                            iframe_urls.append({
                                'url': fix_url(frame_url),
                                'lang': lang,
                                'source': title
                            })
            
            if not iframe_urls:
                iframeSrc_el = soup.select_one('div#tv-spoox2 iframe')
                iframeSrc = iframeSrc_el.get('src') if iframeSrc_el else None
                if iframeSrc:
                    iframe_urls.append({
                        'url': fix_url(iframeSrc),
                        'lang': 'Auto',
                        'source': 'DiziMag'
                    })
            
            print(f"🎬 [DiziMag] Found {len(iframe_urls)} iframes: {iframe_urls}")
            if not iframe_urls: return {'streams': []}
            
            try:
                from curl_cffi.requests import AsyncSession
                import re
                streams = []
                
                async with AsyncSession(impersonate='chrome110') as s:
                    for item in iframe_urls:
                        try:
                            print(f"🎬 [DiziMag] Fetching iframe: {item['url']}")
                            r = await s.get(item['url'], headers={'Referer': url, 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
                            print(f"🎬 [DiziMag] Iframe fetch status: {r.status_code}")
                            if r.status_code == 200:
                                iframe_body = r.text
                                bePlayerScript = None
                                iframe_soup = BeautifulSoup(iframe_body, 'html.parser')
                                for script in iframe_soup.find_all('script'):
                                    html = script.string or ''
                                    if 'bePlayer' in html:
                                        bePlayerScript = html
                                        break
                                        
                                if bePlayerScript:
                                    print(f"🎬 [DiziMag] Found bePlayer script")
                                    match = re.search(r"bePlayer\('(.*?)',\s*'(.*?)'\)", bePlayerScript)
                                    if match:
                                        key = match.group(1)
                                        jsonCipherStr = match.group(2)
                                        cipherData = json.loads(jsonCipherStr.replace('\\/', '/'))
                                        decrypted = decrypt_be_player(key, cipherData.get('ct'), cipherData.get('s'))
                                        
                                        if decrypted:
                                            print(f"🎬 [DiziMag] Decryption successful for {item['url']}")
                                            jsonData = json.loads(decrypted)
                                            subtitles = []
                                            
                                            if 'strSubtitles' in jsonData and isinstance(jsonData['strSubtitles'], list):
                                                for sub in jsonData['strSubtitles']:
                                                    label = sub.get('label') or ''
                                                    isTurkish = any(k in label.lower() for k in ['tur', 'tr', 'türkçe', 'turkce'])
                                                    sub_lang = 'Turkish' if isTurkish else (label if label else 'Unknown')
                                                    
                                                    file_url = sub.get('file')
                                                    if not file_url: continue
                                                        
                                                    if file_url.startswith('/'):
                                                        file_url = urllib.parse.urljoin(item['url'], file_url)
                                                        
                                                    subtitles.append({
                                                        'id': sub_lang.lower().replace(' ', '_'),
                                                        'url': file_url,
                                                        'lang': sub_lang
                                                    })
                                                    
                                            if jsonData.get('video_location'):
                                                iframe_origin = f"{urllib.parse.urlparse(item['url']).scheme}://{urllib.parse.urlparse(item['url']).netloc}"
                                                print(f"🎬 [DiziMag] Extracted stream: {jsonData['video_location']}")
                                                streams.append({
                                                    'name': f"DiziMag\n{item['source']}",
                                                    'title': f"{item['source']} ({item['lang']})\nAuto",
                                                    'url': jsonData['video_location'],
                                                    'type': 'm3u8',
                                                    'subtitles': subtitles if subtitles else None,
                                                    'behaviorHints': {
                                                        'notWebReady': False,
                                                        'proxyHeaders': {
                                                            'request': {
                                                                'Referer': iframe_origin + "/",
                                                                'Origin': iframe_origin,
                                                                'User-Agent': self.get_headers()['User-Agent'],
                                                                'Cookie': "; ".join([f"{k}={v}" for k, v in s.cookies.get_dict().items()])
                                                            }
                                                        }
                                                    }
                                                })
                        except Exception as e:
                            print(f"❌ Iframe fetch/parse error: {e}")
                
                print(f"🎬 [DiziMag] Returning {len(streams)} streams")
                return {'streams': streams}
            except Exception as e:
                import traceback
                print(f"❌ Stream process error: {e}")
                traceback.print_exc()
                return {'streams': []}

        return {'ok': True}
