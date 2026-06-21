import asyncio
import base64
import json
import re
import time
import random
import urllib.parse
from bs4 import BeautifulSoup
from Crypto.Cipher import AES

BASE_URL = 'https://cizgivedizi.com'

CATALOG_TAG_MAP = {
    'cizgivedizi_diziler': 'diz',
    'cizgivedizi_cizgi_diziler': 'çd',
    'cizgivedizi_animeler': 'ani',
    'cizgivedizi_yansimalar': 'yans',
    'cizgivedizi_preschool': 'pro',
    'cizgivedizi_belgesel': 'bel',
    'cizgivedizi_komedi': 'kom',
    'cizgivedizi_macera': 'mac'
}

def get_enhanced_headers(referer=BASE_URL):
    return {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Referer': referer
    }

def fix_image_format(url):
    if not url: return None
    # Cloudinary proxy is returning 401 Unauthorized, returning original url.
    return url

def normalize_string(text):
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = text.replace('İ', 'I').replace('Ğ', 'G').replace('Ü', 'U').replace('Ş', 'S').replace('Ö', 'O').replace('Ç', 'C')
    text = text.replace('-', ' ').replace('_', ' ').replace('.', ' ')
    return text

def url_create(metin):
    harfler = {
        "İ": "I", "ı": "i", "Ş": "S", "ş": "s", "Ğ": "G", "ğ": "g", 
        "Ü": "U", "ü": "u", "Ö": "O", "ö": "o", "Ç": "C", "ç": "c", 
        "/": "", "?": ""
    }
    metin = metin.lower()
    for k, v in harfler.items():
        metin = metin.replace(k, v)
    metin = metin.replace(" ", "_")
    return metin

def crypto_aes_handler(data_b64, passphrase_str, encrypt=False):
    try:
        if encrypt:
            pass
        else:
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
            decrypted = decrypted[:-pad_len]
            return decrypted.decode('utf-8')
    except Exception as e:
        print(f"❌ AES decrypt error: {e}")
        return None


