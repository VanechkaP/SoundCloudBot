import asyncio
import os
import yt_dlp


async def download_soundcloud_track(url: str, output_dir: str = "downloads") -> dict:
    """
    Скачивает трек из SoundCloud через yt-dlp, конвертирует в MP3 (128 kbps),
    вшивает обложку/теги и возвращает информацию о файле.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    outtmpl_path = os.path.join(output_dir, '%(title)s.%(ext)s')

    ydl_opts = {
        'format': 'bestaudio/best',
        'writethumbnail': True,
        'embedthumbnail': True,
        'addmetadata': True,
        'outtmpl': outtmpl_path,
        'noplaylist': True,
        'quiet': True,
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            },
            {
                'key': 'FFmpegThumbnailsConvertor',
                'format': 'jpg',
                'when': 'before_dl'
            },
            {
                'key': 'EmbedThumbnail',
            },
            {
                'key': 'FFmpegMetadata',
            }
        ],
    }

    loop = asyncio.get_event_loop()

    def extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            filepath = os.path.splitext(filename)[0] + ".mp3"

            # Безопасно берем ссылку на обложку
            thumbnail_url = info.get('thumbnail') or info.get('thumbnails', [{}])[0].get('url')

            return {
                'file_path': filepath,
                'title': info.get('title', 'Unknown Title'),
                'artist': info.get('uploader', 'Unknown Artist'),
                'duration': int(info.get('duration', 0)),
                'thumbnail_url': thumbnail_url  # Ключ теперь железно существует
            }

    return await loop.run_in_executor(None, extract)