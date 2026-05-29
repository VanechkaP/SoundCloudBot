import asyncio
import os
import random
import yt_dlp


async def download_soundcloud_track(url: str, progress_callback=None, output_dir: str = "downloads") -> dict:
    """Скачивает трек из SoundCloud в оригинальном формате (m4a/ogg) БЕЗ ПЕРЕКОДИРОВАНИЯ,
    чтобы полностью убрать нагрузку на процессор хостинга.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    random_id = f"track_{random.randint(100000, 999999)}"
    # Используем %(ext)s, чтобы yt-dlp сам сохранил файл в родном формате потока
    outtmpl_path = os.path.join(output_dir, f"{random_id}.%(ext)s")

    main_loop = asyncio.get_event_loop()

    def ydl_progress_hook(d):
        if d['status'] == 'downloading' and progress_callback:
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate')

            if total:
                percent = (downloaded / total) * 100
                asyncio.run_coroutine_threadsafe(progress_callback(percent), main_loop)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': outtmpl_path,
        'noplaylist': True,
        'quiet': True,
        'progress_hooks': [ydl_progress_hook],
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://soundcloud.com/',
        },
        'postprocessors': [
            {
                'key': 'FFmpegMetadata',  # Только прописываем теги, звук не трогаем
            }
        ],
    }

    def extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Динамически забираем расширение, в котором сохранился файл
            ext = info.get('ext', 'm4a')
            filepath = os.path.join(output_dir, f"{random_id}.{ext}")

            thumbnail_url = info.get('thumbnail') or info.get('thumbnails', [{}])[0].get('url')

            return {
                'file_path': filepath,
                'title': info.get('title', 'Unknown Title'),
                'artist': info.get('uploader', 'Unknown Artist'),
                'duration': int(info.get('duration', 0)),
                'thumbnail_url': thumbnail_url
            }

    return await main_loop.run_in_executor(None, extract)