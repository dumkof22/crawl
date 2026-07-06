import base64
import json
import urllib.parse
import random
import time
import hashlib
from bs4 import BeautifulSoup

def cryptojs_decrypt(password, cipher_text):
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import padding
        
        ct_bytes = base64.b64decode(cipher_text)
        salt_bytes = ct_bytes[8:16]
        cipher_text_bytes = ct_bytes[16:]

        key_size = 32
        iv_size = 16

        password_bytes = password.encode('utf-8')
        derived_bytes = evp_kdf(password_bytes, salt_bytes, key_size + iv_size)

        key = derived_bytes[:key_size]
        iv = derived_bytes[key_size:key_size + iv_size]

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        decrypted_padded = decryptor.update(cipher_text_bytes) + decryptor.finalize()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
        
        return decrypted.decode('utf-8')
    except Exception as e:
        print(f"❌ CryptoJS decrypt error: {e}")
        return None

def evp_kdf(password, salt, key_size):
    md5_hashes = []
    digest = b''
    while len(b''.join(md5_hashes)) < key_size:
        hash_obj = hashlib.md5()
        hash_obj.update(digest)
        hash_obj.update(password)
        hash_obj.update(salt)
        digest = hash_obj.digest()
        md5_hashes.append(digest)
    return b''.join(md5_hashes)[:key_size]

def add_wmode_opaque(url):
    if '/player/king/king.php' in url:
        return url.replace('king.php?v=', 'king.php?wmode=opaque&v=')
    elif '/player/moly/moly.php' in url:
        return url.replace('moly.php?h=', 'moly.php?wmode=opaque&h=')
    elif '/player/haydi.php' in url:
        return url.replace('haydi.php?v=', 'haydi.php?wmode=opaque&v=')
    return url