class CizgiveDiziScraper:
    def __init__(self):
        self.manifest = {
            "id": "community.cizgivedizi",
            "version": "1.0.0",
            "name": "CizgiveDizi",
            "description": "Türkçe çizgi film ve dizi platformu - CizgiveDizi için Stremio eklentisi (Instruction Mode)",
            "logo": "https://cizgivedizi.com/Logo.png",
            "resources": ["catalog", "meta", "stream"],
            "types": ["series", "movie"],
            "catalogs": [
                {"type": "series", "id": "cizgivedizi_diziler", "name": "Diziler", "extra": [{"name": "skip", "isRequired": False}]},
                {"type": "series", "id": "cizgivedizi_cizgi_diziler", "name": "Çizgi Diziler", "extra": [{"name": "skip", "isRequired": False}]},
                {"type": "series", "id": "cizgivedizi_animeler", "name": "Animeler", "extra": [{"name": "skip", "isRequired": False}]},
                {"type": "series", "id": "cizgivedizi_yansimalar", "name": "Yansımalar", "extra": [{"name": "skip", "isRequired": False}]},
                {"type": "series", "id": "cizgivedizi_preschool", "name": "Okul Öncesi", "extra": [{"name": "skip", "isRequired": False}]},
                {"type": "series", "id": "cizgivedizi_belgesel", "name": "Belgesel", "extra": [{"name": "skip", "isRequired": False}]},
                {"type": "series", "id": "cizgivedizi_komedi", "name": "Komedi", "extra": [{"name": "skip", "isRequired": False}]},
                {"type": "series", "id": "cizgivedizi_macera", "name": "Macera", "extra": [{"name": "skip", "isRequired": False}]},
                {"type": "series", "id": "cizgivedizi_search", "name": "Ara", "extra": [{"name": "search", "isRequired": True}, {"name": "skip", "isRequired": False}]}
            ],
            "idPrefixes": ["cizgivedizi"]
        }

    def getManifest(self):
        return self.manifest

    async def handleCatalog(self, args):
        print(f"\n🎯 [CizgiveDizi Catalog] Generating instructions...")
        catalog_id = args.get('id')
        extra = args.get('extra', {})
        search_query = extra.get('search')
        
        random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        
        if catalog_id == 'cizgivedizi_search' and search_query:
            request_id = f"cizgivedizi-search-{int(time.time()*1000)}-{random_id}"
            headers = get_enhanced_headers(BASE_URL)
            headers['Accept-Charset'] = 'utf-8'
            return {
                "instructions": [{
                    "requestId": request_id,
                    "purpose": "catalog-data",
                    "url": f"{BASE_URL}/dizi/isim.txt",
                    "method": "GET",
                    "headers": headers,
                    "metadata": {
                        "catalogId": catalog_id,
                        "searchQuery": search_query,
                        "additionalUrls": {
                            "poster": f"{BASE_URL}/dizi/poster.txt",
                            "etiket": f"{BASE_URL}/dizi/etiket.txt"
                        }
                    }
                }]
            }
            
        tag_code = CATALOG_TAG_MAP.get(catalog_id)
        if not tag_code:
            return {"instructions": []}
            
        request_id = f"cizgivedizi-catalog-{catalog_id}-{int(time.time()*1000)}-{random_id}"
        headers = get_enhanced_headers(BASE_URL)
        headers['Accept-Charset'] = 'utf-8'
        return {
            "instructions": [{
                "requestId": request_id,
                "purpose": "catalog-data",
                "url": f"{BASE_URL}/dizi/isim.txt",
                "method": "GET",
                "headers": headers,
                "metadata": {
                    "catalogId": catalog_id,
                    "tagCode": tag_code,
                    "additionalUrls": {
                        "poster": f"{BASE_URL}/dizi/poster.txt",
                        "etiket": f"{BASE_URL}/dizi/etiket.txt"
                    }
                }
            }]
        }

    async def handleMeta(self, args):
        video_id = args.get('id', '')
        b64 = video_id.replace('cizgivedizi:', '')
        b64 += '=' * (-len(b64) % 4)
        url = base64.b64decode(b64).decode('utf-8')
        
        encoded_url = urllib.parse.quote(url, safe=";/?:@&=+$,%")
        random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        request_id = f"cizgivedizi-meta-{int(time.time()*1000)}-{random_id}"
        
        return {
            "instructions": [{
                "requestId": request_id,
                "purpose": "meta",
                "url": encoded_url,
                "method": "GET",
                "headers": get_enhanced_headers(BASE_URL)
            }]
        }

    async def handleStream(self, args):
        video_id = args.get('id', '')
        b64 = video_id.replace('cizgivedizi:', '')
        b64 += '=' * (-len(b64) % 4)
        url = base64.b64decode(b64).decode('utf-8')
        
        encoded_url = urllib.parse.quote(url, safe=";/?:@&=+$,%")
        random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        request_id = f"cizgivedizi-stream-{int(time.time()*1000)}-{random_id}"
        
        return {
            "instructions": [{
                "requestId": request_id,
                "purpose": "stream",
                "url": encoded_url,
                "method": "GET",
                "headers": get_enhanced_headers(encoded_url)
            }]
        }
        
    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body')
        url = fetchResult.get('url')
        metadata = fetchResult.get('metadata') or {}
        status = fetchResult.get('status')
        
        if status and status != 200:
            if purpose == 'catalog-data':
                return {"metas": []}
            elif purpose == 'meta':
                return {"meta": None}
            elif 'stream' in purpose or 'extractor' in purpose:
                return {"streams": []}
            return {"ok": False, "error": f"HTTP {status}"}
            
        if purpose == 'catalog-data':
            if isinstance(body, bytes):
                body_str = body.decode('utf-8', errors='ignore')
            else:
                body_str = str(body)
            
            lines = [line.strip() for line in body_str.split('\n') if line.strip().startswith('|')]
            isim_data = {}
            for line in lines:
                match = re.match(r'^\|([^=]+)=(.+)$', line)
                if match:
                    isim_data[match.group(1).strip()] = match.group(2).strip()
                    
            additional_urls = metadata.get('additionalUrls', {})
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    poster_res, etiket_res = await asyncio.gather(
                        client.get(additional_urls.get('poster', '')),
                        client.get(additional_urls.get('etiket', ''))
                    )
                    poster_str = poster_res.text
                    etiket_str = etiket_res.text
                except Exception as e:
                    print(f"Error fetching catalog data: {e}")
                    return {"metas": []}
                    
            poster_data = {}
            for line in poster_str.split('\n'):
                if line.strip().startswith('|'):
                    match = re.match(r'^\|([^=]+)=(.+)$', line.strip())
                    if match:
                        poster_data[match.group(1).strip()] = match.group(2).strip()
                        
            etiket_data = {}
            for line in etiket_str.split('\n'):
                if line.strip().startswith('|'):
                    match = re.match(r'^\|([^=]+)=(.+)$', line.strip())
                    if match:
                        etiket_data[match.group(1).strip()] = match.group(2).strip()
                        
            tag_code = metadata.get('tagCode')
            search_query = metadata.get('searchQuery')
            metas = []
            
            for key, isim in isim_data.items():
                poster = poster_data.get(key)
                etiketler = etiket_data.get(key, '').split(';')
                
                if tag_code and tag_code not in etiketler:
                    continue
                    
                if search_query:
                    n_query = normalize_string(search_query.lower())
                    n_title = normalize_string(isim.lower())
                    if n_query not in n_title:
                        continue
                        
                dizi_url_part = url_create(isim)
                dizi_url = f"{BASE_URL}/dizi/{key}/{dizi_url_part}"
                dizi_id = 'cizgivedizi:' + base64.b64encode(dizi_url.encode('utf-8')).decode('utf-8').replace('=', '')
                
                metas.append({
                    "id": dizi_id,
                    "type": "series",
                    "name": isim,
                    "poster": fix_image_format(poster)
                })
            return {"metas": metas}
            
        elif purpose == 'meta':
            soup = BeautifulSoup(body, 'html.parser')
            
            title_el = soup.select_one('.infoLine h4') or soup.select_one('h4') or soup.select_one('h1')
            title = title_el.text.strip() if title_el else None
            if not title or title == 'Hoş Geldiniz':
                return {"meta": None}
                
            poster_el = soup.select_one('picture img') or soup.select_one('img')
            raw_poster = poster_el.get('src') if poster_el else None
            if raw_poster and not raw_poster.startswith('http'):
                raw_poster = raw_poster if raw_poster.startswith('/') else f"/{raw_poster}"
                raw_poster = f"{BASE_URL}{raw_poster}"
            poster = fix_image_format(raw_poster)
            
            plot_el = soup.select_one('p.lead')
            if plot_el:
                plot = plot_el.text.strip()
            else:
                plot = ""
                for p in soup.select('p'):
                    txt = p.text.strip()
                    if len(txt) > 50 and '©' not in txt and 'Sitemize' not in txt:
                        plot = txt
                        break
                        
            tags = []
            for el in soup.select('[data-bs-title]'):
                t = el.get('data-bs-title')
                if t and len(t) > 2 and t not in tags:
                    tags.append(t)
                    
            videos = []
            for i, a in enumerate(soup.select('a.bolum')):
                href = a.get('href')
                if not href: continue
                
                sezon_str = a.get('data-sezon')
                try:
                    sezon = int(sezon_str) if sezon_str else 1
                except Exception:
                    sezon = 1
                parts = href.split('/')
                try:
                    episode = int(parts[-2])
                except Exception:
                    episode = i + 1
                    
                title_attr = a.get('title') or a.get('data-bs-title')
                ep_name = parts[-1].replace('_', ' ').capitalize() if len(parts) > 0 else ""
                ep_title = ep_name if title_attr else f"{episode}. Bölüm"
                
                full_url = href if href.startswith('http') else f"{BASE_URL}{href}"
                vid_id = 'cizgivedizi:' + base64.b64encode(full_url.encode('utf-8')).decode('utf-8').replace('=', '')
                
                vid = {
                    "id": vid_id,
                    "title": ep_title,
                    "season": sezon,
                    "episode": episode
                }
                if title_attr:
                    vid["overview"] = title_attr
                videos.append(vid)
                
            return {
                "meta": {
                    "id": 'cizgivedizi:' + base64.b64encode(url.encode('utf-8')).decode('utf-8').replace('=', ''),
                    "type": "series",
                    "name": title,
                    "poster": poster,
                    "background": poster,
                    "description": plot or "Açıklama mevcut değil",
                    "genres": tags if tags else None,
                    "videos": videos
                }
            }
            
        elif purpose == 'stream':
            soup = BeautifulSoup(body, 'html.parser')
            play_link = soup.select_one('a[href*="/play"]')
            play_url = play_link.get('href') if play_link else None
            
            if not play_url:
                iframe = soup.select_one('iframe')
                if iframe: play_url = iframe.get('src')
                
            if not play_url:
                return {"streams": []}
                
            full_play_url = play_url if play_url.startswith('http') else f"{BASE_URL}{play_url}"
            
            if any(x in full_play_url for x in ['video.sibnet.ru', 'cizgiduo.online', 'cizgipass', 'drive.google.com']):
                extractor_type = 'generic'
                server_name = 'CizgiveDizi'
                if 'cizgiduo.online' in full_play_url:
                    extractor_type = 'cizgiduo'
                    server_name = 'CizgiDuo'
                elif 'cizgipass' in full_play_url:
                    extractor_type = 'cizgipass'
                    server_name = 'CizgiPass'
                elif 'drive.google.com' in full_play_url:
                    extractor_type = 'googledrive'
                    server_name = 'GdrivePlayer'
                elif 'video.sibnet.ru' in full_play_url:
                    extractor_type = 'sibnet'
                    server_name = 'SibNet'
                    
                random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
                encoded = urllib.parse.quote(full_play_url, safe=";/?:@&=+$,%")
                return {
                    "instructions": [{
                        "requestId": f"cizgivedizi-extract-{int(time.time()*1000)}-{random_id}",
                        "purpose": "extractor",
                        "url": encoded,
                        "method": "GET",
                        "headers": get_enhanced_headers(encoded),
                        "metadata": {
                            "originalUrl": url,
                            "extractorType": extractor_type,
                            "serverName": server_name
                        }
                    }]
                }
                
            random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
            encoded = urllib.parse.quote(full_play_url, safe=";/?:@&=+$,%")
            return {
                "instructions": [{
                    "requestId": f"cizgivedizi-play-{int(time.time()*1000)}-{random_id}",
                    "purpose": "play-page",
                    "url": encoded,
                    "method": "GET",
                    "headers": get_enhanced_headers(encoded),
                    "metadata": {"originalUrl": url}
                }]
            }
            
        elif purpose == 'play-page':
            soup = BeautifulSoup(body, 'html.parser')
            iframes = []
            for iframe in soup.select('iframe'):
                src = iframe.get('src')
                if src:
                    iframes.append(src if src.startswith('http') else f"{BASE_URL}{src}")
                    
            if not iframes: return {"streams": []}
            
            instructions = []
            for i, iframe_url in enumerate(iframes):
                extractor_type = 'generic'
                server_name = f'Server {i+1}'
                if 'cizgiduo.online' in iframe_url:
                    extractor_type = 'cizgiduo'
                    server_name = 'CizgiDuo'
                elif 'cizgipass' in iframe_url:
                    extractor_type = 'cizgipass'
                    server_name = 'CizgiPass'
                elif 'drive.google.com' in iframe_url:
                    extractor_type = 'googledrive'
                    server_name = 'GdrivePlayer'
                elif 'video.sibnet.ru' in iframe_url:
                    extractor_type = 'sibnet'
                    server_name = 'SibNet'
                    
                random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
                encoded = urllib.parse.quote(iframe_url, safe=";/?:@&=+$,%")
                instructions.append({
                    "requestId": f"cizgivedizi-extract-{int(time.time()*1000)}-{random_id}-{i}",
                    "purpose": "extractor",
                    "url": encoded,
                    "method": "GET",
                    "headers": get_enhanced_headers(encoded),
                    "metadata": {
                        "originalUrl": metadata.get('originalUrl') or url,
                        "extractorType": extractor_type,
                        "serverName": server_name
                    }
                })
            return {"instructions": instructions}
            
        elif purpose == 'extractor':
            extractor_type = metadata.get('extractorType', 'generic')
            server_name = metadata.get('serverName', 'CizgiveDizi')
            original_url = metadata.get('originalUrl', url)
            encoded_url = urllib.parse.quote(url, safe=";/?:@&=+$,%")
            
            streams = []
            if extractor_type in ['cizgiduo', 'cizgipass']:
                match = re.search(r"bePlayer\('([^']+)',\s*'(\{[^}]+\})'\);", body)
                if match:
                    password = match.group(1)
                    data = match.group(2)
                    decrypted = crypto_aes_handler(data, password, False)
                    if decrypted:
                        v_match = re.search(r'video_location":"([^"]+)', decrypted)
                        if v_match:
                            m3u_url = v_match.group(1).replace('\\', '')
                            streams.append({
                                "name": server_name,
                                "title": server_name,
                                "url": m3u_url,
                                "behaviorHints": {
                                    "notWebReady": False,
                                    "bingeGroup": 'cizgivedizi-stream',
                                    "proxyHeaders": {
                                        "request": {
                                            "User-Agent": "Mozilla/5.0",
                                            "Referer": encoded_url
                                        }
                                    }
                                }
                            })
            elif extractor_type == 'googledrive':
                parts = url.split('/d/')
                if len(parts) > 1:
                    url_id = parts[1].split('/')[0]
                    random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
                    return {
                        "instructions": [{
                            "requestId": f"cizgivedizi-gdrive-api-{int(time.time()*1000)}-{random_id}",
                            "purpose": "googledrive-api",
                            "url": "https://gdplayer.vip/api/video",
                            "method": "POST",
                            "headers": {
                                "Content-Type": "application/x-www-form-urlencoded",
                                "User-Agent": "Mozilla/5.0"
                            },
                            "body": f"file_id={url_id}&subtitle=",
                            "metadata": {"serverName": server_name, "urlId": url_id}
                        }]
                    }
            elif extractor_type == 'sibnet':
                match = re.search(r'player\.src\(\[\{src:\s*"([^"]+)"', body)
                if match:
                    m3u = match.group(1)
                    if not m3u.startswith('http'):
                        m3u = f"https://video.sibnet.ru{m3u}"
                    streams.append({
                        "name": server_name,
                        "title": server_name,
                        "url": m3u,
                        "behaviorHints": {
                            "notWebReady": False,
                            "bingeGroup": 'cizgivedizi-stream',
                            "proxyHeaders": {
                                "request": {"Referer": encoded_url}
                            }
                        }
                    })
            else:
                m3u = re.search(r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
                if not m3u: m3u = re.search(r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"', body)
                if not m3u: m3u = re.search(r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', body)
                if not m3u: m3u = re.search(r'(https?:\/\/[^\s"\'<>()]+\.m3u8[^\s"\'<>()]*)', body)
                if m3u:
                    m3u_url = m3u.group(1) if len(m3u.groups()) > 0 else m3u.group(0)
                    streams.append({
                        "name": server_name,
                        "title": server_name,
                        "url": m3u_url,
                        "behaviorHints": {
                            "notWebReady": False,
                            "bingeGroup": 'cizgivedizi-stream',
                            "proxyHeaders": {"request": {"Referer": encoded_url}}
                        }
                    })
            return {"streams": streams}
            
        elif purpose == 'googledrive-api':
            try:
                data = json.loads(body)
                if data.get('status') == 'success' and 'embedUrl' in data.get('data', {}):
                    embed_url = data['data']['embedUrl']
                    random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
                    return {
                        "instructions": [{
                            "requestId": f"cizgivedizi-gdrive-embed-{int(time.time()*1000)}-{random_id}",
                            "purpose": "googledrive-embed",
                            "url": embed_url,
                            "method": "GET",
                            "headers": get_enhanced_headers('https://gdplayer.vip/'),
                            "metadata": {"serverName": metadata.get('serverName')}
                        }]
                    }
            except Exception:
                pass
            return {"streams": []}
            
        elif purpose == 'googledrive-embed':
            soup = BeautifulSoup(body, 'html.parser')
            body_el = soup.select_one('body[ng-init]')
            if body_el:
                ng_init = body_el.get('ng-init')
                match = re.search(r"init\('([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']*)'\)", ng_init)
                if match:
                    play_url = match.group(1)
                    key_hex = match.group(2)
                    video_api = f"{play_url}/?video_id={key_hex}&action=get_video"
                    random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
                    return {
                        "instructions": [{
                            "requestId": f"cizgivedizi-gdrive-video-{int(time.time()*1000)}-{random_id}",
                            "purpose": "googledrive-video",
                            "url": video_api,
                            "method": "GET",
                            "headers": {
                                "User-Agent": "Mozilla/5.0",
                                "Referer": "https://gdplayer.vip/"
                            },
                            "metadata": {
                                "serverName": metadata.get('serverName'),
                                "playUrl": play_url,
                                "keyHex": key_hex
                            }
                        }]
                    }
            return {"streams": []}
            
        elif purpose == 'googledrive-video':
            streams = []
            try:
                data = json.loads(body)
                if 'qualities' in data:
                    play_url = metadata.get('playUrl')
                    key_hex = metadata.get('keyHex')
                    server_name = metadata.get('serverName')
                    for q in data['qualities']:
                        quality = q.get('quality')
                        v_url = f"{play_url}/?video_id={key_hex}&quality={quality}&action=p"
                        streams.append({
                            "name": f"{server_name} {quality}p",
                            "title": f"{server_name} {quality}p",
                            "url": v_url,
                            "behaviorHints": {
                                "notWebReady": False,
                                "bingeGroup": 'cizgivedizi-stream',
                                "proxyHeaders": {
                                    "request": {
                                        "User-Agent": "Mozilla/5.0",
                                        "Referer": "https://gdplayer.vip/"
                                    }
                                }
                            }
                        })
            except Exception:
                pass
            return {"streams": streams}
            
        return {"ok": True}