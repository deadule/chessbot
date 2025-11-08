import os
import tempfile
import subprocess
import logging
import time
import asyncio
from typing import Tuple, Optional, Callable
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Handles video processing and conversion using FFmpeg"""
    
    def __init__(self, bot: Bot, temp_dir: str = None, progress_callback: Callable = None):
        self.bot = bot
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.progress_callback = progress_callback
        
    async def process_video(self, file_id: str, video_id: int, title: str, chat_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Process video and convert to 480p and 1080p
        Returns tuple of (file_id_480p, file_id_1080p)
        """
        start_time = time.time()
        logger.info(f"🎬 Starting video processing for video {video_id}: '{title}'")
        
        try:
            # Create temporary directory for this video
            video_temp_dir = os.path.join(self.temp_dir, f"video_{video_id}")
            os.makedirs(video_temp_dir, exist_ok=True)
            
            # Step 1: Download original video
            await self._update_progress(0, "📥 Downloading original video...")
            logger.info(f"📥 Downloading video {video_id} from Telegram...")
            original_path = await self._download_video(file_id, video_temp_dir)
            if not original_path:
                error_msg = f"❌ Failed to download video {file_id}"
                logger.error(error_msg)
                await self._update_progress(0, error_msg)
                return None, None
            
            download_time = time.time() - start_time
            logger.info(f"✅ Video downloaded in {download_time:.1f}s")
            
            # Step 2: Convert to 480p
            await self._update_progress(20, "🔄 Converting to 480p...")
            logger.info(f"🔄 Converting video {video_id} to 480p...")
            file_480p = await self._convert_video(original_path, video_temp_dir, "480p", video_id)
            if not file_480p:
                error_msg = f"❌ Failed to convert video {video_id} to 480p"
                logger.error(error_msg)
                await self._update_progress(20, error_msg)
                return None, None
            
            convert_480p_time = time.time() - start_time - download_time
            logger.info(f"✅ 480p conversion completed in {convert_480p_time:.1f}s")
            
            # Step 3: Convert to 1080p
            await self._update_progress(60, "🔄 Converting to 1080p...")
            logger.info(f"🔄 Converting video {video_id} to 1080p...")
            file_1080p = await self._convert_video(original_path, video_temp_dir, "1080p", video_id)
            if not file_1080p:
                error_msg = f"❌ Failed to convert video {video_id} to 1080p"
                logger.error(error_msg)
                await self._update_progress(60, error_msg)
                return None, None
            
            convert_1080p_time = time.time() - start_time - download_time - convert_480p_time
            logger.info(f"✅ 1080p conversion completed in {convert_1080p_time:.1f}s")
            
            # Step 4: Upload both versions to Telegram
            await self._update_progress(80, "📤 Uploading 480p to Telegram...")
            logger.info(f"📤 Uploading 480p version of video {video_id}...")
            file_id_480p = await self._upload_video(file_480p, title, "480p", chat_id)
            
            await self._update_progress(90, "📤 Uploading 1080p to Telegram...")
            logger.info(f"📤 Uploading 1080p version of video {video_id}...")
            file_id_1080p = await self._upload_video(file_1080p, title, "1080p", chat_id)
            
            # Step 5: Cleanup
            await self._update_progress(95, "🧹 Cleaning up temporary files...")
            self._cleanup_temp_files(video_temp_dir)
            
            total_time = time.time() - start_time
            logger.info(f"🎉 Video {video_id} processing completed successfully in {total_time:.1f}s total")
            await self._update_progress(100, f"✅ Processing completed in {total_time:.1f}s!")
            
            return file_id_480p, file_id_1080p
            
        except Exception as e:
            error_msg = f"❌ Error processing video {video_id}: {str(e)}"
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
        try:
            file = await self.bot.get_file(file_id)
            file_path = os.path.join(temp_dir, f"original_{file_id}.mp4")
            await file.download_to_drive(file_path)
            return file_path
        except TelegramError as e:
            logger.error(f"Failed to download video {file_id}: {e}")
            return None
    
    async def _convert_video(self, input_path: str, temp_dir: str, quality: str, video_id: int) -> Optional[str]:
        """Convert video to specified quality using FFmpeg with progress tracking"""
        try:
            output_path = os.path.join(temp_dir, f"{quality}_{video_id}.mp4")
            
            # Get video duration for progress calculation
            duration = await self._get_video_duration(input_path)
            if duration <= 0:
                logger.warning(f"Could not determine video duration for {quality} conversion")
                duration = 60  # Default fallback
            
            # FFmpeg command based on quality
            if quality == "480p":
                cmd = [
                    "ffmpeg", "-i", input_path,
                    "-vf", "scale=854:480",
                    "-c:v", "libx264",
                    "-crf", "23",
                    "-preset", "medium",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-progress", "pipe:1",  # Output progress to stdout
                    "-y",  # Overwrite output file
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
                    "-progress", "pipe:1",  # Output progress to stdout
                    "-y",  # Overwrite output file
                    output_path
                ]
            else:
                logger.error(f"Unsupported quality: {quality}")
                return None
            
            # Run FFmpeg with progress tracking
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Track progress
            progress_start = 20 if quality == "480p" else 60
            last_progress = 0
            
            while True:
                try:
                    # Read progress line
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=1.0)
                    if not line:
                        break
                    
                    line_str = line.decode().strip()
                    if "out_time_ms=" in line_str:
                        # Extract current time
                        try:
                            time_str = line_str.split("out_time_ms=")[1].split()[0]
                            current_time = int(time_str) / 1000000  # Convert to seconds
                            progress = min(int((current_time / duration) * 100), 100)
                            
                            # Update progress every 5%
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
                    # Check if process is still running
                    if process.returncode is not None:
                        break
                    continue
            
            # Wait for process to complete
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
                    chat_id=chat_id,  # Upload to the same chat where admin uploaded
                    video=video_file,
                    caption=f"{title} ({quality})",
                    supports_streaming=True
                )
                return message.video.file_id
        except TelegramError as e:
            logger.error(f"Failed to upload {quality} video: {e}")
            return None
    
    def _cleanup_temp_files(self, temp_dir: str):
        """Clean up temporary files"""
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")
    
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
            
            # Find video stream
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
            
            # Get duration from format
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
