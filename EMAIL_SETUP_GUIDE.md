# 📧 คู่มือการตั้งค่าอีเมลสำหรับฟีเจอร์ลืมรหัสผ่าน

## 🔧 การแก้ไขปัญหา

### ปัญหาที่พบ
- อีเมลไม่ส่งเมื่อกดลืมรหัสผ่าน
- Hardcoded credentials ในโค้ด
- URL ในลิงก์รีเซ็ตใช้ localhost

### การแก้ไข
1. ✅ เพิ่ม environment variables สำหรับการตั้งค่าอีเมล
2. ✅ แก้ไข URL ในลิงก์รีเซ็ตให้ใช้ Railway domain
3. ✅ เพิ่มการตรวจสอบการตั้งค่าอีเมล

## 🚀 การตั้งค่าใน Railway

### 1. Environment Variables ที่ต้องเพิ่ม

ใน Railway Dashboard → Variables tab เพิ่ม:

```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_USE_TLS=true
APP_URL=https://your-railway-domain.railway.app
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

### 3. ตัวอย่างการตั้งค่า

```bash
# Railway Environment Variables
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=tireweb@gmail.com
MAIL_PASSWORD=abcd efgh ijkl mnop  # App Password
MAIL_USE_TLS=true
APP_URL=https://tireweb-production.railway.app
```

## 🧪 การทดสอบ

### 1. ทดสอบใน Local Development

สร้างไฟล์ `.env`:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_USE_TLS=true
APP_URL=http://localhost:5000
```

### 2. ทดสอบใน Railway

1. ตั้งค่า Environment Variables
2. Deploy โค้ดใหม่
3. ลองกดลืมรหัสผ่าน
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

### ปัญหาที่พบบ่อย

1. **"Email configuration missing"**:
   - ตรวจสอบว่าได้ตั้งค่า environment variables แล้ว

2. **"Authentication failed"**:
   - ตรวจสอบว่าใช้ App Password ไม่ใช่รหัสผ่านปกติ
   - ตรวจสอบว่าเปิด 2FA แล้ว

3. **"Connection refused"**:
   - ตรวจสอบ MAIL_SERVER และ MAIL_PORT

## 📝 หมายเหตุ

- App Password จะมีรูปแบบ: `abcd efgh ijkl mnop` (16 ตัวอักษร แบ่งเป็น 4 กลุ่ม)
- ห้ามใช้รหัสผ่านปกติของ Gmail ใน production
- ลิงก์รีเซ็ตจะหมดอายุใน 1 ชั่วโมง
- อีเมลจะส่งเป็น HTML format พร้อม styling
