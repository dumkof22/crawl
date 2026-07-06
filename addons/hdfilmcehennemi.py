import base64
import json
import re
import urllib.parse
import random
import time
from bs4 import BeautifulSoup

def base64_decode_safe(s):
    # Padding ekle
    s = s.strip()
    s += '=' * (-len(s) % 4)
    try:
        return base64.b64decode(s).decode('utf-8')
    except:
        try:
            return base64.b64decode(s).decode('latin1')
        except:
            return ''

def base64_encode_safe(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8').replace('=', '')

def rot_n(s, n):
    result = ''
    for c in s:
        if 'a' <= c <= 'z':
            result += chr(((ord(c) - ord('a') + n) % 26) + ord('a'))
        elif 'A' <= c <= 'Z':
            result += chr(((ord(c) - ord('A') + n) % 26) + ord('A'))
        else:
            result += c
    return result

def dc_hello(base64_input, magic_number=399756995, js_body=""):
    """Site algoritması: Dynamic JS parser for rplayer & mobi"""
    try:
        results_to_try = []
        
        # 1) Fully dynamic parsing based on js_body operations
        if js_body:
            res = base64_input
            ops_block_match = re.search(r'result\s*=\s*value;(.*?)let\s+unmix', js_body, re.DOTALL)
            if ops_block_match:
                ops_block = ops_block_match.group(1)
                operations = re.findall(r'result\s*=\s*(result\.replace.*?}\)|result\.split.*?join\([^)]*\)|atob\([^)]*\))', ops_block, re.DOTALL)
                for op in operations:
                    if not op.strip(): continue
                    if 'reverse()' in op:
                        res = res[::-1]
                    elif 'atob' in op:
                        res = base64_decode_safe(res)
                    elif 'replace' in op and 'String.fromCharCode' in op:
                        rot_match = re.search(r'o-base\+?(\d+)', op)
                        if rot_match:
                            res = rot_n(res, int(rot_match.group(1)))
                
                dyn_magic = magic_number
                dyn_offset = 5
                unmix_pattern = re.search(r'charCode\s*-\s*\(?(\d+)\s*%\s*\(i\s*\+\s*(\d+)\)', js_body)
                if unmix_pattern:
                    dyn_magic = int(unmix_pattern.group(1))
                    dyn_offset = int(unmix_pattern.group(2))
                
                results_to_try.append((res, dyn_magic, dyn_offset))

            # Old dynamic fallback
            res_old = base64_input
            if "reverse()" in js_body:
                res_old = res_old[::-1]
            if "rot13" in js_body.lower():
                res_old = rot_n(res_old, 13)
            for _ in range(js_body.count("atob(")):
                res_old = base64_decode_safe(res_old)
            if res_old:
                results_to_try.append((res_old, magic_number, 5))
                
        # 2) Static Fallbacks
        res1 = base64_decode_safe(rot_n(base64_input[::-1], 13))
        if res1: results_to_try.append((res1, magic_number, 5))
        
        res2 = base64_decode_safe(base64_decode_safe(base64_input[::-1]))
        if res2: results_to_try.append((res2, magic_number, 5))

        for decoded, mgc, off in results_to_try:
            unmix = ''
            for i in range(len(decoded)):
                char_code = ord(decoded[i])
                char_code = ((char_code - (mgc % (i + off))) % 256 + 256) % 256
                unmix += chr(char_code)
            
            unmix = unmix.replace('\n', '').replace('\r', '').strip()
            if 'http' in unmix or '.m3u8' in unmix:
                return unmix
                
        print(f"⚠️  [dc_hello] None of the results worked. tried {len(results_to_try)} methods.")
        if results_to_try:
            print(f"⚠️  [dc_hello] First result unmix start: {unmix[:50]}...")
        return None
    except Exception as e:
        print(f"⚠️  dcHello error: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_and_unpack(packed_js):
    try:
        eval_pattern = re.compile(r'eval\(function\(p,a,c,k,e,(?:r|d)\)')
        if not eval_pattern.search(packed_js):
            return packed_js

        full_match = re.search(r"}\('(.*)',(\d+),(\d+),'(.*)'\.", packed_js)
        if not full_match:
            return packed_js

        p = full_match.group(1)
        a = int(full_match.group(2))
        c = int(full_match.group(3))
        k = full_match.group(4).split('|')

        p = p.replace("\\'", "'")

        def to_base(num, radix):
            chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
            if num == 0:
                return '0'
            res = ''
            while num > 0:
                res = chars[num % radix] + res
                num = num // radix
            return res

        result = p
        for i in range(c - 1, -1, -1):
            if i < len(k) and k[i]:
                placeholder = to_base(i, a)
                regex = re.compile(r'\b' + re.escape(placeholder) + r'\b')
                result = regex.sub(k[i], result)
        
        return result

    except Exception as e:
        print(f'⚠️  Unpack error: {e}')
        return packed_js

class HDFilmCehennemiScraper:
    def __init__(self):
        self.BASE_URL = 'https://www.hdfilmcehennemi.nl'
        self.manifest = {
            'id': 'community.hdfilmcehennemi',
            'version': '1.0.0',
            'name': 'HDFilmCehennemi',
            'description': 'Türkçe film ve dizi izleme platformu - HDFilmCehennemi için Stremio eklentisi',
            'logo': 'https://image.winudf.com/v2/image1/Y29tLmNlaGVubmVtLm1vYmlsZS5hcHBfaWNvbl8xNjE0OTU1NDg1XzA1Mw/icon.png?w=184&fakeurl=1',
            'resources': ['catalog', 'meta', 'stream'],
            'types': ['movie', 'series'],
            'catalogs': [
                {
                    'type': 'movie',
                    'id': 'hdfc_search',
                    'name': 'Arama',
                    'extra': [{'name': 'search', 'isRequired': True}]
                },
                {
                    'type': 'movie',
                    'id': 'hdfc_yeni_filmler',
                    'name': 'Yeni Eklenen Filmler',
                    'extra': [{'name': 'skip', 'isRequired': False}]
                },
                {
                    'type': 'movie',
                    'id': 'hdfc_tavsiye',
                    'name': 'Tavsiye Filmler',
                    'extra': [{'name': 'skip', 'isRequired': False}]
                },
                {
                    'type': 'movie',
                    'id': 'hdfc_imdb7',
                    'name': 'IMDB 7+ Filmler',
                    'extra': [{'name': 'skip', 'isRequired': False}]
                },
                {
                    'type': 'movie',
                    'id': 'hdfc_yorumlanan',
                    'name': 'En Çok Yorumlananlar',
                    'extra': [{'name': 'skip', 'isRequired': False}]
                },
                {
                    'type': 'movie',
                    'id': 'hdfc_begenilen',
                    'name': 'En Çok Beğenilenler',
                    'extra': [{'name': 'skip', 'isRequired': False}]
                },
                {
                    'type': 'movie',
                    'id': 'hdfc_robot',
                    'name': 'Film Robotu',
                    'extra': [{'name': 'skip', 'isRequired': False}]
                }
            ],
            'idPrefixes': ['hdfc']
        }
        
        self.CATALOG_URLS = {
            'hdfc_yeni_filmler': f"{self.BASE_URL}/film-robotu-1/",
            'hdfc_tavsiye': f"{self.BASE_URL}/category/tavsiye-filmler-izle3/",
            'hdfc_imdb7': f"{self.BASE_URL}/imdb-7-puan-uzeri-filmler-2/",
            'hdfc_yorumlanan': f"{self.BASE_URL}/en-cok-yorumlananlar-2/",
            'hdfc_begenilen': f"{self.BASE_URL}/en-cok-begenilen-filmleri-izle-4/",
            'hdfc_robot': f"{self.BASE_URL}/film-robotu-1/"
        }

    def getManifest(self):
        return self.manifest

    def _resolve_iframe_url(self, iframe_url, sourceName=''):
        """iframe URL'sini kaynağa göre doğru formata çevir"""
        sourceLower = sourceName.lower().strip()
        
        # Rapidrame kaynağı ise ve URL'de rapidrame_id varsa → /rplayer/ kullan
        if 'rapidrame' in sourceLower and 'rapidrame_id=' in iframe_url:
            rapidrameId = iframe_url.split('rapidrame_id=')[-1].split('&')[0]
            resolved = f"{self.BASE_URL}/rplayer/{rapidrameId}"
            print(f"🔀 [resolve] Rapidrame kaynağı → {resolved}")
            return resolved
        
        # Rapidrame domaini ise (rapidrame.com/e/...)
        if 'rapidrame.com' in iframe_url or 'rapidrame.net' in iframe_url:
            resolved = iframe_url
            print(f"🔀 [resolve] Rapidrame domain → {resolved}")
            return resolved
        
        # mobi embed URL → doğrudan kullan (Close ve diğer kaynaklar için)
        if 'mobi' in iframe_url or 'embed' in iframe_url:
            print(f"🔀 [resolve] Mobi/Embed doğrudan → {iframe_url[:80]}...")
            return iframe_url
        
        # Diğer durumlar → olduğu gibi kullan
        print(f"🔀 [resolve] Doğrudan → {iframe_url[:80]}...")
        return iframe_url

    def _extract_tracks(self, content, subtitles, audioTracks):
        """HTML/JS içeriğinden subtitle ve audio track çıkar"""
        # tracks: [...] pattern'ini ara
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
                    # Trailing comma temizleme
                    raw = re.sub(r',\s*\]', ']', raw)
                    tracksData = json.loads(raw)
                    
                    for track in tracksData:
                        kind = track.get('kind', '').lower()
                        file_url = track.get('file', '')
                        
                        if not file_url:
                            continue
                        
                        if not file_url.startswith('http'):
                            file_url = f"{self.BASE_URL}{file_url}" if file_url.startswith('/') else f"https:{file_url}"
                        
                        label = track.get('label') or track.get('language') or ''
                        
                        if kind in ['captions', 'subtitles']:
                            sub_id = label.lower().replace(' ', '_') if label else 'tr'
                            # Duplicate kontrolü
                            if not any(s['url'] == file_url for s in subtitles):
                                subtitles.append({
                                    'id': sub_id,
                                    'url': file_url,
                                    'lang': label or 'Türkçe'
                                })
                                print(f"   📝 Altyazı bulundu: {label or 'Türkçe'} → {file_url[:60]}...")
                        
                        elif kind in ['audio', 'audiotrack']:
                            audio_id = label.lower().replace(' ', '_') if label else 'default'
                            if not any(a['url'] == file_url for a in audioTracks):
                                audioTracks.append({
                                    'id': audio_id,
                                    'url': file_url,
                                    'lang': label or 'Orijinal'
                                })
                                print(f"   🎵 Ses track bulundu: {label or 'Orijinal'} → {file_url[:60]}...")
                    
                    if subtitles or audioTracks:
                        break  # Başarılı parse, diğer pattern'lere geçme
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"   ⚠️ Track parse hatası: {e}")
                    continue

    async def handleCatalog(self, args):
        print('\n🎯 [HDFilmCehennemi Catalog] Generating instructions...')
        catalogId = args.get('id')
        extra = args.get('extra', {})
        skip = int(extra.get('skip', 0))
        page = (skip // 16) + 1
        searchQuery = extra.get('search')
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))

        if catalogId == 'hdfc_search':
            if not searchQuery:
                return {'instructions': []}
            requestId = f"hdfc-search-{int(time.time()*1000)}-{randomId}"
            return {
                'instructions': [{
                    'requestId': requestId,
                    'purpose': 'catalog_search',
                    'url': f"{self.BASE_URL}/search/?q={urllib.parse.quote(searchQuery)}",
                    'method': 'GET',
                    'headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
                        'Accept': 'application/json, text/javascript, */*; q=0.01',
                        'X-Requested-With': 'fetch',
                        'Referer': f"{self.BASE_URL}/"
                    },
                    'metadata': {'hiddenweb': True}
                }]
            }

        url = self.CATALOG_URLS.get(catalogId)
        if not url:
            return {'instructions': []}

        requestId = f"hdfc-catalog-{catalogId}-{page}-{int(time.time()*1000)}-{randomId}"
        return {
            'instructions': [{
                'requestId': requestId,
                'purpose': 'catalog',
                'url': url.replace('sayfano', str(page)),
                'method': 'GET',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    'Accept': '*/*'
                },
                'metadata': {'hiddenweb': True}
            }]
        }

    async def handleMeta(self, args):
        url_base64 = args.get('id', '').replace('hdfc:', '')
        url = base64_decode_safe(url_base64)
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        requestId = f"hdfc-meta-{int(time.time()*1000)}-{randomId}"

        return {
            'instructions': [{
                'requestId': requestId,
                'purpose': 'meta',
                'url': url,
                'method': 'GET',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
                },
                'metadata': {'hiddenweb': True}
            }]
        }

    async def handleStream(self, args):
        parts = args.get('id', '').replace('hdfc:', '').split('_')
        url_base64 = parts[0]
        url = base64_decode_safe(url_base64)
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        requestId = f"hdfc-stream-{int(time.time()*1000)}-{randomId}"

        return {
            'instructions': [{
                'requestId': requestId,
                'purpose': 'stream',
                'url': url,
                'method': 'GET',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
                },
                'metadata': {'hiddenweb': True}
            }]
        }

    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body', '')
        url = fetchResult.get('url', '')

        print(f"\n⚙️ [HDFilmCehennemi Process] Purpose: {purpose}")

        if purpose == 'catalog':
            try:
                html_content = body
                try:
                    data = json.loads(body)
                    if isinstance(data, dict) and 'html' in data:
                        html_content = data['html']
                except json.JSONDecodeError:
                    pass # It's raw HTML

                soup = BeautifulSoup(html_content, 'html.parser')
                metas = []

                for elem in soup.find_all('a'):
                    title = elem.get('title')
                    href = elem.get('href')
                    img = elem.find('img')
                    
                    if title and href and img:
                        poster = img.get('data-src') or img.get('src')
                        if not poster:
                            continue
                            
                        # URL'nin film veya dizi URL'si olduğundan emin ol (gereksiz menü linklerini filtrele)
                        if any(x in href for x in ['/category/', '/arama/', '/iletisim/', '/hakkimizda/']):
                            continue
                            
                        if 'hdfilmcehennemi' in href or href.startswith('/'):
                            meta_id = 'hdfc:' + base64_encode_safe(href)
                            metas.append({
                                'id': meta_id,
                                'type': 'movie',
                                'name': title.replace(' izle', ''),
                                'poster': poster
                            })

                print(f"✅ Found {len(metas)} items in catalog")
                return {'metas': metas}
            except Exception as e:
                print(f"⚠️  Catalog parse error: {e}")
                return {'metas': []}

        if purpose == 'catalog_search':
            with open("test_search2.html", "w", encoding="utf-8") as f:
                f.write(body)
            try:
                metas = []
                # PRIMARY: regex-based extraction from raw WebView-mangled HTML
                # WebView renders JSON as HTML which breaks DOM structure,
                # so regex on raw text is the most reliable method
                def clean_url(u):
                    """Clean mangled URL from WebView output"""
                    u = u.replace('\\/', '/').replace('\\', '')
                    u = re.sub(r'(?<!:)//', '/', u)  # fix double slashes except after protocol
                    if not u.startswith('http'):
                        u = 'https:/' + u
                    if '://' not in u:
                        u = u.replace(':/', '://', 1)
                    return u.rstrip('/')
                
                # Extract all film/series page URLs from href attributes
                raw_urls = re.findall(
                    r'href=[^>]*?(https?:[/\\]+www\.hdfilmcehennemi\.nl[/\\]+[a-z0-9\-]+[/\\]*)',
                    body, re.IGNORECASE
                )
                # Extract all poster image URLs
                raw_posters = re.findall(
                    r'src=[^>]*?(https?:[/\\]+www\.hdfilmcehennemi\.nl[/\\]+images[/\\]+thumb[/\\]+poster[/\\]+[a-z0-9\-]+\.webp)',
                    body, re.IGNORECASE
                )
                # Extract all titles from title class elements
                raw_titles = re.findall(
                    r'class=[^>]*?title[^>]*?>([^<&]+)',
                    body
                )
                # Extract all years from year class elements
                raw_years = re.findall(
                    r'class=[^>]*?year[^>]*?>(\d{4})',
                    body
                )
                
                count = min(len(raw_urls), len(raw_titles))
                for i in range(count):
                    href = clean_url(raw_urls[i])
                    title = raw_titles[i].strip()
                    poster = clean_url(raw_posters[i]) if i < len(raw_posters) else ''
                    year = raw_years[i] if i < len(raw_years) else ''
                    
                    if not title or not href:
                        continue
                    
                    # Filter out non-movie links
                    if any(x in href for x in ['/category/', '/arama/', '/iletisim/', '/hakkimizda/', '/yapim-yili/', '/tur/']):
                        continue
                    
                    type_ = 'series' if '/dizi/' in href else 'movie'
                    
                    if year:
                        title = f"{title} ({year})"
                    
                    meta_id = 'hdfc:' + base64_encode_safe(href)
                    
                    print(f"[HDFilmCehennemi REGEX] Title: {title} | URL: {href} | Poster: {poster}")
                    
                    metas.append({
                        'id': meta_id,
                        'type': type_,
                        'name': title.replace(' izle', ''),
                        'poster': poster.replace('/thumb/', '/list/') if poster else None,
                        'description': title
                    })
                
                # FALLBACK: JSON parsing if regex found nothing
                if not metas:
                    json_data = None
                    body_text = body
                    if body.strip().startswith('<html') or body.strip().startswith('<!DOCTYPE'):
                        try:
                            soup = BeautifulSoup(body, 'html.parser')
                            if soup.body:
                                body_text = soup.body.text
                        except:
                            pass
                    
                    try:
                        json_data = json.loads(body_text)
                    except:
                        try:
                            soup = BeautifulSoup(body, 'html.parser')
                            pre = soup.find('pre')
                            if pre:
                                json_data = json.loads(pre.text)
                        except:
                            pass
                    
                    if json_data and 'results' in json_data:
                        for item_html in json_data['results']:
                            try:
                                item_html = item_html.replace('\\/', '/')
                                item_soup = BeautifulSoup(item_html, 'html.parser')
                                
                                a_tags = item_soup.find_all('a')
                                href = None
                                for a in a_tags:
                                    h = a.get('href')
                                    if h and 'hdfilmcehennemi' in h:
                                        href = h.replace('"', '')
                                        break
                                        
                                if not href: continue
                                    
                                img = item_soup.find('img')
                                poster = ''
                                if img:
                                    poster = (img.get('src') or img.get('data-src') or '').replace('"', '')
                                    
                                title_tag = item_soup.find(class_='title')
                                title = title_tag.text.strip() if title_tag else ''
                                if not title and img:
                                    title = img.get('alt', '')
                                    
                                if not title: continue
                                
                                type_ = 'series' if '/dizi/' in href else 'movie'
                                
                                year_tag = item_soup.find(class_='year')
                                year = year_tag.text.strip() if year_tag else ''
                                if year:
                                    title = f"{title} ({year})"
                                
                                meta_id = 'hdfc:' + base64_encode_safe(href)
                                
                                print(f"[HDFilmCehennemi JSON] Title: {title} | URL: {href} | Poster: {poster}")
                                
                                metas.append({
                                    'id': meta_id,
                                    'type': type_,
                                    'name': title.replace(' izle', ''),
                                    'poster': poster.replace('/thumb/', '/list/') if poster else None,
                                    'description': title
                                })
                            except Exception as e:
                                print(f"[HDFilmCehennemi] Search parse item error: {e}")
                                continue
                
                print(f"✅ Found {len(metas)} search results")
                return {'metas': metas}
            except Exception as e:
                print(f"❌ Search parsing error: {e}")
                return {'metas': []}

        if purpose == 'meta':
            soup = BeautifulSoup(body, 'html.parser')

            title_elem = soup.find('h1', class_='section-title')
            title = title_elem.text.replace(' izle', '').strip() if title_elem else 'Bilinmeyen'

            poster_elems = soup.select('aside.post-info-poster img.lazyload')
            poster = poster_elems[-1].get('data-src') if poster_elems else None

            desc_elem = soup.select_one('article.post-info-content > p')
            description = desc_elem.text.strip() if desc_elem else 'Açıklama mevcut değil'

            year_elem = soup.select_one('div.post-info-year-country a')
            year = year_elem.text.strip() if year_elem else None

            rating_elem = soup.select_one('div.post-info-imdb-rating span')
            rating = rating_elem.text.split('(')[0].strip() if rating_elem else None

            genres = [a.text.strip() for a in soup.select('div.post-info-genres a')]
            
            cast = []
            for a in soup.select('div.post-info-cast a'):
                strong = a.find('strong')
                if strong:
                    cast.append(strong.text.strip())

            trailer_elem = soup.select_one('div.post-info-trailer button')
            trailerUrl = None
            if trailer_elem and trailer_elem.get('data-modal'):
                trailerUrl = f"https://www.youtube.com/watch?v={trailer_elem.get('data-modal').replace('trailer/', '')}"

            metaId = 'hdfc:' + base64_encode_safe(url)

            recommendations = []
            for elem in soup.select('div.section-slider-container div.slider-slide'):
                a_tag = elem.find('a')
                img_tag = elem.find('img')
                if a_tag and img_tag:
                    recName = a_tag.get('title')
                    recHref = a_tag.get('href')
                    recPoster = img_tag.get('data-src') or img_tag.get('src')

                    if recName and recHref:
                        recId = 'hdfc:' + base64_encode_safe(recHref)
                        recommendations.append({
                            'id': recId,
                            'type': 'movie',
                            'name': recName,
                            'poster': recPoster
                        })

            hasSeasonsTab = len(soup.select('div.seasons')) > 0

            if hasSeasonsTab:
                videos = []
                for a in soup.select('div.seasons-tab-content a'):
                    h4 = a.find('h4')
                    epName = h4.text.strip() if h4 else ''
                    epHref = a.get('href', '')

                    epEpisode_match = re.search(r'(\d+)\.\s*?Bölüm', epName)
                    epEpisode = int(epEpisode_match.group(1)) if epEpisode_match else None
                    
                    epSeason_match = re.search(r'(\d+)\.\s*?Sezon', epName)
                    epSeason = int(epSeason_match.group(1)) if epSeason_match else 1

                    if epName and epHref:
                        fullUrl = epHref if epHref.startswith('http') else f"{self.BASE_URL}{epHref}"
                        episodeId = base64_encode_safe(fullUrl)
                        videos.append({
                            'id': f"hdfc:{episodeId}",
                            'title': epName,
                            'season': epSeason,
                            'episode': epEpisode
                        })

                meta = {
                    'id': metaId,
                    'type': 'series',
                    'name': title,
                    'poster': poster,
                    'background': poster,
                    'description': description,
                    'releaseInfo': year,
                    'imdbRating': rating,
                    'genres': genres,
                    'cast': cast,
                    'trailer': trailerUrl,
                    'recommendations': recommendations[:20],
                    'videos': videos
                }
                print(f"✅ Meta retrieved (Series): {title} with {len(videos)} episodes")
                return {'meta': meta}
            else:
                meta = {
                    'id': metaId,
                    'type': 'movie',
                    'name': title,
                    'poster': poster,
                    'background': poster,
                    'description': description,
                    'releaseInfo': year,
                    'imdbRating': rating,
                    'genres': genres,
                    'cast': cast,
                    'trailer': trailerUrl,
                    'recommendations': recommendations[:20]
                }
                print(f"✅ Meta retrieved (Movie): {title}")
                return {'meta': meta}

        if purpose == 'stream':
            soup = BeautifulSoup(body, 'html.parser')
            instructions = []

            # 1) Film sayfasındaki iframe'leri doğrudan çıkar (aktif kaynaklar için)
            page_iframes = {}
            for iframe_elem in soup.select('div.video-container iframe'):
                iframe_classes = iframe_elem.get('class', [])
                iframe_class = iframe_classes[0].lower() if iframe_classes else ''
                iframe_url = iframe_elem.get('data-src') or iframe_elem.get('src')
                if iframe_url and iframe_class:
                    page_iframes[iframe_class] = iframe_url
                    print(f"🔍 [stream] Sayfa iframe bulundu: class={iframe_class} url={iframe_url[:80]}...")

            for elem in soup.select('div.alternative-links'):
                langCode = elem.get('data-lang', '').upper()
                for button in elem.select('button.alternative-link'):
                    sourceName = button.text.replace('(HDrip Xbet)', '').strip()
                    videoID = button.get('data-video')
                    fullSourceName = f"{sourceName} {langCode}".strip()

                    if not videoID:
                        continue

                    # Sayfadaki iframe'den doğrudan URL çıkarma (hızlı yol)
                    direct_iframe = page_iframes.get(sourceName.lower())
                    
                    if direct_iframe:
                        print(f"⚡ [stream] Doğrudan iframe kullanılıyor: {sourceName} → {direct_iframe[:80]}...")
                        iframe_url = self._resolve_iframe_url(direct_iframe, sourceName)
                        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                        requestId = f"hdfc-extract-{int(time.time()*1000)}-{randomId}"
                        instructions.append({
                            'requestId': requestId,
                            'purpose': 'stream_extract',
                            'url': iframe_url,
                            'method': 'GET',
                            'headers': {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                                'Referer': f"{self.BASE_URL}/"
                            },
                            'metadata': {
                                'sourceName': fullSourceName,
                                'originalIframe': direct_iframe,
                                'hiddenweb': True
                            }
                        })
                    else:
                        # Sayfada iframe yok → /video/{videoID}/ endpoint'inden al
                        print(f"🔄 [stream] /video/ endpoint kullanılıyor: {sourceName} → videoID={videoID}")
                        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                        requestId = f"hdfc-video-{int(time.time()*1000)}-{randomId}"
                        instructions.append({
                            'requestId': requestId,
                            'purpose': 'stream_video',
                            'url': f"{self.BASE_URL}/video/{videoID}/",
                            'method': 'GET',
                            'headers': {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                                'Content-Type': 'application/json',
                                'X-Requested-With': 'fetch',
                                'Origin': self.BASE_URL,
                                'Referer': url
                            },
                            'metadata': {
                                'sourceName': fullSourceName,
                                'videoID': videoID,
                                'pageUrl': url,
                                'hiddenweb': True
                            }
                        })

            print(f"✅ Found {len(instructions)} video source(s)")
            if instructions:
                return {'instructions': instructions}
            return {'streams': []}

        if purpose == 'stream_video':
            try:
                print(f"🔍 [stream_video] Body uzunluğu: {len(body)}")
                print(f"🔍 [stream_video] Body ilk 500 karakter: {body[:500]}")

                iframe = None
                sourceName = fetchResult.get('metadata', {}).get('sourceName', '')

                # 1) JSON response'dan iframe çıkar (HTML-wrapped JSON desteği)
                json_text = body
                # HTML wrapper'ı varsa (<pre> tag içindeki JSON'ı çıkar)
                if body.strip().startswith('<'):
                    try:
                        _soup = BeautifulSoup(body, 'html.parser')
                        _pre = _soup.find('pre')
                        if _pre:
                            json_text = _pre.get_text()
                            print(f"🔍 [stream_video] <pre> tag'den JSON çıkarıldı: {json_text[:200]}")
                    except:
                        pass
                
                try:
                    json_data = json.loads(json_text)
                    if isinstance(json_data, dict):
                        # Nested data.html pattern
                        data_obj = json_data.get('data', json_data)
                        html_content = data_obj.get('html', data_obj.get('iframe', data_obj.get('embed', '')))
                        if html_content:
                            html_content = html_content.replace('\\/', '/')
                            iframe_soup = BeautifulSoup(html_content, 'html.parser')
                            iframe_elem = iframe_soup.find('iframe')
                            if iframe_elem:
                                iframe = iframe_elem.get('data-src') or iframe_elem.get('src')
                                print(f"🔍 [stream_video] JSON iframe bulundu: {iframe}")
                        # Doğrudan URL alanı
                        if not iframe:
                            iframe = data_obj.get('url') or data_obj.get('src') or data_obj.get('embed_url')
                            if iframe:
                                print(f"🔍 [stream_video] JSON URL bulundu: {iframe}")
                except (json.JSONDecodeError, ValueError):
                    pass

                # 2) Escaped HTML'den iframe çıkar
                if not iframe:
                    iframe_match = re.search(r'data-src=\\?"([^"\\]+)', body)
                    if iframe_match:
                        iframe = iframe_match.group(1)
                        print(f"🔍 [stream_video] Regex data-src bulundu: {iframe}")

                # 3) Normal HTML'den iframe çıkar
                if not iframe:
                    iframe_match = re.search(r'(?:src|data-src)\s*=\s*["\']([^"\']+(?:mobi|rapidrame|embed|player)[^"\']*)["\']', body, re.IGNORECASE)
                    if iframe_match:
                        iframe = iframe_match.group(1)
                        print(f"🔍 [stream_video] Regex src bulundu: {iframe}")

                # 4) BeautifulSoup fallback
                if not iframe:
                    soup = BeautifulSoup(body, 'html.parser')
                    iframe_elem = soup.find('iframe')
                    if iframe_elem:
                        iframe = iframe_elem.get('data-src') or iframe_elem.get('src')
                        print(f"🔍 [stream_video] BS4 iframe bulundu: {iframe}")

                # 5) Herhangi bir URL pattern
                if not iframe:
                    url_match = re.search(r'(https?://[^\s"\'\\]+(?:embed|player|video)[^\s"\'\\]*)', body)
                    if url_match:
                        iframe = url_match.group(1)
                        print(f"🔍 [stream_video] URL pattern bulundu: {iframe}")

                if iframe:
                    iframe = iframe.replace('\\/', '/').replace('\\', '')
                    iframe_url = self._resolve_iframe_url(iframe, sourceName)
                    print(f"✅ [stream_video] Final iframe URL: {iframe_url}")
                    
                    randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                    requestId = f"hdfc-extract-{int(time.time()*1000)}-{randomId}"
                    
                    return {
                        'instructions': [{
                            'requestId': requestId,
                            'purpose': 'stream_extract',
                            'url': iframe_url,
                            'method': 'GET',
                            'headers': {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                                'Referer': f"{self.BASE_URL}/"
                            },
                            'metadata': {
                                'sourceName': fetchResult.get('metadata', {}).get('sourceName'),
                                'originalIframe': iframe,
                                'hiddenweb': True
                            }
                        }]
                    }
                
                print(f"⚠️  [stream_video] Iframe bulunamadı!")
                return {'streams': []}
            except Exception as e:
                print(f"⚠️  Stream video error: {e}")
                import traceback
                traceback.print_exc()
                return {'streams': []}

        if purpose == 'stream_extract':
            streams = []
            streamName = fetchResult.get('metadata', {}).get('sourceName', 'HDFilmCehennemi')
            subtitles = []
            audioTracks = []

            try:
                print(f"🔍 [stream_extract] Body uzunluğu: {len(body)}")
                print(f"🔍 [stream_extract] Body ilk 500 karakter: {body[:500]}")

                # ===== ALTYAZI VE SES TRACK ÇIKARMA =====
                self._extract_tracks(body, subtitles, audioTracks)

                # ===== VIDEO URL ÇIKARMA =====
                finalUrl = None

                # Yöntem 1: Tüm script'leri topla, unpack et, birleşik içerikte dc_ ara
                all_scripts = re.findall(r'<script[^>]*>(.*?)</script>', body, re.DOTALL)
                print(f"🔍 [stream_extract] Toplam {len(all_scripts)} script tag bulundu")
                
                # Tüm script içeriklerini topla (packed olanları unpack et)
                combined_content = ""
                for idx, script_content in enumerate(all_scripts):
                    script_content = script_content.strip()
                    if not script_content or len(script_content) < 20:
                        continue
                    
                    if 'eval(function(p,a,c,k,e' in script_content:
                        unpacked = get_and_unpack(script_content)
                        if unpacked != script_content:
                            print(f"🔍 [stream_extract] Script #{idx}: Packed → unpacked ({len(unpacked)} chars)")
                            combined_content += unpacked + "\n"
                        else:
                            combined_content += script_content + "\n"
                    else:
                        combined_content += script_content + "\n"
                
                print(f"🔍 [stream_extract] Birleşik content uzunluğu: {len(combined_content)}")
                
                # Unpacked content'ten de track çıkar
                if not subtitles:
                    self._extract_tracks(combined_content, subtitles, audioTracks)
                
                # dc_ fonksiyon tanımı ve var s_ = dc_(...) pattern'ini ara
                var_pattern = re.compile(r'var\s+(s_\w+)\s*=\s*(\w+)\(\[(.*?)\]\)')
                for match in var_pattern.finditer(combined_content):
                    varName = match.group(1)
                    funcName = match.group(2)
                    print(f"🔍 [stream_extract] Var bulundu: {varName} = {funcName}([...])")
                    
                    # Fonksiyon tanımından magic number çıkar
                    funcPattern = re.compile(
                        r'function\s+' + re.escape(funcName) + r'\s*\([^)]*\)\s*\{([\s\S]*?)return\s+unmix[\s\S]*?\}',
                        re.MULTILINE
                    )
                    funcMatch = funcPattern.search(combined_content)
                    
                    magic_number = 399756995
                    js_body = ""
                    if funcMatch:
                        js_body = funcMatch.group(1)
                        magicMatch = re.search(r'\((\d+)\s*%', funcMatch.group(0))
                        if magicMatch:
                            magic_number = int(magicMatch.group(1))
                    print(f"🔍 [stream_extract] Magic number: {magic_number}")

                    arrayContent = match.group(3)
                    arrayItems = re.findall(r'"([^"]+)"', arrayContent)
                    
                    if arrayItems:
                        print(f"🔍 [stream_extract] dc_hello items: {len(arrayItems)}, ilk: {arrayItems[0][:50]}...")
                        
                        # Join edip dene (site genelde tüm parçaları birleştiriyor)
                        joined = "".join(arrayItems)
                        decoded = dc_hello(joined, magic_number, js_body)
                        if decoded:
                            print(f"🔍 [stream_extract] dc_hello joined decoded: {repr(decoded[:100])}")
                        if decoded and ('http' in decoded or '.m3u8' in decoded):
                            finalUrl = decoded
                            print(f"✅ [stream_extract] dc_hello joined URL: {finalUrl[:80]}...")
                        
                        # Tek tek dene
                        if not finalUrl:
                            for item in arrayItems:
                                decoded = dc_hello(item, magic_number, js_body)
                                if decoded and ('http' in decoded or '.m3u8' in decoded):
                                    finalUrl = decoded
                                    print(f"✅ [stream_extract] dc_hello item URL: {finalUrl[:80]}...")
                                    break
                                    
                    if finalUrl:
                        break
                
                # Fallback: Birleşik content'ten m3u8 URL çıkar
                if not finalUrl:
                    m3u8_match = re.search(r'(?:file|source|src|url)\s*[:=]\s*["\']?(https?://[^\s"\'\\,\]]+\.m3u8[^\s"\'\\,\]]*)', combined_content)
                    if m3u8_match:
                        finalUrl = m3u8_match.group(1)
                        print(f"✅ [stream_extract] m3u8 from combined: {finalUrl[:80]}...")
                
                # Fallback: sources array
                if not finalUrl:
                    sources_match = re.search(r'sources\s*:\s*\[\s*\{[^}]*?(?:file|src)\s*:\s*["\']([^"\']+)["\']', combined_content)
                    if sources_match:
                        finalUrl = sources_match.group(1)
                        print(f"✅ [stream_extract] sources array URL: {finalUrl[:80]}...")

                # Yöntem 2: Raw body'den doğrudan m3u8 URL çıkar
                if not finalUrl:
                    m3u8_match = re.search(r'(https?://[^\s"\'\\,\]]+\.m3u8[^\s"\'\\,\]]*)', body)
                    if m3u8_match:
                        finalUrl = m3u8_match.group(1)
                        print(f"✅ [stream_extract] Raw m3u8 URL: {finalUrl[:80]}...")

                # Yöntem 3: file: "..." pattern (packed olmayan)
                if not finalUrl:
                    file_match = re.search(r'(?:file|source)\s*:\s*["\']([^"\']+(?:\.m3u8|\.mp4)[^"\']*)["\']', body)
                    if file_match:
                        finalUrl = file_match.group(1)
                        print(f"✅ [stream_extract] file: pattern URL: {finalUrl[:80]}...")

                if finalUrl and finalUrl.startswith('http'):
                    finalUrl = finalUrl.replace('\\/', '/').replace('\\', '')
                    streamType = 'm3u8' if '.m3u8' in finalUrl else 'mp4'
                    streamData = {
                        'name': streamName,
                        'title': streamName,
                        'url': finalUrl,
                        'type': streamType,
                        'behaviorHints': {'notWebReady': False}
                    }
                    if subtitles: streamData['subtitles'] = subtitles
                    if audioTracks: streamData['audioTracks'] = audioTracks
                    streams.append(streamData)
                    print(f"✅ Stream extracted: {finalUrl[:80]}...")
                    print(f"   📝 Subtitles: {len(subtitles)}, 🎵 Audio: {len(audioTracks)}")
                else:
                    print(f"⚠️  [stream_extract] Video URL bulunamadı!")

            except Exception as e:
                print(f"⚠️  Stream extract error: {e}")
                import traceback
                traceback.print_exc()

            return {'streams': streams}

        return {'ok': True}
