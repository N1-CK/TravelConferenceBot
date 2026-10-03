"""Names for files returned by Telegram's getFile endpoint."""

import hashlib
import os


def telegram_download_name(file_path: str, file_id: str, data: bytes) -> str:
    """Give extensionless Telegram photos a format and unique download name."""
    filename = os.path.basename(file_path)
    if '.' in filename:
        return filename
    if data.startswith(b'\xff\xd8\xff'):
        ext = '.jpg'
    elif data.startswith(b'\x89PNG\r\n\x1a\n'):
        ext = '.png'
    elif data.startswith((b'GIF87a', b'GIF89a')):
        ext = '.gif'
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        ext = '.webp'
    else:
        ext = ''
    unique = hashlib.sha256(file_id.encode()).hexdigest()[:10]
    return f'{filename or "file"}_{unique}{ext}'
