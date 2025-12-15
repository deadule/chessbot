import os
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

VIDEO_STORAGE_DIR = os.getenv("VIDEO_STORAGE_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "video_storage"))

class VideoProcessor:
    """Handles video processing and conversion using FFmpeg"""
    
    def __init__(self, bot: Bot, video_storage_dir: str = None, progress_callback: Callable = None):
        self.bot = bot
        self.video_storage_dir = video_storage_dir or VIDEO_STORAGE_DIR
        os.makedirs(self.video_storage_dir, exist_ok=True)
        logger.info(f"Video storage directory: {self.video_storage_dir}")
        self.progress_callback = progress_callback
        
    async def process_video(self, file_id: str, video_id: int, title: str, chat_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Process video and convert to 480p and 1080p
        Returns tuple of (file_id_480p, file_id_1080p)
        """
        start_time = time.time()
        logger.info(f"🎬 Starting video processing for video {video_id}: '{title}'")
        
        try:
            video_dir = os.path.join(self.video_storage_dir, f"video_{video_id}")
            os.makedirs(video_dir, exist_ok=True)
            
            await self._update_progress(0, "📥 Downloading original video...")
            logger.info(f"📥 Downloading video {video_id} from Telegram...")
            original_path = await self._download_video(file_id, video_dir)
            if not original_path:
                error_msg = (
                    f"❌ **Ошибка загрузки видео**\n\n"
                    f"Не удалось загрузить видео с серверов Telegram.\n\n"
                    f"Возможные причины:\n"
                    f"• Видео слишком большое\n"
                    f"• Проблемы с соединением\n"
                    f"• Превышено время ожидания ({VIDEO_DOWNLOAD_TIMEOUT}s)\n\n"
                    f"Попробуйте загрузить видео позже или используйте видео меньшего размера."
                )
                logger.error(f"Video download failed for video {video_id} (file_id: {file_id})")
                await self._update_progress(0, error_msg)
                return None, None
            
            download_time = time.time() - start_time
            logger.info(f"✅ Video downloaded in {download_time:.1f}s")
            
            await self._update_progress(20, "🔄 Converting to 480p...")
            logger.info(f"🔄 Converting video {video_id} to 480p...")
            file_480p = await self._convert_video(original_path, video_dir, "480p", video_id)
            if not file_480p:
                error_msg = f"❌ Failed to convert video to 480p"
                logger.error(error_msg)
                await self._update_progress(20, error_msg)
                return None, None
            
            convert_480p_time = time.time() - start_time - download_time
            logger.info(f"✅ 480p conversion completed in {convert_480p_time:.1f}s")

            await self._update_progress(60, "🔄 Converting to 1080p...")
            logger.info(f"🔄 Converting video {video_id} to 1080p...")
            file_1080p = await self._convert_video(original_path, video_dir, "1080p", video_id)
            if not file_1080p:
                error_msg = f"❌ Failed to convert video to 1080p"
                logger.error(error_msg)
                await self._update_progress(60, error_msg)
                return None, None
            
            convert_1080p_time = time.time() - start_time - download_time - convert_480p_time
            logger.info(f"✅ 1080p conversion completed in {convert_1080p_time:.1f}s")

            await self._update_progress(80, "📤 Uploading 480p to Telegram...")
            logger.info(f"📤 Uploading 480p version of video {video_id}...")
            file_id_480p = await self._upload_video(file_480p, title, "480p", chat_id)
            
            await self._update_progress(90, "📤 Uploading 1080p to Telegram...")
            logger.info(f"📤 Uploading 1080p version of video {video_id}...")
            file_id_1080p = await self._upload_video(file_1080p, title, "1080p", chat_id)
            
            await self._update_progress(95, "✅ Processing completed!")
            
            total_time = time.time() - start_time
            logger.info(f"🎉 Video {video_id} processing completed successfully in {total_time:.1f}s total")
            logger.info(f"Video files saved to: {video_dir}")
            await self._update_progress(100, f"✅ Processing completed in {total_time:.1f}s!")
            
            return file_id_480p, file_id_1080p
            
        except Exception as e:
            error_msg = f"❌ Error processing video"
            logger.error(error_msg, exc_info=True)
            await self._update_progress(0, error_msg)
            return None, None
    
    async def _update_progress(self, percentage: int, message: str):
        """Update progress and send notification if callback is available"""
        if self.progress_callback:
            await self.progress_callback(percentage, message)
        else:
            logger.info(f"Progress {percentage}%: {message}")
    
    def _create_progress_bar(self, percentage: int, width: int = 20) -> str:
        """Create a visual progress bar"""
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {percentage}%"
    
    async def _download_video(self, file_id: str, temp_dir: str) -> Optional[str]:
        """Download video from Telegram"""
        logger.info(f"Starting download for file_id: {file_id}, temp_dir: {temp_dir}")
        try:
            logger.info(f"Calling bot.get_file({file_id})...")
            file = await self.bot.get_file(file_id)
            logger.info(f"Got file object: size={file.file_size if file.file_size else 'unknown'}")
            file_path = os.path.join(temp_dir, f"original_{file_id}.mp4")

            file_size_mb = file.file_size / (1024 * 1024) if file.file_size else None
            if file_size_mb:
                logger.info(f"Downloading video {file_id} (size: {file_size_mb:.2f} MB, timeout: {VIDEO_DOWNLOAD_TIMEOUT}s)")
            
            logger.info(f"File object: {file}")
            logger.info(f"File path: {file.file_path}")
            
            await file.download_to_drive(file_path, write_timeout=VIDEO_DOWNLOAD_TIMEOUT)
            
            if os.path.exists(file_path):
                downloaded_size = os.path.getsize(file_path) / (1024 * 1024)
                logger.info(f"Successfully downloaded video {file_id} ({downloaded_size:.2f} MB)")
                return file_path
            else:
                logger.error(f"Download completed but file not found at {file_path}")
                return None

        except TelegramError as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            if "Timed out" in error_msg or "timeout" in error_msg.lower():
                logger.error(
                    f"Timeout error downloading video {file_id}: {error_msg} "
                    f"(timeout setting: {VIDEO_DOWNLOAD_TIMEOUT}s). "
                    f"The video may be too large or the connection is slow."
                )
            elif "Network" in error_type or "Connection" in error_msg:
                logger.error(
                    f"Network error downloading video {file_id}: {error_msg}. "
                    f"Please check your connection and try again."
                )
            else:
                logger.error(
                    f"Failed to download video {file_id}: {error_type} - {error_msg}"
                )
            return None
        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                f"Unexpected error downloading video {file_id}: {error_type} - {str(e)}",
                exc_info=True
            )
            return None
    
    async def _convert_video(self, input_path: str, temp_dir: str, quality: str, video_id: int) -> Optional[str]:
        """Convert video to specified quality using FFmpeg with progress tracking"""
        try:
            output_path = os.path.join(temp_dir, f"{quality}_{video_id}.mp4")
            
            duration = await self._get_video_duration(input_path)
            if duration <= 0:
                logger.warning(f"Could not determine video duration for {quality} conversion")
                duration = 60

            if quality == "480p":
                cmd = [
                    "ffmpeg", "-i", input_path,
                    "-vf", "scale=854:480",
                    "-c:v", "libx264",
                    "-crf", "23",
                    "-preset", "medium",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-progress", "pipe:1",
                    "-y", 
                    output_path
                ]
            elif quality == "1080p":
                cmd = [
                    "ffmpeg", "-i", input_path,
                    "-vf", "scale=1920:1080",
                    "-c:v", "libx264",
                    "-crf", "20",
                    "-preset", "medium",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-progress", "pipe:1",
                    "-y",
                    output_path
                ]
            else:
                logger.error(f"Unsupported quality: {quality}")
                return None
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            progress_start = 20 if quality == "480p" else 60
            last_progress = 0
            
            while True:
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=1.0)
                    if not line:
                        break
                    
                    line_str = line.decode().strip()
                    if "out_time_ms=" in line_str:
                        try:
                            time_str = line_str.split("out_time_ms=")[1].split()[0]
                            current_time = int(time_str) / 1000000  # Convert to seconds
                            progress = min(int((current_time / duration) * 100), 100)
                            
                            if progress - last_progress >= 5:
                                progress_bar = self._create_progress_bar(progress)
                                await self._update_progress(
                                    progress_start + int(progress * 0.4),  # Scale to conversion range
                                    f"🔄 Converting to {quality}... {progress_bar}"
                                )
                                last_progress = progress
                        except (ValueError, IndexError):
                            pass
                            
                except asyncio.TimeoutError:
                    if process.returncode is not None:
                        break
                    continue
            
            await process.wait()
            
            if process.returncode != 0:
                stderr = await process.stderr.read()
                error_msg = f"FFmpeg failed for {quality}: {stderr.decode()}"
                logger.error(error_msg)
                return None
            
            if not os.path.exists(output_path):
                logger.error(f"Output file not created for {quality}")
                return None
            
            logger.info(f"✅ {quality} conversion completed successfully")
            return output_path
            
        except asyncio.TimeoutError:
            logger.error(f"FFmpeg timeout for {quality}")
            return None
        except Exception as e:
            logger.error(f"Error converting video to {quality}: {e}", exc_info=True)
            return None
    
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
    
    async def _upload_video(self, file_path: str, title: str, quality: str, chat_id: str) -> Optional[str]:
        """Upload converted video to Telegram"""
        try:
            with open(file_path, 'rb') as video_file:
                message = await self.bot.send_video(
                    chat_id=chat_id, 
                    video=video_file,
                    caption=f"{title} ({quality})",
                    supports_streaming=True
                )
                return message.video.file_id
        except TelegramError as e:
            logger.error(f"Failed to upload {quality} video: {e}")
            return None
    
    def delete_video_files(self, video_id: int) -> bool:
        """Delete video files from storage for a given video_id"""
        try:
            video_dir = os.path.join(self.video_storage_dir, f"video_{video_id}")
            if os.path.exists(video_dir):
                shutil.rmtree(video_dir, ignore_errors=True)
                logger.info(f"Deleted video files for video_id {video_id} from {video_dir}")
                return True
            else:
                logger.debug(f"Video directory not found for video_id {video_id}: {video_dir}")
                return False
        except Exception as e:
            logger.error(f"Error deleting video files for video_id {video_id}: {e}", exc_info=True)
            return False
    
    @staticmethod
    def delete_video_files_static(video_id: int, video_storage_dir: str = None) -> bool:
        """Static method to delete video files without instantiating VideoProcessor"""
        try:
            storage_dir = video_storage_dir or VIDEO_STORAGE_DIR
            video_dir = os.path.join(storage_dir, f"video_{video_id}")
            if os.path.exists(video_dir):
                shutil.rmtree(video_dir, ignore_errors=True)
                logger.info(f"Deleted video files for video_id {video_id} from {video_dir}")
                return True
            else:
                logger.debug(f"Video directory not found for video_id {video_id}: {video_dir}")
                return False
        except Exception as e:
            logger.error(f"Error deleting video files for video_id {video_id}: {e}", exc_info=True)
            return False
    
    def check_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available on the system"""
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def get_video_info(self, file_path: str) -> dict:
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
