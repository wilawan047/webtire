import os
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

    # ✅ Upload folders → ต้องอยู่ใน static/uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    PROFILE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'profiles')
    TIRE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'tires')
    PROMOTION_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'promotions')
    SLIDER_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'sliders')
    LOGO_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'logos')

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
