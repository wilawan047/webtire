# 🚀 Railway Deployment Guide

## การตั้งค่าระบบสำหรับการใช้งานออนไลน์

### 1. Environment Variables ที่ต้องตั้งค่าใน Railway

```bash
# Railway Environment
RAILWAY_ENVIRONMENT=true

# Security
SECRET_KEY=your-very-secure-secret-key-here

# Database (ใช้ค่าที่ Railway ให้มา)
DB_HOST=switchyard.proxy.rlwy.net
DB_PORT=21922
DB_USER=root
DB_PASSWORD=your-database-password
DB_NAME=railway

# App Configuration
APP_URL=https://your-app-name.up.railway.app
DEBUG=false

# Security Settings
SESSION_COOKIE_SECURE=true
CORS_ORIGINS=https://your-app-name.up.railway.app

# Logging
LOG_LEVEL=INFO
```

### 2. การตั้งค่าใน Railway Dashboard

1. **ไปที่ Railway Dashboard**
2. **เลือก Project ของคุณ**
3. **ไปที่ Variables tab**
4. **เพิ่ม Environment Variables ตามรายการด้านบน**

### 3. การ Deploy

```bash
# 1. Push โค้ดไปยัง GitHub
git add .
git commit -m "Configure for Railway production deployment"
git push origin main

# 2. Railway จะ deploy อัตโนมัติ
```

### 4. การตรวจสอบการทำงาน

1. **ตรวจสอบ Logs** ใน Railway Dashboard
2. **ทดสอบการเข้าถึง** ผ่าน URL ที่ Railway ให้มา
3. **ทดสอบการอัปโหลดไฟล์**
4. **ทดสอบการจองบริการ**

### 5. การปรับปรุงประสิทธิภาพ

- **Gunicorn Workers**: 3 workers (ปรับได้ตาม CPU)
- **Timeout**: 300 วินาที
- **Max Requests**: 1000 requests per worker
- **Keep-Alive**: 2 วินาที

### 6. การ Monitor

- **Railway Metrics**: ดูใน Dashboard
- **Application Logs**: ดูใน Logs tab
- **Database Performance**: ดูใน Database tab

### 7. การ Backup

- **Database**: Railway มี auto-backup
- **Files**: ใช้ external storage (AWS S3, Cloudinary)

### 8. การ Troubleshooting

**ปัญหาที่พบบ่อย:**

1. **Database Connection Error**
   - ตรวจสอบ Environment Variables
   - ตรวจสอบ Database Status

2. **File Upload Error**
   - ตรวจสอบ MAX_CONTENT_LENGTH
   - ตรวจสอบ Upload Folder Permissions

3. **Session Error**
   - ตรวจสอบ SECRET_KEY
   - ตรวจสอบ SESSION_COOKIE_SECURE

### 9. การอัปเดต

```bash
# 1. แก้ไขโค้ด
# 2. Commit และ Push
git add .
git commit -m "Update feature"
git push origin main

# 3. Railway จะ deploy อัตโนมัติ
```

### 10. การตั้งค่า Domain (Optional)

1. **ไปที่ Settings > Domains**
2. **เพิ่ม Custom Domain**
3. **ตั้งค่า DNS**
4. **อัปเดต CORS_ORIGINS**

---

## ✅ Checklist การ Deploy

- [ ] ตั้งค่า Environment Variables
- [ ] ตรวจสอบ Database Connection
- [ ] ทดสอบการอัปโหลดไฟล์
- [ ] ทดสอบการจองบริการ
- [ ] ตรวจสอบ Logs
- [ ] ทดสอบ Performance
- [ ] ตั้งค่า Monitoring
- [ ] Backup Strategy

---

**🎉 ระบบพร้อมใช้งานออนไลน์แล้ว!**
