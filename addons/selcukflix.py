import base64
import json
import re
import urllib.parse
import random
import time
from bs4 import BeautifulSoup

def base64_decode_safe(s):
    s = s.strip()
    s += '=' * (-len(s) % 4)
    try:
        return base64.b64decode(s).decode('utf-8')
    except:
        try:
            return base64.b64decode(s).decode('latin1')
        except:
            return ''

def base64_decode_iso(s):
    s = s.strip()
    s += '=' * (-len(s) % 4)
    try:
        latin1 = base64.b64decode(s).decode('latin1')
        return latin1.encode('latin1').decode('utf-8')
    except:
        return base64_decode_safe(s)

def base64_encode_safe(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8').replace('=', '')

def fix_poster_url(url):
    if not url: return None
    return url \
        .replace('images-macellan-online.cdn.ampproject.org/i/s/', '') \
        .replace('file.dizilla.club', 'file.macellan.online') \
        .replace('images.dizilla.club', 'images.macellan.online') \
        .replace('images.dizimia4.com', 'images.macellan.online') \
        .replace('file.dizimia4.com', 'file.macellan.online') \
        .replace('/f/f/', '/630/910/') \
        .replace('file.hdfilmcehennemi.net/', 'file.macellan.online/') \
        .replace('images.hdfilmcehennemi.net/', 'images.macellan.online/')

def decode_av(input_str):
    try:
        reversed_str = input_str[::-1]
        firstPass = base64.b64decode(reversed_str)
        key = 'K9L'
        adjusted = bytearray(len(firstPass))
        for i in range(len(firstPass)):
            sub = firstPass[i] - ((ord(key[i % 3]) % 5) + 1)
            adjusted[i] = sub & 0xFF
        secondPass = base64.b64decode(adjusted)
        return secondPass.decode('utf-8')
    except Exception as e:
        print(f"❌ decode_av error: {e}")
        return ''

def decode_ee(encoded):
    try:
        s = encoded.replace('-', '+').replace('_', '/')
        s += '=' * (-len(s) % 4)
        decodedBytes = base64.b64decode(s)
        a = decodedBytes.decode('utf-8')
        import codecs
        rot13 = codecs.encode(a, 'rot_13')
        return rot13[::-1]
    except Exception as e:
        print(f"❌ decode_ee error: {e}")
        return ''

def decrypt_selcukflix_data(encrypted_base64):
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import padding
        import hashlib
        import base64
        
        key_str = "!!22xx!!90!!"
        key_hash = hashlib.sha256(key_str.encode('utf-8')).digest()
        key = base64.b64encode(key_hash).decode('utf-8')[:32].encode('utf-8')
        iv = b'\x00' * 16
        
        s = encrypted_base64.strip()
        s += '=' * (-len(s) % 4)
        encrypted_data = base64.b64decode(s)
        
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
        
        return decrypted.decode('utf-8')
    except Exception as e:
        print(f"AES Decryption error: {e}")
        return base64_decode_iso(encrypted_base64)

class SelcukFlixScraper:
    def __init__(self):
        self.BASE_URL = 'https://selcukflix.co'
        self.manifest = {
            'id': 'community.selcukflix',
            'version': '1.0.0',
            'name': 'SelcukFlix',
            'description': 'Türkçe dizi ve film izleme platformu - SelcukFlix için Stremio eklentisi (Instruction Mode)',
            'logo': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRSUvIFqAlaBRC0QXNibBOpw-RjKhU6liBQ5-xATVp3S4uyEi2QGXzHXdEW0WvcgWABUw&usqp=CAU',
            'resources': ['catalog', 'meta', 'stream'],
            'types': ['movie', 'series'],
            'catalogs': [
                {'type': 'series', 'id': 'selcukflix_latest_episodes', 'name': 'Yeni Eklenen Bölümler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_new_series', 'name': 'Yeni Diziler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_korean', 'name': 'Kore Dizileri', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_turkish', 'name': 'Yerli Diziler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_aile', 'name': 'Aile', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_animasyon', 'name': 'Animasyon', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_aksiyon', 'name': 'Aksiyon', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_bilimkurgu', 'name': 'Bilim Kurgu', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_dram', 'name': 'Dram', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_fantastik', 'name': 'Fantastik', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_gerilim', 'name': 'Gerilim', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_gizem', 'name': 'Gizem', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_korku', 'name': 'Korku', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_komedi', 'name': 'Komedi', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_romantik', 'name': 'Romantik', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'selcukflix_search', 'name': 'Film Ara', 'extra': [{'name': 'search', 'isRequired': True}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'selcukflix_search_series', 'name': 'Dizi Ara', 'extra': [{'name': 'search', 'isRequired': True}, {'name': 'skip', 'isRequired': False}]}
            ],
            'idPrefixes': ['selcukflix']
        }
        
        self.CATEGORY_MAP = {
            'selcukflix_aile': '15',
            'selcukflix_animasyon': '17',
            'selcukflix_aksiyon': '9',
            'selcukflix_bilimkurgu': '5',
            'selcukflix_dram': '2',
            'selcukflix_fantastik': '12',
            'selcukflix_gerilim': '18',
            'selcukflix_gizem': '3',
            'selcukflix_korku': '8',
            'selcukflix_komedi': '4',
            'selcukflix_romantik': '7'
        }

    def get_enhanced_headers(self, referer=None, is_ajax=False):
        if referer is None:
            referer = self.BASE_URL
        headers = {
            'Accept': 'application/json, text/plain, */*' if is_ajax else 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0',
            'Sec-Fetch-Dest': 'empty' if is_ajax else 'document',
            'Sec-Fetch-Mode': 'cors' if is_ajax else 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'max-age=0'
        }
        if referer:
            headers['Referer'] = referer
        if is_ajax:
            headers['X-Requested-With'] = 'XMLHttpRequest'
        return headers

    def getManifest(self):
        return self.manifest

    async def handleCatalog(self, args):
        print('\n🎯 [SelcukFlix Catalog] Generating instructions...')
        catalogId = args.get('id')
        extra = args.get('extra', {})
        searchQuery = extra.get('search')
        skip = int(extra.get('skip', 0))
        page = (skip // 24) + 1
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))

        if catalogId in ['selcukflix_search', 'selcukflix_search_series'] and searchQuery:
            requestId = f"selcukflix-search-{catalogId}-{int(time.time()*1000)}-{randomId}"
            searchUrl = f"{self.BASE_URL}/api/bg/searchcontent?searchterm={urllib.parse.quote(searchQuery)}"
            return {
                'instructions': [{
                    'requestId': requestId,
                    'purpose': 'catalog-search',
                    'url': searchUrl,
                    'method': 'POST',
                    'headers': self.get_enhanced_headers(self.BASE_URL, True),
                    'metadata': {'catalogId': catalogId, 'hiddenweb': True}
                }]
            }

        if catalogId == 'selcukflix_latest_episodes':
            requestId = f"selcukflix-episodes-{int(time.time()*1000)}-{randomId}"
            return {
                'instructions': [{
                    'requestId': requestId,
                    'purpose': 'catalog-episodes',
                    'url': f"{self.BASE_URL}/tum-bolumler",
                    'method': 'GET',
                    'headers': self.get_enhanced_headers(self.BASE_URL, False),
                    'metadata': {'catalogId': catalogId, 'hiddenweb': True}
                }]
            }

        apiUrl = ''
        categoryId = self.CATEGORY_MAP.get(catalogId)

        if catalogId == 'selcukflix_turkish':
            apiUrl = f"{self.BASE_URL}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2024&imdbPointMin=5&imdbPointMax=10&categoryIdsComma=&countryIdsComma=29&orderType=date_desc&languageId=-1&currentPage={page}&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma="
        elif catalogId == 'selcukflix_korean':
            apiUrl = f"{self.BASE_URL}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2026&imdbPointMin=1&imdbPointMax=10&categoryIdsComma=&countryIdsComma=21&orderType=date_desc&languageId=-1&currentPage={page}&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma=KR"
        elif categoryId:
            apiUrl = f"{self.BASE_URL}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2026&imdbPointMin=1&imdbPointMax=10&categoryIdsComma={categoryId}&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage={page}&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma="
        else:
            apiUrl = f"{self.BASE_URL}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2026&imdbPointMin=1&imdbPointMax=10&categoryIdsComma=&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage={page}&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma="

        requestId = f"selcukflix-catalog-{catalogId}-{int(time.time()*1000)}-{randomId}"
        return {
            'instructions': [{
                'requestId': requestId,
                'purpose': 'catalog-api',
                'url': apiUrl,
                'method': 'POST',
                'headers': self.get_enhanced_headers(self.BASE_URL, True),
                'metadata': {'catalogId': catalogId, 'hiddenweb': True}
            }]
        }

    async def handleMeta(self, args):
        urlBase64 = args.get('id', '').replace('selcukflix:', '')
        url = base64_decode_safe(urlBase64)
        if url and not url.startswith('http'):
            url = f"{self.BASE_URL}{url}" if url.startswith('/') else f"{self.BASE_URL}/{url}"

        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        requestId = f"selcukflix-meta-{int(time.time()*1000)}-{randomId}"
        return {
            'instructions': [{
                'requestId': requestId,
                'purpose': 'meta',
                'url': url,
                'method': 'GET',
                'headers': self.get_enhanced_headers(self.BASE_URL, False),
                'metadata': {'hiddenweb': True}
            }]
        }

    async def handleStream(self, args):
        urlBase64 = args.get('id', '').replace('selcukflix:', '')
        url = base64_decode_safe(urlBase64)
        if url and not url.startswith('http'):
            url = f"{self.BASE_URL}{url}" if url.startswith('/') else f"{self.BASE_URL}/{url}"

        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        requestId = f"selcukflix-stream-{int(time.time()*1000)}-{randomId}"
        return {
            'instructions': [{
                'requestId': requestId,
                'purpose': 'stream',
                'url': url,
                'method': 'GET',
                'headers': self.get_enhanced_headers(self.BASE_URL, False),
                'metadata': {'hiddenweb': True}
            }]
        }

    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body', '')
        url = fetchResult.get('url', '')
        metadata = fetchResult.get('metadata', {})

        print(f"\n⚙️ [SelcukFlix Process] Purpose: {purpose}")

        is_bad_body = False
        if not body.strip():
            is_bad_body = True
        elif 'cloudflare' in body.lower() and ('challenge' in body.lower() or 'ray id' in body.lower() or 'attention required' in body.lower() or 'just a moment' in body.lower()):
            is_bad_body = True
        elif 'chrome-error' in body.lower():
            is_bad_body = True
        elif purpose in ['catalog-api', 'catalog-search'] and not body.strip().startswith('{'):
            is_bad_body = True

        if is_bad_body and url:
            print(f"⚠️ Bad body received from Flutter for {purpose}")

        if purpose == 'catalog-search':
            try:
                response = json.loads(body)
                if 'response' not in response:
                    return {'metas': []}

                decodedSearch = decrypt_selcukflix_data(response['response'])
                cleanedJson = re.sub(r'[\x00-\x1F\x7F]', ' ', decodedSearch)
                searchData = json.loads(cleanedJson)

                metas = []
                catalogId = metadata.get('catalogId')

                if 'result' in searchData and isinstance(searchData['result'], list):
                    for item in searchData['result']:
                        title = item.get('object_name') or item.get('title')
                        slug = item.get('used_slug') or item.get('slug')
                        poster = item.get('object_poster_url') or item.get('poster')
                        itemType = item.get('used_type') or item.get('type')

                        if not title or not slug: continue
                        if '/seri-filmler/' in slug: continue

                        fixedSlug = slug if slug.startswith('/') else f"/{slug}"
                        fullUrl = fixedSlug if fixedSlug.startswith('http') else f"{self.BASE_URL}{fixedSlug}"
                        mappedType = 'movie' if itemType == 'Movies' else 'series'

                        if catalogId == 'selcukflix_search' and mappedType != 'movie': continue
                        if catalogId == 'selcukflix_search_series' and mappedType != 'series': continue

                        meta_id = 'selcukflix:' + base64_encode_safe(fullUrl)
                        metas.append({
                            'id': meta_id,
                            'type': mappedType,
                            'name': title,
                            'poster': fix_poster_url(poster)
                        })

                return {'metas': metas}
            except Exception as e:
                print(f'❌ Search parsing error: {e}')
                return {'metas': []}

        if purpose == 'catalog-episodes':
            try:
                soup = BeautifulSoup(body, 'html.parser')
                instructions = []
                
                for elem in soup.select('div.col-span-3 a'):
                    h2 = elem.find('h2')
                    name = h2.text.strip() if h2 else None
                    ep_div = elem.select_one('div.opacity-80')
                    epName = ep_div.text.strip().replace('. Sezon ', 'x').replace('. Bölüm', '') if ep_div else ''
                    epHref = elem.get('href')
                    img = elem.select_one('div.image img')
                    posterUrl = img.get('src') if img else None

                    if name and epHref:
                        title = f"{name} - {epName}"
                        fixedHref = epHref if epHref.startswith('/') else f"/{epHref}"
                        fullUrl = fixedHref if fixedHref.startswith('http') else f"{self.BASE_URL}{fixedHref}"
                        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))

                        instructions.append({
                            'requestId': f"selcukflix-episode-detail-{int(time.time()*1000)}-{randomId}",
                            'purpose': 'episode-detail',
                            'url': fullUrl,
                            'method': 'GET',
                            'headers': self.get_enhanced_headers(self.BASE_URL, False),
                            'metadata': {
                                'hiddenweb': True,
                                'title': title,
                                'posterUrl': fix_poster_url(posterUrl)
                            }
                        })

                return {'instructions': instructions}
            except Exception as e:
                print(f'❌ Episodes parsing error: {e}')
                return {'metas': []}

        if purpose == 'episode-detail':
            try:
                soup = BeautifulSoup(body, 'html.parser')
                seriesHref = None
                poster_a = soup.select_one('div.poster a')
                if poster_a: seriesHref = poster_a.get('href')

                if not seriesHref:
                    for a in soup.find_all('a', href=True):
                        if '/dizi/' in a['href']:
                            seriesHref = a['href']
                            break

                if not seriesHref:
                    canonical = soup.select_one('link[rel="canonical"]')
                    if canonical and canonical.get('href'):
                        diziSlug = canonical.get('href').split('/')[-1].split('-')[0]
                        seriesHref = f"/dizi/{diziSlug}"

                if not seriesHref:
                    return {'metas': []}

                fixedHref = seriesHref if seriesHref.startswith('/') else f"/{seriesHref}"
                fullUrl = fixedHref if fixedHref.startswith('http') else f"{self.BASE_URL}{fixedHref}"
                meta_id = 'selcukflix:' + base64_encode_safe(fullUrl)

                return {
                    'metas': [{
                        'id': meta_id,
                        'type': 'series',
                        'name': metadata.get('title'),
                        'poster': metadata.get('posterUrl')
                    }]
                }
            except Exception as e:
                print(f'❌ Episode detail parsing error: {e}')
                return {'metas': []}

        if purpose == 'catalog-api':
            try:
                print(f"🔍 [catalog-api] Body length: {len(body)} First 100: {body[:100]}")
                response = json.loads(body)
                if 'response' not in response:
                    return {'metas': []}

                decodedData = decrypt_selcukflix_data(response['response'])
                cleanedJson = re.sub(r'[\x00-\x1F\x7F]', ' ', decodedData)
                mediaList = json.loads(cleanedJson)

                metas = []
                if 'result' in mediaList and isinstance(mediaList['result'], list):
                    for item in mediaList['result']:
                        title = item.get('original_title') or item.get('originalTitle')
                        slug = item.get('used_slug') or item.get('usedSlug')
                        poster = item.get('poster_url') or item.get('posterUrl')

                        if not title or not slug: continue

                        fixedSlug = slug if slug.startswith('/') else f"/{slug}"
                        fullUrl = fixedSlug if fixedSlug.startswith('http') else f"{self.BASE_URL}{fixedSlug}"
                        meta_id = 'selcukflix:' + base64_encode_safe(fullUrl)

                        metas.append({
                            'id': meta_id,
                            'type': 'series',
                            'name': title,
                            'poster': fix_poster_url(poster)
                        })

                return {'metas': metas}
            except Exception as e:
                print(f'❌ Catalog API parsing error: {e}')
                return {'metas': []}

        if purpose == 'meta':
            try:
                soup = BeautifulSoup(body, 'html.parser')
                scriptData = soup.select_one('script#__NEXT_DATA__')

                if not scriptData:
                    return {'meta': None}

                nextData = json.loads(scriptData.string)
                secureData = nextData.get('props', {}).get('pageProps', {}).get('secureData')

                if not secureData:
                    return {'meta': None}

                decodedJson = decrypt_selcukflix_data(secureData)
                cleanedJson = re.sub(r'[\x00-\x1F\x7F]', ' ', decodedJson)
                contentDetails = json.loads(cleanedJson)

                item = contentDetails.get('contentItem', {})
                relatedData = contentDetails.get('RelatedResults', {})

                title = item.get('original_title') or item.get('originalTitle')
                poster = fix_poster_url(item.get('poster_url') or item.get('posterUrl'))
                description = item.get('description', 'Açıklama mevcut değil')
                year = item.get('release_year') or item.get('releaseYear')
                tags = item.get('categories', '').split(',') if item.get('categories') else []
                rating = item.get('imdb_point') or item.get('imdbPoint')
                duration = item.get('total_minutes') or item.get('totalMinutes')

                actors = []
                movieCasts = relatedData.get('getMovieCastsById', {}).get('result', [])
                if movieCasts:
                    for cast in movieCasts:
                        if cast.get('name'): actors.append(cast['name'])

                trailer = None
                trailers = relatedData.get('getContentTrailers', {}).get('result', [])
                if trailers:
                    trailer = trailers[0].get('raw_url') or trailers[0].get('rawUrl')

                if 'getSerieSeasonAndEpisodes' in relatedData:
                    videos = []
                    seriesData = relatedData['getSerieSeasonAndEpisodes'].get('result', [])
                    for season in seriesData:
                        seasonNo = season.get('season_no') or season.get('seasonNo')
                        for episode in season.get('episodes', []):
                            epSlug = episode.get('used_slug') or episode.get('usedSlug')
                            epText = episode.get('episode_text') or episode.get('epText') or episode.get('ep_text')
                            epNo = episode.get('episode_no') or episode.get('episodeNo')
                            
                            if epSlug:
                                fixedSlug = epSlug if epSlug.startswith('/') else f"/{epSlug}"
                                epUrl = fixedSlug if fixedSlug.startswith('http') else f"{self.BASE_URL}{fixedSlug}"
                                videoId = 'selcukflix:' + base64_encode_safe(epUrl)
                                videos.append({
                                    'id': videoId,
                                    'title': epText or f"{seasonNo}. Sezon {epNo}. Bölüm",
                                    'season': seasonNo,
                                    'episode': epNo
                                })

                    meta = {
                        'id': 'selcukflix:' + base64_encode_safe(url),
                        'type': 'series',
                        'name': title,
                        'poster': poster,
                        'background': poster,
                        'description': description,
                        'releaseInfo': str(year) if year else None,
                        'imdbRating': str(rating) if rating else None,
                        'genres': tags if tags else None,
                        'cast': actors if actors else None,
                        'videos': videos
                    }
                    return {'meta': meta}
                else:
                    meta = {
                        'id': 'selcukflix:' + base64_encode_safe(url),
                        'type': 'movie',
                        'name': title,
                        'poster': poster,
                        'background': poster,
                        'description': description,
                        'releaseInfo': str(year) if year else None,
                        'imdbRating': str(rating) if rating else None,
                        'genres': tags if tags else None,
                        'runtime': f"{duration} dk" if duration else None,
                        'cast': actors if actors else None
                    }
                    return {'meta': meta}
            except Exception as e:
                print(f'❌ Meta parsing error: {e}')
                return {'meta': None}

        if purpose == 'stream':
            try:
                soup = BeautifulSoup(body, 'html.parser')
                scriptData = soup.select_one('script#__NEXT_DATA__')

                if not scriptData:
                    return {'streams': []}

                nextData = json.loads(scriptData.string)
                secureData = nextData.get('props', {}).get('pageProps', {}).get('secureData')

                if not secureData:
                    return {'streams': []}

                decodedJson = decrypt_selcukflix_data(secureData)
                cleanedJson = re.sub(r'[\x00-\x1F\x7F]', ' ', decodedJson)
                contentDetails = json.loads(cleanedJson)

                relatedData = contentDetails.get('RelatedResults', {})
                rawSources = []

                if '/dizi/' in url:
                    epSources = relatedData.get('getEpisodeSources', {}).get('result', [])
                    if epSources:
                        rawSources = epSources
                else:
                    movieParts = relatedData.get('getMoviePartsById', {}).get('result', [])
                    for part in movieParts:
                        partId = part.get('id')
                        sourceKey = f"getMoviePartSourcesById_{partId}"
                        sources = relatedData.get(sourceKey, {}).get('result', [])
                        if sources:
                            rawSources.extend(sources)

                if not rawSources:
                    return {'streams': []}

                instructions = []
                processedIframes = set()

                for source in rawSources:
                    sourceContent = source.get('source_content') or source.get('sourceContent')
                    if not sourceContent:
                        continue

                    soupSource = BeautifulSoup(sourceContent, 'html.parser')
                    iframe = soupSource.find('iframe')
                    iframeUrl = iframe.get('src') if iframe else None

                    if not iframeUrl:
                        continue

                    iframeUrl = iframeUrl if iframeUrl.startswith('http') else f"https:{iframeUrl}"
                    if 'sn.dplayer74.site' in iframeUrl:
                        iframeUrl = iframeUrl.replace('sn.dplayer74.site', 'sn.hotlinger.com')

                    if iframeUrl in processedIframes:
                        continue
                    processedIframes.add(iframeUrl)

                    randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                    requestId = f"selcukflix-extractor-{int(time.time()*1000)}-{randomId}"

                    instructions.append({
                        'requestId': requestId,
                        'purpose': 'video-extractor',
                        'url': iframeUrl,
                        'method': 'GET',
                        'headers': {
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Referer': self.BASE_URL + '/'
                        },
                        'metadata': {
                            'hiddenweb': True,
                            'originalUrl': url,
                            'extractorType': 'auto',
                            'iframeUrl': iframeUrl,
                            'languageName': source.get('language_name') or 'Bilinmeyen Dil',
                            'qualityName': source.get('quality_name') or '1080P',
                            
                        }
                    })

                if instructions:
                    return {'instructions': instructions}
                return {'streams': []}
            except Exception as e:
                print(f'❌ Stream parsing error: {e}')
                return {'streams': []}

        if purpose == 'video-extractor':
            try:
                streams = []
                extractorUrl = url.lower()

                if 'cloudflare' in body.lower() or 'attention required' in body.lower() or 'just a moment' in body.lower() or not body.strip() or 'chrome-error' in body.lower():
                    print(f"⚠️ Bad body received from Flutter for video extractor")

                if any(x in extractorUrl for x in ['contentx.me', 'hotlinger.com', 'pichive.online', 'playru.net', 'dplayer82.site', 'dplayer74.site']):
                    
                    iframeSubtitles = []
                    subUrls = set()
                    audioTracks = []
                    audioUrls = set()
                    
                    tracks_match = re.search(r'tracks\s*:\s*(\[[\s\S]*?\])\s*[,}]', body)
                    if tracks_match:
                        try:
                            tracksData = json.loads(tracks_match.group(1))
                            for track in tracksData:
                                if track.get('kind') in ['captions', 'subtitles'] and track.get('file'):
                                    subUrl = track['file'].replace('\\/', '/').replace('\\u0026', '&').replace('\\', '')
                                    subLang = (track.get('label') or track.get('language') or 'Türkçe').replace('\\u0131', 'ı').replace('\\u0130', 'İ').replace('\\u00fc', 'ü').replace('\\u00e7', 'ç').replace('\\u011f', 'ğ').replace('\\u015f', 'ş')
                                    
                                    keywords = ['tur', 'tr', 'türkçe', 'turkce']
                                    language = 'Turkish Forced' if 'Forced' in subLang else ('Turkish' if any(k in subLang.lower() for k in keywords) else subLang)
                                    
                                    if subUrl not in subUrls:
                                        subUrls.add(subUrl)
                                        iframeSubtitles.append({
                                            'id': language.lower().replace(' ', '_'),
                                            'url': subUrl if subUrl.startswith('http') else f"https:{subUrl}",
                                            'lang': language
                                        })
                                elif track.get('kind') in ['audio', 'audiotrack'] and track.get('file'):
                                    audioUrl = track['file'].replace('\\/', '/').replace('\\u0026', '&').replace('\\', '')
                                    audioLang = (track.get('label') or track.get('language') or 'Orijinal').replace('\\u0131', 'ı').replace('\\u0130', 'İ').replace('\\u00fc', 'ü').replace('\\u00e7', 'ç').replace('\\u011f', 'ğ').replace('\\u015f', 'ş')
                                    
                                    if audioUrl not in audioUrls:
                                        audioUrls.add(audioUrl)
                                        audioTracks.append({
                                            'id': audioLang.lower().replace(' ', '_'),
                                            'url': audioUrl if audioUrl.startswith('http') else f"https:{audioUrl}",
                                            'lang': audioLang
                                        })
                        except Exception as e:
                            print(f"⚠️  Tracks parse error: {e}")

                    if not iframeSubtitles:
                        subRegex = r'"file":"((?:\\\\"|[^"])+)"(?:,"kind":"captions")?,"label":"((?:\\\\"|[^"])+)"'
                        for match in re.finditer(subRegex, body):
                            subUrlRaw = match.group(1)
                            subLangRaw = match.group(2)
                            
                            subUrl = subUrlRaw.replace('\\/', '/').replace('\\u0026', '&').replace('\\', '')
                            subLang = subLangRaw.replace('\\u0131', 'ı').replace('\\u0130', 'İ').replace('\\u00fc', 'ü').replace('\\u00e7', 'ç').replace('\\u011f', 'ğ').replace('\\u015f', 'ş')
                            
                            keywords = ['tur', 'tr', 'türkçe', 'turkce']
                            language = 'Turkish Forced' if 'Forced' in subLang else ('Turkish' if any(k in subLang.lower() for k in keywords) else subLang)
                            
                            if subUrl not in subUrls:
                                subUrls.add(subUrl)
                                iframeSubtitles.append({
                                    'id': language.lower().replace(' ', '_'),
                                    'url': subUrl if subUrl.startswith('http') else f"https:{subUrl}",
                                    'lang': language
                                })

                    openPlayerMatch = re.search(r"window\.openPlayer\('([^']+)'", body)
                    
                    prefetchedMatch = re.search(r'_prefetchedSource:\s*(\{.*?\n\s*\})', body, re.DOTALL)
                    if not prefetchedMatch:
                        prefetchedMatch = re.search(r'_prefetchedSource:\s*(\{.*?\})', body)
                    
                    if prefetchedMatch:
                        try:
                            idx = body.find('_prefetchedSource:')
                            if idx != -1:
                                p_body = body[idx + len('_prefetchedSource:'):].strip()
                                brace_count = 0
                                end_idx = -1
                                for i, char in enumerate(p_body):
                                    if char == '{':
                                        brace_count += 1
                                    elif char == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            end_idx = i
                                            break
                                if end_idx != -1:
                                    json_str = p_body[:end_idx+1]
                                    data = json.loads(json_str)
                                    for item in data.get('playlist', []):
                                        for source in item.get('sources', []):
                                            file_url = source.get('file')
                                            if file_url:
                                                if file_url.startswith('/'):
                                                    parsed_url = urllib.parse.urlparse(url)
                                                    domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                                                    file_url = f"{domain}{file_url}"
                                                streams.append({
                                                    'name': metadata.get('languageName') or 'Pichive',
                                                    'title': f"{metadata.get('qualityName') or 'Auto'} (Pichive)",
                                                    'url': file_url,
                                                    'type': 'm3u8',
                                                    'behaviorHints': {
                                                        'notWebReady': False,
                                                        'proxyHeaders': {
                                                            'request': {
                                                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                                                'Referer': url,
                                                                'Origin': f"{urllib.parse.urlparse(url).scheme}://{urllib.parse.urlparse(url).netloc}"
                                                            }
                                                        }
                                                    },
                                                    'subtitles': iframeSubtitles,
                                                    'audioTracks': audioTracks
                                                })
                        except Exception as e:
                            print(f"⚠️ _prefetchedSource parse error: {e}")

                    if openPlayerMatch:
                        iExtract = openPlayerMatch.group(1)
                        parsed_url = urllib.parse.urlparse(url)
                        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        sourceUrl = f"{domain}/source2.php?v={iExtract}"

                        dublajMatch = re.search(r'''","([^']+)","Türkçe"''', body)
                        iDublaj = dublajMatch.group(1) if dublajMatch else None

                        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                        return {
                            'instructions': [{
                                'requestId': f"selcukflix-contentx-source-{int(time.time()*1000)}-{randomId}",
                                'purpose': 'contentx-source',
                                'url': sourceUrl,
                                'method': 'GET',
                                'headers': {
                                    'Accept': 'application/json, text/plain, */*',
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                    'Referer': url,
                                    'Origin': domain
                                },
                                'metadata': {
                                    'hiddenweb': True,
                                    'originalUrl': metadata.get('originalUrl') or url,
                                    'iframeUrl': url,
                                    'extractorName': 'ContentX',
                                    'iframeSubtitles': iframeSubtitles,
                                    'audioTracks': audioTracks,
                                    'iDublaj': iDublaj,
                                    'domain': domain,
                                    'languageName': metadata.get('languageName'),
                                    'qualityName': metadata.get('qualityName'),
                                   
                                }
                            }]
                        }

                if 'rapidvid.net' in extractorUrl:
                    avMatch = re.search(r"file:\s*av\('([^']+)'\)", body)
                    if avMatch:
                        decrypted = decode_av(avMatch.group(1))
                        streams.append({
                            'name': 'RapidVid',
                            'title': 'RapidVid',
                            'url': decrypted,
                            'type': 'm3u8',
                            'behaviorHints': {'notWebReady': False}
                        })
                
                if 'vidmoxy.com' in extractorUrl:
                    eeMatch = re.search(r'file\s*:\s*EE\.dd\("([^"]+)"', body)
                    if eeMatch:
                        decoded = decode_ee(eeMatch.group(1))
                        streams.append({
                            'name': 'VidMoxy',
                            'title': 'VidMoxy',
                            'url': decoded,
                            'type': 'm3u8',
                            'behaviorHints': {'notWebReady': False}
                        })
                
                if 'vidmoly.to' in extractorUrl or 'vidmoly.net' in extractorUrl:
                    m3uMatches = re.findall(r'file\s*:\s*"([^"]+\.m3u8[^"]*)"', body)
                    for i, m in enumerate(m3uMatches):
                        streams.append({
                            'name': f'VidMoly {i+1}' if len(m3uMatches) > 1 else 'VidMoly',
                            'title': f'VidMoly {i+1}' if len(m3uMatches) > 1 else 'VidMoly',
                            'url': m,
                            'type': 'm3u8',
                            'behaviorHints': {'notWebReady': False}
                        })

                if 'trstx.org' in extractorUrl or 'sobreatsesuyp.com' in extractorUrl:
                    fileMatch = re.search(r'file":"([^"]+)"', body)
                    if fileMatch:
                        fileUrl = fileMatch.group(1).replace('\\', '')
                        parsed_url = urllib.parse.urlparse(url)
                        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        postUrl = f"{domain}/{fileUrl}"
                        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                        return {
                            'instructions': [{
                                'requestId': f"selcukflix-trstx-post-{int(time.time()*1000)}-{randomId}",
                                'purpose': 'trstx-post',
                                'url': postUrl,
                                'method': 'POST',
                                'headers': {
                                    'Accept': 'application/json, text/plain, */*',
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                    'Referer': url,
                                    'Content-Type': 'application/x-www-form-urlencoded'
                                },
                                'metadata': {
                                    'hiddenweb': True,
                                    'originalUrl': url,
                                    'extractorName': 'TRsTX' if 'trstx' in extractorUrl else 'Sobreatsesuyp',
                                    
                                }
                            }]
                        }
                        
                if 'turkeyplayer.com' in extractorUrl:
                    fileMatch = re.search(r'"file":"([^"]+)"', body)
                    if fileMatch:
                        rawM3u = fileMatch.group(1).replace('\\', '')
                        fixM3u = rawM3u.replace('thumbnails.vtt', 'master.txt')
                        titleMatch = re.search(r'"title":"([^"]*)"', body)
                        title = titleMatch.group(1) if titleMatch else ''
                        lang = 'Altyazılı' if 'SUB' in title else ('Dublaj' if 'DUB' in title else '')
                        name = f"TurkeyPlayer {lang}".strip()
                        streams.append({
                            'name': name,
                            'title': name,
                            'url': fixM3u,
                            'type': 'm3u8',
                            'behaviorHints': {
                                'notWebReady': False,
                                'headers': {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0',
                                    'Referer': url
                                }
                            }
                        })
                        
                if 'turbo.imgz.me' in extractorUrl:
                    fileMatch = re.search(r'file:\s*"([^"]+)"', body)
                    if fileMatch:
                        streams.append({
                            'name': 'TurboImgz',
                            'title': 'TurboImgz',
                            'url': fileMatch.group(1),
                            'type': 'm3u8',
                            'behaviorHints': {'notWebReady': False}
                        })

                # Try generic m3u8
                m3u_urls = set()
                
                # Look for file: "..." or file: '...'
                for match in re.finditer(r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body, re.IGNORECASE):
                    m3u_urls.add(match.group(1).replace('\\/', '/'))
                
                # General fallback: look for any .m3u8 URL in the body
                if not m3u_urls:
                    for match in re.finditer(r'(https?://[^\s"\'<>]+?\.m3u8[^\s"\'<>]*)', body, re.IGNORECASE):
                        m3u_urls.add(match.group(1).replace('\\/', '/'))

                for i, m3u_url in enumerate(m3u_urls):
                    streams.append({
                        'name': f'SelcukFlix {i+1}' if len(m3u_urls) > 1 else 'SelcukFlix',
                        'title': f'SelcukFlix {i+1}' if len(m3u_urls) > 1 else 'SelcukFlix',
                        'url': m3u_url,
                        'type': 'm3u8',
                        'behaviorHints': {'notWebReady': False}
                    })
                return {'streams': streams}
            except Exception as e:
                print(f'❌ Video extractor error: {e}')
                return {'streams': []}

        if purpose == 'contentx-source':
            try:
                m3uLink = None
                try:
                    jsonData = json.loads(body)
                    if 'playlist' in jsonData and len(jsonData['playlist']) > 0 and 'sources' in jsonData['playlist'][0] and len(jsonData['playlist'][0]['sources']) > 0:
                        m3uLink = jsonData['playlist'][0]['sources'][0].get('file')
                    elif 'file' in jsonData:
                        m3uLink = jsonData['file']
                except:
                    fileMatch = re.search(r'"file":"([^"]+)"', body)
                    if fileMatch: m3uLink = fileMatch.group(1).replace('\\', '')

                if m3uLink:
                    extractorName = metadata.get('extractorName', 'ContentX')
                    subtitlesForMetadata = metadata.get('iframeSubtitles', [])
                    
                    try:
                        jsonData = json.loads(body)
                        tracks = jsonData.get('playlist', [{}])[0].get('tracks', [])
                        subUrls = {s['url'] for s in subtitlesForMetadata}
                        audioTracksForMetadata = metadata.get('audioTracks', []) or []
                        audioUrls = {a['url'] for a in audioTracksForMetadata}
                        
                        for track in tracks:
                            if track.get('kind') in ['captions', 'subtitles'] and track.get('file') and track.get('label'):
                                subUrl = track['file'].replace('\\/', '/').replace('\\u0026', '&').replace('\\', '')
                                subLangRaw = track['label']
                                subLang = subLangRaw.replace('\\u0131', 'ı').replace('\\u0130', 'İ').replace('\\u00fc', 'ü').replace('\\u00e7', 'ç').replace('\\u011f', 'ğ').replace('\\u015f', 'ş')
                                
                                keywords = ['tur', 'tr', 'türkçe', 'turkce']
                                language = 'Turkish Forced' if 'Forced' in subLang else ('Turkish' if any(k in subLang.lower() for k in keywords) else subLang)
                                finalSubUrl = subUrl if subUrl.startswith('http') else f"https:{subUrl}"
                                
                                if finalSubUrl not in subUrls:
                                    subUrls.add(finalSubUrl)
                                    subtitlesForMetadata.append({
                                        'id': language.lower().replace(' ', '_'),
                                        'url': finalSubUrl,
                                        'lang': language
                                    })
                            elif track.get('kind') in ['audio', 'audiotrack'] and track.get('file'):
                                audioUrl = track['file'].replace('\\/', '/').replace('\\u0026', '&').replace('\\', '')
                                audioLangRaw = track.get('label') or track.get('language') or 'Orijinal'
                                audioLang = audioLangRaw.replace('\\u0131', 'ı').replace('\\u0130', 'İ').replace('\\u00fc', 'ü').replace('\\u00e7', 'ç').replace('\\u011f', 'ğ').replace('\\u015f', 'ş')
                                finalAudioUrl = audioUrl if audioUrl.startswith('http') else f"https:{audioUrl}"
                                
                                if finalAudioUrl not in audioUrls:
                                    audioUrls.add(finalAudioUrl)
                                    audioTracksForMetadata.append({
                                        'id': audioLang.lower().replace(' ', '_'),
                                        'url': finalAudioUrl,
                                        'lang': audioLang
                                    })
                        metadata['audioTracks'] = audioTracksForMetadata
                    except: pass
                    
                    if 'm.php' in m3uLink:
                        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                        return {
                            'instructions': [{
                                'requestId': f"selcukflix-m3u8-resolve-{int(time.time()*1000)}-{randomId}",
                                'purpose': 'm3u8-resolve',
                                'url': m3uLink,
                                'method': 'GET',
                                'headers': {
                                    'Accept': '*/*',
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                    'Referer': metadata.get('iframeUrl') or url,
                                    'Origin': urllib.parse.urlparse(metadata.get('iframeUrl') or url).scheme + "://" + urllib.parse.urlparse(metadata.get('iframeUrl') or url).netloc
                                },
                                'metadata': {
                                    'hiddenweb': True,
                                    'originalUrl': metadata.get('originalUrl'),
                                    'iframeUrl': metadata.get('iframeUrl') or url,
                                    'extractorName': extractorName,
                                    'proxyUrl': m3uLink,
                                    'subtitles': subtitlesForMetadata,
                                    'audioTracks': metadata.get('audioTracks') or [],
                                    'languageName': metadata.get('languageName'),
                                    'qualityName': metadata.get('qualityName'),
                                    
                                }
                            }]
                        }

                    parsed_m3u = urllib.parse.urlparse(m3uLink)
                    m3u8Origin = f"{parsed_m3u.scheme}://{parsed_m3u.netloc}"
                    iframeReferer = metadata.get('iframeUrl') or url

                    langTag = f" - {metadata.get('languageName')}" if metadata.get('languageName') else ''
                    titleName = f"{extractorName}{langTag}"

                    streamObj = {
                        'name': extractorName,
                        'title': titleName,
                        'url': m3uLink,
                        'behaviorHints': {
                            'notWebReady': False,
                            'proxyHeaders': {
                                'request': {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                    'Referer': iframeReferer,
                                    'Origin': m3u8Origin
                                }
                            }
                        }
                    }

                    if subtitlesForMetadata:
                        streamObj['subtitles'] = subtitlesForMetadata

                    iDublaj = metadata.get('iDublaj')
                    if iDublaj:
                        domain = metadata.get('domain') or urllib.parse.urlparse(metadata.get('iframeUrl') or url).scheme + "://" + urllib.parse.urlparse(metadata.get('iframeUrl') or url).netloc
                        dublajUrl = f"{domain}/source2.php?v={iDublaj}"
                        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                        return {
                            'streams': [streamObj],
                            'instructions': [{
                                'requestId': f"selcukflix-dublaj-source-{int(time.time()*1000)}-{randomId}",
                                'purpose': 'contentx-dublaj',
                                'url': dublajUrl,
                                'method': 'GET',
                                'headers': {
                                    'Accept': 'application/json, text/plain, */*',
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                    'Referer': metadata.get('iframeUrl') or url,
                                    'Origin': domain
                                },
                                'metadata': {
                                    'hiddenweb': True,
                                    'originalUrl': metadata.get('originalUrl'),
                                    'iframeUrl': metadata.get('iframeUrl') or url,
                                    'extractorName': extractorName,
                                    'subtitles': subtitlesForMetadata,
                                    'audioTracks': metadata.get('audioTracks') or [],
                                    'languageName': metadata.get('languageName'),
                                    'qualityName': metadata.get('qualityName'),
                                 
                                }
                            }]
                        }

                    return {'streams': [streamObj]}
                return {'streams': []}
            except Exception as e:
                print(f'❌ ContentX source parsing error: {e}')
                return {'streams': []}
                
        if purpose == 'contentx-dublaj':
            try:
                dublajM3u = None
                try:
                    jsonData = json.loads(body)
                    if 'playlist' in jsonData and len(jsonData['playlist']) > 0 and 'sources' in jsonData['playlist'][0] and len(jsonData['playlist'][0]['sources']) > 0:
                        dublajM3u = jsonData['playlist'][0]['sources'][0].get('file')
                    elif 'file' in jsonData:
                        dublajM3u = jsonData['file']
                except:
                    fileMatch = re.search(r'"file":"([^"]+)"', body)
                    if fileMatch: dublajM3u = fileMatch.group(1).replace('\\', '')
                    
                if dublajM3u:
                    extractorName = metadata.get('extractorName', 'ContentX')
                    if 'm.php' in dublajM3u:
                        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                        return {
                            'instructions': [{
                                'requestId': f"selcukflix-dublaj-m3u8-resolve-{int(time.time()*1000)}-{randomId}",
                                'purpose': 'dublaj-m3u8-resolve',
                                'url': dublajM3u,
                                'method': 'GET',
                                'headers': {
                                    'Accept': '*/*',
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                    'Referer': metadata.get('iframeUrl') or url,
                                    'Origin': urllib.parse.urlparse(metadata.get('iframeUrl') or url).scheme + "://" + urllib.parse.urlparse(metadata.get('iframeUrl') or url).netloc
                                },
                                'metadata': {
                                    'hiddenweb': True,
                                    'originalUrl': metadata.get('originalUrl'),
                                    'iframeUrl': metadata.get('iframeUrl') or url,
                                    'extractorName': extractorName,
                                    'proxyUrl': dublajM3u,
                                    'subtitles': metadata.get('subtitles') or [],
                                    'audioTracks': metadata.get('audioTracks') or [],
                                    'isDublaj': True,
                                    'languageName': metadata.get('languageName'),
                                    'qualityName': metadata.get('qualityName'),
                                    
                                }
                            }]
                        }

                    parsed_m3u = urllib.parse.urlparse(dublajM3u)
                    m3u8Origin = f"{parsed_m3u.scheme}://{parsed_m3u.netloc}"
                    iframeReferer = metadata.get('iframeUrl') or url

                    streamObj = {
                        'name': f"{extractorName} - Türkçe Dublaj",
                        'title': f"{extractorName} - Türkçe Dublaj",
                        'url': dublajM3u,
                        'behaviorHints': {
                            'notWebReady': False,
                            'proxyHeaders': {
                                'request': {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                    'Referer': iframeReferer,
                                    'Origin': m3u8Origin
                                }
                            }
                        }
                    }
                    if metadata.get('subtitles'):
                        streamObj['subtitles'] = metadata.get('subtitles')
                    if metadata.get('audioTracks'):
                        streamObj['audioTracks'] = metadata.get('audioTracks')
                    return {'streams': [streamObj]}
                return {'streams': []}
            except Exception as e:
                print(f'❌ ContentX dublaj parsing error: {e}')
                return {'streams': []}
                
        if purpose in ['m3u8-resolve', 'dublaj-m3u8-resolve']:
            try:
                realM3u8Url = None
                redirectUrl = body.strip()
                
                if redirectUrl and redirectUrl.startswith('http') and not ('<html' in redirectUrl.lower()):
                    realM3u8Url = redirectUrl
                elif '#EXTM3U' in body or '#EXT-X-STREAM-INF' in body:
                    realM3u8Url = metadata.get('proxyUrl') or url
                else:
                    try:
                        jsonData = json.loads(body)
                        if 'url' in jsonData:
                            realM3u8Url = jsonData['url']
                        elif 'file' in jsonData:
                            realM3u8Url = jsonData['file']
                        elif 'source' in jsonData:
                            realM3u8Url = jsonData['source']
                    except:
                        pass

                if realM3u8Url:
                    extractorName = metadata.get('extractorName', 'ContentX')
                    if metadata.get('isDublaj') or purpose == 'dublaj-m3u8-resolve':
                        name = f"{extractorName} - Türkçe Dublaj"
                    else:
                        langTag = f" - {metadata.get('languageName')}" if metadata.get('languageName') else ''
                        name = f"{extractorName}{langTag}"
                    
                    parsed_m3u = urllib.parse.urlparse(realM3u8Url)
                    m3u8Origin = f"{parsed_m3u.scheme}://{parsed_m3u.netloc}"
                    iframeReferer = metadata.get('iframeUrl') or url
                    
                    streamObj = {
                        'name': name,
                        'title': name,
                        'url': realM3u8Url,
                        'behaviorHints': {
                            'notWebReady': False,
                            'proxyHeaders': {
                                'request': {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                    'Referer': iframeReferer,
                                    'Origin': m3u8Origin
                                }
                            }
                        }
                    }
                    if metadata.get('subtitles'):
                        streamObj['subtitles'] = metadata.get('subtitles')
                    if metadata.get('audioTracks'):
                        streamObj['audioTracks'] = metadata.get('audioTracks')
                    return {'streams': [streamObj]}
                return {'streams': []}
            except Exception as e:
                print(f'❌ M3U8 resolve error: {e}')
                return {'streams': []}

        if purpose == 'trstx-post':
            try:
                data = json.loads(body)
                streams = []
                extractorName = metadata.get('extractorName', 'TRsTX')
                videoData = data[1:] if len(data) > 1 else []
                parsed_url = urllib.parse.urlparse(url)
                domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                
                for item in videoData:
                    if item.get('file') and item.get('title'):
                        fileUrl = f"{domain}/playlist/{item['file'][1:]}.txt"
                        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                        return {
                            'instructions': [{
                                'requestId': f"selcukflix-trstx-video-{int(time.time()*1000)}-{randomId}",
                                'purpose': 'trstx-video',
                                'url': fileUrl,
                                'method': 'POST',
                                'headers': {
                                    'Accept': '*/*',
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                    'Referer': metadata.get('originalUrl'),
                                    'Content-Type': 'application/x-www-form-urlencoded'
                                },
                                'metadata': {
                                    'hiddenweb': True,
                                    'title': item['title'],
                                    'extractorName': extractorName,
                                   
                                }
                            }]
                        }
                return {'streams': streams}
            except Exception as e:
                print(f'❌ TRsTX post parsing error: {e}')
                return {'streams': []}

        if purpose == 'trstx-video':
            try:
                m3uLink = body.strip()
                title = metadata.get('title', 'HD')
                extractorName = metadata.get('extractorName', 'TRsTX')
                return {
                    'streams': [{
                        'name': f"{extractorName} - {title}",
                        'title': f"{extractorName} - {title}",
                        'url': m3uLink,
                        'type': 'm3u8',
                        'behaviorHints': {'notWebReady': False}
                    }]
                }
            except Exception as e:
                print(f'❌ TRsTX video parsing error: {e}')
                return {'streams': []}

        return {'ok': True}
