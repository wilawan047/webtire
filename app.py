from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g
from flask_wtf.csrf import CSRFProtect
from config import Config
from database import get_db, close_db_connection, ensure_page_views_table
from utils import allowed_file, get_device_type
from decorators import login_required, customer_login_required, owner_login_required
from routes.auth import auth
from routes.api import api
from routes.admin import admin
from routes.staff import staff
from routes.owner import owner
from routes.customer import customer
import os
import time
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

# สร้าง Flask app
app = Flask(__name__)
app.config.from_object(Config)

# ตั้งค่าการเชื่อมต่อฐานข้อมูล
# NOTE: ใช้ port 3307 ห้ามแก้กลับเป็น 3306
import database
database.DB_CONFIG.update({
    'host': os.environ.get('DB_HOST', 'switchyard.proxy.rlwy.net'),
    'port': int(os.environ.get('DB_PORT', 21922)),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'mxAiijYOvjVtdUrdtVCVyMygyvxOFOhO'),
    'database': os.environ.get('DB_NAME', 'railway')
})

# ตั้งค่า CSRF protection
csrf = CSRFProtect(app)

# ตั้งค่า database teardown
app.teardown_request(close_db_connection)

# สร้างโฟลเดอร์สำหรับอัปโหลดไฟล์
upload_folders = [
    app.config['UPLOAD_FOLDER'],
    app.config['PROFILE_UPLOAD_FOLDER'],
    app.config['TIRE_UPLOAD_FOLDER'],
    app.config['PROMOTION_UPLOAD_FOLDER'],
    app.config['SLIDER_UPLOAD_FOLDER'],
    app.config['LOGO_UPLOAD_FOLDER']
]

# สร้างโฟลเดอร์พร้อม error handling
for folder in upload_folders:
    try:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ Created upload folder: {folder}")
    except Exception as e:
        print(f"❌ Error creating folder {folder}: {e}")
        # ถ้าเป็น Railway environment และไม่สามารถสร้างโฟลเดอร์ได้
        if app.config.get('RAILWAY_ENVIRONMENT'):
            print(f"⚠️ Railway environment detected - using fallback directory")
            # ใช้ fallback directory
            fallback_dir = os.path.join(os.path.expanduser('~'), 'uploads')
            os.makedirs(fallback_dir, exist_ok=True)

# ลงทะเบียน blueprints
app.register_blueprint(auth)
app.register_blueprint(api)
app.register_blueprint(admin)
app.register_blueprint(staff)
app.register_blueprint(owner)
app.register_blueprint(customer)

# สร้างตารางที่จำเป็น
with app.app_context():
    # ensure_roles_table() - ไม่จำเป็นแล้วเพราะใช้ role_name ในตาราง users แทน
    ensure_page_views_table()

# ===== CSRF EXEMPTIONS =====
# Exempt API routes from CSRF protection
try:
    csrf.exempt(api.view_functions['api_tires'])
    csrf.exempt(api.view_functions['api_customer_detail'])
    csrf.exempt(api.view_functions['api_bookings'])
    csrf.exempt(api.view_functions['api_booking_detail'])
    csrf.exempt(api.view_functions['api_page_views_summary'])
    csrf.exempt(api.view_functions['api_promotions_active'])
    csrf.exempt(api.view_functions['api_staff'])
    csrf.exempt(api.view_functions['api_tire_widths'])
    csrf.exempt(api.view_functions['api_tire_aspects'])
    csrf.exempt(api.view_functions['api_tire_rims'])
    csrf.exempt(api.view_functions['log_page_view'])
    csrf.exempt(api.view_functions['api_log_page_view'])
    csrf.exempt(api.view_functions['page_views_summary'])
    csrf.exempt(api.view_functions['get_tire_models'])
    csrf.exempt(api.view_functions['get_vehicle_models'])
    csrf.exempt(customer.view_functions['api_car_brands'])
    csrf.exempt(customer.view_functions['api_car_models'])
    csrf.exempt(customer.view_functions['api_car_years'])
    pass
except KeyError:
    pass

# Exempt logout routes from CSRF protection
try:
    csrf.exempt(app.view_functions['customer_logout'])
    csrf.exempt(app.view_functions['staff_logout'])
    csrf.exempt(app.view_functions['owner_logout'])
except KeyError:
    pass

# ฟังก์ชันสำหรับบันทึกการเข้าชมหน้าเว็บ
def log_page_view(page_id: str):
    """บันทึกการเข้าชมหน้าเว็บ"""
    try:
        # สร้างตาราง page_views ถ้ายังไม่มี
        ensure_page_views_table()
        
        cursor = get_db().cursor()
        
        # อัปเดตการเข้าชม
        cursor.execute("""
            INSERT INTO page_views (page_id, views)
            VALUES (%s, 1)
            ON DUPLICATE KEY UPDATE 
                views = views + 1,
                last_viewed_at = NOW()
        """, (page_id,))
        
        get_db().commit()
        
    except Exception as e:
        print(f"Error logging page view: {e}")

