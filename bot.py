import os
import logging
import tempfile
import time
import traceback
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Ubah ke DEBUG untuk lebih detail
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class DebugVideoBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_TOKEN')
        if not self.token:
            raise ValueError("❌ TELEGRAM_TOKEN not set")
            
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
        self.user_sessions = {}
        
        logging.info("✅ Debug Bot Initialized")
    
    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("debug", self.debug_command))
        self.application.add_handler(CommandHandler("test", self.test_command))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🐛 **Debug Bot Mode**\n\n"
            "Mari test video generation step-by-step:\n"
            "1. Upload gambar\n"
            "2. Kirim prompt sederhana\n"
            "3. Lihat debug info\n\n"
            "Commands:\n"
            "/debug - Status system\n"
            "/test - Test API connection"
        )
    
    async def debug_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check system status"""
        import psutil
        
        # Check API keys
        google_key = os.getenv('GOOGLE_AI_API_KEY')
        stability_key = os.getenv('STABILITY_API_KEY')
        
        debug_info = f"""
🔍 **DEBUG INFORMATION**

**API Keys:**
• Google AI: {'✅ Set' if google_key else '❌ Missing'}
• Stability AI: {'✅ Set' if stability_key else '❌ Missing'}

**System:**
• Memory: {psutil.virtual_memory().percent}%
• Disk: {psutil.disk_usage('/').percent}%
• Active Sessions: {len(self.user_sessions)}

