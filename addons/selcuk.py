import asyncio
import base64
import json
import re
import time
import random
import urllib.parse
from bs4 import BeautifulSoup

BASE_URL = 'https://www.sporcafe-8938c262c9.xyz'
DYNAMIC_PLAYER_DOMAIN = ''

def get_channel_filter(catalog_id):
    filters = {
        'selcuk_bein_sports': re.compile(r'bein\s*sports|beIN\s*SPORTS', re.IGNORECASE),
        'selcuk_s_sport': re.compile(r'^s\s*sport', re.IGNORECASE),
        'selcuk_tivibu_spor': re.compile(r'tivibu\s*spor', re.IGNORECASE),
        'selcuk_tabii_spor': re.compile(r'tabii\s*spor', re.IGNORECASE),
        'selcuk_other_sports': re.compile(r'eurosport|nba\s*tv|trt\s*spor|a\s*spor|smart\s*spor|dazn|ufc|sky\s*sports|motor', re.IGNORECASE)
    }
    return filters.get(catalog_id)

class SelcukScraper:
    def __init__(self):
        self.manifest = {
            "id": "community.selcuksports",
            "version": "2.0.0",
            "name": "SporCafe",
            "description": "Canlı spor kanalları - SelcukSports için Stremio eklentisi (Instruction Mode)",
            "logo": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRUPMbiKPHBQdUZiUrf6of2YQb7DKW5VPZnEg&s",
            "resources": ["catalog", "meta", "stream"],
            "types": ["tv", "channel"],
            "catalogs": [
                {"type": "tv", "id": "selcuk_live_matches", "name": "🔴 Canlı Maçlar", "extra": [{"name": "skip", "isRequired": False}]},
                {"type": "tv", "id": "selcuk_bein_sports", "name": "⚽ beIN SPORTS", "extra": [{"name": "skip", "isRequired": False}]},
                {"type": "tv", "id": "selcuk_s_sport", "name": "🏀 S Sport", "extra": [{"name": "skip", "isRequired": False}]},
                {"type": "tv", "id": "selcuk_tivibu_spor", "name": "📺 Tivibu Spor", "extra": [{"name": "skip", "isRequired": False}]},
                {"type": "tv", "id": "selcuk_tabii_spor", "name": "📱 tabii Spor", "extra": [{"name": "skip", "isRequired": False}]},
                {"type": "tv", "id": "selcuk_other_sports", "name": "🎾 Diğer Spor Kanalları", "extra": [{"name": "skip", "isRequired": False}]},
                {"type": "tv", "id": "selcuk_all_channels", "name": "📡 Tüm Kanallar (7/24)", "extra": [{"name": "skip", "isRequired": False}]}
            ],
            "idPrefixes": ["selcuk"]
        }

    def getManifest(self):
        return self.manifest

    async def handleCatalog(self, args):
        catalog_id = args.get('id')
        print(f"\n🎯 [SelcukSports Catalog] Generating instructions...")
        print(f"📋 Catalog ID: {catalog_id}")

        random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        request_id = f"selcuk-catalog-{catalog_id}-{int(time.time()*1000)}-{random_id}"
        
        return {
            "instructions": [{
                "requestId": request_id,
                "purpose": "catalog",
                "url": BASE_URL,
                "method": "GET",
                "headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                    "Referer": BASE_URL,
                    "Origin": BASE_URL
                },
                "metadata": { "catalogId": catalog_id }
            }]
        }

    async def handleMeta(self, args):
        video_id = args.get('id', '')
        url_base64 = video_id.replace('selcuk:channel:', '').replace('selcuk:match:', '')
        url_base64 += '=' * (-len(url_base64) % 4)
        url = base64.b64decode(url_base64).decode('utf-8')

        print(f"📺 [SelcukSports Meta] Generating instructions for: {url[:80]}...")

        random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        request_id = f"selcuk-meta-{int(time.time()*1000)}-{random_id}"
        
        stream_id = ''
        try:
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            stream_id = query_params.get('id', [''])[0]
        except Exception as e:
            print(f"   URL parse hatası: {e}")

        return {
            "instructions": [{
                "requestId": request_id,
                "purpose": "meta",
                "url": BASE_URL, # Ana sayfadan channelsData'yı alacağız
                "method": "GET",
                "headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": BASE_URL
                },
                "metadata": { "originalUrl": url, "streamId": stream_id }
            }]
        }

    async def handleStream(self, args):
        video_id = args.get('id', '')
        url_base64 = video_id.replace('selcuk:channel:', '').replace('selcuk:match:', '')
        url_base64 += '=' * (-len(url_base64) % 4)
        player_url = base64.b64decode(url_base64).decode('utf-8')

        print(f"🎬 [SelcukSports Stream] Generating instructions for: {player_url[:80]}...")

        full_player_url = player_url
        global DYNAMIC_PLAYER_DOMAIN
        if DYNAMIC_PLAYER_DOMAIN:
            try:
                old_parsed = urllib.parse.urlparse(full_player_url)
                if old_parsed.netloc:
                    full_player_url = full_player_url.replace(old_parsed.netloc, DYNAMIC_PLAYER_DOMAIN)
            except:
                pass
                
        if not full_player_url.startswith('http'):
            if full_player_url.startswith('//'):
                full_player_url = 'https:' + full_player_url
            elif full_player_url.startswith('/'):
                full_player_url = BASE_URL + full_player_url
            else:
                full_player_url = BASE_URL + '/' + full_player_url

        random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        request_id = f"selcuk-stream-{int(time.time()*1000)}-{random_id}"
        
        try:
            origin = urllib.parse.urlparse(full_player_url).scheme + "://" + urllib.parse.urlparse(full_player_url).netloc + "/"
        except:
            origin = full_player_url
            
        return {
            "instructions": [{
                "requestId": request_id,
                "purpose": "stream",
                "url": full_player_url,
                "method": "GET",
                "headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": origin
                },
                "metadata": { "originalPlayerUrl": full_player_url }
            }]
        }

    def parse_channels(self, body_str, catalog_id):
        channels = []
        
        match = re.search(r'const\s+channelsData\s*=\s*(\[[\s\S]*?\])\s*;', body_str)
        if not match:
            print('⚠️ channelsData bulunamadı')
            return channels
            
        global DYNAMIC_PLAYER_DOMAIN
        player_base = ""
        iframe_match = re.search(r'const\s+mainIframeUrl\s*=\s*["\']([^"\']+)["\']', body_str)
        if iframe_match:
            player_base = iframe_match.group(1)
            try:
                DYNAMIC_PLAYER_DOMAIN = urllib.parse.urlparse(player_base).netloc
            except:
                pass
        elif DYNAMIC_PLAYER_DOMAIN:
            player_base = f"https://{DYNAMIC_PLAYER_DOMAIN}/index.php?id="
            
        try:
            json_str = match.group(1).strip()
            channels_data = json.loads(json_str)
            print(f"✓ channelsData parse edildi: {len(channels_data)} kanal")
        except Exception as e:
            print(f"⚠️ channelsData JSON parse hatası: {e}")
            return channels

        for channel in channels_data:
            stream_id = channel.get('stream_url')
            channel_name = channel.get('name')
            channel_logo = channel.get('logo_url') or channel.get('logo') or channel.get('image') or channel.get('icon')
            
            if not stream_id or not channel_name:
                continue
                
            if catalog_id not in ['selcuk_live_matches', 'selcuk_all_channels']:
                filter_regex = get_channel_filter(catalog_id)
                if filter_regex and not filter_regex.search(channel_name):
                    continue
                    
            full_url = player_base + stream_id
            id_b64 = base64.b64encode(full_url.encode('utf-8')).decode('utf-8').replace('=', '')
            channel_id = f"selcuk:channel:{id_b64}"
            
            poster_url = f"https://via.placeholder.com/300x450/1a1a1a/ffffff?text={urllib.parse.quote(channel_name)}"
            if channel_logo and isinstance(channel_logo, str):
                if channel_logo.startswith('http'): poster_url = channel_logo
                elif channel_logo.startswith('data:'): poster_url = channel_logo
                elif channel_logo.startswith('//'): poster_url = 'https:' + channel_logo
                elif channel_logo.startswith('/'): poster_url = BASE_URL + channel_logo
                else: poster_url = BASE_URL + '/' + channel_logo
                
            channels.append({
                "id": channel_id,
                "type": "tv",
                "name": f"📺 {channel_name}",
                "poster": poster_url,
                "posterShape": "square",
                "description": f"{channel_name} - Canlı Yayın"
            })
            
        return channels
        
    def parse_live_matches(self, body_str):
        matches = []
        
        match = re.search(r'const\s+channelsData\s*=\s*(\[[\s\S]*?\])\s*;', body_str)
        if not match:
            print('⚠️ channelsData bulunamadı (live matches)')
            return matches
            
        global DYNAMIC_PLAYER_DOMAIN
        player_base = ""
        iframe_match = re.search(r'const\s+mainIframeUrl\s*=\s*["\']([^"\']+)["\']', body_str)
        if iframe_match:
            player_base = iframe_match.group(1)
            try:
                DYNAMIC_PLAYER_DOMAIN = urllib.parse.urlparse(player_base).netloc
            except:
                pass
        elif DYNAMIC_PLAYER_DOMAIN:
            player_base = f"https://{DYNAMIC_PLAYER_DOMAIN}/index.php?id="
            
        try:
            json_str = match.group(1).strip()
            channels_data = json.loads(json_str)
            print(f"✓ channelsData parse edildi: {len(channels_data)} kanal (live matches)")
        except Exception as e:
            print(f"⚠️ channelsData JSON parse hatası: {e}")
            return matches

        for channel in channels_data:
            stream_id = channel.get('stream_url')
            match_name = channel.get('name')
            channel_logo = channel.get('logo_url') or channel.get('logo') or channel.get('image') or channel.get('icon')
            
            if not stream_id or not match_name:
                continue
                
            full_url = player_base + stream_id
            id_b64 = base64.b64encode(full_url.encode('utf-8')).decode('utf-8').replace('=', '')
            match_id = f"selcuk:match:{id_b64}"
            
            poster_url = f"https://via.placeholder.com/300x450/ff0000/ffffff?text={urllib.parse.quote('CANLI')}"
            if channel_logo and isinstance(channel_logo, str):
                if channel_logo.startswith('http'): poster_url = channel_logo
                elif channel_logo.startswith('data:'): poster_url = channel_logo
                elif channel_logo.startswith('//'): poster_url = 'https:' + channel_logo
                elif channel_logo.startswith('/'): poster_url = BASE_URL + channel_logo
                else: poster_url = BASE_URL + '/' + channel_logo
                
            matches.append({
                "id": match_id,
                "type": "tv",
                "name": f"🔴 {match_name}",
                "poster": poster_url,
                "posterShape": "square",
                "description": f"Canlı: {match_name}"
            })
            
        return matches

    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body', '')
        url = fetchResult.get('url', '')
        metadata = fetchResult.get('metadata') or {}
        
        print(f"\n⚙️ [SelcukSports Process] Purpose: {purpose}")
        print(f"   URL: {str(url)[:80]}...")

        if isinstance(body, bytes):
            body_str = body.decode('utf-8', errors='ignore')
        else:
            body_str = str(body)

        if purpose == 'catalog':
            catalog_id = metadata.get('catalogId')
            metas = []
            
            if catalog_id == 'selcuk_live_matches':
                metas = self.parse_live_matches(body_str)
            else:
                metas = self.parse_channels(body_str, catalog_id)
                
            unique_metas = {}
            for m in metas:
                if m['name'] not in unique_metas:
                    unique_metas[m['name']] = m
                    
            metas_list = list(unique_metas.values())
            print(f"✅ Found {len(metas_list)} items in catalog")
            return {"metas": metas_list}

        if purpose == 'meta':
            stream_id = metadata.get('streamId', '')
            original_url = metadata.get('originalUrl', url)
            channel_name = 'Canlı Yayın'
            channel_logo = None
            
            print(f"   Stream ID: {stream_id}")
            
            match = re.search(r'const\s+channelsData\s*=\s*(\[[\s\S]*?\])\s*;', body_str)
            if match:
                try:
                    json_str = match.group(1).strip()
                    channels_data = json.loads(json_str)
                    
                    channel = next((ch for ch in channels_data if ch.get('stream_url') == stream_id), None)
                    if channel:
                        channel_name = channel.get('name') or channel_name
                        channel_logo = channel.get('logo_url') or channel.get('logo') or channel.get('image') or channel.get('icon')
                        print(f"   ✓ Kanal bulundu: {channel_name}")
                        if channel_logo:
                            print(f"   ✓ Logo: {channel_logo}")
                    else:
                        print(f"   ⚠️ Kanal bulunamadı (streamId: {stream_id})")
                except Exception as e:
                    print(f"   ⚠️ channelsData parse hatası: {e}")
            else:
                print("   ⚠️ channelsData bulunamadı")
                
            enc_title = urllib.parse.quote(channel_name)
            poster_url = f"https://via.placeholder.com/300x450/1a1a1a/ffffff?text={enc_title}"
            background_url = f"https://via.placeholder.com/1920x1080/1a1a1a/ffffff?text={enc_title}"
            
            if channel_logo and isinstance(channel_logo, str):
                if channel_logo.startswith('http'):
                    poster_url = background_url = channel_logo
                elif channel_logo.startswith('data:'):
                    poster_url = background_url = channel_logo
                elif channel_logo.startswith('//'):
                    poster_url = background_url = 'https:' + channel_logo
                elif channel_logo.startswith('/'):
                    poster_url = background_url = BASE_URL + channel_logo
                else:
                    poster_url = background_url = BASE_URL + '/' + channel_logo
                    
            url_id = base64.b64encode(original_url.encode('utf-8')).decode('utf-8').replace('=', '')
            return {
                "meta": {
                    "id": f"selcuk:{url_id}",
                    "type": "tv",
                    "name": channel_name,
                    "poster": poster_url,
                    "posterShape": "square",
                    "background": background_url,
                    "description": f"{channel_name} - Canlı Yayın",
                    "genres": ["Spor", "Canlı TV"]
                }
            }

        if purpose == 'stream':
            streams = []
            full_player_url = metadata.get('originalPlayerUrl', url)
            
            m3u8_patterns = [
                re.compile(r'this\.baseStreamUrl\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE),
                re.compile(r'https?:\/\/[a-z0-9]+\.[a-z0-9]+\.[a-z0-9.]+\/[^"\'\s]*playlist\.m3u8', re.IGNORECASE),
                re.compile(r'https?:\/\/[a-z0-9]+\.[a-z0-9]+\.[a-z0-9.]+\/[^"\'\s]*index\.m3u8', re.IGNORECASE),
                re.compile(r'["\']?file["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', re.IGNORECASE),
                re.compile(r'["\']?source["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', re.IGNORECASE),
                re.compile(r'["\']?src["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', re.IGNORECASE),
                re.compile(r'["\']?url["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', re.IGNORECASE),
                re.compile(r'["\']?hlsUrl["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', re.IGNORECASE),
                re.compile(r'(https?:\/\/[^"\'\s<>]+\.m3u8[^\s"\'<>]*)', re.IGNORECASE)
            ]
            
            m3u8_link = None
            base_stream_url = None

            for i, pattern in enumerate(m3u8_patterns):
                match = pattern.search(body_str)
                if match:
                    m3u8_link = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    m3u8_link = m3u8_link.replace('\\', '').replace('\\"', '"')
                    
                    if i == 0:
                        base_stream_url = m3u8_link
                        print(f"✓ baseStreamUrl bulundu: {base_stream_url}")
                        try:
                            parsed_url = urllib.parse.urlparse(full_player_url)
                            query_params = urllib.parse.parse_qs(parsed_url.query)
                            stream_id = query_params.get('id', ['selcukbeinsports1'])[0]
                            m3u8_link = f"{base_stream_url}{stream_id}/playlist.m3u8"
                            print(f"✓ M3U8 linki oluşturuldu: {m3u8_link}")
                        except:
                            m3u8_link = f"{base_stream_url}selcukbeinsports1/playlist.m3u8"
                            print(f"✓ M3U8 linki oluşturuldu (fallback): {m3u8_link}")
                    else:
                        print(f"✓ M3U8 bulundu (Pattern #{i+1}): {m3u8_link[:80]}...")
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
                    "name": "SelcukSports HD",
                    "title": "SelcukSports HD (M3U8 + Headers)",
                    "url": m3u8_link,
                    "behaviorHints": {
                        "notWebReady": True,
                        "bingeGroup": "selcuk-live",
                        "proxyHeaders": {
                            "request": stream_headers
                        }
                    }
                })
                
                streams.append({
                    "name": "SelcukSports (Header'sız)",
                    "title": "SelcukSports HD (M3U8)",
                    "url": m3u8_link,
                    "behaviorHints": {
                        "notWebReady": True,
                        "bingeGroup": "selcuk-live"
                    }
                })
            else:
                print("⚠️ M3U8 bulunamadı, iframe player kullanılacak")
                streams.append({
                    "name": "SelcukSports HD (İframe)",
                    "title": "SelcukSports HD (İframe Player)",
                    "url": full_player_url,
                    "behaviorHints": {
                        "notWebReady": False,
                        "bingeGroup": "selcuk-live"
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
