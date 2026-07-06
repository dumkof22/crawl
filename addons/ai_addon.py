import base64
import json
import urllib.parse
import urllib.parse
import random
import time
import os
import asyncio
from bs4 import BeautifulSoup

def base64_encode_safe(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8').replace('=', '')

def base64_decode_safe(s):
    s = s.strip()
    s += '=' * (-len(s) % 4)
    try:
        return base64.b64decode(s).decode('utf-8')
    except:
        return ''

class GeminiAIFinderScraper:
    def __init__(self):
        self.manifest = {
            'id': 'ai.gemini.finder',
            'version': '1.0.0',
            'name': 'Gemini AI Finder',
            'description': 'Arama sonuçlarını ve sayfaları Gemini 1.5 Flash AI kullanarak analiz edip video bulan eklenti.',
            'logo': 'https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg',
            'resources': ['catalog', 'meta', 'stream'],
            'types': ['movie', 'series'],
            'catalogs': [
                {'type': 'movie', 'id': 'gemini_search', 'name': 'AI ile Ara', 'extra': [{'name': 'search', 'isRequired': True}]}
            ],
            'idPrefixes': ['gemini']
        }
        self.CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'addon-config.json')

    def get_api_key(self):
        try:
            if os.path.exists(self.CONFIG_PATH):
                with open(self.CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Try to get it from headers set in admin panel
                    addon_conf = config.get('addons', {}).get('ai.gemini.finder', {})
                    headers = addon_conf.get('headers', {})
                    if isinstance(headers, str):
                        try:
                            headers = json.loads(headers)
                        except:
                            headers = {}
                    
                    key = headers.get('Gemini-API-Key')
                    if key: return key
                    
                    # Also fallback to base config if someone put it there directly
                    return config.get('geminiApiKey', '')
        except Exception as e:
            print(f"Error reading api key: {e}")
        return os.environ.get('GEMINI_API_KEY', '')


    def get_enhanced_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/134.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            '__COOKIE_HINT__': 'FLUTTER_INJECT_WEBVIEW_COOKIES'
        }

    def getManifest(self):
        return self.manifest

    async def handleCatalog(self, args):
        catalogId = args.get('id')
        extra = args.get('extra', {})
        searchQuery = extra.get('search')
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))

        if catalogId == 'gemini_search' and searchQuery:
            # Google'da arama yapılması için talimat döndürüyoruz
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(searchQuery + ' izle full')}"
            return {
                'instructions': [{
                    'requestId': f"gemini-search-{int(time.time()*1000)}-{randomId}",
                    'purpose': 'google-search',
                    'url': search_url,
                    'method': 'GET',
                    'headers': self.get_enhanced_headers(),
                    'metadata': {'searchQuery': searchQuery, 'hiddenweb': True}
                }]
            }
        return {'metas': []}

    async def handleMeta(self, args):
        urlBase64 = args.get('id', '').replace('gemini:', '')
        url = base64_decode_safe(urlBase64)
        
        meta = {
            'id': f"gemini:{urlBase64}",
            'type': 'movie',
            'name': f"AI Hedefi: {url}",
            'description': "Gemini AI tarafından seçilen hedef site.",
            'poster': 'https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg'
        }
        return {'meta': meta}

    async def handleStream(self, args):
        urlBase64 = args.get('id', '').replace('gemini:', '')
        url = base64_decode_safe(urlBase64)
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        
        return {
            'instructions': [{
                'requestId': f"gemini-ai-step-{int(time.time()*1000)}-{randomId}",
                'purpose': 'ai-step',
                'url': url,
                'method': 'GET',
                'headers': self.get_enhanced_headers(),
                'metadata': {'step': 1, 'hiddenweb': True}
            }]
        }

    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        body = fetchResult.get('body', '')
        url = fetchResult.get('url', '')
        metadata = fetchResult.get('metadata', {})

        if purpose == 'google-search':
            soup = BeautifulSoup(body, 'html.parser')
            links = []
            for a in soup.select('a'):
                href = a.get('href', '')
                if href.startswith('http') and 'google.com' not in href and 'youtube.com' not in href:
                    title = a.text.strip()
                    if title:
                        links.append(f"Title: {title} | URL: {href}")
            
            # Sadece ilk 10 linki verelim
            links_text = "\n".join(links[:10])
            searchQuery = metadata.get('searchQuery', 'film')
            
            prompt = f"Kullanıcı '{searchQuery}' kelimesini arattı. Google arama sonuçlarından aşağıdaki linkleri bulduk:\n\n{links_text}\n\nLütfen bu linkler arasından filmi/diziyi bedava izleyebileceği en uygun yasadışı veya yasal korsan/film izleme sitesinin (hdfilmcehennemi, dizipal vb.) linkini seç. Sadece URL'yi yaz, başka hiçbir kelime ekleme."
            
            ai_response = ""
            
            api_key = self.get_api_key()
            if not api_key:
                return {'metas': [{'id': 'gemini:error', 'type': 'movie', 'name': 'API Key Eksik', 'description': 'Lütfen admin panelden API key ekleyin.'}]}
                
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2}
            }
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            
            return {
                'instructions': [{
                    'requestId': f"gemini-google-{int(time.time()*1000)}-{random.randint(100,999)}",
                    'purpose': 'google-search-ai',
                    'url': gemini_url,
                    'method': 'POST',
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps(payload),
                    'metadata': {'searchQuery': searchQuery, 'hiddenweb': True}
                }]
            }

        if purpose == 'google-search-ai':
            try:
                data = json.loads(body)
                ai_response = data['candidates'][0]['content']['parts'][0]['text'].strip()
            except Exception as e:
                return {'metas': [{'id': 'gemini:error', 'type': 'movie', 'name': 'AI Hata', 'description': str(e)}]}

            if ai_response.startswith('http'):
                chosen_url = ai_response.strip()
                meta_id = 'gemini:' + base64_encode_safe(chosen_url)
                return {
                    'metas': [{
                        'id': meta_id,
                        'type': 'movie',
                        'name': 'AI Seçimi (Tıkla)',
                        'description': f"Gemini tarafından seçilen link: {chosen_url}",
                        'poster': 'https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg'
                    }]
                }
            else:
                return {
                    'metas': [{
                        'id': 'gemini:error',
                        'type': 'movie',
                        'name': 'AI Hata/Sonuç Bulamadı',
                        'description': ai_response,
                    }]
                }

        if purpose == 'ai-step':
            step = metadata.get('step', 1)
            
            if step > 5: # Sonsuz döngüyü engellemek için
                return {'streams': []}

            # HTML içeriği çok büyük olabilir, gereksizleri silelim
            soup = BeautifulSoup(body, 'html.parser')
            for script in soup(["script", "style", "svg", "path"]):
                script.decompose()
            
            # Iframe'leri ve linkleri koruyalım
            iframes = [str(i) for i in soup.find_all('iframe')]
            
            html_text = soup.get_text(separator=' ', strip=True)
            # Metni kısaltalım (ilk 10000 karakter)
            html_excerpt = html_text[:10000]
            
            iframe_text = "\n".join(iframes)
            
            prompt = f"""
Biz bir web sitesinden video m3u8 veya mp4 linki çıkarmaya çalışıyoruz. Veya bir iframe içindeki video player'a ulaşmamız gerekiyor.
Şu anki URL: {url}

Sayfadaki iframe'ler:
{iframe_text}

Sayfanın içeriğinden kısa bir kesit:
{html_excerpt}

GÖREVİN:
1. Eğer bu sayfa bir video barındırıyorsa ve iframe linki veya m3u8/mp4 linkini anladıysan,
   Video m3u8 veya mp4 ise ŞU FORMATTA CEVAP VER:
   VIDEO: <url>
   Eğer video bir iframe içindeyse ve bizim o iframe sayfasına gitmemiz gerekiyorsa ŞU FORMATTA CEVAP VER:
   NEXT: <iframe_url>
2. Eğer videoyu oynatmak için sayfadaki başka bir linke (örneğin Part 2, Alternatif 1) tıklamak gerekiyorsa:
   NEXT: <url>
3. Eğer hiçbir şey bulamadıysan:
   FAIL

Lütfen SADECE yukarıdaki formatlardan birini kullanarak cevap ver. Başka hiçbir şey yazma.
"""
            api_key = self.get_api_key()
            if not api_key:
                return {'streams': []}
                
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2}
            }
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            
            return {
                'instructions': [{
                    'requestId': f"gemini-step-{int(time.time()*1000)}-{random.randint(100,999)}",
                    'purpose': 'ai-step-ai',
                    'url': gemini_url,
                    'method': 'POST',
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps(payload),
                    'metadata': {'step': step, 'originalUrl': url, 'hiddenweb': True}
                }]
            }

        if purpose == 'ai-step-ai':
            try:
                data = json.loads(body)
                ai_response = data['candidates'][0]['content']['parts'][0]['text'].strip()
            except Exception as e:
                print(f"Gemini Step AI Error: {e}")
                return {'streams': []}
                
            step = metadata.get('step', 1)
            url = metadata.get('originalUrl', '')
            
            if ai_response.startswith('VIDEO:'):
                video_url = ai_response.replace('VIDEO:', '').strip()
                if video_url.startswith('//'): video_url = 'https:' + video_url
                elif video_url.startswith('/'): video_url = f"https://{urllib.parse.urlparse(url).netloc}{video_url}"
                
                return {
                    'streams': [{
                        'name': 'Gemini AI Stream',
                        'title': 'AI Buldu',
                        'url': video_url,
                        'type': 'm3u8' if '.m3u8' in video_url else 'mp4'
                    }]
                }
            elif ai_response.startswith('NEXT:'):
                next_url = ai_response.replace('NEXT:', '').strip()
                if next_url.startswith('//'): next_url = 'https:' + next_url
                elif next_url.startswith('/'): next_url = f"https://{urllib.parse.urlparse(url).netloc}{next_url}"
                
                randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                headers = self.get_enhanced_headers()
                headers['Referer'] = url
                
                return {
                    'instructions': [{
                        'requestId': f"gemini-ai-step-{int(time.time()*1000)}-{randomId}",
                        'purpose': 'ai-step',
                        'url': next_url,
                        'method': 'GET',
                        'headers': headers,
                        'metadata': {'step': step + 1, 'hiddenweb': True}
                    }]
                }
            else:
                return {'streams': []}

        return {'ok': True}