**Environment:**
• Python: {os.sys.version}
• Platform: {os.sys.platform}
        """
        await update.message.reply_text(debug_info)
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test API connections"""
        try:
            # Test Google AI Studio
            import google.generativeai as genai
            google_key = os.getenv('GOOGLE_AI_API_KEY')
            
            if google_key:
                genai.configure(api_key=google_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content("Hello, test response")
                google_status = "✅ Connected - " + response.text[:50] + "..."
            else:
                google_status = "❌ No API Key"
            
            # Test Stability AI
            stability_key = os.getenv('STABILITY_API_KEY')
            if stability_key:
                import requests
                headers = {"Authorization": f"Bearer {stability_key}"}
                response = requests.get(
                    "https://api.stability.ai/v1/user/account",
                    headers=headers,
                    timeout=10
                )
                if response.status_code == 200:
                    stability_status = "✅ Connected"
                else:
                    stability_status = f"❌ API Error: {response.status_code}"
            else:
                stability_status = "❌ No API Key"
            
            test_results = f"""
🧪 **API TEST RESULTS**

Google AI Studio:
{google_status}

Stability AI:
{stability_status}

**Conclusion:** {'✅ Ready for video generation' if stability_key else '❌ Need Stability API key'}
            """
            await update.message.reply_text(test_results)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Test failed: {str(e)}")
    
    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle image upload dengan debug info"""
        user_id = update.effective_user.id
        
        try:
            # Download image
            photo_file = await update.message.photo[-1].get_file()
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                await photo_file.download_to_drive(temp_file.name)
                image_path = temp_file.name
            
            # Get file info
            file_size = os.path.getsize(image_path)
            
            self.user_sessions[user_id] = {
                'image_path': image_path,
                'waiting_for_prompt': True
            }
            
            await update.message.reply_text(
                f"🖼️ **Image Received**\n\n"
                f"• Size: {file_size / 1024:.1f} KB\n"
                f"• Ready for prompt\n\n"
                f"Kirim prompt sederhana seperti: \"slow motion\""
            )
            
        except Exception as e:
            logging.error(f"Image error: {e}")
            await update.message.reply_text(f"❌ Image error: {str(e)}")
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_text = update.message.text
        
        if user_id in self.user_sessions and self.user_sessions[user_id].get('waiting_for_prompt'):
            await self.try_video_generation(update, user_id, user_text)
        else:
            await update.message.reply_text("Upload gambar dulu, lalu kirim prompt")
    
    async def try_video_generation(self, update: Update, user_id: int, prompt: str):
        """Coba berbagai method video generation"""
        try:
            image_path = self.user_sessions[user_id]['image_path']
            
            # Method 1: Stability AI (Paling reliable)
            await update.message.reply_text("🔄 Method 1: Trying Stability AI...")
            video_path = await self.try_stability_ai(image_path, prompt)
            
            if video_path:
                await self.send_video_result(update, video_path, prompt, "Stability AI")
                return
            
            # Method 2: Google AI + Fallback
            await update.message.reply_text("🔄 Method 2: Trying Google AI Analysis...")
            video_path = await self.try_google_ai_fallback(image_path, prompt)
            
            if video_path:
                await self.send_video_result(update, video_path, prompt, "Google AI Enhanced")
                return
            
            # Method 3: Simple conversion (fallback)
            await update.message.reply_text("🔄 Method 3: Trying fallback method...")
            video_path = await self.try_fallback_method(image_path, prompt)
            
            if video_path:
                await self.send_video_result(update, video_path, prompt, "Fallback")
                return
            
            # All methods failed
            await update.message.reply_text(
                "❌ **All generation methods failed**\n\n"
                "Possible solutions:\n"
                "1. Add Stability AI API key\n"
                "2. Try different image\n"
                "3. Use simpler prompt\n"
                "4. Check API quota\n\n"
                "Run /debug for system status"
            )
            
        except Exception as e:
            logging.error(f"Generation error: {traceback.format_exc()}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
        
        finally:
            # Cleanup
            if user_id in self.user_sessions:
                image_path = self.user_sessions[user_id].get('image_path')
                if image_path and os.path.exists(image_path):
                    os.unlink(image_path)
                del self.user_sessions[user_id]
    
    async def try_stability_ai(self, image_path: str, prompt: str) -> str:
        """Try Stability AI video generation"""
        try:
            stability_key = os.getenv('STABILITY_API_KEY')
            if not stability_key:
                logging.warning("No Stability API key")
                return None
            
            import aiohttp
            headers = {"Authorization": f"Bearer {stability_key}"}
            
            async with aiohttp.ClientSession() as session:
                with open(image_path, 'rb') as img_file:
                    form_data = aiohttp.FormData()
                    form_data.add_field('image', img_file)
                    form_data.add_field('seed', '0')
                    form_data.add_field('cfg_scale', '1.8')
                    form_data.add_field('motion_bucket_id', '127')
                    form_data.add_field('prompt', prompt)
                
                async with session.post(
                    "https://api.stability.ai/v2beta/image-to-video",
                    headers=headers,
                    data=form_data,
                    timeout=60
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        generation_id = data.get('id')
                        logging.info(f"Stability generation started: {generation_id}")
                        
                        # Poll for result
                        return await self.poll_stability_result(session, generation_id)
                    else:
                        error_text = await response.text()
                        logging.error(f"Stability API error: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logging.error(f"Stability AI error: {e}")
            return None
    
    async def poll_stability_result(self, session, generation_id: str, max_attempts: int = 20):
        """Poll Stability AI for result"""
        headers = {"Authorization": f"Bearer {os.getenv('STABILITY_API_KEY')}"}
        
        for attempt in range(max_attempts):
            await asyncio.sleep(5)
            logging.info(f"Polling attempt {attempt + 1}/{max_attempts}")
            
            try:
                async with session.get(
                    f"https://api.stability.ai/v2beta/image-to-video/result/{generation_id}",
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        video_data = await response.read()
                        if len(video_data) > 1000:  # Minimum video size
                            temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
                            temp_file.write(video_data)
                            temp_file.close()
                            logging.info("✅ Video generated successfully")
                            return temp_file.name
                    
                    elif response.status == 202:
                        continue  # Still processing
                    else:
                        break
                        
            except Exception as e:
                logging.error(f"Polling error: {e}")
                continue
        
        logging.error("Polling timeout")
        return None
    
    async def try_google_ai_fallback(self, image_path: str, prompt: str) -> str:
        """Try Google AI with fallback to simple video"""
        try:
            # Use Google AI to enhance prompt
            import google.generativeai as genai
            genai.configure(api_key=os.getenv('GOOGLE_AI_API_KEY'))
            
            from PIL import Image
            img = Image.open(image_path)
            
            enhanced_prompt = f"""
            Enhance this video prompt: "{prompt}"
            for the uploaded image. Make it more descriptive for video generation.
            """
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([enhanced_prompt, img])
            enhanced = response.text.strip()
            
            logging.info(f"Google AI enhanced prompt: {enhanced}")
            
            # Try Stability AI with enhanced prompt
            return await self.try_stability_ai(image_path, enhanced)
            
        except Exception as e:
            logging.error(f"Google AI fallback error: {e}")
            return None
    
    async def try_fallback_method(self, image_path: str, prompt: str) -> str:
        """Simple fallback - create slideshow video"""
        try:
            from PIL import Image, ImageDraw
            import subprocess
            import os
            
            # Create simple slideshow from image
            img = Image.open(image_path)
            
            # Create output directory
            os.makedirs('temp_frames', exist_ok=True)
            
            # Create multiple frames for video
            frames = []
            for i in range(10):
                frame = img.copy()
                draw = ImageDraw.Draw(frame)
                draw.text((10, 10), f"Frame {i+1}", fill='white')
                frame_path = f'temp_frames/frame_{i:03d}.jpg'
                frame.save(frame_path)
                frames.append(frame_path)
            
            # Create video using ffmpeg
            video_path = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
            
            # Try to use ffmpeg if available
            try:
                subprocess.run([
                    'ffmpeg', '-y', '-framerate', '5', '-i', 'temp_frames/frame_%03d.jpg',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', video_path
                ], check=True, timeout=30)
                
                # Cleanup frames
                for frame in frames:
                    if os.path.exists(frame):
                        os.unlink(frame)
                if os.path.exists('temp_frames'):
                    os.rmdir('temp_frames')
                
                return video_path
                
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                # ffmpeg not available
                return None
                
        except Exception as e:
            logging.error(f"Fallback method error: {e}")
            return None
    
    async def send_video_result(self, update: Update, video_path: str, prompt: str, method: str):
        """Send video result to user"""
        try:
            file_size = os.path.getsize(video_path)
            
            if file_size < 50 * 1024 * 1024:  # Telegram limit
                with open(video_path, 'rb') as video_file:
                    await update.message.reply_video(
                        video=video_file,
                        caption=f"🎬 **Success!** ({method})\nPrompt: {prompt}",
                        parse_mode='Markdown'
                    )
                logging.info("✅ Video sent successfully")
            else:
                await update.message.reply_text("❌ Video too large for Telegram")
            
            # Cleanup
            os.unlink(video_path)
            
        except Exception as e:
            logging.error(f"Send video error: {e}")
            await update.message.reply_text(f"❌ Error sending video: {str(e)}")
    
    def run(self):
        print("🐛 Starting Debug Bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Check environment
    required = ['TELEGRAM_TOKEN', 'GOOGLE_AI_API_KEY']
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing: {', '.join(missing)}")
        print("💡 Set in Railway environment variables")
        exit(1)
    
    bot = DebugVideoBot()
    bot.run()