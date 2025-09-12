import os
import re
import json
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse, urljoin
from flask import request, current_app

def allowed_file(filename):
    """ตรวจสอบนามสกุลไฟล์ที่อนุญาต"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def verify_password(password, hash_string):
    """ตรวจสอบรหัสผ่าน"""
    if not hash_string:
        return False
    
    # ใช้ werkzeug.security สำหรับการตรวจสอบรหัสผ่าน
    # รองรับ pbkdf2 hashes (scrypt hashes จะยังทำงานได้ผ่าน werkzeug)
    try:
        return check_password_hash(hash_string, password)
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def validate_booking_status(status):
    """ตรวจสอบสถานะการจอง"""
    valid_statuses = ['รอดำเนินการ', 'สำเร็จ', 'ยกเลิก']
    return status in valid_statuses

def validate_gender(gender):
    """ตรวจสอบเพศ"""
    valid_genders = ['ชาย', 'หญิง', 'ไม่ระบุ']
    return gender in valid_genders

def validate_tire_load_type(load_type):
    """ตรวจสอบประเภทโหลดยาง"""
    valid_types = ['Standard Load', 'Extra Load', 'Light Load']
    return load_type in valid_types

def validate_service_tire_position(position):
    """ตรวจสอบตำแหน่งยาง"""
    valid_positions = ['หน้า', 'หลัง', 'หน้าซ้าย', 'หน้าขวา', 'หลังซ้าย', 'หลังขวา']
    return position in valid_positions

def validate_pagination_params(page, per_page):
    """ตรวจสอบพารามิเตอร์ pagination"""
    try:
        page = int(page) if page else 1
        per_page = int(per_page) if per_page else current_app.config['DEFAULT_PER_PAGE']
        
        page = max(1, page)
        per_page = min(current_app.config['MAX_PER_PAGE'], max(1, per_page))
        
        return page, per_page
    except (ValueError, TypeError):
        return 1, current_app.config['DEFAULT_PER_PAGE']

def validate_sort_params(sort, direction, allowed_fields):
    """ตรวจสอบพารามิเตอร์ sorting"""
    if sort not in allowed_fields:
        sort = allowed_fields[0]
    
    direction = direction.upper() if direction else 'ASC'
    if direction not in ['ASC', 'DESC']:
        direction = 'ASC'
    
    return sort, direction

def is_safe_url(target):
    """ตรวจสอบ URL ว่าปลอดภัยหรือไม่"""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

def get_device_type(user_agent):
    """ตรวจสอบประเภทอุปกรณ์"""
    user_agent = user_agent.lower()
    
    if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
        return 'mobile'
    elif 'tablet' in user_agent or 'ipad' in user_agent:
        return 'tablet'
    else:
        return 'desktop'

def get_brand_name(brand_id):
    """ฟังก์ชันช่วยในการแปลง brand_id เป็น brand_name"""
    if not brand_id:
        return ''
    
    try:
        with open('static/data/vehicle_brands_models.json', encoding='utf-8') as f:
            brands_data = json.load(f)
        for brand in brands_data['brands']:
            if str(brand['brand_id']) == str(brand_id):
                return brand['brand_name']
    except Exception as e:
        print(f"Error getting brand name: {e}")
    
    return ''

def safe_file_save(file, upload_folder, filename):
    """บันทึกไฟล์อย่างปลอดภัยพร้อม error handling"""
    try:
        # สร้างโฟลเดอร์ถ้ายังไม่มี
        os.makedirs(upload_folder, exist_ok=True)
        
        # สร้าง path สำหรับไฟล์
        file_path = os.path.join(upload_folder, filename)
        
        # บันทึกไฟล์
        file.save(file_path)
        
        # ตรวจสอบว่าไฟล์ถูกบันทึกจริง
        if os.path.exists(file_path):
            print(f"✅ File saved successfully: {file_path}")
            return True, file_path
        else:
            print(f"❌ File not saved: {file_path}")
            return False, None
            
    except Exception as e:
        print(f"❌ Error saving file {filename}: {e}")
        return False, None

def get_upload_folder_path(upload_folder_name):
    """ดึง path ของ upload folder พร้อม fallback"""
    try:
        from flask import current_app
        folder_path = current_app.config.get(upload_folder_name)
        
        # ตรวจสอบว่าโฟลเดอร์มีอยู่จริงและสามารถเขียนได้
        if folder_path and os.path.exists(folder_path) and os.access(folder_path, os.W_OK):
            return folder_path
        
        # ถ้าเป็น Railway environment และโฟลเดอร์ไม่สามารถใช้งานได้
        if current_app.config.get('RAILWAY_ENVIRONMENT'):
            # ใช้ fallback directory
            fallback_dir = os.path.join(os.path.expanduser('~'), 'uploads', upload_folder_name.lower())
            os.makedirs(fallback_dir, exist_ok=True)
            print(f"⚠️ Using fallback directory: {fallback_dir}")
            return fallback_dir
            
        return folder_path
        
    except Exception as e:
        print(f"❌ Error getting upload folder: {e}")
        return None

def make_json_serializable(data):
    """แปลงข้อมูลให้เป็น JSON serializable"""
    if data is None:
        return None
    elif isinstance(data, (str, int, float, bool)):
        return data
    elif isinstance(data, (list, tuple)):
        return [make_json_serializable(item) for item in data]
    elif isinstance(data, dict):
        return {key: make_json_serializable(value) for key, value in data.items()}
    elif hasattr(data, '__dict__'):
        # สำหรับ object ที่มี attributes
        return str(data)
    else:
        # สำหรับ object อื่นๆ เช่น Decimal, datetime, etc.
        return str(data)

