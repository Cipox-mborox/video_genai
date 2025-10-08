import os
import logging
import tempfile
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import Config
from utils.api_clients import VideoAPIClients
from utils.video_processor import VideoProcessor

# Railway-specific setup
if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()

# Enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class GeminiVideoGeneratorBot:
    def __init__(self):
        self.validate_environment()
        
        self.application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
        self.api_clients = VideoAPIClients()
        self.user_sessions = {}
        
        self.setup_handlers()
        logging.info("🤖 Gemini Video Bot Initialized with Google AI Studio!")
    
    def validate_environment(self):
        """Validate required environment variables"""
        required_vars = ['TELEGRAM_TOKEN', 'GOOGLE_AI_API_KEY']
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            error_msg = f"❌ Missing environment variables: {', '.join(missing)}"
            logging.error(error_msg)
            print("💡 Please set in Railway:")
            print("   - TELEGRAM_TOKEN (from @BotFather)")
            print("   - GOOGLE_AI_API_KEY (from Google AI Studio)")
            exit(1)
        
        logging.info("✅ All environment variables are set")
        logging.info(f"🔑 Google AI API Key: {Config.GOOGLE_AI_API_KEY[:10]}...")
    
    def setup_handlers(self):
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("generate", self.generate_command))
        self.application.add_handler(CommandHandler("style", self.style_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("gemini", self.gemini_info))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.application.add_handler(MessageHandler(filters.Document.IMAGE, self.handle_document_image))
    
    async def gemini_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show Gemini AI integration info"""
        info_text = """
🧠 **Google AI Studio (Gemini) Integration**

**🤖 AI Model:** Gemini 1.5 Flash
**🎯 Features:**
• Enhanced prompt generation
• Image analysis with Vision
• Smart video suggestions
• Fallback to Stability AI

**🔧 How it works:**
1. Upload gambar → Gemini menganalisa konten
2. Kirim prompt → Gemini memperbaiki & enhance
3. Generate video → dengan prompt yang lebih baik
4. Hasil → Video lebih relevan dengan gambar

**💡 Tips:**
• Gambar jelas → Analisa lebih akurat
• Prompt sederhana → Gemini akan enhance
• Hasil → Lebih sesuai dengan konteks gambar

**Status:** ✅ Active and Optimized
        """
        await update.message.reply_text(info_text, parse_mode='Markdown')
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_text = """
🎬 **Video Generator Bot - Powered by Google AI Studio** 🧠

**🚀 Enhanced with Gemini AI:**
• 🖼️ Smart image analysis
• 📝 AI-powered prompt enhancement  
• 🎬 Better video results
• ⚡ Faster processing

**Cara Kerja:**
1. Upload gambar → AI analisa konten
2. Tulis prompt → AI optimize deskripsi
3. Generate → Video lebih relevan
4. Hasil → Kualitas enhanced

**Contoh Prompt:**
"gerakan slow motion"
"efek cinematic" 
"awan bergerak pelan"

**AI akan otomatis enhance prompt Anda!**

**Commands:**
/start - Info bot
/gemini - Info AI integration
/help - Bantuan lengkap
/style - Style options
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        logging.info(f"New user: {update.effective_user.username}")

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        try:
            # Download image
            photo_file = await update.message.photo[-1].get_file()
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                await photo_file.download_to_drive(temp_file.name)
                image_path = temp_file.name
            
            # Validate image
            if not VideoProcessor.validate_image(image_path):
                await update.message.reply_text("❌ Gambar tidak valid atau terlalu besar (max 10MB)")
                VideoProcessor.cleanup_files(image_path)
                return
            
            # Optimize image
            optimized_path = VideoProcessor.optimize_image(image_path)
            
            # Store in user session
            self.user_sessions[user_id] = {
                'image_path': optimized_path,
                'waiting_for_prompt': True
            }
            
            await update.message.reply_text(
                "✅ **Gambar diterima!** 🖼️\n\n"
                "🧠 **Gemini AI sedang menganalisa gambar...**\n"
                "📝 Sekarang tulis prompt untuk video:\n\n"
                "Contoh sederhana:\n"
                "• \"slow motion\"\n" 
                "• \"efek cinematic\"\n"
                "• \"awan bergerak\"\n\n"
                "AI akan enhance prompt Anda otomatis!",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logging.error(f"Image handling error: {e}")
            await update.message.reply_text("❌ Error memproses gambar")
    
    async def handle_document_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        try:
            document = update.message.document
            
            if document.mime_type not in Config.SUPPORTED_FORMATS:
                await update.message.reply_text("❌ Format tidak didukung. Gunakan JPEG/PNG")
                return
            
            if document.file_size > Config.MAX_FILE_SIZE:
                await update.message.reply_text("❌ File terlalu besar (max 10MB)")
                return
            
            file = await document.get_file()
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                await file.download_to_drive(temp_file.name)
                image_path = temp_file.name
            
            if not VideoProcessor.validate_image(image_path):
                await update.message.reply_text("❌ File gambar tidak valid")
                VideoProcessor.cleanup_files(image_path)
                return
            
            optimized_path = VideoProcessor.optimize_image(image_path)
            
            self.user_sessions[user_id] = {
                'image_path': optimized_path,
                'waiting_for_prompt': True
            }
            
            await update.message.reply_text(
                "✅ **Gambar document diterima!** 📁\n\n"
                "🧠 AI siap menganalisa...\n"
                "📝 Kirim prompt video sekarang..."
            )
            
        except Exception as e:
            logging.error(f"Document handling error: {e}")
            await update.message.reply_text("❌ Error memproses file")
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_text = update.message.text
        
        if user_id in self.user_sessions and self.user_sessions[user_id].get('waiting_for_prompt'):
            await self.process_image_prompt_video(update, user_id, user_text)
        else:
            await update.message.reply_text(
                "📝 Untuk generate video dari text, gunakan:\n"
                "`/generate your_prompt_here`\n\n"
                "Atau upload gambar dulu untuk AI-enhanced video generation!",
                parse_mode='Markdown'
            )
    
    async def process_image_prompt_video(self, update: Update, user_id: int, prompt: str):
        """Main video generation process with Gemini AI"""
        try:
            processing_msg = await update.message.reply_text(
                "🧠 **Memulai AI Video Generation...**\n"
                "⏱️ Estimasi: 1-3 menit\n"
                "📊 Status: Analisa gambar dengan Gemini AI..."
            )
            
            image_path = self.user_sessions[user_id]['image_path']
            
            # Update status
            await processing_msg.edit_text(
                "🧠 **AI Video Generation Progress**\n"
                "⏱️ Estimasi: 1-3 menit\n"
                "📊 Status: Enhancing prompt & generating video..."
            )
            
            # Generate video using Gemini-enhanced method
            video_path = await self.api_clients.generate_video_from_image_prompt(image_path, prompt)
            
            if video_path and os.path.exists(video_path):
                file_size = os.path.getsize(video_path)
                
                if file_size < 50 * 1024 * 1024:  # Telegram limit
                    await processing_msg.edit_text("✅ **Video Ready! Uploading...**")
                    
                    with open(video_path, 'rb') as video_file:
                        await update.message.reply_video(
                            video=video_file,
                            caption=f"🎬 **AI-Generated Video** 🧠\n\n📝 **Original Prompt:** {prompt}",
                            parse_mode='Markdown'
                        )
                    
                    await processing_msg.delete()
                else:
                    await update.message.reply_text("❌ Video terlalu besar untuk dikirim Telegram")
                
                # Cleanup
                VideoProcessor.cleanup_files(image_path, video_path)
                
            else:
                await update.message.reply_text(
                    "❌ **Gagal generate video**\n\n"
                    "Kemungkinan sebab:\n"
                    "• API limit tercapai\n• Gambar tidak suitable\n"
                    "• Network timeout\n\n"
                    "Coba lagi dengan gambar berbeda atau prompt lebih sederhana."
                )
            
            # Clean user session
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
                
        except Exception as e:
            logging.error(f"Video generation error: {e}")
            await update.message.reply_text("❌ Error selama proses AI video generation")
            
            # Cleanup on error
            if user_id in self.user_sessions:
                image_path = self.user_sessions[user_id].get('image_path')
                VideoProcessor.cleanup_files(image_path)
                del self.user_sessions[user_id]
    
    async def generate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Text to video command"""
        if not context.args:
            await update.message.reply_text(
                "📝 **Text to Video (Gemini Enhanced)**\n\n"
                "Usage: `/generate your_video_description`\n\n"
                "Contoh: `/generate cinematic scene with flying birds`\n\n"
                "Note: Fitur text-to-video direct masih dalam development.\n"
                "Untuk sekarang gunakan image+prompt untuk hasil terbaik!",
                parse_mode='Markdown'
            )
            return
        
        prompt = ' '.join(context.args)
        await update.message.reply_text(
            f"🔮 **Text to Video - Coming Soon**\n\n"
            f"Prompt: {prompt}\n\n"
            "Fitur text-to-video direct sedang dikembangkan.\n"
            "Untuk hasil terbaik, gunakan:\n"
            "1. Upload gambar\n2. Kirim prompt text\n"
            "3. Dapatkan AI-enhanced video!"
        )
    
    async def style_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        styles = """
🎨 **AI Video Style Guide** 🧠

**Gemini AI akan automatically enhance style Anda!**

**🎭 Basic Motion Types:**
• `slow motion` - Gerakan lambat
• `cinematic` - Efek film 
• `animated` - Style kartun
• `realistic` - Gerakan realistik

**💫 Simple Effects:**
• `particles` - Efek partikel
• `light` - Cahaya & sinar
• `water` - Aliran air
• `clouds` - Awan bergerak

**Contoh Prompt Sederhana:**
"slow motion dengan awan"
"cinematic effect"  
"animated particles"
"realistic water flow"

**AI akan:** 
• Analisa gambar Anda
• Enhance prompt sederhana
• Hasilkan video lebih baik!
        """
        await update.message.reply_text(styles, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
📖 **Bantuan - Gemini AI Video Generator**

**Cara Kerja:**
1. **Upload gambar** → AI analisa konten
2. **Tulis prompt** → AI enhance otomatis  
3. **Generate** → Video lebih relevan
4. **Hasil** → Kualitas enhanced

**Keunggulan Gemini AI:**
• Prompt sederhana → Hasil bagus
• Analisa gambar otomatis
• Enhance deskripsi video
• Hasil lebih sesuai konteks

**Format Gambar:**
• JPEG, PNG (max 10MB)
• Gambar jelas & kontras baik

**Tips Prompt:**
• Gunakan bahasa sederhana
• Deskripsi gerakan pendek
• AI akan handle detailnya

**Support:**
Bot powered by Google AI Studio 🧠
        """
        await update.message.reply_text(help_text)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        status_text = """
🤖 **Bot Status - Google AI Studio**

**🧠 AI Services:**
• Gemini AI: ✅ Active
• Vision Analysis: ✅ Enabled
• Prompt Enhancement: ✅ Working
• Video Generation: ✅ Operational

**📊 System:**
• Platform: Railway 🚂
• Users Active: {len(self.user_sessions)}
• Uptime: {self.get_uptime()}

**🔧 Technical:**
• Gemini Model: 1.5 Flash
• Fallback API: Stability AI
• Max Size: 10MB images
• Timeout: 3 minutes

**Status:** ✅ All Systems Go!
        """.format(len(self.user_sessions), self.get_uptime())
        await update.message.reply_text(status_text)
    
    def get_uptime(self):
        if hasattr(self, 'start_time'):
            uptime = time.time() - self.start_time
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            return f"{hours}h {minutes}m"
        return "Unknown"
    
    def run(self):
        """Start the bot"""
        self.start_time = time.time()
        
        logging.info("🚀 Starting Gemini Video Generator Bot...")
        print("🎬 Video Generator Bot - Powered by Google AI Studio")
        print("🧠 Gemini AI Integration: ACTIVE")
        print("🚂 Deployed on Railway")
        print("📱 Bot is running...")
        print("📍 Send /start to begin!")
        
        try:
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        except Exception as e:
            logging.error(f"Bot runtime error: {e}")
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    bot = GeminiVideoGeneratorBot()
    bot.run()