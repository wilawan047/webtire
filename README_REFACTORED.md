# TireWeb - โครงสร้างไฟล์ใหม่

## 📁 โครงสร้างไฟล์ปัจจุบัน

```
tireweb/
├── app.py                # ไฟล์หลักของแอปพลิเคชัน
├── config.py             # การตั้งค่าต่างๆ
├── database.py           # การจัดการฐานข้อมูล
├── utils.py              # ฟังก์ชันช่วยเหลือ
├── decorators.py         # Decorators สำหรับ authentication
├── requirements.txt      # Dependencies ของโปรเจค
├── tire_shop.sql         # ไฟล์ฐานข้อมูล SQL
├── routes/               # โฟลเดอร์สำหรับ routes
│   ├── __init__.py
│   ├── auth.py           # Routes การเข้าสู่ระบบ
│   ├── api.py            # API routes
│   ├── admin.py          # Admin routes
│   ├── staff.py          # Staff routes
│   ├── owner.py          # Owner routes
│   └── customer.py       # Customer routes
├── templates/            # HTML templates
│   ├── admin/            # Templates สำหรับ admin
│   ├── staff/            # Templates สำหรับ staff
│   ├── owner/            # Templates สำหรับ owner
│   ├── customer/         # Templates สำหรับ customer
│   └── layout.html       # Layout หลัก
├── static/               # ไฟล์ static
│   ├── js/               # JavaScript files
│   ├── data/             # ข้อมูล JSON
│   └── uploads/          # ไฟล์ที่อัปโหลด
├── fonts/                # ฟอนต์ภาษาไทย
└── README_REFACTORED.md  # ไฟล์นี้
```

## 🔧 ไฟล์หลักและหน้าที่

### 1. app.py (ไฟล์หลัก)
- **หน้าที่**: ไฟล์หลักของแอปพลิเคชัน Flask
- **ขนาด**: ~400 บรรทัด
- **ฟีเจอร์**:
  - Flask app configuration
  - Blueprint registration
  - Template filters (date_thai, comma, percent)
  - Main routes (customer, staff, owner)
  - CSRF protection

### 2. config.py
- **หน้าที่**: การตั้งค่าต่างๆ ของแอปพลิเคชัน
- **ขนาด**: ~50 บรรทัด
- **ฟีเจอร์**:
  - Flask app settings
  - Database configuration
  - File upload settings
  - Session configuration
  - Pagination settings

### 3. database.py
- **หน้าที่**: การจัดการฐานข้อมูล
- **ขนาด**: ~200 บรรทัด
- **ฟีเจอร์**:
  - Database connection pooling
  - UTF-8 encoding support
  - Functions: get_db(), get_cursor()
  - Customer-user synchronization
  - Connection management

### 4. utils.py
- **หน้าที่**: ฟังก์ชันช่วยเหลือต่างๆ
- **ขนาด**: ~120 บรรทัด
- **ฟีเจอร์**:
  - File validation (allowed_file)
  - Password verification
  - Data validation
  - Pagination และ sorting
  - URL safety check
  - Device type detection
  - Brand name conversion

### 5. decorators.py
- **หน้าที่**: Decorators สำหรับ authentication
- **ขนาด**: ~50 บรรทัด
- **ฟีเจอร์**:
  - @login_required - สำหรับ admin/staff/owner
- @customer_login_required - สำหรับลูกค้า
- @owner_login_required - สำหรับเจ้าของกิจการ

### 6. requirements.txt
- **หน้าที่**: รายการ dependencies ของโปรเจค
- **ขนาด**: 7 บรรทัด
- **แพ็คเกจหลัก**:
  - Flask==2.3.3
  - Flask-WTF==1.1.1
  - PyMySQL==1.1.0
  - reportlab==4.0.4

### 7. tire_shop.sql
- **หน้าที่**: ไฟล์ฐานข้อมูล SQL
- **ขนาด**: ~3,200 บรรทัด
- **ฟีเจอร์**:
  - Database schema
  - Sample data
  - Table structures

## 🛣️ Routes และหน้าที่

### 1. routes/auth.py (Authentication Routes)
- **หน้าที่**: จัดการการเข้าสู่ระบบและลงทะเบียน
- **ขนาด**: ~300 บรรทัด
- **Routes**:
  - `/login` - เข้าสู่ระบบผู้ดูแล
  - `/customer/login` - เข้าสู่ระบบลูกค้า
  - `/register` - ลงทะเบียน
  - `/logout` - ออกจากระบบ

