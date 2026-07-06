import json
import random
import asyncio
import time

class YouTubeScraper:
    def __init__(self):
        self.manifest = {
            'id': 'community.youtube.mind',
            'version': '1.1.0',
            'name': 'YouTube (yt-dlp)',
            'description': 'YouTube videoları arama, trendler ve kanallar eklentisi (yt-dlp altyapılı)',
            'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/YouTube_full-color_icon_%282017%29.svg/1024px-YouTube_full-color_icon_%282017%29.svg.png',
            'resources': ['catalog', 'meta', 'stream'],
            'types': ['movie', 'series', 'channel', 'tv'],
            'catalogs': [
                {'type': 'movie', 'id': 'youtube_trending', 'name': 'Trendler', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'youtube_mrbeast', 'name': 'MrBeast', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'youtube_music', 'name': 'Müzik Klipleri', 'extra': [{'name': 'skip', 'isRequired': False}]},
                {'type': 'movie', 'id': 'youtube_search', 'name': 'YouTube Ara', 'extra': [{'name': 'search', 'isRequired': True}, {'name': 'skip', 'isRequired': False}]}
            ],
            'idPrefixes': ['youtube:']
        }

    def getManifest(self):
        return self.manifest

    async def handleCatalog(self, args):
        catalogId = args.get('id')
        extra = args.get('extra', {})
        searchQuery = extra.get('search')
        skip = int(extra.get('skip', 0))
        
        url = "https://www.youtube.com/feed/trending"
        if catalogId == 'youtube_mrbeast':
            url = "https://www.youtube.com/@MrBeast/videos"
        elif catalogId == 'youtube_music':
            url = "https://www.youtube.com/results?search_query=music+pop+hits"
        elif catalogId == 'youtube_search' and searchQuery:
            import urllib.parse
            encoded_query = urllib.parse.quote(searchQuery)
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        return {
            'instructions': [{
                'requestId': f"yt-cat-{int(time.time()*1000)}-{randomId}",
                'purpose': 'catalog',
                'url': url,
                'method': 'GET',
                'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                'metadata': {'catalogId': catalogId, 'searchQuery': searchQuery, 'skip': skip}
            }]
        }

    async def handleMeta(self, args):
        video_id = args.get('id', '').replace('youtube:', '')
        if not video_id: return {'meta': None}

        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        return {
            'instructions': [{
                'requestId': f"yt-meta-{int(time.time()*1000)}-{randomId}",
                'purpose': 'meta',
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'method': 'GET',
                'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                'metadata': {'videoId': video_id}
            }]
        }

    async def handleStream(self, args):
        video_id = args.get('id', '').replace('youtube:', '')
        if not video_id: return {'streams': []}

        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        return {
            'instructions': [{
                'requestId': f"yt-stream-{int(time.time()*1000)}-{randomId}",
                'purpose': 'stream',
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'method': 'GET',
                'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                'metadata': {'videoId': video_id}
            }]
        }

    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        metadata = fetchResult.get('metadata', {})
        
        try:
            import yt_dlp
        except ImportError:
            print("yt-dlp kütüphanesi bulunamadı! 'pip install yt-dlp' ile kurunuz.")
            return {'ok': False, 'error': 'yt-dlp eksik'}
            
        if purpose == 'catalog':
            html = fetchResult.get('body', '')
            if not html: html = ""
            skip = int(metadata.get('skip', 0))
            
            import re
            videos = []
            
            matches = re.finditer(r'"videoId":"([^"]+)".*?"title":\{"runs":\[\{"text":"(.*?)"\}\]', html)
            for match in matches:
                vid = match.group(1)
                title = match.group(2)
                
                if len(vid) == 11 and not any(v['id'] == f"youtube:{vid}" for v in videos):
                    try:
                        clean_title = title.encode('utf-8').decode('unicode_escape') if '\\u' in title else title
                    except:
                        clean_title = title
                        
                    videos.append({
                        'id': f"youtube:{vid}",
                        'type': 'movie',
                        'name': clean_title,
                        'poster': f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                        'description': 'YouTube Video'
                    })
                    
            return {'metas': videos[skip:skip+20]}

        elif purpose == 'meta':
            video_id = metadata.get('videoId')
            html = fetchResult.get('body', '')
            if not html: html = ""
            
            import re
            title = "YouTube Video"
            title_match = re.search(r'"videoPrimaryInfoRenderer":\{"title":\{"runs":\[\{"text":"(.*?)"\}\]', html)
            if title_match:
                title = title_match.group(1)
                try:
                    title = title.encode('utf-8').decode('unicode_escape') if '\\u' in title else title
                except:
                    pass
            elif '<title>' in html:
                t_match = re.search(r'<title>(.*?)</title>', html)
                if t_match:
                    title = t_match.group(1).replace(' - YouTube', '')
                    
            desc = "Detaylar alınamadı."
            desc_match = re.search(r'"description":\{"runs":\[(.*?)\]\}', html)
            if desc_match:
                runs = desc_match.group(1)
                texts = re.findall(r'"text":"(.*?)"', runs)
                desc = "".join(texts)[:500]
                try:
                    desc = desc.encode('utf-8').decode('unicode_escape') if '\\u' in desc else desc
                except:
                    pass
            
            meta = {
                'id': f'youtube:{video_id}',
                'type': 'movie',
                'name': title,
                'poster': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                'background': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                'description': desc
            }
            return {'meta': meta}

        elif purpose == 'stream':
            video_id = metadata.get('videoId')
            html = fetchResult.get('body', '')
            
            # 1) Önce HTML içerisindeki ytInitialPlayerResponse datasını arayalım (Render IP ban'ı atlamak için)
            import re
            import urllib.parse
            
            try:
                # ytInitialPlayerResponse içinden url bulma
                player_res_match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});</script>', html)
                if player_res_match:
                    player_data = json.loads(player_res_match.group(1))
                    streaming_data = player_data.get('streamingData', {})
                    formats = streaming_data.get('formats', []) + streaming_data.get('adaptiveFormats', [])
                    
                    # 720p veya mp4 bulmaya çalışalım
                    best_url = None
                    for f in formats:
                        if 'url' in f:
                            # ses ve görüntü olanı tercih et
                            if 'audio' in f.get('mimeType', '') or 'video' in f.get('mimeType', ''):
                                best_url = f['url']
                                if 'mp4' in f.get('mimeType', '') and '720p' in f.get('qualityLabel', ''):
                                    break # En iyi seçenek
                    
                    if best_url:
                        return {
                            'streams': [{
                                'url': best_url,
                                'name': 'YouTube',
                                'title': '720p / MP4',
                                'behaviorHints': {'notWebReady': False}
                            }]
                        }
            except Exception as e:
                print(f"HTML ayrıştırma hatası: {e}")
            
            # 2) Eğer HTML üzerinden URL bulamazsak, alternatif olarak sunucuda yt-dlp kullanmayı deneriz.
            # Render üzerinde IP ban sebebiyle hata verebilir, bu yüzden yukarıdaki HTML parse her zaman önceliklidir.
            try:
                import yt_dlp
                ydl_opts = {
                    'format': 'best',
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                    stream_url = info.get('url')
                    if stream_url:
                        return {
                            'streams': [{
                                'url': stream_url,
                                'name': 'YouTube (yt-dlp)',
                                'title': 'Auto Quality',
                                'behaviorHints': {'notWebReady': False}
                            }]
                        }
            except Exception as e:
                print(f"yt-dlp stream hatası: {e}")
                
            # Tüm denemelere rağmen URL bulunamazsa, fallback olarak ytId döndürüyoruz
            return {
                'streams': [{
                    'ytId': video_id,
                    'name': 'YouTube',
                    'title': 'YouTube Video (Fallback)',
                    'behaviorHints': {'notWebReady': False}
                }]
            }

        return {'ok': True}
