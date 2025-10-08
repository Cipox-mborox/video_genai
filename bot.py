import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class WorkingVideoBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_TOKEN')
        if not self.token:
            print("❌ ERROR: TELEGRAM_TOKEN not set!")
            exit(1)
            
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
        print("✅ Bot initialized successfully!")
    
    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("test", self.test_command))
        self.application.add_handler(CommandHandler("models", self.models_command))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 **Video Generator Bot**\n\n"
            "🚀 **Now Working!**\n\n"
            "Available Commands:\n"
            "/test - Test API connections\n"
            "/models - List available AI models\n\n"
            "**How to use:**\n"
            "1. Send a photo\n"
            "2. Send a prompt for video\n"
            "3. Get your generated video!"
        )
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test available APIs"""
        try:
            # Test Google AI with correct model
            google_key = os.getenv('GOOGLE_AI_API_KEY')
            if google_key:
                import google.generativeai as genai
                genai.configure(api_key=google_key)
                
                # Get available models
                models = genai.list_models()
                available_models = [model.name for model in models]
                
                # Try to use a working model
                working_model = None
                for model_name in available_models:
                    if 'gemini' in model_name.lower():
                        working_model = model_name
                        break
                
                if working_model:
                    model = genai.GenerativeModel(working_model)
                    response = model.generate_content("Hello, test response")
                    google_status = f"✅ Connected - Model: {working_model}"
                else:
                    google_status = "❌ No Gemini models found"
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

Google AI:
{google_status}

Stability AI:
{stability_status}

**Recommendation:**
{'✅ Ready for video generation' if stability_key else '❌ Add STABILITY_API_KEY for video generation'}
            """
            await update.message.reply_text(test_results)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Test failed: {str(e)}")
    
    async def models_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List available Google AI models"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv('GOOGLE_AI_API_KEY'))
            
            models = genai.list_models()
            model_list = "🤖 **Available Google AI Models:**\n\n"
            
            for model in models:
                if 'gemini' in model.name.lower():
                    model_list += f"• {model.name}\n"
                    model_list += f"  Supported: {', '.join(method for method in model.supported_generation_methods)}\n\n"
            
            await update.message.reply_text(model_list)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting models: {str(e)}")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo upload"""
        await update.message.reply_text(
            "🖼️ **Photo received!**\n\n"
            "Now send me a prompt for the video.\n"
            "Example: 'slow motion' or 'cinematic movement'"
        )
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        text = update.message.text
        await update.message.reply_text(
            f"📝 **Prompt received:** {text}\n\n"
            "Currently setting up video generation...\n"
            "Use /test to check API status"
        )
    
    def run(self):
        print("🚀 Starting Working Video Bot...")
        self.application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    # Check environment
    required = ['TELEGRAM_TOKEN']
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing: {', '.join(missing)}")
        print("💡 Set in Railway environment variables")
        exit(1)
    
    print("✅ Environment check passed")
    bot = WorkingVideoBot()
    bot.run()