### 2. routes/api.py (API Routes)
- **หน้าที่**: จัดการ API endpoints
- **ขนาด**: ~700 บรรทัด
- **Routes**:
  - `/api/tires` - API ยางรถ
  - `/api/customers/<id>` - API ข้อมูลลูกค้า
  - `/api/bookings` - API การจอง
  - `/api/promotions/active` - API โปรโมชั่น
  - `/api/staff` - API ข้อมูลพนักงาน

### 3. routes/admin.py (Admin Routes)
- **หน้าที่**: จัดการระบบสำหรับผู้ดูแลระบบ
- **ขนาด**: ~2,400 บรรทัด
- **Routes**:
  - `/admin/dashboard` - แดชบอร์ดแอดมิน
  - `/admin/tires` - จัดการยางรถ
  - `/admin/customers` - จัดการลูกค้า
  - `/admin/bookings` - จัดการการจอง
  - `/admin/users` - จัดการผู้ใช้
  - `/admin/promotions` - จัดการโปรโมชั่น
  - `/admin/home-slider` - จัดการสไลด์หน้าแรก
  - `/admin/profile` - โปรไฟล์แอดมิน

### 4. routes/staff.py (Staff Routes)
- **หน้าที่**: จัดการระบบสำหรับพนักงาน
- **ขนาด**: ~700 บรรทัด
- **Routes**:
  - `/staff/dashboard` - แดชบอร์ดพนักงาน
  - `/staff/bookings` - จัดการการจอง
  - `/staff/booking-history` - ประวัติการจอง
  - `/staff/profile` - โปรไฟล์พนักงาน

### 5. routes/owner.py (Owner Routes)
- **หน้าที่**: จัดการระบบสำหรับเจ้าของกิจการ
- **ขนาด**: ~750 บรรทัด
- **Routes**:
  - `/owner/dashboard` - แดชบอร์ดเจ้าของกิจการ
  - `/owner/bookings-report` - รายงานการจอง
  - `/owner/page-views-report` - รายงานการเข้าชม
  - `/owner/profile` - โปรไฟล์เจ้าของกิจการ

### 6. routes/customer.py (Customer Routes)
- **หน้าที่**: จัดการระบบสำหรับลูกค้า
- **ขนาด**: ~1,600 บรรทัด
- **Routes**:
  - `/` - หน้าแรกลูกค้า
  - `/tires` - หน้ายางรถ
  - `/booking` - หน้าจองบริการ
  - `/promotions` - หน้าโปรโมชั่น
  - `/profile` - โปรไฟล์ลูกค้า
  - `/edit-profile` - แก้ไขข้อมูลลูกค้า
  - `/change-password` - เปลี่ยนรหัสผ่าน
  - `/booking-history` - ประวัติการจอง

## 🎨 Templates และหน้าที่

### 1. templates/admin/ (Admin Templates)
- **ไฟล์หลัก**:
  - `dashboard.html` - แดชบอร์ดแอดมิน
  - `tire_list.html` - รายการยางรถ
  - `tire_form.html` - ฟอร์มยางรถ
  - `customer_list.html` - รายการลูกค้า
  - `customer_form.html` - ฟอร์มลูกค้า
  - `booking_list.html` - รายการการจอง
  - `user_list.html` - รายการผู้ใช้
  - `promotion_list.html` - รายการโปรโมชั่น

### 2. templates/staff/ (Staff Templates)
- **ไฟล์หลัก**:
  - `dashboard.html` - แดชบอร์ดพนักงาน
  - `bookings.html` - รายการการจอง
  - `view_booking.html` - ดูรายละเอียดการจอง
  - `edit_booking.html` - แก้ไขการจอง
  - `profile.html` - โปรไฟล์พนักงาน

### 3. templates/owner/ (Owner Templates)
- **ไฟล์หลัก**:
  - `dashboard.html` - แดชบอร์ดเจ้าของกิจการ
  - `bookings_report.html` - รายงานการจอง
  - `page_views_report.html` - รายงานการเข้าชม
  - `profile.html` - โปรไฟล์เจ้าของกิจการ

### 4. templates/customer/ (Customer Templates)
- **ไฟล์หลัก**:
  - `home.html` - หน้าแรกลูกค้า
  - `tires.html` - หน้ายางรถ
  - `booking.html` - หน้าจองบริการ
  - `promotions.html` - หน้าโปรโมชั่น
  - `profile.html` - โปรไฟล์ลูกค้า
  - `edit_profile.html` - แก้ไขข้อมูลลูกค้า
  - `booking_history.html` - ประวัติการจอง

## 🚀 วิธีใช้งาน

### 1. ติดตั้ง Dependencies
```bash
pip install -r requirements.txt
```

