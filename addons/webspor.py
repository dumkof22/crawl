import base64
import json
import re
import time
import random
import urllib.parse
from bs4 import BeautifulSoup

BASE_URL = 'https://www.webspor123.xyz'

class WebsporScraper:
    def __init__(self):
        self.manifest = {
            "id": "community.webspor",
            "version": "1.0.0",
            "name": "Webspor",
            "description": "Canlı spor kanalları - Webspor için Stremio eklentisi (Instruction Mode)",
            "logo": "https://www.webspor123.xyz/public/assets/themes/v2/images/uploads/logo.png",
            "resources": ["catalog", "meta", "stream"],
            "types": ["tv", "channel"],
            "catalogs": [
                { "type": "tv", "id": "webspor_football", "name": "⚽ Futbol", "extra": [{"name": "skip", "isRequired": False}] },
                { "type": "tv", "id": "webspor_basketball", "name": "🏀 Basketbol", "extra": [{"name": "skip", "isRequired": False}] },
                { "type": "tv", "id": "webspor_tennis", "name": "🎾 Tenis", "extra": [{"name": "skip", "isRequired": False}] },
                { "type": "tv", "id": "webspor_tv", "name": "📺 7/24 Kanallar", "extra": [{"name": "skip", "isRequired": False}] }
            ],
            "idPrefixes": ["webspor"]
        }

    def getManifest(self):
        return self.manifest

    async def handleCatalog(self, args):
        catalog_id = args.get('id')
        print(f"\n🎯 [Webspor Catalog] Generating instructions...")
        print(f"📋 Catalog ID: {catalog_id}")

        random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        request_id = f"webspor-catalog-{catalog_id}-{int(time.time()*1000)}-{random_id}"
        
        return {
            "instructions": [{
                "requestId": request_id,
                "purpose": "catalog",
                "url": BASE_URL,
                "method": "GET",
                "headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                    "Referer": BASE_URL
                },
                "metadata": { "catalogId": catalog_id, "hiddenweb": True }
            }]
        }

    async def handleMeta(self, args):
        video_id = args.get('id', '')
        url_base64 = video_id.replace('webspor:channel:', '').replace('webspor:match:', '')
        url_base64 += '=' * (-len(url_base64) % 4)
        url = base64.b64decode(url_base64).decode('utf-8')

        print(f"📺 [Webspor Meta] Generating instructions for: {url[:80]}...")

        random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        request_id = f"webspor-meta-{int(time.time()*1000)}-{random_id}"
        
        return {
            "instructions": [{
                "requestId": request_id,
                "purpose": "meta",
                "url": url,
                "method": "GET",
                "headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                    "Referer": BASE_URL
                },
                "metadata": { "hiddenweb": True }
            }]
        }

    async def handleStream(self, args):
        video_id = args.get('id', '')
        url_base64 = video_id.replace('webspor:channel:', '').replace('webspor:match:', '')
        url_base64 += '=' * (-len(url_base64) % 4)
        player_url = base64.b64decode(url_base64).decode('utf-8')

        if not player_url.startswith('http'):
            if player_url.startswith('//'):
                player_url = 'https:' + player_url
            elif player_url.startswith('/'):
                player_url = BASE_URL + player_url
            else:
                player_url = BASE_URL + '/' + player_url

        print(f"🎬 [Webspor Stream] Generating instructions for: {player_url[:80]}...")

        random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        request_id = f"webspor-stream-{int(time.time()*1000)}-{random_id}"
        
        try:
            origin = urllib.parse.urlparse(player_url).scheme + "://" + urllib.parse.urlparse(player_url).netloc + "/"
        except:
            origin = player_url
            
        return {
            "instructions": [{
                "requestId": request_id,
                "purpose": "stream",
                "url": player_url,
                "method": "GET",
                "headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                    "Referer": origin
                },
                "metadata": { "originalPlayerUrl": player_url, "hiddenweb": True }
            }]
        }

    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body', '')
        url = fetchResult.get('url', '')
        metadata = fetchResult.get('metadata') or {}
        
        print(f"\n⚙️ [Webspor Process] Purpose: {purpose}")
        
        if purpose == 'catalog':
            catalog_id = metadata.get('catalogId')
            soup = BeautifulSoup(body, 'html.parser')
            metas = []
            
            item_class = 'tv'
            if catalog_id == 'webspor_football': item_class = 'football'
            elif catalog_id == 'webspor_basketball': item_class = 'basketball'
            elif catalog_id == 'webspor_tennis': item_class = 'tennis'
            
            items = soup.select(f'div.item.{item_class} div[data-url]')
            
            for el in items:
                data_url = el.get('data-url')
                title = el.get('title')
                name_el = el.select_one('strong.name')
                time_el = el.select_one('span.time')
                live_el = el.select_one('span.live')
                
                name = name_el.text.strip() if name_el else title
                time_str = time_el.text.strip() if time_el else (live_el.text.strip() if live_el else 'Canlı Yayın')
                
                if not data_url or not name:
                    continue
                
                id_b64 = base64.b64encode(data_url.encode('utf-8')).decode('utf-8').replace('=', '')
                channel_id = f"webspor:channel:{id_b64}" if item_class == 'tv' else f"webspor:match:{id_b64}"
                
                poster_url = f"https://via.placeholder.com/300x450/1a1a1a/ffffff?text={urllib.parse.quote(name)}"
                
                metas.append({
                    "id": channel_id,
                    "type": "tv",
                    "name": f"📺 {name}" if item_class == 'tv' else f"🔴 {name}",
                    "poster": poster_url,
                    "posterShape": "square",
                    "description": f"{name} - {time_str}"
                })
                
            print(f"✅ Found {len(metas)} items in catalog")
            return {"metas": metas}

        if purpose == 'meta':
            url_id = base64.b64encode(url.encode('utf-8')).decode('utf-8').replace('=', '')
            
            return {
                "meta": {
                    "id": f"webspor:{url_id}",
                    "type": "tv",
                    "name": "Webspor Canlı Yayın",
                    "poster": "https://via.placeholder.com/300x450/1a1a1a/ffffff?text=Webspor",
                    "posterShape": "square",
                    "description": "Canlı Yayın",
                    "genres": ["Spor", "Canlı TV"]
                }
            }

        if purpose == 'stream':
            streams = []
            full_player_url = metadata.get('originalPlayerUrl', url)
            
            m3u8_patterns = [
                re.compile(r'(https?:\/\/[^"\'\s<>]+\.m3u8[^\s"\'<>]*)', re.IGNORECASE)
            ]
            
            m3u8_link = None
            if isinstance(body, bytes):
                body_str = body.decode('utf-8', errors='ignore')
            else:
                body_str = str(body)

            for pattern in m3u8_patterns:
                match = pattern.search(body_str)
                if match:
                    m3u8_link = match.group(1).replace('\\', '').replace('\\"', '"')
                    break
                    
            if m3u8_link:
                try:
                    m3u8_origin = urllib.parse.urlparse(m3u8_link).scheme + "://" + urllib.parse.urlparse(m3u8_link).netloc
                except:
                    m3u8_origin = ""
                    
                try:
                    player_referer = urllib.parse.urlparse(full_player_url).scheme + "://" + urllib.parse.urlparse(full_player_url).netloc + "/"
                except:
                    player_referer = ""
                    
                stream_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                    "Referer": player_referer,
                    "Origin": m3u8_origin
                }
                
                streams.append({
                    "name": "Webspor",
                    "title": "Webspor (M3U8 + Headers)",
                    "url": m3u8_link,
                    "behaviorHints": {
                        "notWebReady": True,
                        "bingeGroup": "webspor-live",
                        "proxyHeaders": {
                            "request": stream_headers
                        }
                    }
                })
                
                streams.append({
                    "name": "Webspor (Header'sız)",
                    "title": "Webspor (M3U8)",
                    "url": m3u8_link,
                    "behaviorHints": {
                        "notWebReady": True,
                        "bingeGroup": "webspor-live"
                    }
                })
            else:
                streams.append({
                    "name": "Webspor (İframe)",
                    "title": "Webspor (İframe Player)",
                    "url": full_player_url,
                    "behaviorHints": {
                        "notWebReady": False,
                        "bingeGroup": "webspor-live"
                    }
                })
                
            streams.append({
                "name": "Tarayıcıda Aç",
                "title": "Tarayıcıda Oynat",
                "externalUrl": full_player_url,
                "behaviorHints": {
                    "notWebReady": True
                }
            })
            
            print(f"✅ Found {len(streams)} stream(s)")
            return {"streams": streams}

        return {"ok": True}
