import asyncio
import base64
import json
import re
import time
import random
import urllib.parse
from bs4 import BeautifulSoup

DYNAMIC_BASE_URLS = [
    'http://www.selcuksportshd1872.xyz',
]

BASE_URL = 'https://www.selcuksportshd6bec1961ef.xyz'
DYNAMIC_PLAYER_DOMAIN = ''

def setDynamicBaseUrl(url):
    global BASE_URL
    if url and url.startswith('http'):
        BASE_URL = url[:-1] if url.endswith('/') else url
        print(f"✅ [SporCafe] Dynamic URL updated: {BASE_URL}")
        return True
    return False

def getDynamicBaseUrls():
    return DYNAMIC_BASE_URLS

def get_channel_filter(catalog_id):
    filters = {
        'selcukshd_bein_sports': re.compile(r'bein\s*sports|beIN\s*SPORTS', re.IGNORECASE),
        'selcukshd_s_sport': re.compile(r'^s\s*sport|S\s*Sport', re.IGNORECASE),
        'selcukshd_tivibu_spor': re.compile(r'tivibu\s*spor|Tivibu\s*Spor', re.IGNORECASE),
        'selcukshd_tabii_spor': re.compile(r'tabii\s*spor|tabii\s*Spor', re.IGNORECASE),
        'selcukshd_other_sports': re.compile(r'eurosport|nba\s*tv|trt\s*spor|a\s*spor|smart\s*spor|dazn|ufc|sky\s*sports|motor|nat\s*geo|discovery|history|bbc|nfl|mlb', re.IGNORECASE)
    }
    return filters.get(catalog_id)

