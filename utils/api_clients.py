import aiohttp
import asyncio
import requests
from config import Config
import logging
from utils.gemini_client import GeminiVideoClient

class VideoAPIClients:
    def __init__(self):
        self.gemini_client = GeminiVideoClient()
        self.stability_headers = {
            "Authorization": f"Bearer {Config.STABILITY_API_KEY}",
        } if Config.STABILITY_API_KEY else {}
        self.luma_headers = {
            "Authorization": f"Bearer {Config.LUMA_API_KEY}",
        } if Config.LUMA_API_KEY else {}
    
    async def generate_video_from_image_prompt(self, image_path: str, prompt: str) -> str:
        """Main video generation method using Gemini AI"""
        try:
            # Try Gemini-enhanced generation first
            logging.info("🎨 Using Gemini AI for enhanced video generation...")
            video_path = await self.gemini_client.generate_video_from_image_prompt(image_path, prompt)
            
            if video_path:
                return video_path
            
            # Fallback to direct Stability AI if Gemini fails
            logging.info("🔄 Falling back to direct Stability AI...")
            return await self.stability_image_to_video(image_path, prompt)
            
        except Exception as e:
            logging.error(f"Video generation error: {e}")
            return None
    
    async def stability_image_to_video(self, image_path: str, prompt: str = ""):
        """Direct Stability AI video generation"""
        if not self.stability_headers:
            return None
            
        try:
            async with aiohttp.ClientSession() as session:
                with open(image_path, 'rb') as img_file:
                    form_data = aiohttp.FormData()
                    form_data.add_field('image', img_file)
                    form_data.add_field('seed', '0')
                    form_data.add_field('cfg_scale', '1.8')
                    form_data.add_field('motion_bucket_id', '127')
                    
                    if prompt:
                        form_data.add_field('prompt', prompt)
                
                async with session.post(
                    "https://api.stability.ai/v2beta/image-to-video",
                    headers=self.stability_headers,
                    data=form_data,
                    timeout=aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        generation_id = data.get('id')
                        return await self._poll_stability_result(session, generation_id)
                    else:
                        error_text = await response.text()
                        logging.error(f"Stability API error: {error_text}")
                        return None
                        
        except Exception as e:
            logging.error(f"Stability client error: {e}")
            return None
    
    async def _poll_stability_result(self, session, generation_id: str, max_attempts: int = 30):
        """Poll for Stability AI result"""
        for attempt in range(max_attempts):
            await asyncio.sleep(5)
            
            try:
                async with session.get(
                    f"https://api.stability.ai/v2beta/image-to-video/result/{generation_id}",
                    headers=self.stability_headers
                ) as response:
                    
                    if response.status == 200:
                        video_data = await response.read()
                        return self._save_video_file(video_data, f"stability_{generation_id}")
                    
                    elif response.status == 202:
                        continue
                    else:
                        break
                        
            except Exception as e:
                logging.error(f"Polling error: {e}")
                continue
        
        return None
    
    def _save_video_file(self, video_data: bytes, filename: str) -> str:
        """Save video data to temporary file"""
        import tempfile
        import os
        
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp_file.write(video_data)
        temp_file.close()
        
        return temp_file.name