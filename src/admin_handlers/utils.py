from asyncio.log import logger
import os
from pathlib import Path
import time
from typing import Optional

async def _download_video_to_persistent(file_id: str, bot) -> Optional[Path]:
    """Download video immediately after upload and save to persistent storage."""
    try:
        file = await bot.get_file(file_id)
        # saved to /app/data/media/uploads
        # VIDEO_STORAGE_DIR = os.getenv("VIDEO_STORAGE_DIR") or "/app/data/media"

        upload_dir = Path(os.getenv("VIDEO_STORAGE_DIR", "/app/data/media"))
        upload_dir.mkdir(parents=True, exist_ok=True)

        safe_name = f"{file_id}_{int(time.time())}.mp4"
        dest_path = upload_dir / safe_name

        await file.download_to_drive(str(dest_path))

        if not dest_path.exists() or dest_path.stat().st_size == 0:
            raise ValueError("Downloaded file is empty")

        logger.info(f"✅ Admin video saved to {dest_path}")
        return dest_path
        
    except Exception as e:
        logger.exception(f"Failed to download admin video {file_id}")
        return None