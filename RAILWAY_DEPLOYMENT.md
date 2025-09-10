# Railway Deployment Guide

## 🚀 การแก้ไขปัญหาการอัปโหลดไฟล์ใน Railway

### ปัญหาที่พบ
- การอัปโหลดรูปโปรไฟล์ไม่ทำงานใน Railway deployment
- ไฟล์ที่อัปโหลดหายไปเมื่อ container restart
- ขาด error handling ที่เหมาะสม
- scrypt package ไม่สามารถ build ได้ใน Railway environment

### การแก้ไข

#### 1. ตั้งค่า Upload Folder สำหรับ Railway
```python
# config.py
if os.environ.get('RAILWAY_ENVIRONMENT'):
    # Railway deployment - ใช้ temp directory
    TEMP_DIR = tempfile.gettempdir()
    UPLOAD_FOLDER = os.path.join(TEMP_DIR, 'tireweb_uploads')
    PROFILE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'profiles')
    # ... โฟลเดอร์อื่นๆ
```

#### 2. เพิ่ม Error Handling และ Logging
```python
# utils.py
def safe_file_save(file, upload_folder, filename):
    """บันทึกไฟล์อย่างปลอดภัยพร้อม error handling"""
    try:
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        if os.path.exists(file_path):
            print(f"✅ File saved successfully: {file_path}")
            return True, file_path
        else:
            print(f"❌ File not saved: {file_path}")
            return False, None
    except Exception as e:
        print(f"❌ Error saving file {filename}: {e}")
        return False, None
```

#### 3. Fallback Mechanism
```python
def get_upload_folder_path(upload_folder_name):
    """ดึง path ของ upload folder พร้อม fallback"""
    folder_path = current_app.config.get(upload_folder_name)
    
    if folder_path and os.path.exists(folder_path) and os.access(folder_path, os.W_OK):
        return folder_path
    
    # ถ้าเป็น Railway environment และโฟลเดอร์ไม่สามารถใช้งานได้
    if current_app.config.get('RAILWAY_ENVIRONMENT'):
        fallback_dir = os.path.join(os.path.expanduser('~'), 'uploads', upload_folder_name.lower())
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir
```

#### 4. แก้ไขปัญหา scrypt Build Error
```python
# ลบ scrypt ออกจาก requirements.txt
# เปลี่ยนจาก:
# scrypt==0.8.20

# อัปเดตการสร้าง password hash
# เปลี่ยนจาก:
password_hash = generate_password_hash(password, method='scrypt')
# เป็น:
password_hash = generate_password_hash(password, method='pbkdf2:sha256')
```

#### 5. แก้ไขปัญหา Static File Serving
```python
# เพิ่ม route สำหรับแสดงรูปภาพจาก temp directory
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """แสดงรูปภาพจาก upload folder"""
    # หาไฟล์ในโฟลเดอร์ต่างๆ และส่งไฟล์กลับ

# เพิ่ม template filter สำหรับสร้าง URL
@app.template_filter('avatar_url')
def avatar_url(filename):
    """สร้าง URL สำหรับรูปโปรไฟล์"""
    if app.config.get('RAILWAY_ENVIRONMENT'):
        return url_for('uploaded_file', filename=filename)
    else:
        return url_for('static', filename='uploads/profiles/' + filename)
```

```html
<!-- อัปเดต template ให้ใช้ filter ใหม่ -->
<img src="{{ user.avatar_filename | avatar_url }}?v={{ range(1, 10000) | random }}"
     alt="Profile Avatar"
     class="w-32 h-32 rounded-full object-cover border-4 border-green-200 shadow-lg">
```

### Environment Variables ที่ต้องตั้งค่าใน Railway

1. **RAILWAY_ENVIRONMENT=true** - เพื่อให้แอปรู้ว่าใช้งานใน Railway
2. **SECRET_KEY** - Flask secret key
3. **Database variables** - ตามที่ Railway ให้มา

### การ Deploy

1. **อัปโหลดโค้ดไปยัง Railway**
2. **ตั้งค่า Environment Variables**
3. **เชื่อมต่อ Database**
4. **Deploy**

### ข้อจำกัดของ Railway

- **Ephemeral Filesystem**: ไฟล์ที่อัปโหลดจะหายไปเมื่อ container restart
- **Temporary Solution**: ใช้ temp directory สำหรับการอัปโหลดไฟล์
- **Production Recommendation**: ควรใช้ external storage เช่น AWS S3, Google Cloud Storage

### การทดสอบ

1. ลองอัปโหลดรูปโปรไฟล์
2. ตรวจสอบ logs ใน Railway dashboard
3. ตรวจสอบว่าไฟล์ถูกบันทึกใน temp directory

### หมายเหตุ

การแก้ไขนี้เป็น temporary solution สำหรับ Railway deployment 
สำหรับ production จริง ควรพิจารณาใช้ external file storage service