class SporCafeScraper:
    def __init__(self):
        self.manifest = {
            "id": "community.selcuksportshd",
            "version": "1.0.0",
            "name": "SelcukSports HD",
            "description": "Canlı spor kanalları - SelcukSportsHD için Stremio eklentisi (Instruction Mode)",
            "logo": "https://play-lh.googleusercontent.com/iWAT8chbA_tavljXfjTqxzc9pAnAiSK72Ikt5uouEQ7CO-af4R8Omvn8f_ypHk1ZFw0=w240-h480-rw",
            "resources": ["catalog", "meta", "stream"],
            "types": ["tv", "channel"],
            "catalogs": [
                { "type": "tv", "id": "selcukshd_live_matches", "name": "🔴 Canlı Maçlar", "extra": [{"name": "skip", "isRequired": False}] },
                { "type": "tv", "id": "selcukshd_bein_sports", "name": "⚽ beIN SPORTS", "extra": [{"name": "skip", "isRequired": False}] },
                { "type": "tv", "id": "selcukshd_s_sport", "name": "🏀 S Sport", "extra": [{"name": "skip", "isRequired": False}] },
                { "type": "tv", "id": "selcukshd_tivibu_spor", "name": "📺 Tivibu Spor", "extra": [{"name": "skip", "isRequired": False}] },
                { "type": "tv", "id": "selcukshd_tabii_spor", "name": "📱 tabii Spor", "extra": [{"name": "skip", "isRequired": False}] },
                { "type": "tv", "id": "selcukshd_other_sports", "name": "🎾 Diğer Spor Kanalları", "extra": [{"name": "skip", "isRequired": False}] },
                { "type": "tv", "id": "selcukshd_all_channels", "name": "📡 Tüm Kanallar (7/24)", "extra": [{"name": "skip", "isRequired": False}] }
            ],
            "idPrefixes": ["selcukshd"]
        }

    def getManifest(self):
        return self.manifest

    async def handleCatalog(self, args):
        catalog_id = args.get('id')
        print(f"\n🎯 [SelcukSportsHD Catalog] Generating instructions...")
        print(f"📋 Catalog ID: {catalog_id}")

        random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        request_id = f"selcukshd-catalog-{catalog_id}-{int(time.time()*1000)}-{random_id}"
        
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
        url_base64 = video_id.replace('selcukshd:channel:', '').replace('selcukshd:match:', '')
        url_base64 += '=' * (-len(url_base64) % 4)
        url = base64.b64decode(url_base64).decode('utf-8')

        print(f"📺 [SelcukSportsHD Meta] Generating instructions for: {url[:80]}...")

        random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=8))
        request_id = f"selcukshd-meta-{int(time.time()*1000)}-{random_id}"
        
        return {
            "instructions": [{
                "requestId": request_id,
                "purpose": "meta",
                "url": url,
                "method": "GET",
                "headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                    "Referer": BASE_URL
                }
            }]
        }

    async def handleStream(self, args):
        video_id = args.get('id', '')
        url_base64 = video_id.replace('selcukshd:channel:', '').replace('selcukshd:match:', '')
        url_base64 += '=' * (-len(url_base64) % 4)
        player_url = base64.b64decode(url_base64).decode('utf-8')

        print(f"🎬 [SelcukSportsHD Stream] Generating instructions for: {player_url[:80]}...")

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
        request_id = f"selcukshd-stream-{int(time.time()*1000)}-{random_id}"
        
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
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                    "Referer": origin
                },
                "metadata": { "originalPlayerUrl": full_player_url }
            }]
        }

    def parse_channels(self, soup, catalog_id):
        channels = []
        tab_selector = 'div.channel-list[data-tab-content]'
        
        if catalog_id == 'selcukshd_live_matches':
            tab_selector = 'div.channel-list[id=\"tab1\"]'
        elif catalog_id in ['selcukshd_bein_sports', 'selcukshd_s_sport', 'selcukshd_tivibu_spor', 'selcukshd_other_sports', 'selcukshd_all_channels']:
            tab_selector = 'div.channel-list[id=\"tab5\"]'
            
        tab = soup.select_one(tab_selector)
        if not tab: return channels
        
        global DYNAMIC_PLAYER_DOMAIN
        for el in tab.select('li a[data-url]'):
            url = el.get('data-url')
            if url:
                try:
                    netloc = urllib.parse.urlparse(url).netloc
                    if netloc and "player" in netloc:
                        DYNAMIC_PLAYER_DOMAIN = netloc
                except:
                    pass
                    
            name_el = el.select_one('div.name')
            time_el = el.select_one('time')
            
            name = name_el.text.strip() if name_el else ''
            time_str = time_el.text.strip() if time_el else ''
            
            logo = None
            if url and '#poster=' in url:
                try:
                    poster_match = re.search(r'#poster=([^&]+)', url)
                    if poster_match:
                        logo = urllib.parse.unquote(poster_match.group(1))
                except Exception as e:
                    print(f"Logo decode hatası: {e}")
                    
            if not logo:
                img = el.select_one('img')
                if img:
                    logo = img.get('src') or img.get('data-src')
                if not logo:
                    logo = el.get('data-logo') or el.get('data-image')
                    
            if not url or not name:
                continue
                
            if catalog_id not in ['selcukshd_live_matches', 'selcukshd_all_channels']:
                filter_regex = get_channel_filter(catalog_id)
                if filter_regex and not filter_regex.search(name):
                    continue
                    
            id_b64 = base64.b64encode(url.encode('utf-8')).decode('utf-8').replace('=', '')
            channel_id = f"selcukshd:channel:{id_b64}"
            
            poster_url = f"https://via.placeholder.com/300x450/1a1a1a/ffffff?text={urllib.parse.quote(name)}"
            if logo:
                if logo.startswith('http'): poster_url = logo
                elif logo.startswith('//'): poster_url = 'https:' + logo
                elif logo.startswith('/'): poster_url = BASE_URL + logo
                elif not logo.startswith('data:'): poster_url = BASE_URL + '/' + logo
                
            channels.append({
                "id": channel_id,
                "type": "tv",
                "name": f"📺 {name}",
                "poster": poster_url,
                "posterShape": "square",
                "description": f"{name} - {time_str or 'Canlı Yayın'}"
            })
            
        print(f"✓ {len(channels)} kanal parse edildi ({catalog_id})")
        return channels
        
    def parse_live_matches(self, soup):
        matches = []
        tab = soup.select_one('div.channel-list[id=\"tab1\"]')
        if not tab: return matches
        
        global DYNAMIC_PLAYER_DOMAIN
        for el in tab.select('li a[data-url]'):
            url = el.get('data-url')
            if url:
                try:
                    netloc = urllib.parse.urlparse(url).netloc
                    if netloc and "player" in netloc:
                        DYNAMIC_PLAYER_DOMAIN = netloc
                except:
                    pass
                    
            name_el = el.select_one('div.name')
            time_el = el.select_one('time')
            
            name = name_el.text.strip() if name_el else ''
            time_str = time_el.text.strip() if time_el else ''
            
            logo = None
            if url and '#poster=' in url:
                try:
                    poster_match = re.search(r'#poster=([^&]+)', url)
                    if poster_match:
                        logo = urllib.parse.unquote(poster_match.group(1))
                except Exception as e:
                    print(f"Logo decode hatası (live match): {e}")
                    
            if not logo:
                img = el.select_one('img')
                if img:
                    logo = img.get('src') or img.get('data-src')
                if not logo:
                    logo = el.get('data-logo') or el.get('data-image')
                    
            if not url or not name:
                continue
                
            id_b64 = base64.b64encode(url.encode('utf-8')).decode('utf-8').replace('=', '')
            match_id = f"selcukshd:match:{id_b64}"
            
            poster_url = f"https://via.placeholder.com/300x450/ff0000/ffffff?text={urllib.parse.quote('CANLI')}"
            if logo:
                if logo.startswith('http'): poster_url = logo
                elif logo.startswith('//'): poster_url = 'https:' + logo
                elif logo.startswith('/'): poster_url = BASE_URL + logo
                elif not logo.startswith('data:'): poster_url = BASE_URL + '/' + logo
                
            matches.append({
                "id": match_id,
                "type": "tv",
                "name": f"🔴 {name}",
                "poster": poster_url,
                "posterShape": "square",
                "description": f"Canlı: {name} - {time_str}"
            })
            
        print(f"✓ {len(matches)} canlı maç parse edildi")
        return matches

    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body', '')
        url = fetchResult.get('url', '')
        metadata = fetchResult.get('metadata') or {}
        
        print(f"\n⚙️ [SelcukSportsHD Process] Purpose: {purpose}")
        print(f"   URL: {str(url)[:80]}...")

        if purpose == 'catalog':
            catalog_id = metadata.get('catalogId')
            metas = []
            
            soup = BeautifulSoup(body, 'html.parser')
            
            if catalog_id == 'selcukshd_live_matches':
                metas = self.parse_live_matches(soup)
            else:
                metas = self.parse_channels(soup, catalog_id)
                
            unique_metas = {}
            for m in metas:
                if m['name'] not in unique_metas:
                    unique_metas[m['name']] = m
                    
            metas_list = list(unique_metas.values())
            print(f"✅ Found {len(metas_list)} items in catalog")
            return {"metas": metas_list}

        if purpose == 'meta':
            soup = BeautifulSoup(body, 'html.parser')
            
            title_el = soup.select_one('title')
            title = title_el.text.strip() if title_el else ""
            if not title:
                h1_el = soup.select_one('h1')
                title = h1_el.text.strip() if h1_el else 'Canlı Yayın'

            logo = None
            og_img = soup.select_one('meta[property="og:image"]')
            tw_img = soup.select_one('meta[name="twitter:image"]')
            channel_logo = soup.select_one('img.channel-logo')
            logo_img = soup.select_one('img.logo')
            chan_info_img = soup.select_one('.channel-info img')
            
            if og_img and og_img.get('content'): logo = og_img.get('content')
            elif tw_img and tw_img.get('content'): logo = tw_img.get('content')
            elif channel_logo and channel_logo.get('src'): logo = channel_logo.get('src')
            elif logo_img and logo_img.get('src'): logo = logo_img.get('src')
            elif chan_info_img and chan_info_img.get('src'): logo = chan_info_img.get('src')
            
            enc_title = urllib.parse.quote(title)
            poster_url = f"https://via.placeholder.com/300x450/1a1a1a/ffffff?text={enc_title}"
            background_url = f"https://via.placeholder.com/1920x1080/1a1a1a/ffffff?text={enc_title}"
            
            if logo:
                if logo.startswith('http'):
                    poster_url = background_url = logo
                elif logo.startswith('//'):
                    poster_url = background_url = 'https:' + logo
                elif logo.startswith('/'):
                    poster_url = background_url = BASE_URL + logo
                elif not logo.startswith('data:'):
                    poster_url = background_url = BASE_URL + '/' + logo
                    
            url_id = base64.b64encode(url.encode('utf-8')).decode('utf-8').replace('=', '')
            return {
                "meta": {
                    "id": f"selcukshd:{url_id}",
                    "type": "tv",
                    "name": title,
                    "poster": poster_url,
                    "posterShape": "square",
                    "background": background_url,
                    "description": f"{title} - Canlı Yayın",
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
                re.compile(r'["\']?url["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', re.IGNORECASE),
                re.compile(r'(https?:\/\/[^"\'\s<>]+\.m3u8[^\s"\'<>]*)', re.IGNORECASE)
            ]
            
            m3u8_link = None
            
            if isinstance(body, bytes):
                body_str = body.decode('utf-8', errors='ignore')
            else:
                body_str = str(body)

            for i, pattern in enumerate(m3u8_patterns):
                match = pattern.search(body_str)
                if match:
                    m3u8_link = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    m3u8_link = m3u8_link.replace('\\', '').replace('\\"', '"')
                    
                    if i == 0:
                        try:
                            parsed_url = urllib.parse.urlparse(full_player_url)
                            query_params = urllib.parse.parse_qs(parsed_url.query)
                            stream_id = query_params.get('id', ['selcukbeinsports1'])[0]
                            m3u8_link = f"{m3u8_link}{stream_id}/playlist.m3u8"
                        except:
                            m3u8_link = f"{m3u8_link}selcukbeinsports1/playlist.m3u8"
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
                    "name": "SelcukSportsHD",
                    "title": "SelcukSportsHD (M3U8 + Headers)",
                    "url": m3u8_link,
                    "behaviorHints": {
                        "notWebReady": True,
                        "bingeGroup": "selcukshd-live",
                        "proxyHeaders": {
                            "request": stream_headers
                        }
                    }
                })
                
                streams.append({
                    "name": "SelcukSportsHD (Header'sız)",
                    "title": "SelcukSportsHD (M3U8)",
                    "url": m3u8_link,
                    "behaviorHints": {
                        "notWebReady": True,
                        "bingeGroup": "selcukshd-live"
                    }
                })
            else:
                streams.append({
                    "name": "SelcukSportsHD (İframe)",
                    "title": "SelcukSportsHD (İframe Player)",
                    "url": full_player_url,
                    "behaviorHints": {
                        "notWebReady": False,
                        "bingeGroup": "selcukshd-live"
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