# ฟังก์ชันสำหรับ render template ลูกค้า
# ย้ายไปยัง routes/customer.py แล้ว

# ===== CUSTOMER ROUTES =====
# ย้ายไปยัง routes/customer.py แล้ว

# ===== STAFF ROUTES =====
# ย้ายไปยัง routes/staff.py แล้ว
# app.py
from flask import redirect, url_for

@app.route("/")
def index():
    return redirect(url_for('customer.home'))



@app.route('/staff/profile', methods=['GET', 'POST'])
@login_required
def staff_profile():
    """หน้าแก้ไขโปรไฟล์พนักงาน"""
    if not session.get('staff_user_id') or session.get('role') != 'staff':
        return redirect(url_for('auth.login'))

    user_id = session.get('staff_user_id')

    if request.method == 'POST':
        try:
            # ดึงข้อมูลจากฟอร์ม
            name = request.form.get('name', '').strip()
            
            # จัดการไฟล์รูปภาพ
            avatar_filename = None
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and file.filename != '':
                    # ตรวจสอบนามสกุลไฟล์
                    if file and allowed_file(file.filename):
                        # สร้างชื่อไฟล์ใหม่
                        timestamp = int(time.time() * 1000)
                        filename = f"{user_id}_{timestamp}_{secure_filename(file.filename)}"
                        
                        # บันทึกไฟล์
                        file_path = os.path.join(app.config['PROFILE_UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        avatar_filename = filename
                        
                        # ลบไฟล์เก่าถ้ามี
                        cursor = get_db().cursor()
                        cursor.execute('SELECT avatar_filename FROM users WHERE user_id = %s', (user_id,))
                        user_data = cursor.fetchone()
                        if user_data and user_data.get('avatar_filename'):
                            old_file_path = os.path.join(app.config['PROFILE_UPLOAD_FOLDER'], user_data['avatar_filename'])
                            if os.path.exists(old_file_path):
                                os.remove(old_file_path)
                    else:
                        flash('นามสกุลไฟล์ไม่ถูกต้อง กรุณาใช้ไฟล์ JPG, PNG เท่านั้น', 'error')
                        return redirect(url_for('staff_profile'))
            
            # อัปเดตข้อมูลในฐานข้อมูล
            cursor = get_db().cursor()
            if avatar_filename:
                cursor.execute('''
                    UPDATE users 
                    SET name = %s, avatar_filename = %s 
                    WHERE user_id = %s
                ''', (name, avatar_filename, user_id))
            else:
                cursor.execute('''
                    UPDATE users 
                    SET name = %s 
                    WHERE user_id = %s
                ''', (name, user_id))
            get_db().commit()        
            # อัปเดต session
            session['name'] = name
            if avatar_filename:
                session['avatar'] = avatar_filename
            
            flash('อัปเดตข้อมูลเรียบร้อยแล้ว', 'success')
            return redirect(url_for('staff_profile'))
            
        except Exception as e:
            print(f"Error updating staff profile: {e}")
            flash('เกิดข้อผิดพลาดในการอัปเดตข้อมูล', 'error')
            return redirect(url_for('staff_profile'))

    # GET request - แสดงฟอร์ม
    try:
        cursor = get_db().cursor()
        cursor.execute('''
            SELECT u.user_id, u.username, u.name, u.avatar_filename, u.created_at
            FROM users u
            WHERE u.user_id = %s
        ''', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash('ไม่พบข้อมูลผู้ใช้', 'error')
            return redirect(url_for('staff_dashboard'))
        
        return render_template('staff/profile.html', user=user)
        
    except Exception as e:
        print(f"Error loading staff profile: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดข้อมูล', 'error')
        return redirect(url_for('staff_dashboard'))

@app.route('/staff/logout', methods=['POST', 'GET'])
@login_required
def staff_logout():
    """ออกจากระบบพนักงาน"""
    session.clear()
    session.permanent = False
    flash('ออกจากระบบพนักงานเรียบร้อย', 'success')
    return redirect(url_for('auth.login'))

# ===== OWNER ROUTES =====
# ย้ายไปยัง routes/owner.py แล้ว

# ===== TEMPLATE FILTERS =====
@app.template_filter('date_thai')
def date_thai(value):
    """แปลงวันที่เป็นภาษาไทย"""
    if not value:
        return ''
    
    thai_months = [
        'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน',
        'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'
    ]
    
    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%d')
    
    return f"{value.day} {thai_months[value.month - 1]} {value.year + 543}"

@app.template_filter('comma')
def comma_format(value):
    """เพิ่ม comma ในตัวเลข"""
    if value is None:
        return '0'
    return f"{value:,}"

@app.template_filter('percent')
def percent_format(value):
    """แปลงเป็นเปอร์เซ็นต์"""
    if value is None:
        return '0%'
    return f"{value:.1f}%"

if __name__ == "__main__":
   app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

