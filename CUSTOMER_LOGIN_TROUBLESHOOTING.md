# คู่มือแก้ไขปัญหาการล็อกอินของลูกค้า

## ปัญหาที่พบบ่อย

### 1. ลูกค้าไม่มีในระบบ
**อาการ:** ล็อกอินไม่ได้ แม้ใส่ username/password ถูกต้อง

**วิธีแก้ไข:**
1. เข้าไปใน Railway Console
2. รันคำสั่ง:
   ```bash
   python create_customer_railway.py
   ```
3. ทดสอบล็อกอินด้วย:
   - Username: `customer01`
   - Password: `123456`

### 2. ปัญหาการเชื่อมต่อฐานข้อมูล
**อาการ:** ข้อความ error เกี่ยวกับ database connection

**วิธีแก้ไข:**
1. ตรวจสอบ logs ใน Railway
2. รอให้ระบบ reconnect ฐานข้อมูล
3. ลองใหม่ใน 1-2 นาที

### 3. ปัญหา CSRF Token
**อาการ:** ข้อความ error เกี่ยวกับ CSRF

**วิธีแก้ไข:**
1. ล้าง cache ของ browser
2. รีเฟรชหน้าเว็บ
3. ลองล็อกอินใหม่

### 4. ปัญหา Session
**อาการ:** ล็อกอินได้แต่ไม่เก็บ session

**วิธีแก้ไข:**
1. ตรวจสอบว่า browser อนุญาต cookies
2. ลองใช้ browser อื่น
3. ล้าง cookies และลองใหม่

## การทดสอบ

### ทดสอบใน Production
1. เข้าไปใน Railway Console
2. รันคำสั่ง:
   ```bash
   python test_customer_login.py
   ```

### ทดสอบการล็อกอิน
1. ไปที่หน้าเว็บ
2. คลิก "เข้าสู่ระบบ"
3. ใส่ข้อมูล:
   - Username: `customer01`
   - Password: `123456`
4. คลิก "เข้าสู่ระบบ"

## การสร้างลูกค้าใหม่

### ผ่านหน้าเว็บ
1. ไปที่หน้าเว็บ
2. คลิก "ลงทะเบียน"
3. กรอกข้อมูลให้ครบถ้วน
4. คลิก "สมัครสมาชิก"

### ผ่านสคริปต์
1. เข้าไปใน Railway Console
2. รันคำสั่ง:
   ```bash
   python create_customer_railway.py
   ```

## การตรวจสอบ Logs

### ดู Logs ใน Railway
1. เข้าไปที่ Railway Dashboard
2. เลือก project
3. คลิก "Logs"
4. ดูข้อความ error

### Debug Messages
ระบบจะแสดง debug messages ใน logs:
- `Customer login attempt for username: [username]`
- `User found: [True/False]`
- `Login failed for username: [username]`

## การติดต่อ Support

หากยังแก้ไขไม่ได้:
1. เก็บ logs จาก Railway
2. บันทึกขั้นตอนที่ทำ
3. ส่งข้อมูลให้ทีมพัฒนา
