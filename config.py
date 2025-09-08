import os
from datetime import timedelta

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or '4eceea41f6118226ad54747b6cbbfa54ae0be9a35f21369726beb4cb424844cf'
    
    # Database Configuration
    # NOTE: ใช้ port 3307 ห้ามแก้กลับเป็น 3306
 
    SECRET_KEY = os.environ.get('SECRET_KEY', 'defaultsecret')
    DB_HOST = os.environ.get('DB_HOST', 'switchyard.proxy.rlwy.net')
    DB_PORT = int(os.environ.get('DB_PORT', 21922))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'mxAiijYOvjVtdUrdtVCVyMygyvxOFOhO')
    DB_NAME = os.environ.get('DB_NAME', 'railway')

    # File Upload Configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    PROFILE_UPLOAD_FOLDER = os.environ.get('PROFILE_UPLOAD_FOLDER', 'uploads/profiles')
    TIRE_UPLOAD_FOLDER = os.environ.get('TIRE_UPLOAD_FOLDER', 'uploads/tires')
    PROMOTION_UPLOAD_FOLDER = os.environ.get('PROMOTION_UPLOAD_FOLDER', 'uploads/promotions')
    SLIDER_UPLOAD_FOLDER = os.environ.get('SLIDER_UPLOAD_FOLDER', 'uploads/sliders')
    LOGO_UPLOAD_FOLDER = os.environ.get('LOGO_UPLOAD_FOLDER', 'uploads/logos')
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Pagination
    DEFAULT_PER_PAGE = 10
    MAX_PER_PAGE = 100













