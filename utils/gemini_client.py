import google.generativeai as genai
import logging
import base64
import tempfile
import asyncio
import aiohttp
from config import Config
from PIL import Image
import io

class GeminiVideoClient:
    def __init__(self):
        # Configure Gemini
        genai.configure(api_key=Config.GOOGLE_AI_API_KEY)
        
        # Initialize models
        try:
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.vision_model = genai.GenerativeModel('gemini-1.5-flash')
            logging.info("✅ Gemini AI Models Initialized")
        except Exception as e:
            logging.error(f"❌ Gemini initialization failed: {e}")
            raise
    
    async def generate_video_from_image_prompt(self, image_path: str, prompt: str) -> str:
        """
        Generate video using Gemini AI from image + prompt
        Note: Currently Gemini doesn't directly generate videos,
        but we can use it for enhanced image analysis and prompt generation
        for other video APIs
        """
        try:
            # Step 1: Analyze image with Gemini for better prompt enhancement
            enhanced_prompt = await self.enhance_prompt_with_vision(image_path, prompt)
            
            # Step 2: Generate video using enhanced prompt with other APIs
            # For now, we'll use Gemini to create better prompts for Stability AI
            video_path = await self.fallback_to_stability_ai(image_path, enhanced_prompt)
            
            return video_path
            
        except Exception as e:
            logging.error(f"Gemini video generation error: {e}")
            return None
    
    async def enhance_prompt_with_vision(self, image_path: str, user_prompt: str) -> str:
        """Use Gemini Vision to analyze image and enhance the prompt"""
        try:
            # Load and prepare image
            with open(image_path, 'rb') as img_file:
                image_data = img_file.read()
            
            image = Image.open(io.BytesIO(image_data))
            
            # Create prompt for analysis
            analysis_prompt = f"""
            Analyze this image and enhance the video generation prompt: "{user_prompt}"
            
            Provide an improved, detailed prompt for video generation that includes:
            1. Specific motion suggestions based on image content
            2. Style recommendations
            3. Camera movement ideas
            4. Lighting and atmosphere
            5. Object-specific animations
            
            Return ONLY the enhanced prompt, nothing else.
            """
            
            # Use Gemini Vision
            response = self.vision_model.generate_content([analysis_prompt, image])
            
            enhanced_prompt = response.text.strip()
            logging.info(f"🎨 Enhanced prompt: {enhanced_prompt}")
            
            return enhanced_prompt if enhanced_prompt else user_prompt
            
        except Exception as e:
            logging.error(f"Gemini vision enhancement error: {e}")
            return user_prompt  # Return original prompt if enhancement fails
    
    async def generate_video_direct(self, prompt: str) -> str:
        """
        Direct text-to-video generation (when available)
        Currently uses Gemini for script/storyboard generation
        """
        try:
            video_script_prompt = f"""
            Create a detailed video script and storyboard for: "{prompt}"
            
            Include:
            - Scene descriptions
            - Camera movements
            - Visual effects
            - Motion details
            - Duration: 5-10 seconds
            
            Format as a structured video plan.
            """
            
            response = self.model.generate_content(video_script_prompt)
            video_plan = response.text
            
            # Save plan as text (for now)
            # When Gemini Video API is available, we'll generate actual video
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(f"Video Plan for: {prompt}\n\n{video_plan}")
                return f.name
                
        except Exception as e:
            logging.error(f"Gemini direct video error: {e}")
            return None
    
    async def fallback_to_stability_ai(self, image_path: str, enhanced_prompt: str) -> str:
        """Fallback to Stability AI with Gemini-enhanced prompt"""
        try:
            if not Config.STABILITY_API_KEY:
                logging.error("No Stability API key available")
                return None
            
            headers = {
                "Authorization": f"Bearer {Config.STABILITY_API_KEY}",
            }
            
            async with aiohttp.ClientSession() as session:
                with open(image_path, 'rb') as img_file:
                    form_data = aiohttp.FormData()
                    form_data.add_field('image', img_file)
                    form_data.add_field('seed', '0')
                    form_data.add_field('cfg_scale', '1.8')
                    form_data.add_field('motion_bucket_id', '127')
                    form_data.add_field('prompt', enhanced_prompt)
                
                async with session.post(
                    "https://api.stability.ai/v2beta/image-to-video",
                    headers=headers,
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
            logging.error(f"Stability fallback error: {e}")
            return None
    
    async def _poll_stability_result(self, session, generation_id: str, max_attempts: int = 30):
        """Poll for Stability AI result"""
        headers = {
            "Authorization": f"Bearer {Config.STABILITY_API_KEY}",
        }
        
        for attempt in range(max_attempts):
            await asyncio.sleep(5)
            
            try:
                async with session.get(
                    f"https://api.stability.ai/v2beta/image-to-video/result/{generation_id}",
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        video_data = await response.read()
                        return self._save_video_file(video_data, f"gemini_enhanced_{generation_id}")
                    
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
    
    async def analyze_image_content(self, image_path: str) -> dict:
        """Use Gemini to analyze image content for better video generation"""
        try:
            with open(image_path, 'rb') as img_file:
                image_data = img_file.read()
            
            image = Image.open(io.BytesIO(image_data))
            
            analysis_prompt = """
            Analyze this image in detail and provide:
            1. Main subjects/objects
            2. Background elements
            3. Colors and lighting
            4. Potential motion opportunities
            5. Recommended video styles
            
            Return as a structured analysis.
            """
            
            response = self.vision_model.generate_content([analysis_prompt, image])
            return {
                'analysis': response.text,
                'suggested_prompts': self._extract_video_suggestions(response.text)
            }
            
        except Exception as e:
            logging.error(f"Image analysis error: {e}")
            return {}
    
    def _extract_video_suggestions(self, analysis: str) -> list:
        """Extract video suggestions from Gemini analysis"""
        # Simple extraction - you can make this more sophisticated
        suggestions = []
        
        if "sky" in analysis.lower() or "cloud" in analysis.lower():
            suggestions.append("slow moving clouds")
        if "water" in analysis.lower() or "river" in analysis.lower():
            suggestions.append("flowing water motion")
        if "tree" in analysis.lower() or "leaf" in analysis.lower():
            suggestions.append("gentle leaf movement")
        if "person" in analysis.lower() or "people" in analysis.lower():
            suggestions.append("subtle human movement")
        
        return suggestions if suggestions else ["cinematic slow motion"]