### 2. รันแอปพลิเคชัน
```bash
python app.py
```

### 3. เข้าถึงแอปพลิเคชัน
- **URL หลัก**: `http://localhost:5000`
- **Admin**: `http://localhost:5000/login`
- **Staff**: `http://localhost:5000/login`
- **Owner**: `http://localhost:5000/login`
- **Customer**: `http://localhost:5000`

## 🔐 ข้อมูลผู้ใช้สำหรับการทดสอบ

### 👨‍💼 ผู้ดูแลระบบ (Admin)
- **Username**: `admin01`
- **Password**: `123456`

### 👨‍💼 พนักงาน (Staff)
- **Username**: `staff01`
- **Password**: `123456`

### 👨‍💼 เจ้าของกิจการ (Owner)
- **Username**: `owner01`
- **Password**: `123456`

### 👤 ลูกค้า (Customer)
- **Username**: `somchai12`
- **Password**: `123456`

## 📊 สถิติไฟล์

| ไฟล์ | บรรทัด | หน้าที่ |
|------|--------|--------|
| app.py | ~400 | ไฟล์หลัก |
| config.py | ~50 | การตั้งค่า |
| database.py | ~200 | ฐานข้อมูล |
| utils.py | ~120 | ฟังก์ชันช่วยเหลือ |
| decorators.py | ~50 | Decorators |
| routes/auth.py | ~300 | Authentication |
| routes/api.py | ~700 | API routes |
| routes/admin.py | ~2,400 | Admin routes |
| routes/staff.py | ~700 | Staff routes |
| routes/owner.py | ~750 | Owner routes |
| routes/customer.py | ~1,600 | Customer routes |

## ✅ สถานะปัจจุบัน

### 🎉 สิ่งที่ทำเสร็จแล้ว:
1. **✅ ย้าย Admin Routes** → `routes/admin.py`
2. **✅ ย้าย Template Filters** → `app.py`
3. **✅ ย้าย Utility Functions** → `utils.py`
4. **✅ ทดสอบการทำงาน** → ผ่านทุกส่วน
5. **✅ ลบไฟล์ app.py เดิม** → เสร็จสิ้น
6. **✅ แก้ไขระบบล็อกอิน** → ทำงานได้ปกติ
7. **✅ สร้าง Blueprints ครบถ้วน** → admin, staff, owner, customer
8. **✅ แก้ไข Blueprint และ URL** → ครบถ้วน
9. **✅ ลบไฟล์ทดสอบ** → test_*.py, check_*.py, etc.
10. **✅ ลบโฟลเดอร์ __pycache__** → สะอาดแล้ว

### 🎯 ผลลัพธ์สุดท้าย:
- **โค้ดเป็นระเบียบ** และแยกส่วนชัดเจน
- **แอปพลิเคชันทำงานได้ปกติ** ทุกฟีเจอร์
- **ระบบล็อกอินทำงานได้** สำหรับทุก role
- **โครงสร้างไฟล์สะอาด** และดูแลรักษาง่าย
- **Blueprint ครบถ้วน** สำหรับทุก role
- **URL routing ถูกต้อง** ไม่มี 404 หรือ redirect ผิด
- **พร้อมสำหรับการพัฒนาต่อ** ในอนาคต

## 🔮 ขั้นตอนต่อไป (ถ้าต้องการ)

1. **เพิ่ม Unit Tests** - สร้างไฟล์ `tests/` สำหรับการทดสอบ
2. **แยก Models** - สร้างไฟล์ `models.py` สำหรับ database models
3. **แยก Services** - สร้างไฟล์ `services.py` สำหรับ business logic
4. **เพิ่ม Error Handling** - จัดการ error ให้ดีขึ้น
5. **เพิ่ม Logging** - เพิ่มระบบ logging
6. **เพิ่ม Documentation** - เพิ่มเอกสาร API
7. **เพิ่ม Security** - เพิ่มความปลอดภัย
8. **เพิ่ม Performance** - ปรับปรุงประสิทธิภาพ

## 📝 หมายเหตุ

- โปรเจคนี้ใช้ **Flask Blueprints** เพื่อจัดระเบียบ routes
- ใช้ **MySQL** เป็นฐานข้อมูล
- รองรับ **ภาษาไทย** ด้วย UTF-8 encoding
- มีระบบ **Authentication และ Authorization** ครบถ้วน
- รองรับ **File Upload** สำหรับรูปภาพ
- มีระบบ **PDF Generation** สำหรับรายงาน
- ใช้ **Tailwind CSS** สำหรับ styling

