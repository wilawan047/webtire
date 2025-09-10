import os
import tempfile
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'defaultsecret'

    # Database (ไม่แตะ)
    DB_HOST = os.environ.get('DB_HOST', 'switchyard.proxy.rlwy.net')
    DB_PORT = int(os.environ.get('DB_PORT', 21922))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'mxAiijYOvjVtdUrdtVCVyMygyvxOFOhO')
    DB_NAME = os.environ.get('DB_NAME', 'railway')

    # ✅ Upload folders → ใช้ temp directory สำหรับ Railway deployment
    # ใน Railway ใช้ temporary directory เพื่อหลีกเลี่ยงปัญหา ephemeral filesystem
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        # Railway deployment - ใช้ temp directory
        TEMP_DIR = tempfile.gettempdir()
        UPLOAD_FOLDER = os.path.join(TEMP_DIR, 'tireweb_uploads')
        PROFILE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'profiles')
        TIRE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'tires')
        PROMOTION_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'promotions')
        SLIDER_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'sliders')
        LOGO_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'logos')
    else:
        # Local development - ใช้ static/uploads
        UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
        PROFILE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'profiles')
        TIRE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'tires')
        PROMOTION_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'promotions')
        SLIDER_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'sliders')
        LOGO_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'logos')

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    
    # Railway specific settings
    RAILWAY_ENVIRONMENT = os.environ.get('RAILWAY_ENVIRONMENT', False)
    
    # Email settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME', ''))
    
    # Email provider over HTTPS (Resend)
    RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
    
    # Alternative: SendGrid
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
    
    # Gmail API (preferred for Gmail users)
    GMAIL_API_KEY = os.environ.get('GMAIL_API_KEY', '')
    
    # App URL for reset links
    APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')