class DiziBoxScraper:
    def __init__(self):
        self.BASE_URL = 'https://www.dizibox.live'
        self.manifest = {
            'id': 'community.dizibox',
            'version': '2.0.0',
            'name': 'DiziBox',
            'description': 'Türkçe dizi izleme platformu - DiziBox için Stremio eklentisi (Instruction Mode)',
            'logo': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTy_DY_ss3ztVcluDRxvnc45u9o0labczkN4GXDo_fYs12zD_l9ylx5PhK71d1hzSAnDQ&usqp=CAU',
            'resources': ['catalog', 'meta', 'stream'],
            'types': ['movie', 'series'],
            'catalogs': [
                {'type': 'series', 'id': 'dizibox_new', 'name': 'Son Eklenenler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizibox_yerli', 'name': 'Yerli Diziler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizibox_archive', 'name': 'Dizi Arşivi', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizibox_action', 'name': 'Aksiyon', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizibox_drama', 'name': 'Drama', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizibox_comedy', 'name': 'Komedi', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizibox_scifi', 'name': 'Bilimkurgu', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizibox_thriller', 'name': 'Gerilim', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizibox_fantasy', 'name': 'Fantastik', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizibox_crime', 'name': 'Suç', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'dizibox_search', 'name': 'Dizi Ara', 'extra': [{'name': 'search', 'isRequired': True}]},
                {'type': 'movie', 'id': 'dizibox_movie_search', 'name': 'Film Ara', 'extra': [{'name': 'search', 'isRequired': True}]}
            ],
            'idPrefixes': ['dizibox']
        }
        self.DIZIBOX_COOKIES = {
            'LockUser': 'true',
            'isTrustedUser': 'true',
            'dbxu': '1743289650198'
        }
        self.CATALOG_URLS = {
            'dizibox_new': f"{self.BASE_URL}/page/SAYFA/",
            'dizibox_yerli': f"{self.BASE_URL}/ulke/turkiye/page/SAYFA/",
            'dizibox_archive': f"{self.BASE_URL}/dizi-arsivi/page/SAYFA/",
            'dizibox_action': f"{self.BASE_URL}/tur/aksiyon/page/SAYFA/",
            'dizibox_drama': f"{self.BASE_URL}/tur/drama/page/SAYFA/",
            'dizibox_comedy': f"{self.BASE_URL}/tur/komedi/page/SAYFA/",
            'dizibox_scifi': f"{self.BASE_URL}/tur/bilimkurgu/page/SAYFA/",
            'dizibox_thriller': f"{self.BASE_URL}/tur/gerilim/page/SAYFA/",
            'dizibox_fantasy': f"{self.BASE_URL}/tur/fantastik/page/SAYFA/",
            'dizibox_crime': f"{self.BASE_URL}/tur/suc/page/SAYFA/"
        }

    def get_default_headers(self, referer=None):
        if not referer: referer = self.BASE_URL
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': referer
        }

    def getManifest(self):
        return self.manifest

    async def handleCatalog(self, args):
        catalogId = args.get('id')
        extra = args.get('extra', {})
        searchQuery = extra.get('search')
        skip = int(extra.get('skip', '0'))
        page = (skip // 20) + 1
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))

        if catalogId == 'dizibox_search':
            if not searchQuery: return {'metas': []}
            return {
                'instructions': [{
                    'requestId': f"dizibox-search-{int(time.time()*1000)}-{randomId}",
                    'purpose': 'catalog-search',
                    'url': f"{self.BASE_URL}/?s={urllib.parse.quote(searchQuery)}",
                    'method': 'GET',
                    'headers': self.get_default_headers(self.BASE_URL),
                    'metadata': {'catalogId': catalogId, 'hiddenweb': True}
                }]
            }

        url = self.CATALOG_URLS.get(catalogId)
        if not url: return {'instructions': []}
        
        url = url.replace('SAYFA', str(page))

        return {
            'instructions': [{
                'requestId': f"dizibox-catalog-{catalogId}-{int(time.time()*1000)}-{randomId}",
                'purpose': 'catalog',
                'url': url,
                'method': 'GET',
                'headers': self.get_default_headers(self.BASE_URL),
                'metadata': {'catalogId': catalogId, 'hiddenweb': True}
            }]
        }

    async def handleMeta(self, args):
        urlBase64 = args.get('id', '').replace('dizibox:', '')
        urlBase64 += '=' * (-len(urlBase64) % 4)
        url = base64.b64decode(urlBase64).decode('utf-8')
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        return {
            'instructions': [{
                'requestId': f"dizibox-meta-{int(time.time()*1000)}-{randomId}",
                'purpose': 'meta',
                'url': url,
                'method': 'GET',
                'headers': self.get_default_headers(self.BASE_URL),
                'metadata': {'hiddenweb': True}
            }]
        }

    async def handleStream(self, args):
        urlBase64 = args.get('id', '').replace('dizibox:', '')
        urlBase64 += '=' * (-len(urlBase64) % 4)
        url = base64.b64decode(urlBase64).decode('utf-8')
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        return {
            'instructions': [{
                'requestId': f"dizibox-stream-{int(time.time()*1000)}-{randomId}",
                'purpose': 'stream',
                'url': url,
                'method': 'GET',
                'headers': self.get_default_headers(url),
                'metadata': {'hiddenweb': True}
            }]
        }

    def parse_series_item(self, soup, elem):
        """article elementinden dizi bilgisi çıkar"""
        try:
            a_tag = elem.find('a')
            if not a_tag: return None
            href = a_tag.get('href')
            if not href: return None
            
            # Sadece /diziler/ linklerini kabul et (bölüm linkleri değil)
            if '/diziler/' not in href:
                return None
            
            # Başlığı çeşitli yerlerden bulmaya çalış
            title = None
            # 1. poster-title (tür sayfaları: a.poster-title)
            title_el = elem.select_one('a.poster-title')
            if title_el:
                title = title_el.text.strip()
            # 2. post-title (arşiv/arama sayfaları)
            if not title:
                title_el = elem.select_one('div.post-title a, .post-title a, .post-title')
                if title_el:
                    title = title_el.text.strip()
            # 3. figcaption içinde
            if not title:
                fig_title = elem.select_one('figcaption .post-title, .thumbnail-figcaption .post-title, figcaption a')
                if fig_title:
                    title = fig_title.text.strip()
            # 4. h2/h3/title attr
            if not title:
                title_el = elem.select_one('h2 a, h3 a, .title a')
                if title_el:
                    title = title_el.text.strip()
            # 5. a tag'inin title attribute'u
            if not title:
                title = a_tag.get('title', '').replace(' izle', '').strip()
            # 6. a tag text
            if not title:
                title = a_tag.text.strip()
            if not title:
                return None
            
            # Başlıktan " izle" suffix'ini kaldır
            import re
            title = re.sub(r'\s+izle$', '', title).strip()
            
            fullUrl = href if href.startswith('http') else f"{self.BASE_URL}{href}"
            
            # Poster resmi bul - birden fazla img olabilir, en uygununu seç
            posterUrl = None
            # Önce figure-link içindeki afis (katalog sayfaları)
            img = elem.select_one('a.figure-link img.afis')
            if not img:
                img = elem.select_one('img.afis')
            if not img:
                img = elem.select_one('img.main-cover')
            if not img:
                img = elem.select_one('img.wp-post-image')
            if not img:
                img = elem.find('img')
            if img:
                # data-src öncelikli (src genelde base64 placeholder oluyor)
                candidate = img.get('data-src') or img.get('data-lazy-src') or img.get('src')
                if candidate and not candidate.startswith('data:'):
                    posterUrl = candidate
                elif candidate and candidate.startswith('data:'):
                    # Tüm attribute'ları kontrol et
                    for attr in ['data-src', 'data-lazy-src', 'srcset']:
                        val = img.get(attr)
                        if val and not val.startswith('data:'):
                            posterUrl = val.split(',')[0].strip().split(' ')[0]
                            break
            
            # Background image fallback
            if not posterUrl:
                fig = elem.select_one('figure, .thumbnail, .poster')
                if fig and fig.get('style'):
                    bg_match = re.search(r'url\(["\']?([^"\')]+)["\']?\)', fig.get('style'))
                    if bg_match:
                        posterUrl = bg_match.group(1)
            
            meta_id = 'dizibox:' + base64.b64encode(fullUrl.encode('utf-8')).decode('utf-8').replace('=', '')
            return {'id': meta_id, 'type': 'series', 'name': title, 'poster': posterUrl}
        except: return None


    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body', '')
        url = fetchResult.get('url', '')
        metadata = fetchResult.get('metadata', {})
        status = fetchResult.get('status')

        if status and status != 200:
            if purpose in ['catalog', 'catalog-search']: return {'metas': []}
            if purpose in ['meta', 'season-episodes']: return {'meta': None}
            if 'stream' in purpose or 'iframe' in purpose or 'decrypt' in purpose: return {'streams': []}
            return {'ok': False, 'error': f'HTTP {status}'}

        if purpose in ['catalog-search', 'catalog']:
            soup = BeautifulSoup(body, 'html.parser')
            metas = []
            catalogId = metadata.get('catalogId')
            
            # Arama sonuçları ve arşiv sayfası
            if purpose == 'catalog-search' or catalogId == 'dizibox_archive':
                for elem in soup.select('article.detailed-article'):
                    meta = self.parse_series_item(soup, elem)
                    if meta: metas.append(meta)
                if not metas:
                    for elem in soup.select('article'):
                        meta = self.parse_series_item(soup, elem)
                        if meta: metas.append(meta)
                if metas:
                    print(f"📋 [DiziBox] {catalogId or purpose}: {len(metas)} dizi bulundu")
                    return {'metas': metas}
            
            # Tür/kategori sayfaları ve ana sayfa - tüm article tiplerini tara
            import re
            # 1. article.article-series-poster (tür sayfaları: grid-six/grid-five)
            for elem in soup.select('article.article-series-poster'):
                meta = self.parse_series_item(soup, elem)
                if meta: metas.append(meta)
            
            # 2. article.detailed-article (arşiv ve bazı kategori sayfaları)
            for elem in soup.select('article.detailed-article'):
                meta = self.parse_series_item(soup, elem)
                if meta: metas.append(meta)
            
            # 3. article.article-series-small-grid (önerilen diziler)
            for elem in soup.select('article.article-series-small-grid'):
                meta = self.parse_series_item(soup, elem)
                if meta: metas.append(meta)
            
            # 4. article.grid-four / article.grid-box (kategori grid)
            for elem in soup.select('article.grid-four, article.grid-box'):
                meta = self.parse_series_item(soup, elem)
                if meta: metas.append(meta)
            
            # 5. article.article-episode-card (bölüm kartları - son eklenenler)
            if not metas:
                seen_urls = set()
                for elem in soup.select('article.article-episode-card'):
                    a_tag = elem.find('a')
                    if a_tag and a_tag.get('href'):
                        href = a_tag.get('href')
                        # Bölüm linkinden dizi ana sayfasını çıkar
                        dizi_match = re.match(r'(https?://[^/]+/diziler/[^/]+/)', href)
                        if dizi_match:
                            dizi_url = dizi_match.group(1)
                            if dizi_url not in seen_urls:
                                seen_urls.add(dizi_url)
                                title = a_tag.get('title', '').strip()
                                # Bölüm bilgisini kaldır, sadece dizi adını al
                                title_clean = re.sub(r'\d+\.\s*Sezon\s*\d+\.\s*Bölüm.*', '', title).strip()
                                title_clean = re.sub(r'\s+izle$', '', title_clean).strip()
                                if not title_clean:
                                    title_clean = dizi_url.rstrip('/').split('/')[-1].replace('-', ' ').title()
                                img = elem.find('img')
                                posterUrl = None
                                if img:
                                    candidate = img.get('data-src') or img.get('data-lazy-src') or img.get('src')
                                    if candidate and not candidate.startswith('data:'):
                                        posterUrl = candidate
                                meta_id = 'dizibox:' + base64.b64encode(dizi_url.encode('utf-8')).decode('utf-8').replace('=', '')
                                metas.append({'id': meta_id, 'type': 'series', 'name': title_clean, 'poster': posterUrl})
            
            # 6. Genel fallback - tüm article elementleri
            if not metas:
                for elem in soup.select('article'):
                    meta = self.parse_series_item(soup, elem)
                    if meta: metas.append(meta)
            
            # Tekrar eden dizileri kaldır
            seen_ids = set()
            unique_metas = []
            for m in metas:
                if m['id'] not in seen_ids:
                    seen_ids.add(m['id'])
                    unique_metas.append(m)
            
            print(f"📋 [DiziBox] Katalog ({catalogId}): {len(unique_metas)} dizi bulundu")
            return {'metas': unique_metas}

        if purpose == 'meta':
            soup = BeautifulSoup(body, 'html.parser')
            
            title = 'Unknown'
            title_el = soup.select_one('h1')
            if title_el:
                title = title_el.text.strip()
            
            # Poster
            poster = None
            poster_el = soup.select_one('img.main-cover') or soup.select_one('figure.poster img')
            if poster_el:
                poster = poster_el.get('src') or poster_el.get('data-src')
            if not poster:
                og = soup.select_one('meta[property="og:image"]')
                if og: poster = og.get('content')
            if poster and not poster.startswith('http'):
                poster = f"{self.BASE_URL}{poster}" if poster.startswith('/') else f"{self.BASE_URL}/{poster}"
                
            # Description
            description = 'Aciklama mevcut degil'
            desc_el = soup.select_one('div.tv-story') or soup.select_one('.series-summary p') or soup.select_one('.summary')
            if desc_el:
                description = desc_el.text.strip()
            
            # Genres, Actors, Year
            year = None
            tags = []
            cast = []
            terms_div = soup.select_one('div.terms')
            if terms_div:
                parts = [p.strip() for p in terms_div.text.split('|')]
                for p in parts:
                    if p.isdigit() and len(p) == 4:
                        year = int(p)
                    elif ',' in p and not any(k in p.lower() for k in ['dram', 'kurgu', 'aksiyon', 'komedi', 'gerilim']):
                        cast = [a.strip() for a in p.split(',')]
                    elif ' ' not in p or ',' in p:
                        tags = [t.strip() for t in p.split(',')]
            
            # IMDB
            imdbRating = None
            imdb_el = soup.select_one('span.label')
            if imdb_el and 'imdb:' in imdb_el.text.lower():
                try: imdbRating = str(float(imdb_el.text.lower().replace('imdb:', '').strip()))
                except: pass
            
            # cast = [el.text.strip() for el in soup.select('a[href*="/oyuncu/"]')]
            
            # Bolumleri cek: article.grid-box veya article.grid-four
            import re
            videos = []
            for elem in soup.select('article.grid-box, article.grid-four'):
                # a.season-episode en güvenilir selector
                ep_a = elem.select_one('a.season-episode')
                if not ep_a:
                    ep_a = elem.select_one('div.post-title a')
                if not ep_a:
                    ep_a = elem.select_one('a')
                if not ep_a: continue
                epTitle = ep_a.text.strip()
                epHref = ep_a.get('href')
                
                if epTitle and epHref:
                    seasonMatch = re.search(r'(\d+)\.\s*Sezon', epTitle, re.IGNORECASE)
                    episodeMatch = re.search(r'(\d+)[\.\s]*(B[oö]l[uü]m|bolum|bölüm)', epTitle, re.IGNORECASE)
                    season = int(seasonMatch.group(1)) if seasonMatch else 1
                    episode = int(episodeMatch.group(1)) if episodeMatch else None
                    fullEpUrl = epHref if epHref.startswith('http') else f"{self.BASE_URL}{epHref}"
                    videoId = 'dizibox:' + base64.b64encode(fullEpUrl.encode('utf-8')).decode('utf-8').replace('=', '')
                    videos.append({'id': videoId, 'title': epTitle, 'season': season, 'episode': episode})
                    
            seasonLinks = []
            for elem in soup.select('div#seasons-list a, #seasons-list a'):
                s_href = elem.get('href')
                if s_href: seasonLinks.append(s_href if s_href.startswith('http') else f"{self.BASE_URL}{s_href}")
                
            metaId = 'dizibox:' + base64.b64encode(url.encode('utf-8')).decode('utf-8').replace('=', '')
            metaObj = {
                'id': metaId,
                'type': 'series',
                'name': title,
                'poster': poster,
                'background': poster,
                'description': description,
                'releaseInfo': str(year) if year else None,
                'imdbRating': imdbRating,
                'genres': tags if tags else None,
                'cast': cast if cast else None,
                'videos': videos
            }
                
            if seasonLinks:
                limitedSeasonLinks = seasonLinks[:8]
                instructions = []
                for i, link in enumerate(limitedSeasonLinks):
                    randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                    instructions.append({
                        'requestId': f"dizibox-season-{int(time.time()*1000)}-{randomId}-{i}",
                        'purpose': 'season-episodes',
                        'url': link,
                        'method': 'GET',
                        'headers': self.get_default_headers(url),
                        'metadata': {
                            'seriesUrl': url, 
                            'seriesTitle': title, 
                            'poster': poster,
                            'description': description,
                            'tags': tags,
                            'cast': cast,
                            'imdbRating': imdbRating,
                            'year': str(year) if year else None,
                            'hiddenweb': True
                        }
                    })
                return {'instructions': instructions, 'partialMeta': metaObj}
                
            return {'meta': metaObj}

        if purpose == 'season-episodes':
            soup = BeautifulSoup(body, 'html.parser')
            videos = []
            for elem in soup.select('article.grid-box, article.grid-four'):
                # a.season-episode öncelikli
                ep_link = elem.select_one('a.season-episode')
                if not ep_link:
                    ep_link = elem.select_one('div.post-title a')
                epTitle = ep_link.text.strip() if ep_link else None
                epHref = ep_link.get('href') if ep_link else None
                        
                if epTitle and epHref:
                    import re
                    seasonMatch = re.search(r'(\d+)[\.\s]*(Sezon|sezon)', epTitle, re.IGNORECASE)
                    episodeMatch = re.search(r'(\d+)[\.\s]*(Bölüm|bolum|bölum)', epTitle, re.IGNORECASE)
                    season = int(seasonMatch.group(1)) if seasonMatch else 1
                    episode = int(episodeMatch.group(1)) if episodeMatch else None
                    fullEpUrl = epHref if epHref.startswith('http') else f"{self.BASE_URL}{epHref}"
                    videoId = 'dizibox:' + base64.b64encode(fullEpUrl.encode('utf-8')).decode('utf-8').replace('=', '')
                    videos.append({'id': videoId, 'title': epTitle, 'season': season, 'episode': episode})
                    
            seriesTitle = metadata.get('seriesTitle', 'Dizi')
            seriesUrl = metadata.get('seriesUrl', url)
            
            return {
                'meta': {
                    'id': 'dizibox:' + base64.b64encode(seriesUrl.encode('utf-8')).decode('utf-8').replace('=', ''),
                    'type': 'series',
                    'name': seriesTitle,
                    'poster': metadata.get('poster'),
                    'description': metadata.get('description'),
                    'genres': metadata.get('tags', []),
                    'cast': metadata.get('cast', []),
                    'imdbRating': metadata.get('imdbRating'),
                    'releaseInfo': metadata.get('year'),
                    'videos': videos
                }
            }

        if purpose == 'stream':
            soup = BeautifulSoup(body, 'html.parser')
            iframe_el = soup.select_one('div#video-area iframe')
            if not iframe_el:
                iframe_el = soup.select_one('iframe')
            if not iframe_el or not iframe_el.get('src'): return {'streams': []}
            
            iframeSrc = iframe_el.get('src')
            mainIframeUrl = iframeSrc if iframeSrc.startswith('http') else f"{self.BASE_URL}{iframeSrc}"
            mainIframeUrl = add_wmode_opaque(mainIframeUrl)
            
            # Ana sunucu
            instructions = []
            randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
            
            main_name = 'DiziBox'
            select_el = soup.select_one('select.woca-linkpages-dd')
            if select_el:
                first_opt = select_el.find('option')
                if first_opt: main_name = first_opt.text.strip()
                
                for opt in select_el.find_all('option'):
                    if opt.get('selected') == 'selected' or not opt.get('value'):
                        main_name = opt.text.strip()
                        break
                        
            instructions.append({
                'requestId': f"dizibox-iframe-{int(time.time()*1000)}-{randomId}-0",
                'purpose': 'iframe-extract',
                'url': mainIframeUrl,
                'method': 'GET',
                'headers': self.get_default_headers(url),
                'metadata': {'originalUrl': url, 'streamName': main_name, 'hiddenweb': True}
            })
            
            # Alternatif sunuculari ekle
            if select_el:
                idx = 1
                for opt in select_el.find_all('option'):
                    val = opt.get('value')
                    if val and val.startswith('http') and 'izle' in val and opt.get('selected') != 'selected':
                        instructions.append({
                            'requestId': f"dizibox-alt-{int(time.time()*1000)}-{randomId}-{idx}",
                            'purpose': 'alternative-page',
                            'url': val,
                            'method': 'GET',
                            'headers': self.get_default_headers(url),
                            'metadata': {'originalUrl': url, 'streamName': opt.text.strip(), 'hiddenweb': True}
                        })
                        idx += 1
                        
            return {'instructions': instructions}

        if purpose == 'alternative-page':
            soup = BeautifulSoup(body, 'html.parser')
            iframe_el = soup.select_one('div#video-area iframe')
            if not iframe_el or not iframe_el.get('src'): return {'streams': []}
            
            iframeUrl = iframe_el.get('src') if iframe_el.get('src').startswith('http') else f"{self.BASE_URL}{iframe_el.get('src')}"
            iframeUrl = add_wmode_opaque(iframeUrl)
            
            randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
            return {
                'instructions': [{
                    'requestId': f"dizibox-alt-iframe-{int(time.time()*1000)}-{randomId}",
                    'purpose': 'iframe-extract',
                    'url': iframeUrl,
                    'method': 'GET',
                    'headers': self.get_default_headers(url),
                    'metadata': {'originalUrl': metadata.get('originalUrl', url), 'streamName': metadata.get('streamName', 'DiziBox'), 'hiddenweb': True}
                }]
            }

        if purpose == 'iframe-extract':
            soup = BeautifulSoup(body, 'html.parser')
            streamName = metadata.get('streamName', 'DiziBox')
            playerIframe_el = soup.select_one('div#Player iframe')
            
            if playerIframe_el and playerIframe_el.get('src'):
                playerIframe = playerIframe_el.get('src')
                fullIframeUrl = playerIframe if playerIframe.startswith('http') else f"{self.BASE_URL}{playerIframe}"
                sheilaUrl = fullIframeUrl.replace('/embed/', '/embed/sheila/').replace('vidmoly.me', 'vidmoly.net')
                
                randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                if 'dbx.molystream' in fullIframeUrl or 'vidmoly' in fullIframeUrl:
                    return {
                        'instructions': [{
                            'requestId': f"dizibox-molystream-{int(time.time()*1000)}-{randomId}",
                            'purpose': 'molystream-direct',
                            'url': sheilaUrl,
                            'method': 'GET',
                            'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': fullIframeUrl},
                            'metadata': {'streamName': streamName, 'embedUrl': fullIframeUrl, 'hiddenweb': True}
                        }]
                    }
                    
                return {
                    'instructions': [{
                        'requestId': f"dizibox-iframe-stream-{int(time.time()*1000)}-{randomId}",
                        'purpose': 'iframe-stream',
                        'url': sheilaUrl,
                        'method': 'GET',
                        'headers': self.get_default_headers(url),
                        'metadata': {'streamName': streamName, 'embedUrl': fullIframeUrl, 'originalUrl': metadata.get('originalUrl', url), 'hiddenweb': True}
                    }]
                }
                
            anyIframe = soup.select_one('iframe')
            if anyIframe and anyIframe.get('src'):
                randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                return {
                    'instructions': [{
                        'requestId': f"dizibox-general-{int(time.time()*1000)}-{randomId}",
                        'purpose': 'iframe-stream',
                        'url': anyIframe.get('src'),
                        'method': 'GET',
                        'headers': self.get_default_headers(url),
                        'metadata': {'streamName': streamName, 'originalUrl': metadata.get('originalUrl', url), 'hiddenweb': True}
                    }]
                }
                
            # If no iframe, maybe the current page IS the player (e.g. king.php without iframe)
            import re
            cryptMatch = re.search(r'CryptoJS\.AES\.decrypt\(["\'](.+?)["\'],\s*["\'](.+?)["\']\)', body)
            randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
            if cryptMatch:
                encryptedData = cryptMatch.group(1)
                password = cryptMatch.group(2)
                return {
                    'instructions': [{
                        'requestId': f"dizibox-decrypt-{int(time.time()*1000)}-{randomId}",
                        'purpose': 'king-decrypt',
                        'url': url,
                        'method': 'GET',
                        'metadata': {'streamName': streamName, 'encryptedData': encryptedData, 'password': password, 'body': body, 'originalUrl': metadata.get('originalUrl', url), 'hiddenweb': True}
                    }]
                }
                
            m3uMatch = re.search(r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"', body)
            if not m3uMatch: m3uMatch = re.search(r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'sources:\s*\[\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'(https?://[^\s"\'<>()]+\.m3u8[^\s"\'<>()]*)', body)
            
            if m3uMatch:
                subtitles = []
                subUrls = set()
                tracks_match = re.search(r'tracks\s*:\s*(\[[\s\S]*?\])\s*[,}]', body)
                if tracks_match:
                    try:
                        import json
                        tracksData = json.loads(tracks_match.group(1))
                        for track in tracksData:
                            if track.get('kind') in ['captions', 'subtitles'] and track.get('file'):
                                subUrl = track['file'].replace('\\/', '/').replace('\\u0026', '&').replace('\\', '')
                                subLang = (track.get('label') or track.get('language') or 'Türkçe')
                                if subUrl not in subUrls:
                                    subUrls.add(subUrl)
                                    subtitles.append({
                                        'id': subLang.lower().replace(' ', '_'),
                                        'url': subUrl if subUrl.startswith('http') else f"https:{subUrl}" if subUrl.startswith('//') else f"{self.BASE_URL}{subUrl}" if subUrl.startswith('/') else subUrl,
                                        'lang': subLang
                                    })
                    except: pass
                if not subtitles:
                    subRegex = r'"file":"((?:\\\\"|[^"])+)"(?:,"kind":"captions")?,"label":"((?:\\\\"|[^"])+)"'
                    for match in re.finditer(subRegex, body):
                        subUrlRaw = match.group(1)
                        subLangRaw = match.group(2)
                        subUrl = subUrlRaw.replace('\\/', '/').replace('\\', '')
                        if subUrl not in subUrls:
                            subUrls.add(subUrl)
                            subtitles.append({
                                'id': subLangRaw.lower().replace(' ', '_'),
                                'url': subUrl if subUrl.startswith('http') else f"https:{subUrl}" if subUrl.startswith('//') else f"{self.BASE_URL}{subUrl}" if subUrl.startswith('/') else subUrl,
                                'lang': subLangRaw
                            })

                return {'streams': [{
                    'name': streamName,
                    'title': streamName,
                    'url': m3uMatch.group(1),
                    'type': 'm3u8',
                    'subtitles': subtitles,
                    'behaviorHints': {
                        'notWebReady': False,
                        'proxyHeaders': {
                            'request': {
                                'Referer': metadata.get('originalUrl', url),
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            }
                        }
                    }
                }]}
            return {'streams': []}

        if purpose == 'molystream-direct':
            import os
            try:
                with open('/tmp/dizibox_moly.html', 'w', encoding='utf-8') as f:
                    f.write(body)
            except: pass
            
            import re
            import json
            
            iframeSubtitles = []
            subUrls = set()
            
            # Extract subtitles
            tracks_match = re.search(r'tracks\s*:\s*(\[[\s\S]*?\])\s*[,}]', body)
            if tracks_match:
                try:
                    tracksData = json.loads(tracks_match.group(1))
                    for track in tracksData:
                        if track.get('kind') in ['captions', 'subtitles'] and track.get('file'):
                            subUrl = track['file'].replace('\\/', '/').replace('\\u0026', '&').replace('\\', '')
                            subLang = (track.get('label') or track.get('language') or 'Türkçe')
                            if subUrl not in subUrls:
                                subUrls.add(subUrl)
                                iframeSubtitles.append({
                                    'id': subLang.lower().replace(' ', '_'),
                                    'url': subUrl if subUrl.startswith('http') else f"https:{subUrl}",
                                    'lang': subLang
                                })
                except Exception as e:
                    print(f"⚠️  Tracks parse error: {e}")
                    
            if not iframeSubtitles:
                subRegex = r'"file":"((?:\\\\"|[^"])+)"(?:,"kind":"captions")?,"label":"((?:\\\\"|[^"])+)"'
                for match in re.finditer(subRegex, body):
                    subUrlRaw = match.group(1)
                    subLangRaw = match.group(2)
                    subUrl = subUrlRaw.replace('\\/', '/').replace('\\', '')
                    if subUrl not in subUrls:
                        subUrls.add(subUrl)
                        iframeSubtitles.append({
                            'id': subLangRaw.lower().replace(' ', '_'),
                            'url': subUrl if subUrl.startswith('http') else f"https:{subUrl}",
                            'lang': subLangRaw
                        })
            
            # Extract video streams
            m3uMatches = re.findall(r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            streams = []
            for i, m in enumerate(m3uMatches):
                streams.append({
                    'name': metadata.get('streamName', 'DiziBox'),
                    'title': f'Auto {i+1}' if len(m3uMatches) > 1 else 'Auto',
                    'url': m,
                    'type': 'm3u8',
                    'subtitles': iframeSubtitles,
                    'behaviorHints': {
                        'notWebReady': False,
                        'proxyHeaders': {
                            'request': {
                                'Referer': metadata.get('embedUrl', ''),
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            }
                        }
                    }
                })
            
            # Fallback for direct EXTM3U
            if not streams and '#EXTM3U' in body:
                streams.append({
                    'name': metadata.get('streamName', 'DiziBox'),
                    'title': 'Auto',
                    'url': url,
                    'type': 'm3u8',
                    'subtitles': iframeSubtitles,
                    'behaviorHints': {
                        'notWebReady': False,
                        'proxyHeaders': {
                            'request': {
                                'Referer': metadata.get('embedUrl', ''),
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            }
                        }
                    }
                })
                
            return {'streams': streams}

        if purpose == 'iframe-stream':
            import re
            streamName = metadata.get('streamName', 'DiziBox')
            
            cryptMatch = re.search(r'CryptoJS\.AES\.decrypt\(["\'](.+?)["\'],\s*["\'](.+?)["\']\)', body)
            randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
            if cryptMatch:
                encryptedData = cryptMatch.group(1)
                password = cryptMatch.group(2)
                return {
                    'instructions': [{
                        'requestId': f"dizibox-decrypt-{int(time.time()*1000)}-{randomId}",
                        'purpose': 'king-decrypt',
                        'url': url,
                        'method': 'GET',
                        'metadata': {'streamName': streamName, 'encryptedData': encryptedData, 'password': password, 'body': body, 'originalUrl': metadata.get('originalUrl', url), 'hiddenweb': True}
                    }]
                }
                
            m3uMatch = re.search(r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"', body)
            if not m3uMatch: m3uMatch = re.search(r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'sources:\s*\[\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
            if not m3uMatch: m3uMatch = re.search(r'(https?://[^\s"\'<>()]+\.m3u8[^\s"\'<>()]*)', body)
            
            if m3uMatch:
                subtitles = []
                subUrls = set()
                tracks_match = re.search(r'tracks\s*:\s*(\[[\s\S]*?\])\s*[,}]', body)
                if tracks_match:
                    try:
                        import json
                        tracksData = json.loads(tracks_match.group(1))
                        for track in tracksData:
                            if track.get('kind') in ['captions', 'subtitles'] and track.get('file'):
                                subUrl = track['file'].replace('\\/', '/').replace('\\u0026', '&').replace('\\', '')
                                subLang = (track.get('label') or track.get('language') or 'Türkçe')
                                if subUrl not in subUrls:
                                    subUrls.add(subUrl)
                                    subtitles.append({
                                        'id': subLang.lower().replace(' ', '_'),
                                        'url': subUrl if subUrl.startswith('http') else f"https:{subUrl}" if subUrl.startswith('//') else f"{self.BASE_URL}{subUrl}" if subUrl.startswith('/') else subUrl,
                                        'lang': subLang
                                    })
                    except: pass
                if not subtitles:
                    subRegex = r'"file":"((?:\\\\"|[^"])+)"(?:,"kind":"captions")?,"label":"((?:\\\\"|[^"])+)"'
                    for match in re.finditer(subRegex, body):
                        subUrlRaw = match.group(1)
                        subLangRaw = match.group(2)
                        subUrl = subUrlRaw.replace('\\/', '/').replace('\\', '')
                        if subUrl not in subUrls:
                            subUrls.add(subUrl)
                            subtitles.append({
                                'id': subLangRaw.lower().replace(' ', '_'),
                                'url': subUrl if subUrl.startswith('http') else f"https:{subUrl}" if subUrl.startswith('//') else f"{self.BASE_URL}{subUrl}" if subUrl.startswith('/') else subUrl,
                                'lang': subLangRaw
                            })

                return {'streams': [{
                    'name': streamName,
                    'title': streamName,
                    'url': m3uMatch.group(1),
                    'type': 'm3u8',
                    'subtitles': subtitles,
                    'behaviorHints': {
                        'notWebReady': False,
                        'proxyHeaders': {
                            'request': {
                                'Referer': metadata.get('originalUrl', url),
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            }
                        }
                    }
                }]}
            return {'streams': []}

        if purpose == 'king-decrypt':
            encryptedData = metadata.get('encryptedData')
            password = metadata.get('password')
            orig_body = metadata.get('body', '')
            streamName = metadata.get('streamName', 'DiziBox')
            
            if encryptedData and password:
                decrypted = cryptojs_decrypt(password, encryptedData)
                if decrypted:
                    import re
                    m3uMatch = re.search(r'(https?://[^\s"\'<>()]+\.m3u8[^\s"\'<>()]*)', decrypted)
                    if m3uMatch:
                        subtitles = []
                        subUrls = set()
                        
                        # Extract subtitles
                        tracks_match = re.search(r'tracks\s*:\s*(\[[\s\S]*?\])\s*[,}]', orig_body)
                        if not tracks_match: tracks_match = re.search(r'tracks\s*:\s*(\[[\s\S]*?\])\s*[,}]', decrypted)
                        
                        if tracks_match:
                            try:
                                import json
                                tracksData = json.loads(tracks_match.group(1))
                                for track in tracksData:
                                    if track.get('kind') in ['captions', 'subtitles'] and track.get('file'):
                                        subUrl = track['file'].replace('\\/', '/').replace('\\u0026', '&').replace('\\', '')
                                        subLang = (track.get('label') or track.get('language') or 'Türkçe')
                                        if subUrl not in subUrls:
                                            subUrls.add(subUrl)
                                            subtitles.append({
                                                'id': subLang.lower().replace(' ', '_'),
                                                'url': subUrl if subUrl.startswith('http') else f"https:{subUrl}" if subUrl.startswith('//') else f"{self.BASE_URL}{subUrl}" if subUrl.startswith('/') else subUrl,
                                                'lang': subLang
                                            })
                            except: pass
                            
                        if not subtitles:
                            subRegex = r'"file":"((?:\\\\"|[^"])+)"(?:,"kind":"captions")?,"label":"((?:\\\\"|[^"])+)"'
                            for match in re.finditer(subRegex, orig_body):
                                subUrlRaw = match.group(1)
                                subLangRaw = match.group(2)
                                subUrl = subUrlRaw.replace('\\/', '/').replace('\\', '')
                                if subUrl not in subUrls:
                                    subUrls.add(subUrl)
                                    subtitles.append({
                                        'id': subLangRaw.lower().replace(' ', '_'),
                                        'url': subUrl if subUrl.startswith('http') else f"https:{subUrl}" if subUrl.startswith('//') else f"{self.BASE_URL}{subUrl}" if subUrl.startswith('/') else subUrl,
                                        'lang': subLangRaw
                                    })
                                    
                        return {'streams': [{
                            'name': streamName,
                            'title': 'Auto (Decrypted)',
                            'url': m3uMatch.group(1),
                            'type': 'm3u8',
                            'subtitles': subtitles,
                            'behaviorHints': {
                                'notWebReady': False,
                                'proxyHeaders': {
                                    'request': {
                                        'Referer': metadata.get('originalUrl', 'https://www.dizibox.live/'),
                                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                                    }
                                }
                            }
                        }]}
            return {'streams': []}

        return {'ok': True}
