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
        
        # Flutter'ın algılayabilmesi için zorunlu olarak instruction dönüyoruz.
        # processFetchResult tarafında HTML'i yoksayıp yt-dlp ile işi çözeceğiz.
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        return {
            'instructions': [{
                'requestId': f"yt-cat-{int(time.time()*1000)}-{randomId}",
                'purpose': 'catalog',
                'url': 'https://www.youtube.com',
                'method': 'GET',
                'headers': {'User-Agent': 'Mozilla/5.0'},
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
                'url': 'https://www.youtube.com',
                'method': 'GET',
                'headers': {'User-Agent': 'Mozilla/5.0'},
                'metadata': {'videoId': video_id}
            }]
        }

    async def handleStream(self, args):
        video_id = args.get('id', '').replace('youtube:', '')
        randomId = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        
        return {
            'instructions': [{
                'requestId': f"yt-stream-{int(time.time()*1000)}-{randomId}",
                'purpose': 'stream_extract',
                'url': 'https://www.youtube.com',
                'method': 'GET',
                'headers': {'User-Agent': 'Mozilla/5.0'},
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
            catalogId = metadata.get('catalogId')
            searchQuery = metadata.get('searchQuery')
            skip = int(metadata.get('skip', 0))
            
            def _get_catalog():
                ydl_opts = {'extract_flat': True, 'quiet': True}
                url = ""
                if catalogId == 'youtube_trending':
                    url = "ytsearch20:trending videos 2025"
                elif catalogId == 'youtube_mrbeast':
                    url = "https://www.youtube.com/@MrBeast/videos"
                elif catalogId == 'youtube_music':
                    url = "ytsearch20:music pop hits"
                elif catalogId == 'youtube_search' and searchQuery:
                    url = f"ytsearch20:{searchQuery}"
                    
                if not url: return []
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        info = ydl.extract_info(url, download=False)
                        entries = info.get('entries', [])
                        if not entries and 'title' in info:
                            entries = [info]
                            
                        metas = []
                        for entry in entries[skip:skip+20]:
                            if not entry.get('id'): continue
                            poster = f"https://img.youtube.com/vi/{entry['id']}/hqdefault.jpg"
                            desc = ""
                            if entry.get('view_count'): desc += f"İzlenme: {entry['view_count']:,} | "
                            if entry.get('duration'): desc += f"Süre: {int(entry['duration']//60)}:{int(entry['duration']%60):02d} | "
                            if entry.get('uploader'): desc += f"Kanal: {entry['uploader']}"
                            
                            metas.append({
                                'id': f"youtube:{entry['id']}",
                                'type': 'movie',
                                'name': entry.get('title', 'Video'),
                                'poster': poster,
                                'description': desc.strip(' | ')
                            })
                        return metas
                    except Exception as e:
                        print(f"yt-dlp catalog error: {e}")
                        return []
                        
            metas = await asyncio.to_thread(_get_catalog)
            return {'metas': metas}

        elif purpose == 'meta':
            video_id = metadata.get('videoId')
            def _get_meta():
                ydl_opts = {'quiet': True, 'skip_download': True, 'extract_flat': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                        poster = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                        return {
                            'id': f'youtube:{video_id}',
                            'type': 'movie',
                            'name': info.get('title', 'YouTube Video'),
                            'poster': poster,
                            'background': poster,
                            'description': info.get('description', 'Açıklama bulunamadı.'),
                            'releaseInfo': info.get('upload_date', '')
                        }
                    except:
                        return None
                        
            meta = await asyncio.to_thread(_get_meta)
            if not meta:
                meta = {
                    'id': f'youtube:{video_id}',
                    'type': 'movie',
                    'name': 'YouTube Video',
                    'poster': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                    'description': 'Detaylar alınamadı.'
                }
            return {'meta': meta}

        elif purpose == 'stream_extract':
            video_id = metadata.get('videoId')
            def _get_stream():
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'remote_components': ['ejs:github'],
                    'js_runtimes': {'node': {}}
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                        
                        formats = info.get('formats', [])
                        streams = []
                        combined = []
                        
                        for f in formats:
                            if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('url'):
                                combined.append(f)
                                
                        # Yüksek kaliteden düşüğe doğru sırala
                        combined.sort(key=lambda x: x.get('height', 0) or 0, reverse=True)
                        
                        added_heights = set()
                        for f in combined:
                            height = f.get('height')
                            if not height or height in added_heights:
                                continue
                            added_heights.add(height)
                            
                            quality_name = f"{height}p"
                            streams.append({
                                'url': f.get('url'),
                                'name': f"YouTube\n{quality_name}",
                                'title': f"YouTube - {quality_name} (Direkt)",
                                'behaviorHints': {'notWebReady': False}
                            })
                            
                        # Eğer hiçbir birleşik format bulamazsa yt-dlp'nin best formatını dön
                        if not streams and info.get('url'):
                            streams.append({
                                'url': info.get('url'),
                                'name': 'YouTube\nOtomatik',
                                'title': 'YouTube - Otomatik Kalite',
                                'behaviorHints': {'notWebReady': False}
                            })
                            
                        return streams
                    except Exception as e:
                        print(f"yt-dlp stream error: {e}")
                        return None
                        
            streams = await asyncio.to_thread(_get_stream)
            if not streams:
                streams = [{
                    'ytId': video_id,
                    'externalUrl': f'https://youtube.com/watch?v={video_id}',
                    'name': 'YouTube\nHata',
                    'title': 'YouTube Oynatıcı (Hata)',
                    'behaviorHints': {'notWebReady': True}
                }]
            return {'streams': streams}

        return {'ok': True}
