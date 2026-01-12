import os
from pathlib import Path
import tempfile
import subprocess
import logging
import time
import asyncio
import shutil
from typing import Tuple, Optional, Callable
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

VIDEO_DOWNLOAD_TIMEOUT = 300

VIDEO_STORAGE_DIR = os.getenv("VIDEO_STORAGE_DIR") or "/app/data/media"

class VideoProcessor:
    """Handles video processing and conversion using FFmpeg"""
    def __init__(
        self,
        bot,
        video_storage_dir: str = None,
        progress_callback: Callable = None,
    ):
        self.bot = bot
        storage_dir = video_storage_dir or VIDEO_STORAGE_DIR
        self.video_storage_dir = Path(storage_dir)
        self.video_storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Video storage directory: {self.video_storage_dir}")

        self.media_dir = self.video_storage_dir 
        self.progress_callback = progress_callback

    async def process_video(
        self, original_path: str, video_id: int, title: str, chat_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Process video and convert to 480p and 1080p.
        Returns tuple of (file_id_480p, file_id_1080p)
        """
        start_time = time.time()
        
        if not original_path or not isinstance(original_path, str):
            logger.error(f"❌ Invalid original_path: {original_path} (type: {type(original_path)})")
            return None, None

        original_path = Path(original_path)
        if not original_path.exists():
            logger.error(f"❌ Original video file missing: {original_path}")
            return None, None
        if original_path.stat().st_size == 0:
            logger.error(f"❌ Original video is empty: {original_path}")
            return None, None
        
        logger.info(f"🎬 Starting processing for video {video_id}: '{title}'")

        # Per-video working directory (inside persistent storage)
        video_dir = self.video_storage_dir / f"video_{video_id}"
        video_dir.mkdir(parents=True, exist_ok=True)

        file_id_480p = None
        file_id_1080p = None

        try:
            # 480p conversion
            await self._update_progress(20, "🔄 Converting to 480p...")
            path_480p = await self._convert_video(original_path, video_dir, "480p", video_id)
            if not path_480p:
                logger.error("❌ 480p conversion failed")
                return None, None

            # 1080p conversion
            await self._update_progress(60, "🔄 Converting to 1080p...")
            path_1080p = await self._convert_video(original_path, video_dir, "1080p", video_id)
            if not path_1080p:
                logger.error("❌ 1080p conversion failed")
                return None, None

            # UPLOAD 480p
            await self._update_progress(80, "📤 Uploading 480p...")
            file_id_480p = await self._upload_video(str(path_480p), title, "480p", chat_id)
            if not file_id_480p:
                logger.error("❌ 480p upload failed")
                return None, None

            # UPLOAD 1080p
            await self._update_progress(90, "📤 Uploading 1080p...")
            file_id_1080p = await self._upload_video(str(path_1080p), title, "1080p", chat_id)
            if not file_id_1080p:
                logger.error("❌ 1080p upload failed")
                return None, None

            # Success
            return file_id_480p, file_id_1080p

        except Exception as e:
            logger.exception(f"❌ Unexpected error processing video {video_id}: {e}")
            return None, None

    async def _download_video(self, file_id: str, target_dir: Path) -> Optional[Path]:
        """
        Download video and place it in `target_dir`.
        In local mode, this is fast (no HTTP). Always copies to persistent dir.
        """
        try:
            file = await self.bot.get_file(file_id)
            if not file.file_path:
                logger.error("❌ file.file_path is None — check local_mode or Bot API server")
                return None

            temp_path = Path(await file.download_to_drive())

            logger.info(f"📥 Got file at: {temp_path} (size: {temp_path.stat().st_size} B)")

            orig_name = temp_path.name or "video.mp4"
            safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", f"{file_id}_{orig_name}")[:128]
            dest_path = target_dir / safe_name

            shutil.copy2(temp_path, dest_path)
            logger.info(f"💾 Copied to: {dest_path}")

            try:
                if temp_path != dest_path and temp_path.exists():
                    temp_path.unlink()
            except Exception as e:
                logger.warning(f"Could not remove temp file {temp_path}: {e}")

            if not dest_path.exists() or dest_path.stat().st_size == 0:
                raise ValueError("Downloaded file is missing or empty")

            return dest_path
        
        except TelegramError as e:
            logger.error(f"Telegram error downloading {file_id}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Failed to download video {file_id}")
            return None

    async def _update_progress(self, percentage: int, message: str):
        if self.progress_callback:
            await self.progress_callback(percentage, message)
        else:
            bar = self._create_progress_bar(percentage)
            logger.info(f"{bar} {message}")

    def _create_progress_bar(self, percentage: int, width: int = 20) -> str:
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}]"

    async def _upload_video(self, file_path: str, title: str, quality: str, chat_id: str) -> Optional[str]:
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"📁 File does not exist: {file_path}")
                return None
            if path.stat().st_size == 0:
                logger.error(f"EmptyEntries File is empty: {file_path}")
                return None

            size_mb = path.stat().st_size / (1024 * 1024)
            logger.info(f"📤 Uploading {quality} ({size_mb:.2f} MB) to chat {chat_id}: {file_path}")

            with open(path, "rb") as f:
                message = await self.bot.send_video(
                    chat_id=chat_id,
                    video=f,
                    caption=f"{title} ({quality})",
                    supports_streaming=True
                )
            logger.info(f"✅ Upload succeeded, file_id: {message.video.file_id}")
            return message.video.file_id

        except TelegramError as e:
            logger.error(f"❌ Telegram API error during {quality} upload: {repr(e)}")
            return None
        except Exception as e:
            logger.exception(f"🔥 Unexpected error during {quality} upload: {e}")
            return None
    
    def delete_video_files(self, video_id: int, delete_original: bool = False, original_path: str | Path | None = None) -> bool:
        """
        Delete processed video files for a given video_id.
        """
        return self._delete_files_impl(
            video_id=video_id,
            storage_dir=self.storage_dir,
            delete_original=delete_original,
            original_path=original_path
        )

    @staticmethod
    def delete_video_files_static(
        video_id: int,
        video_storage_dir: str | Path | None = None,
        delete_original: bool = False,
        original_path: str | Path | None = None
    ) -> bool:
        """Static version — useful for cleanup in DB layer or background tasks."""
        storage_dir = Path(video_storage_dir or VIDEO_STORAGE_DIR)
        return VideoProcessor._delete_files_impl(
            video_id=video_id,
            storage_dir=storage_dir,
            delete_original=delete_original,
            original_path=original_path
        )

    @staticmethod
    def _delete_files_impl(
        video_id: int,
        storage_dir: Path,
        delete_original: bool = False,
        original_path: str | Path | None = None
    ) -> bool:
        success = True

        video_dir = storage_dir / f"video_{video_id}"
        if video_dir.exists():
            try:
                shutil.rmtree(video_dir)
                logger.info(f"🗑️ Deleted working dir: {video_dir}")
            except Exception as e:
                logger.error(f"❌ Failed to delete {video_dir}: {e}", exc_info=True)
                success = False
        else:
            logger.debug(f"📁 Working dir not found: {video_dir}")

        if delete_original and original_path:
            orig_path = Path(original_path)
            if orig_path.exists():
                try:
                    orig_path.unlink()
                    logger.info(f"🗑️ Deleted original: {orig_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to delete original {orig_path}: {e}")
                    success = False
            else:
                logger.debug(f"📹 Original file not found: {orig_path}")

        return success


# ffmpeg helpers


    async def _convert_video(self, input_path: str, temp_dir: str, quality: str, video_id: int) -> Optional[str]:
        try:
            # Ensure input is string
            input_path = str(input_path)
            if not os.path.exists(input_path) or os.path.getsize(input_path) == 0:
                logger.error(f"Input file missing or empty: {input_path}")
                return None

            output_path = os.path.join(temp_dir, f"{quality}_{video_id}.mp4")

            # Get duration
            duration = await self._get_video_duration(input_path)
            if duration <= 0:
                logger.warning(f"Could not determine video duration for {quality} conversion")
                duration = 60

            # Build command with STRINGS only
            if quality == "480p":
                cmd = [
                        "ffmpeg", "-y", "-i", input_path,
                        "-vf", "scale=854:480",
                        "-c:v", "libx264",
                        "-crf", "23",
                        "-preset", "medium",
                        "-profile:v", "baseline",
                        "-level", "3.0",
                        "-pix_fmt", "yuv420p",
                        "-c:a", "aac",
                        "-b:a", "128k",
                        "-movflags", "+faststart",
                        "-avoid_negative_ts", "make_zero",
                        output_path
                    ]
            elif quality == "1080p":
                cmd = [
                    "ffmpeg", "-y", "-i", input_path,
                    "-vf", "scale=1920:1080",
                    "-c:v", "libx264",
                    "-crf", "20",
                    "-preset", "medium",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    output_path
                ]
            else:
                logger.error(f"Unsupported quality: {quality}")
                return None

            logger.info(f"▶️ Starting FFmpeg for {quality}: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"💥 FFmpeg failed for {quality} (exit {process.returncode})")
                logger.error(f"STDERR:\n{stderr.decode('utf-8', errors='replace')}")
                return None

            if not os.path.exists(output_path):
                logger.error(f"⚠️ Output file not found: {output_path}")
                return None

            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"✅ {quality} conversion succeeded ({size_mb:.2f} MB)")
            return output_path

        except Exception as e:
            logger.exception(f"🔥 Exception during {quality} conversion: {e}")
            return None

    def _check_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available on the system"""
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _get_video_info(self, file_path: str) -> dict:
        """Get video information using FFmpeg"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {"duration": 0, "width": 0, "height": 0}
            
            import json
            data = json.loads(result.stdout)

            video_stream = None
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                    break
            
            duration = 0
            width = 0
            height = 0
            
            if video_stream:
                width = int(video_stream.get("width", 0))
                height = int(video_stream.get("height", 0))
            
            format_info = data.get("format", {})
            duration_str = format_info.get("duration", "0")
            try:
                duration = int(float(duration_str))
            except (ValueError, TypeError):
                duration = 0
            
            return {
                "duration": duration,
                "width": width,
                "height": height
            }
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {"duration": 0, "width": 0, "height": 0}

    async def _get_video_duration(self, file_path: str) -> float:
        """Get video duration using ffprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                "-of", "csv=p=0", file_path
            ]
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                duration_str = stdout.decode().strip()
                return float(duration_str)
            return 0
        except Exception as e:
            logger.warning(f"Could not get video duration: {e}")
            return 0
    