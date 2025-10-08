import os
from PIL import Image
import logging

class VideoProcessor:
    @staticmethod
    def validate_image(file_path: str) -> bool:
        """Validate image file"""
        try:
            with Image.open(file_path) as img:
                img.verify()
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:  # 10MB
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Image validation error: {e}")
            return False
    
    @staticmethod
    def optimize_image(image_path: str, max_size: tuple = (1024, 1024)) -> str:
        """Optimize image for video generation"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save optimized version
                optimized_path = image_path.replace('.jpg', '_optimized.jpg')
                img.save(optimized_path, 'JPEG', quality=85)
                
                return optimized_path
                
        except Exception as e:
            logging.error(f"Image optimization error: {e}")
            return image_path  # Return original if optimization fails
    
    @staticmethod
    def cleanup_files(*file_paths):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logging.error(f"Cleanup error for {file_path}: {e}")