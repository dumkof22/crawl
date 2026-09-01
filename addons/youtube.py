import json
import random
import asyncio
import time
import uuid
import urllib.parse

# ytdlp.online — instruction-mode ile kullanılan public yt-dlp servisi.
#   GET /api/v1/stream?command=<yt-dlp komutu>&job_id=<uuid>&source=index&engine=nightly
#   -> SSE gövdesi: "data: <satır>" frame'leri, sonda "event: close".
# NOT: anonim kullanıcıda IP başına GÜNDE 5 istek limiti var; dönen googlevideo URL'leri
# ytdlp.online sunucu IP'sine kilitli olabilir (playback cihazda 403 verebilir).
YTDLP_ONLINE_BASE = "https://ytdlp.online"

class YouTubeScraper:
    def __init__(self):
        self.manifest = {
            'id': 'community.youtube.mind',
            'version': '1.2.0',
            'name': 'YouTube',
            'description': 'YouTube videoları arama, trendler ve kanallar eklentisi',
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
        print(f"🔎 [youtube] handleStream RAW args: {json.dumps(args, ensure_ascii=False)}")
        raw_id = args.get('id', '')
        video_id = raw_id.replace('youtube:', '').strip()
        print(f"🔎 [youtube] raw_id={raw_id!r} -> video_id={video_id!r}")
        if not video_id:
            print("⚠️ [youtube] video_id boş, streams: []")
            return {'streams': []}

        # Direkt CDN URL'ini ytdlp.online üzerinden (instruction mode) çekiyoruz.
        # Fetch Flutter tarafında yapılır; SSE gövdesi processFetchResult'ta ayrıştırılır.
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        # 22 (720p muxed) -> 18 (360p muxed) -> best (tek dosya) : oynatıcı tek URL ister
        command = f'--get-url --no-playlist -f 22/18/best "{watch_url}"'
        job_id = str(uuid.uuid4())
        stream_url = (
            f"{YTDLP_ONLINE_BASE}/api/v1/stream"
            f"?command={urllib.parse.quote(command)}"
            f"&job_id={job_id}&source=index&engine=nightly"
        )
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        result = {
            'instructions': [{
                'requestId': f"yt-stream-{int(time.time()*1000)}-{randomId}",
                'purpose': 'stream',
                'url': stream_url,
                'method': 'GET',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': f"{YTDLP_ONLINE_BASE}/",
                    'Accept': 'text/event-stream'
                },
                'metadata': {'videoId': video_id, 'hiddenweb': False}
            }]
        }
        print(f"✅ [youtube] handleStream -> ytdlp.online instruction: {stream_url}")
        return result

    def _fallback_streams(self, video_id):
        # ytdlp.online'dan URL alınamazsa: YouTube'u cihazın kendi webview'inde aç.
        return {
            'streams': [
                {
                    'name': 'YouTube', 'title': 'YouTube Player (gömülü)',
                    'url': f"https://www.youtube.com/embed/{video_id}?autoplay=1&playsinline=1",
                    'type': 'movie',
                    'behaviorHints': {'notWebReady': False, 'bingeGroup': 'youtube'}
                },
                {
                    'name': 'YouTube', 'title': 'YouTube Sayfası (webview)',
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'type': 'movie',
                    'behaviorHints': {'notWebReady': False, 'bingeGroup': 'youtube'}
                },
                {
                    'name': 'YouTube', 'title': 'Tarayıcı / YouTube uygulamasında aç',
                    'externalUrl': f"https://www.youtube.com/watch?v={video_id}",
                    'behaviorHints': {'notWebReady': True}
                }
            ]
        }

    async def processFetchResult(self, fetchResult):
        purpose = fetchResult.get('purpose')
        metadata = fetchResult.get('metadata', {})

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
            import re
            import html as _html
            video_id = metadata.get('videoId')
            body = fetchResult.get('body', '') or ''
            print(f"🔎 [youtube] stream SSE body ({len(body)} bytes): {body[:600]}")

            # SSE "data: ..." satırlarını topla, HTML-entity çöz
            lines = []
            for m in re.finditer(r'^data:\s?(.*)$', body, re.MULTILINE):
                lines.append(_html.unescape(m.group(1).strip()))
            joined = "\n".join(lines)

            # Limit / hata mesajı kontrolü
            low = joined.lower()
            if 'daily launch limit' in low or 'limit reached' in low:
                print("⚠️ [youtube] ytdlp.online günlük limit doldu -> fallback")
                return self._fallback_streams(video_id)

            # googlevideo / m3u8 URL'leri çıkar
            urls = re.findall(r'https://[^\s"\'<>]+(?:googlevideo\.com|\.m3u8)[^\s"\'<>]*', joined)
            urls = [u for u in urls if 'videoplayback' in u or '.m3u8' in u]

            streams = []
            if urls:
                u = urls[0]
                itag = re.search(r'[?&]itag=(\d+)', u)
                is_hls = '.m3u8' in u
                streams.append({
                    'name': 'YouTube (ytdlp.online)',
                    'title': ('HLS' if is_hls else f"MP4 (itag {itag.group(1)})" if itag else 'MP4'),
                    'url': u,
                    'type': 'm3u8' if is_hls else 'mp4',
                    'behaviorHints': {
                        'notWebReady': True,
                        'bingeGroup': 'youtube',
                        'proxyHeaders': {'request': {
                            'User-Agent': 'Mozilla/5.0',
                            'Referer': 'https://www.youtube.com/',
                            'Origin': 'https://www.youtube.com'
                        }}
                    }
                })
                print(f"✅ [youtube] ytdlp.online URL bulundu: {u[:120]}...")
            else:
                print("⚠️ [youtube] ytdlp.online SSE'de URL yok -> fallback")

            # Her durumda webview yedeklerini de ekle
            streams += self._fallback_streams(video_id)['streams']
            return {'streams': streams}

        return {'ok': True}
