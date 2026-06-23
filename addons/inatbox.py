import base64
import json
import re
import urllib.parse
import urllib.request
import random
import time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

def base64_encode_safe(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8').replace('=', '')

def decrypt_aes(encrypted_data_with_iv, key_str):
    try:
        key = key_str.encode('utf8')
        iv = key_str.encode('utf8')
        
        encrypted_part1 = encrypted_data_with_iv.split(':')[0]
        cipher1 = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor1 = cipher1.decryptor()
        
        pad1 = encrypted_part1 + '=' * (-len(encrypted_part1) % 4)
        dec1_padded = decryptor1.update(base64.b64decode(pad1)) + decryptor1.finalize()
        unpadder1 = padding.PKCS7(128).unpadder()
        dec1 = unpadder1.update(dec1_padded) + unpadder1.finalize()
        decrypted1 = dec1.decode('utf8')
        
        encrypted_part2 = decrypted1.split(':')[0]
        cipher2 = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor2 = cipher2.decryptor()
        
        pad2 = encrypted_part2 + '=' * (-len(encrypted_part2) % 4)
        dec2_padded = decryptor2.update(base64.b64decode(pad2)) + decryptor2.finalize()
        unpadder2 = padding.PKCS7(128).unpadder()
        dec2 = unpadder2.update(dec2_padded) + unpadder2.finalize()
        
        print(f"🐛 [InatBox Debug] Decrypted data successfully. Length: {len(dec2)}")
        return dec2.decode('utf8')
    except Exception as e:
        import traceback
        print(f"❌ Decryption error: {e}")
        traceback.print_exc()
        return None

def vk_source_fix(url):
    if url and url.startswith('act'):
        return f"https://vk.com/al_video.php?{url}"
    return url

def determine_content_type(item, catalog_id):
    dt = item.get('diziType')
    if dt in ['dizi', 'dizi_mode']: return 'series'
    if dt in ['film', 'film_mode']: return 'movie'
    if catalog_id in ['yabanci-dizi', 'yerli-dizi']: return 'series'
    ct = item.get('chType')
    if ct:
        if ct in ['live_url', 'live_mode', 'tekli_regex_lb_sh_3']: return 'tv'
        return 'movie'
    return 'movie'

class InatBoxScraper:
    def __init__(self):
        self.CONFIG = {
            'contentUrl': 'https://diziboxen.help/CDN/001/002/dizibox',
            'aesKey': 'GxGQWghI0aSiADee',
            'userAgent': 'speedrestapi'
        }
        
        self.CATALOG_URLS = {
            'spor': 'https://sprboxs.bar/CDN/001/SPR/spor_v3.php',
            'tod': 'https://sprboxs.bar/CDN/001/SPR/ccc/a/index.php',
            'cf': "https://dizilabmedia.click/CDN/001/002/dizilab/cf.php",
            'ct': "https://dizilabmedia.click/CDN/001/002/dizilab/ct.php",
            'sinema': f"{self.CONFIG['contentUrl']}/tv/sinema.php",
            'dini': f"{self.CONFIG['contentUrl']}/tv/dini.php",
            'gain': f"{self.CONFIG['contentUrl']}/ga/index.php",
            'netflix': f"{self.CONFIG['contentUrl']}/nf/index.php",
            'disney': f"{self.CONFIG['contentUrl']}/dsny/index.php",
            'amazon': f"{self.CONFIG['contentUrl']}/amz/index.php",
            'hbo': f"{self.CONFIG['contentUrl']}/hb/index.php",
            'tabii': f"{self.CONFIG['contentUrl']}/tbi/index.php",
            'yabanci-dizi': f"{self.CONFIG['contentUrl']}/yabanci-dizi/index.php",
            'yerli-dizi': f"{self.CONFIG['contentUrl']}/yerli-dizi/index.php"
        }

        self.manifest = {
            'id': 'com.keyiflerolsun.inatbox',
            'version': '3.0.8',
            'name': 'InatBox',
            'description': 'Turkish TV channels, movies and series streaming (Python Port)',
            'logo': 'https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEh3vCp6N1K4bECoYRQD-cisJF2_6V_Hk01ZhDmoPR2JuM8O5qr4MqrPO1munM9cRlleBBSK6odYhLtDBWv4E3vhPhynlmS5hVVtJZShHoGA5REQ8_3v8SIlccTEqzVQu2UJyNYQdJNrKIfWy66RQeT0D-CcmFCbHPz5023H6p2v5fv4NVloZ5Rqo_yGrIY/s320/iNat-Box-App.png',
            'resources': ['catalog', 'meta', 'stream'],
            'types': ['movie', 'series', 'tv'],
            'catalogs': [
                {'type': 'tv', 'id': 'spor', 'name': '⚽ Spor Kanalları', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'tod', 'name': '🎬 TOD', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'tv', 'id': 'cf', 'name': '👧 Çocuk Filmleri', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'tv', 'id': 'ct', 'name': '👧 Çocuk TV', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'tv', 'id': 'sinema', 'name': '🎬 Sinema Kanalları', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'tv', 'id': 'dini', 'name': '🕌 Dini Kanallar', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                
                {'type': 'movie', 'id': 'gain', 'name': '🎬 Gain', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'netflix', 'name': '🎬 Netflix', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'disney', 'name': '🎬 Disney+', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'amazon', 'name': '🎬 Amazon Prime', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'hbo', 'name': '🎬 HBO Max', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'tabii', 'name': '🎬 Tabii', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                
                {'type': 'series', 'id': 'yabanci-dizi', 'name': '📺 Yabancı Diziler', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                {'type': 'series', 'id': 'yerli-dizi', 'name': '📺 Yerli Diziler', 'extra': [{'name': 'search', 'isRequired': False}, {'name': 'skip', 'isRequired': False}]},
                
                {'type': 'movie', 'id': 'inat_search', 'name': '🔍 Tümünde Ara', 'extra': [{'name': 'search', 'isRequired': True}, {'name': 'skip', 'isRequired': False}]}
            ],
            'idPrefixes': ['inatbox']
        }

    def getManifest(self):
        return self.manifest

    def _extract_tracks(self, content, sourceUrl, subtitles, audioTracks):
        """HTML/JS içeriğinden subtitle ve audio track çıkar"""
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
                    raw = re.sub(r',\s*\]', ']', raw)
                    tracksData = json.loads(raw)
                    
                    for track in tracksData:
                        kind = track.get('kind', '').lower()
                        file_url = track.get('file', '')
                        
                        if not file_url:
                            continue
                        
                        if not file_url.startswith('http'):
                            file_url = urllib.parse.urljoin(sourceUrl, file_url)
                        
                        label = track.get('label') or track.get('language') or ''
                        
                        if kind in ['captions', 'subtitles']:
                            sub_id = label.lower().replace(' ', '_') if label else 'tr'
                            if not any(s['url'] == file_url for s in subtitles):
                                subtitles.append({'id': sub_id, 'url': file_url, 'lang': label or 'Türkçe'})
                        elif kind in ['audio', 'audiotrack']:
                            audio_id = label.lower().replace(' ', '_') if label else 'default'
                            if not any(a['url'] == file_url for a in audioTracks):
                                audioTracks.append({'id': audio_id, 'url': file_url, 'lang': label or 'Orijinal'})
                    
                    if subtitles or audioTracks:
                        break
                except:
                    continue

    def _extract_item_subtitles(self, item, subtitles):
        try:
            chReg = item.get('chReg')
            if chReg and chReg != 'null':
                if isinstance(chReg, str): chReg = json.loads(chReg)
                if isinstance(chReg, list):
                    for regItem in chReg:
                        if regItem.get('Subtitle'):
                            for part in regItem['Subtitle'].split(','):
                                m = re.search(r'\[([^\]]+)\]', part)
                                if m:
                                    lang = m.group(1)
                                    subUrl = part.replace(f"[{lang}]", '').strip()
                                    if subUrl:
                                        sub_id = lang.lower().replace(' ', '_')
                                        if not any(s['url'] == subUrl for s in subtitles):
                                            subtitles.append({'id': sub_id, 'url': subUrl, 'lang': lang})
                        if regItem.get('SubtitleUrl'):
                            lang = regItem.get('SubtitleLang') or regItem.get('SubtitleName') or 'Türkçe'
                            sub_id = lang.lower().replace(' ', '_')
                            if not any(s['url'] == regItem['SubtitleUrl'] for s in subtitles):
                                subtitles.append({'id': sub_id, 'url': regItem['SubtitleUrl'], 'lang': lang})
        except Exception as e: print("EXCEPTION IN LOOP:", e)
        
        try:
            if item.get('SubtitleUrl'):
                lang = item.get('SubtitleLang') or item.get('SubtitleName') or 'Türkçe'
                sub_id = lang.lower().replace(' ', '_')
                if not any(s['url'] == item['SubtitleUrl'] for s in subtitles):
                    subtitles.append({'id': sub_id, 'url': item['SubtitleUrl'], 'lang': lang})
            if item.get('diziSubUrl'):
                lang = 'Türkçe'
                sub_id = 'tr'
                if not any(s['url'] == item['diziSubUrl'] for s in subtitles):
                    subtitles.append({'id': sub_id, 'url': item['diziSubUrl'], 'lang': lang})
        except Exception as e: print("EXCEPTION IN LOOP:", e)

    def get_aes_key(self, url):
        import string
        import random
        if url and 'rest' in url:
            return 'ge8vbw9439fz6pei'
            
        letters_and_digits = string.ascii_letters + string.digits
        random_key = ''.join(random.choice(letters_and_digits) for i in range(16))
        
        print(f"🔑 [Key Generator] {url} için üretilen yeni AES: {random_key}")
        return random_key

    def buildRequestBody(self, extraFields=None, aesKey=None):
        key = aesKey or self.CONFIG['aesKey']
        base = {'1': key, '0': key}
        if extraFields and extraFields.get('q'):
            base['q'] = extraFields['q']
        parts = [f"{urllib.parse.quote(str(k))}={urllib.parse.quote(str(v))}" for k, v in base.items()]
        return "&".join(parts)

    async def handleCatalog(self, args):
        catalogId = args.get('id')
        extra = args.get('extra', {})
        searchQuery = extra.get('search')
        skip = int(extra.get('skip', 0))
        
        print(f"📋 [InatBox Catalog] Catalog ID: {catalogId}, Search: {searchQuery}, Skip: {skip}")
        
        if catalogId == 'inat_search' or searchQuery:
            if not searchQuery:
                return {'instructions': []}
            requestId = f"inat-search-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
            searchUrl = f"{self.CONFIG['contentUrl']}/search.php"
            aesKey = self.get_aes_key(searchUrl)
            body = self.buildRequestBody({'q': searchQuery}, aesKey=aesKey)
            
            parsed = urllib.parse.urlparse(searchUrl)
            return {
                'instructions': [{
                    'requestId': requestId,
                    'purpose': 'catalog_search',
                    'url': searchUrl,
                    'method': 'POST',
                    'headers': {
                        'Cache-Control': 'no-cache',
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'Referer': 'https://speedrestapi.com/',
                        'X-Requested-With': 'com.bp.box',
                        'User-Agent': self.CONFIG['userAgent']
                    },
                    'body': body,
                    'metadata': {'catalogId': catalogId, 'searchQuery': searchQuery, 'aesKey': aesKey, 'skip': skip}
                }]
            }
            
        baseUrl = self.CATALOG_URLS.get(catalogId)
        if not baseUrl:
            print(f"❌ [InatBox Catalog] No URL mapped for {catalogId}")
            return {'instructions': []}
            
        aesKey = self.get_aes_key(baseUrl)
        requestBody = self.buildRequestBody(aesKey=aesKey)
        requestId = f"inat-catalog-{catalogId}-{int(time.time()*1000)}"
        parsed = urllib.parse.urlparse(baseUrl)
        
        return {
            'instructions': [{
                'requestId': requestId,
                'purpose': 'catalog',
                'url': baseUrl,
                'method': 'POST',
                'headers': {
                    'Cache-Control': 'no-cache',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Referer': 'https://speedrestapi.com/',
                    'X-Requested-With': 'com.bp.box',
                    'User-Agent': self.CONFIG['userAgent']
                },
                'body': requestBody,
                'metadata': {'catalogId': catalogId, 'aesKey': aesKey, 'skip': skip}
            }]
        }

    async def handleMeta(self, args):
        try:
            padded = args.get('id', '').replace('inatbox:', '')
            padded += '=' * (-len(padded) % 4)
            itemData = base64.b64decode(padded).decode('utf8')
            item = json.loads(itemData)
        except Exception as e:
            print(f"Error parsing meta id: {e}")
            return {'instructions': []}
            
        print('📺 [InatBox Meta] for', item.get('diziName') or item.get('chName'))
        
        if item.get('diziType') and item.get('diziUrl'):
            requestId = f"inat-meta-{int(time.time()*1000)}"
            parsed = urllib.parse.urlparse(item.get('diziUrl'))
            aesKey = self.get_aes_key(item.get('diziUrl'))
            body = self.buildRequestBody(aesKey=aesKey)
            return {
                'instructions': [{
                    'requestId': requestId,
                    'purpose': 'meta_series_seasons' if item.get('diziType') in ['dizi', 'dizi_mode'] else 'meta',
                    'url': item.get('diziUrl'),
                    'method': 'POST',
                    'headers': {
                        'Cache-Control': 'no-cache',
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'Referer': 'https://speedrestapi.com/',
                        'X-Requested-With': 'com.bp.box',
                        'User-Agent': self.CONFIG['userAgent']
                    },
                    'body': body,
                    'metadata': {'originalItem': item, 'aesKey': aesKey}
                }],
                'metadata': {'originalItem': item, 'aesKey': aesKey}
            }
            
        if item.get('chUrl') and item.get('chType'):
            return {'instructions': [], 'metadata': {'originalItem': item, 'isChannel': True}}
            
        return {'instructions': [], 'metadata': {'originalItem': item}}

    async def handleStream(self, args):
        try:
            padded = args.get('id', '').replace('inatbox:', '')
            padded += '=' * (-len(padded) % 4)
            itemData = base64.b64decode(padded).decode('utf8')
            item = json.loads(itemData)
        except:
            return {'instructions': []}
            
        fetchUrl = None
        needsExtraction = False
        
        chType = item.get('chType')
        diziType = item.get('diziType')
        
        if diziType in ['film', 'film_mode']:
            fetchUrl = item.get('diziUrl')
            needsExtraction = True
        elif chType in ['tekli_regex_lb_sh_3', 'tekli_regex_lb_sh_3_mode']:
            fetchUrl = item.get('chUrl')
            needsExtraction = True
        elif chType and ('tekli_regex' in chType or chType == 'cable_sh'):
            extractUrl = vk_source_fix(item.get('chUrl') or item.get('url'))
            
            referer = 'https://speedrestapi.com/'
            ua = self.CONFIG['userAgent']
            
            try:
                chHeaders = item.get('chHeaders', [])
                if isinstance(chHeaders, list) and len(chHeaders) > 0 and isinstance(chHeaders[0], dict):
                    referer = chHeaders[0].get('Referer', referer)
                    ua = chHeaders[0].get('UserAgent', ua)
            except Exception as e: print("EXCEPTION IN LOOP:", e)
            
            if '.m3u8' in extractUrl or '.mpd' in extractUrl:
                print(f"🐛 [InatBox Debug] Returning direct stream link: {extractUrl}")
                return await self.processFetchResult({
                    'purpose': 'stream_extract',
                    'body': '',
                    'metadata': {'originalItem': item}
                })
            
            return {
                'instructions': [{
                    'requestId': f"inat-extract-{int(time.time()*1000)}",
                    'purpose': 'stream_extract',
                    'url': extractUrl,
                    'method': 'GET',
                    'headers': {
                        'Accept': '*/*',
                        'Referer': referer,
                        'User-Agent': ua,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    'metadata': {'originalItem': item, 'extractorNeeded': True}
                }],
                'metadata': {'originalItem': item, 'extractorNeeded': True}
            }
        elif chType in ['live_url', 'live_mode'] and (item.get('chUrl') or item.get('url')):
            streamUrl = vk_source_fix(item.get('chUrl') or item.get('url'))
            if not streamUrl:
                return {'streams': []}
                
            headersObject = {
                'User-Agent': self.CONFIG['userAgent'],
                'Referer': 'https://speedrestapi.com/',
                'X-Requested-With': 'com.bp.box'
            }
            
            try:
                chHeaders = item.get('chHeaders')
                if chHeaders and chHeaders != 'null':
                    if isinstance(chHeaders, str):
                        parsed = json.loads(chHeaders)
                        if isinstance(parsed, list) and len(parsed)>0:
                            headersObject.update(parsed[0])
                        elif isinstance(parsed, dict):
                            headersObject.update(parsed)
                    elif isinstance(chHeaders, list) and len(chHeaders)>0:
                        headersObject.update(chHeaders[0])
                    elif isinstance(chHeaders, dict):
                        headersObject.update(chHeaders)
            except Exception as e: print("EXCEPTION IN LOOP:", e)
            
            try:
                chReg = item.get('chReg')
                if chReg and chReg != 'null':
                    if isinstance(chReg, str):
                        parsed = json.loads(chReg)
                        if isinstance(parsed, list) and len(parsed)>0 and parsed[0].get('playSH2'):
                            headersObject['Cookie'] = parsed[0]['playSH2']
                    elif isinstance(chReg, list) and len(chReg)>0 and chReg[0].get('playSH2'):
                        headersObject['Cookie'] = chReg[0]['playSH2']
            except Exception as e: print("EXCEPTION IN LOOP:", e)
            
            return {'streams': [{
                'url': streamUrl,
                'name': item.get('diziName') or item.get('chName') or 'InatBox Stream',
                'title': item.get('diziName') or item.get('chName') or 'InatBox Stream',
                'behaviorHints': {
                    'notWebReady': False,
                    'httpHeaders': headersObject
                },
                'addonName': 'inatbox'
            }]}
            
        if fetchUrl:
            parsed = urllib.parse.urlparse(fetchUrl)
            aesKey = self.get_aes_key(fetchUrl)
            body = self.buildRequestBody(aesKey=aesKey)
            requestId = f"inat-stream-{int(time.time()*1000)}"
            return {
                'instructions': [{
                    'requestId': requestId,
                    'purpose': 'stream_fetch_for_extract' if needsExtraction else 'stream',
                    'url': fetchUrl,
                    'method': 'POST',
                    'headers': {
                        'Cache-Control': 'no-cache',
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'Referer': 'https://speedrestapi.com/',
                        'X-Requested-With': 'com.bp.box',
                        'User-Agent': self.CONFIG['userAgent']
                    },
                    'body': body,
                    'metadata': {'originalItem': item, 'needsExtraction': needsExtraction, 'aesKey': aesKey}
                }],
                'metadata': {'originalItem': item, 'needsExtraction': needsExtraction, 'aesKey': aesKey}
            }
            
        return {'streams': []}

    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body')
        metadata = fetchResult.get('metadata', {})
        url = fetchResult.get('url')
        addonManifestUrl = fetchResult.get('addonManifestUrl')
        
        print(f"🐛 [InatBox Debug] processFetchResult started. Purpose: {purpose}, Body length: {len(str(body))}", flush=True)
        if isinstance(body, str):
            print(f"🐛 [InatBox Debug] Body start: {repr(body[:100])}", flush=True)
        
        if not body and metadata:
            if metadata.get('directItem'):
                item = metadata['directItem']
                if item.get('chType') not in ['live_url', 'live_mode']:
                    return {'streams': []}
                
                streamUrl = vk_source_fix(item.get('chUrl') or item.get('url'))
                if not streamUrl:
                    return {'streams': []}
                    
                headersObject = {
                    'User-Agent': self.CONFIG['userAgent'],
                    'Referer': 'https://speedrestapi.com/',
                    'X-Requested-With': 'com.bp.box'
                }
                
                try:
                    chHeaders = item.get('chHeaders')
                    if chHeaders and chHeaders != 'null':
                        if isinstance(chHeaders, str):
                            parsed = json.loads(chHeaders)
                            if isinstance(parsed, list) and len(parsed)>0:
                                headersObject.update(parsed[0])
                            elif isinstance(parsed, dict):
                                headersObject.update(parsed)
                        elif isinstance(chHeaders, list) and len(chHeaders)>0:
                            headersObject.update(chHeaders[0])
                        elif isinstance(chHeaders, dict):
                            headersObject.update(chHeaders)
                except Exception as e: print("EXCEPTION IN LOOP:", e)
                
                try:
                    chReg = item.get('chReg')
                    if chReg and chReg != 'null':
                        if isinstance(chReg, str):
                            parsed = json.loads(chReg)
                            if isinstance(parsed, list) and len(parsed)>0 and parsed[0].get('playSH2'):
                                headersObject['Cookie'] = parsed[0]['playSH2']
                        elif isinstance(chReg, list) and len(chReg)>0 and chReg[0].get('playSH2'):
                            headersObject['Cookie'] = chReg[0]['playSH2']
                except Exception as e: print("EXCEPTION IN LOOP:", e)
                
                streams = [{
                    'url': streamUrl,
                    'name': item.get('diziName') or item.get('chName') or 'InatBox Stream',
                    'title': item.get('diziName') or item.get('chName') or 'InatBox Stream',
                    'behaviorHints': {
                        'notWebReady': False,
                        'httpHeaders': headersObject
                    },
                    'addonName': 'inatbox',
                    'addonManifestUrl': addonManifestUrl
                }]
                
                subtitles = []
                self._extract_item_subtitles(item, subtitles)
                if subtitles:
                    streams[0]['subtitles'] = subtitles
                    
                print(f"🐛 [InatBox Debug] Extracted direct stream: {streamUrl}")
                return {'streams': streams}
                
        isHTML = isinstance(body, str) and (body.strip().startswith('<!DOCTYPE') or body.strip().startswith('<html'))
        is_bad_body = not body or isHTML
        
        if is_bad_body and url and purpose in ['catalog', 'catalog_search', 'meta_series_seasons', 'meta_series_episodes', 'stream_fetch_for_extract']:
            print("⚠️ Bad body received from Flutter. Attempting domain rotation...", flush=True)
            parsed = urllib.parse.urlparse(url)
            headers = {
                'Cache-Control': 'no-cache',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': 'https://speedrestapi.com/',
                'X-Requested-With': 'com.bp.box',
                'User-Agent': self.CONFIG['userAgent']
            }
            body_data = self.buildRequestBody({'q': metadata.get('searchQuery', '')}, aesKey=metadata.get('aesKey')) if purpose == 'catalog_search' else self.buildRequestBody(aesKey=metadata.get('aesKey'))
            
            domains = ['diziboxen.help', 'foxlab.cfd', 'bozspra.cfd', 'dizilabmedia.click']
            current_domain = parsed.netloc
            if current_domain in domains:
                current_idx = domains.index(current_domain)
                next_idx = current_idx + 1
                if next_idx < len(domains):
                    next_domain = domains[next_idx]
                    new_url = url.replace(current_domain, next_domain)
                    new_parsed = urllib.parse.urlparse(new_url)
                    
                    requestId = f"inat-retry-{int(time.time()*1000)}-{random.randint(1000,9999)}"
                    print(f"🔄 Rotating to new domain: {next_domain}", flush=True)
                    return {
                        'instructions': [{
                            'requestId': requestId,
                            'purpose': purpose,
                            'url': new_url,
                            'method': 'POST',
                            'headers': headers,
                            'body': body_data,
                            'metadata': metadata
                        }]
                    }

        if purpose in ['stream_extract', 'meta']:
            pass 
        else:
            if not body or (isinstance(body, str) and (body.strip().startswith('<!DOCTYPE') or body.strip().startswith('<html'))):
                return {'metas': []} if purpose in ['catalog', 'catalog_search'] else {'streams': []}
                
        data = None
        if purpose not in ['stream_extract', 'meta']:
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict) and 'response' in parsed and isinstance(parsed['response'], str):
                    body_to_decrypt = parsed['response']
                else:
                    data = parsed
                    body_to_decrypt = None
            except:
                body_to_decrypt = body
                
            if not data and body_to_decrypt:
                aesKey = metadata.get('aesKey', self.CONFIG['aesKey'])
                
                item_for_aes = metadata.get('originalItem', {})
                if item_for_aes.get('chType') in ['tekli_regex_lb_sh_3', 'tekli_regex_lb_sh_3_mode']:
                    ch_reg = item_for_aes.get('chReg')
                    if ch_reg and isinstance(ch_reg, list) and len(ch_reg) > 0:
                        regex1 = ch_reg[0].get('Regex1')
                        if regex1 and regex1 != 'null':
                            aesKey = regex1
                            
                try:
                    decrypted = decrypt_aes(body_to_decrypt, aesKey)
                    if decrypted:
                        try:
                            data = json.loads(decrypted)
                        except Exception as json_err:
                            print(f"❌ [InatBox Debug] JSON Parse error after decryption: {json_err}")
                            print(f"🐛 [InatBox Debug] First 100 chars of decrypted: {repr(decrypted[:100])}")
                except Exception as e:
                    print(f"❌ [InatBox Debug] Outer decrypt error: {e}")
                    return {'metas': []} if purpose in ['catalog', 'catalog_search'] else {'streams': []}
            
            if not data:
                return {'metas': []} if purpose in ['catalog', 'catalog_search'] else {'streams': []}

        if purpose in ['catalog', 'catalog_search']:
            items = []
            if isinstance(data, list): items = data
            elif isinstance(data, dict):
                if 'results' in data and isinstance(data['results'], list): items = data['results']
                elif 'channels' in data and isinstance(data['channels'], list): items = data['channels']
                elif 'items' in data and isinstance(data['items'], list): items = data['items']
                elif 'data' in data and isinstance(data['data'], list): items = data['data']
                elif 'response' in data and isinstance(data['response'], list): items = data['response']
                else:
                    items = [v for k,v in data.items() if isinstance(v, dict)]
            
            print(f"🐛 [InatBox Debug] Parsed Data keys: {data.keys() if isinstance(data, dict) else type(data)}", flush=True)
            print(f"🐛 [InatBox Debug] Extracted {len(items)} items from payload", flush=True)
            
            skip = int(metadata.get('skip', 0))
            if skip > 0:
                items = items[skip:]
            items = items[:100]
            print(f"🐛 [InatBox Debug] After pagination (skip={skip}): {len(items)} items", flush=True)
            
            metas = []
            catalogId = metadata.get('catalogId', '')
            for item in items:
                try:
                    ctype = item.get('diziType') or item.get('chType')
                    if ctype in ['link', 'web']: continue
                    
                    name = item.get('diziName') or item.get('chName') or item.get('name') or item.get('title') or 'Unknown'
                    poster = item.get('diziImg') or item.get('chImg') or item.get('img') or item.get('poster')
                    meta_id = 'inatbox:' + base64_encode_safe(json.dumps(item))
                    
                    type_val = determine_content_type(item, catalogId)
                    posterShape = 'square' if type_val == 'tv' else 'poster'
                    
                    metas.append({
                        'id': meta_id,
                        'type': type_val,
                        'name': name,
                        'poster': poster,
                        'posterShape': posterShape,
                        'description': item.get('diziDetay') or item.get('description') or '',
                        'releaseInfo': item.get('diziYear') or item.get('year') or '',
                        'addonName': 'inatbox',
                        'addonManifestUrl': addonManifestUrl
                    })
                except Exception as e:
                    print(f"Error processing item: {e}")
            return {'metas': metas}

        if purpose == 'stream_extract':
            item = metadata.get('originalItem')
            if not item: return {'streams': []}
            
            ch_name_str = item.get('chName') or item.get('diziName') or ''
            lang_tag = 'TR' if ' TR' in ch_name_str or '-TR' in ch_name_str or '- TR' in ch_name_str else 'EN' if ' EN' in ch_name_str or '-EN' in ch_name_str or '- EN' in ch_name_str else ''
            base_name = f"InatBox {lang_tag}".strip()
            
            sourceUrl = item.get('chUrl') or item.get('url')
            streams = []
            subtitles = []
            audioTracks = []
            
            self._extract_item_subtitles(item, subtitles)
            if body and isinstance(body, str):
                self._extract_tracks(body, sourceUrl, subtitles, audioTracks)
                
            if '.m3u8' in sourceUrl or '.mpd' in sourceUrl:
                headersObject = {'User-Agent': self.CONFIG['userAgent'], 'Referer': ''}
                try:
                    chHeaders = item.get('chHeaders')
                    if chHeaders and chHeaders != 'null':
                        if isinstance(chHeaders, str):
                            parsed = json.loads(chHeaders)
                            if isinstance(parsed, list) and len(parsed)>0: headersObject.update(parsed[0])
                            elif isinstance(parsed, dict): headersObject.update(parsed)
                        elif isinstance(chHeaders, list) and len(chHeaders)>0: headersObject.update(chHeaders[0])
                        elif isinstance(chHeaders, dict): headersObject.update(chHeaders)
                except Exception as e: print("EXCEPTION IN LOOP:", e)
                
                try:
                    chReg = item.get('chReg')
                    if chReg and chReg != 'null':
                        if isinstance(chReg, str):
                            parsed = json.loads(chReg)
                            if isinstance(parsed, list) and len(parsed)>0 and parsed[0].get('playSH2'):
                                headersObject['Cookie'] = parsed[0]['playSH2']
                        elif isinstance(chReg, list) and len(chReg)>0 and chReg[0].get('playSH2'):
                            headersObject['Cookie'] = chReg[0]['playSH2']
                except Exception as e: print("EXCEPTION IN LOOP:", e)
                
                stream = {
                    'url': sourceUrl,
                    'name': f"{base_name} (Direct)",
                    'title': ch_name_str or 'Direct Stream',
                    'behaviorHints': {'notWebReady': False, 'httpHeaders': headersObject},
                    'addonName': 'inatbox',
                    'addonManifestUrl': addonManifestUrl
                }
                print(f"🐛 [InatBox Debug] Extracted direct stream: {sourceUrl}")
                streams.append(stream)
                
            elif 'dzen.ru' in sourceUrl:
                for match in re.finditer(r'\{"url":"([^"]*)","type":"([^"]*)"\}', body, re.IGNORECASE):
                    videoUrl = match.group(1)
                    qMatch = re.search(r'=(\w+)$', videoUrl)
                    qualityMap = {'tiny':'256p','lowest':'426p','low':'640p','medium':'852p','high':'1280p','fullhd':'1920p'}
                    quality = qualityMap.get(qMatch.group(1)) if qMatch else 'Unknown'
                    streams.append({
                        'url': videoUrl,
                        'name': f"{base_name}\n{quality}",
                        'title': ch_name_str or 'Dzen Stream',
                        'behaviorHints': {'notWebReady': False, 'httpHeaders': {'Referer': 'https://dzen.ru/'}},
                        'addonName': 'inatbox',
                        'addonManifestUrl': addonManifestUrl
                    })
                    print(f"🐛 [InatBox Debug] Extracted Dzen stream: {videoUrl}")
            elif 'vk.com' in sourceUrl:
                match = re.search(r'"([^"]*m3u8[^"]*)"', body)
                if match:
                    videoUrl = match.group(1).replace('\\/', '/')
                    streams.append({
                        'url': videoUrl,
                        'name': f"{base_name} (VK)",
                        'title': ch_name_str or 'VK Stream',
                        'behaviorHints': {'notWebReady': False, 'httpHeaders': {'Referer': 'https://vk.com/'}},
                        'addonName': 'inatbox',
                        'addonManifestUrl': addonManifestUrl
                    })
                    print(f"🐛 [InatBox Debug] Extracted VK stream: {videoUrl}")
            elif 'disk.yandex.com' in sourceUrl:
                match = re.search(r'https?:\/\/[^\s"]*?master-playlist\.m3u8', body)
                if match:
                    streams.append({
                        'url': match.group(0),
                        'name': f"{base_name} (Yandex)",
                        'title': ch_name_str or 'Yandex Disk',
                        'behaviorHints': {'notWebReady': False, 'httpHeaders': {'Referer': ''}},
                        'addonName': 'inatbox',
                        'addonManifestUrl': addonManifestUrl
                    })
                    print(f"🐛 [InatBox Debug] Extracted Yandex stream: {match.group(0)}")
            elif 'cdn.dzen.ru' in sourceUrl:
                if '.m3u8' in sourceUrl or '.mpd' in sourceUrl:
                    streams.append({
                        'url': sourceUrl,
                        'name': f"{base_name} (CDN)",
                        'title': ch_name_str or 'Dzen CDN',
                        'behaviorHints': {'notWebReady': False, 'httpHeaders': {'Referer': ''}},
                        'addonName': 'inatbox',
                        'addonManifestUrl': addonManifestUrl
                    })
                    print(f"🐛 [InatBox Debug] Extracted Dzen CDN stream: {sourceUrl}")
            elif 'cdn.jwplayer.com' in sourceUrl or '.m3u8' in sourceUrl:
                streams.append({
                    'url': sourceUrl,
                    'name': f"{base_name} (CDN)",
                    'title': ch_name_str or 'CDN Stream',
                    'behaviorHints': {'notWebReady': False, 'httpHeaders': {'Referer': ''}},
                    'addonName': 'inatbox',
                    'addonManifestUrl': addonManifestUrl
                })
                print(f"🐛 [InatBox Debug] Extracted CDN stream: {sourceUrl}")
                
            if not streams:
                chReg = item.get('chReg')
                extractedUrl = None
                if chReg and isinstance(chReg, list) and len(chReg)>0:
                    regexPattern = chReg[0].get('Regex1')
                    if regexPattern and regexPattern != 'null':
                        # First try AES decryption (if Regex1 is actually an AES key)
                        try:
                            decrypted = decrypt_aes(body, regexPattern)
                            if decrypted:
                                parsed_json = json.loads(decrypted)
                                extractedUrl = parsed_json.get('chUrl')
                        except Exception as e: print("EXCEPTION IN LOOP:", e)
                        
                        # Fallback to standard regex search if decryption failed or didn't yield a URL
                        if not extractedUrl:
                            try:
                                match = re.search(regexPattern, body, re.IGNORECASE)
                                if match and match.group(1):
                                    extractedUrl = match.group(1)
                            except Exception as e: print("EXCEPTION IN LOOP:", e)
                
                finalUrl = extractedUrl or sourceUrl
                headersArray = item.get('chHeaders') or {'Referer': '', 'User-Agent': self.CONFIG['userAgent']}
                if isinstance(headersArray, str) and headersArray != 'null':
                    try: headersArray = json.loads(headersArray)
                    except: headersArray = {'Referer': '', 'User-Agent': self.CONFIG['userAgent']}
                if isinstance(headersArray, list) and len(headersArray) > 0: headersArray = headersArray[0]
                if not headersArray: headersArray = {'Referer': '', 'User-Agent': self.CONFIG['userAgent']}
                
                genericStream = {
                    'url': finalUrl,
                    'name': base_name,
                    'title': ch_name_str or 'Generic Stream',
                    'behaviorHints': {'notWebReady': False, 'httpHeaders': headersArray},
                    'addonName': 'inatbox',
                    'addonManifestUrl': addonManifestUrl
                }
                print(f"🐛 [InatBox Debug] Extracted generic stream: {finalUrl}")
                streams.append(genericStream)
                
            for s in streams:
                if subtitles and 'subtitles' not in s:
                    s['subtitles'] = subtitles
                if audioTracks and 'audioTracks' not in s:
                    s['audioTracks'] = audioTracks
                    
            return {'streams': streams}

        if purpose == 'stream_fetch_for_extract':
            item = metadata.get('originalItem')
            if not item or not data: return {'streams': []}
            items_to_process = data if isinstance(data, list) else [data]
            all_streams = []
            
            for d in items_to_process:
                if not isinstance(d, dict) or not d.get('chUrl'): continue
                
                chHeaders = d.get('chHeaders') or item.get('chHeaders') or []
                ext_item = item.copy()
                ext_item.update(d)
                
                ext_item['chUrl'] = vk_source_fix(d.get('chUrl'))
                ext_item['chName'] = d.get('chName') or d.get('diziName') or item.get('chName') or item.get('diziName')
                ext_item['chImg'] = d.get('chImg') or d.get('diziImg') or item.get('chImg') or item.get('diziImg')
                ext_item['chHeaders'] = chHeaders
                
                if not ext_item.get('chReg'): ext_item['chReg'] = item.get('chReg')
                if not ext_item.get('chType'): ext_item['chType'] = item.get('chType') or item.get('diziType')
                
                source_url = ext_item['chUrl']
                body = ''
                
                if '.m3u8' not in source_url and '.mpd' not in source_url:
                    try:
                        print(f"🐛 [InatBox Debug] Fetching {source_url} natively in Python...")
                        req = urllib.request.Request(source_url, headers={'User-Agent': self.CONFIG['userAgent']})
                        with urllib.request.urlopen(req, timeout=5) as response:
                            body = response.read().decode('utf-8', errors='ignore')
                    except Exception as e:
                        print(f"🐛 [InatBox Debug] Native fetch failed for {source_url}: {e}")
                
                res = await self.processFetchResult({
                    'purpose': 'stream_extract',
                    'body': body,
                    'metadata': {'originalItem': ext_item},
                    'addonManifestUrl': addonManifestUrl
                })
                
                if res and 'streams' in res:
                    all_streams.extend(res['streams'])
            
            if all_streams:
                return {'streams': all_streams}
                
            # Fallback to single instruction if native extraction completely failed and we only have 1 item
            if len(items_to_process) > 0:
                d = items_to_process[0]
                chHeaders = d.get('chHeaders') or item.get('chHeaders') or []
                ext_item = item.copy()
                ext_item.update(d)
                ext_item['chUrl'] = vk_source_fix(d.get('chUrl'))
                if not ext_item.get('chReg'): ext_item['chReg'] = item.get('chReg')
                
                referer = 'https://speedrestapi.com/'
                ua = self.CONFIG['userAgent']
                if isinstance(chHeaders, list) and len(chHeaders)>0 and isinstance(chHeaders[0], dict):
                    referer = chHeaders[0].get('Referer', referer)
                    ua = chHeaders[0].get('UserAgent', ua)
                    
                return {
                    'instructions': [{
                        'requestId': f"inat-extract-{int(time.time()*1000)}",
                        'purpose': 'stream_extract',
                        'url': ext_item['chUrl'],
                        'method': 'GET',
                        'headers': {
                            'Accept': '*/*',
                            'Referer': referer,
                            'User-Agent': ua,
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        'metadata': {'originalItem': ext_item, 'extractorNeeded': True}
                    }]
                }
            
            return {'streams': []}

        if purpose in ['meta', 'meta_series_seasons', 'meta_series_episodes']:
            item = metadata.get('originalItem')
            if not item: return {'meta': None}
            
            if metadata.get('isChannel'):
                meta_id = 'inatbox:' + base64_encode_safe(json.dumps(item))
                return {'meta': {
                    'id': meta_id, 'type': 'tv', 'name': item.get('chName') or 'Unknown',
                    'poster': item.get('chImg'), 'posterShape': 'square', 'description': '',
                    'addonName': 'inatbox', 'addonManifestUrl': addonManifestUrl
                }}
                
            meta_id = 'inatbox:' + base64_encode_safe(json.dumps(item))
            
            type_val = 'movie'
            if item.get('diziType') in ['dizi', 'dizi_mode']: type_val = 'series'
            elif item.get('diziType') in ['film', 'film_mode']: type_val = 'movie'
            elif item.get('chType'):
                if item.get('chType') in ['live_url', 'live_mode', 'tekli_regex_lb_sh_3']: type_val = 'tv'
                else: type_val = 'movie'
                
            if purpose in ['meta_series_seasons', 'meta_series_episodes']:
                type_val = 'series'
                
            meta = {
                'id': meta_id, 'type': type_val, 'name': item.get('diziName') or item.get('chName') or 'Unknown',
                'poster': item.get('diziImg') or item.get('chImg'), 'description': item.get('diziDetay') or '',
                'releaseInfo': item.get('diziYear') or '', 'addonName': 'inatbox', 'addonManifestUrl': addonManifestUrl
            }
            
            if purpose == 'meta_series_seasons' and type_val == 'series' and isinstance(data, list):
                episodeInstructions = []
                for idx, season in enumerate(data):
                    if season.get('diziUrl'):
                        try:
                            parsed = urllib.parse.urlparse(season.get('diziUrl'))
                            episodeInstructions.append({
                                'requestId': f"inat-season-{idx+1}-{int(time.time()*1000)}",
                                'purpose': 'meta_series_episodes',
                                'url': season.get('diziUrl'),
                                'method': 'POST',
                                'headers': {
                                    'Cache-Control': 'no-cache',
                                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                    'Referer': 'https://speedrestapi.com/',
                                    'X-Requested-With': 'com.bp.box',
                                    'User-Agent': self.CONFIG['userAgent']
                                },
                                'body': self.buildRequestBody(aesKey=metadata.get('aesKey')),
                                'metadata': {'originalItem': item, 'seasonNumber': idx+1, 'seasonName': season.get('diziName'), 'aesKey': metadata.get('aesKey')}
                            })
                        except Exception as e: print("EXCEPTION IN LOOP:", e)
                if data and data[0].get('diziImg'):
                    meta['poster'] = data[0]['diziImg']
                if not episodeInstructions: return {'meta': meta}
                return {'instructions': episodeInstructions, 'partialMeta': meta}
                
            if purpose == 'meta_series_episodes' and isinstance(data, list):
                seasonNumber = metadata.get('seasonNumber', 1)
                videos = []
                for idx, ep in enumerate(data):
                    if ep.get('chName') or ep.get('diziName'):
                        ep_id = 'inatbox:' + base64_encode_safe(json.dumps(ep))
                        videos.append({
                            'id': ep_id,
                            'title': ep.get('chName') or ep.get('diziName'),
                            'thumbnail': ep.get('chImg') or ep.get('diziImg'),
                            'season': seasonNumber,
                            'episode': idx + 1
                        })
                return {'partialMeta': {'videos': videos}}
                
            if type_val == 'movie' and item.get('diziType') in ['film', 'film_mode']:
                if isinstance(data, list) and len(data)>0:
                    firstItem = data[0]
                    vid_id = 'inatbox:' + base64_encode_safe(json.dumps(firstItem))
                    meta['videos'] = [{
                        'id': vid_id, 'title': item.get('diziName') or 'Film',
                        'thumbnail': firstItem.get('chImg') or item.get('diziImg'),
                        'released': item.get('diziYear') or ''
                    }]
                else:
                    vid_id = 'inatbox:' + base64_encode_safe(json.dumps(item))
                    meta['videos'] = [{
                        'id': vid_id, 'title': item.get('diziName') or 'Film',
                        'thumbnail': item.get('diziImg'),
                        'released': item.get('diziYear') or ''
                    }]
                return {'meta': meta}
                
            return {'meta': meta}

        return {'ok': True}
