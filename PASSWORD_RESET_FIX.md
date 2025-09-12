# 🔧 แก้ไขปัญหาการส่งลิงก์รีเซ็ตรหัสผ่าน

## ✅ ปัญหาที่แก้ไขแล้ว

1. **Hardcoded credentials** - เปลี่ยนให้ใช้ environment variables
2. **URL ใช้ localhost** - เปลี่ยนให้ใช้ APP_URL จาก config
3. **ไม่มีการตรวจสอบการตั้งค่า** - เพิ่มการตรวจสอบก่อนส่งอีเมล

## 🚀 วิธีการแก้ไข

### 1. ตั้งค่า Environment Variables

สร้างไฟล์ `.env` ในโฟลเดอร์หลัก:

```env
# Email Configuration (จำเป็นสำหรับการรีเซ็ตรหัสผ่าน)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_USE_TLS=true
MAIL_DEFAULT_SENDER=your-email@gmail.com

# App URL (จำเป็นสำหรับลิงก์รีเซ็ต)
APP_URL=http://localhost:5000

# Secret Key
SECRET_KEY=your-secret-key-here
```

### 2. การสร้าง Gmail App Password

1. **เปิด 2-Factor Authentication**:
   - ไปที่ [Google Account](https://myaccount.google.com/)
   - Security → 2-Step Verification
   - เปิดใช้งานถ้ายังไม่ได้เปิด

2. **สร้าง App Password**:
   - ไปที่ Security → 2-Step Verification → App passwords
   - เลือก "Mail" และอุปกรณ์
   - คัดลอก password ที่ได้ (16 ตัวอักษร)

3. **ใช้ App Password**:
   - ใส่ใน `MAIL_PASSWORD` environment variable
   - **ห้ามใช้รหัสผ่านปกติของ Gmail**

### 3. สำหรับ Railway Deployment

ใน Railway Dashboard → Variables tab เพิ่ม:

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_USE_TLS=true
APP_URL=https://your-railway-domain.railway.app
```

## 🧪 การทดสอบ

### 1. ทดสอบใน Local Development

1. ตั้งค่าไฟล์ `.env` ตามตัวอย่างข้างต้น
2. รันแอปพลิเคชัน
3. ไปที่หน้าเข้าสู่ระบบ
4. กด "ลืมรหัสผ่าน"
5. กรอกอีเมลที่ลงทะเบียนไว้
6. ตรวจสอบอีเมลที่ได้รับ

### 2. ทดสอบใน Railway

1. ตั้งค่า Environment Variables ใน Railway
2. Deploy โค้ดใหม่
3. ทดสอบการส่งอีเมลรีเซ็ตรหัสผ่าน
4. ตรวจสอบ logs ใน Railway dashboard

## 🔍 การ Debug

### ตรวจสอบ Logs

ใน Railway Dashboard → Deployments → View Logs:

```
✅ Reset email sent to user@example.com
```

หรือ

```
❌ Error sending reset email: [error details]
```

### ข้อความแสดงข้อผิดพลาด

- **"ระบบส่งอีเมลยังไม่ได้ตั้งค่า"**: ตรวจสอบ environment variables
- **"Email configuration missing"**: ตรวจสอบ MAIL_USERNAME และ MAIL_PASSWORD
- **"Authentication failed"**: ตรวจสอบ App Password
- **"Connection refused"**: ตรวจสอบ MAIL_SERVER และ MAIL_PORT

## 📝 หมายเหตุ

- App Password จะมีรูปแบบ: `abcd efgh ijkl mnop` (16 ตัวอักษร แบ่งเป็น 4 กลุ่ม)
- ห้ามใช้รหัสผ่านปกติของ Gmail ใน production
- ลิงก์รีเซ็ตจะหมดอายุใน 1 ชั่วโมง
- อีเมลจะส่งเป็น HTML format พร้อม styling
- ระบบจะตรวจสอบการตั้งค่าอีเมลก่อนส่งทุกครั้ง
