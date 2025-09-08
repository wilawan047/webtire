from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, current_app, jsonify
from database import get_cursor, get_db
from utils import allowed_file
from decorators import login_required, staff_required
import os
import json
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import time

staff = Blueprint('staff', __name__, url_prefix='/staff')

@staff.route('/dashboard')
@staff_required
def dashboard():
    """หน้าแดชบอร์ดหลักของพนักงาน"""
    try:
        cursor = get_cursor()
        
        # สถิติสรุป
        cursor.execute('SELECT COUNT(*) as total FROM bookings')
        total_bookings = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as pending FROM bookings WHERE status = "รอดำเนินการ"')
        pending_bookings = cursor.fetchone()['pending']
        
        cursor.execute('SELECT COUNT(*) as completed FROM bookings WHERE status = "สำเร็จ"')
        completed_bookings = cursor.fetchone()['completed']
        
        cursor.execute('SELECT COUNT(*) as today FROM bookings WHERE DATE(booking_date) = CURDATE()')
        today_bookings = cursor.fetchone()['today']
        
        # การจองล่าสุด
        cursor.execute('''
            SELECT b.booking_id, b.booking_date, b.status,
                   CONCAT(c.first_name, ' ', c.last_name) as customer_name,
                   c.phone,
                   CONCAT(v.brand_name, ' ', v.model_name) as vehicle_info,
                   v.license_plate
            FROM bookings b
            JOIN customers c ON b.customer_id = c.customer_id
            JOIN vehicles v ON b.vehicle_id = v.vehicle_id
            ORDER BY b.booking_date DESC
            LIMIT 10
        ''')
        recent_bookings = cursor.fetchall()
        
        return render_template('staff/dashboard.html', 
                             total_bookings=total_bookings,
                             pending_bookings=pending_bookings,
                             completed_bookings=completed_bookings,
                             today_bookings=today_bookings,
                             recent_bookings=recent_bookings)
    except Exception as e:
        print(f"Error in staff_dashboard: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดข้อมูล', 'error')
        return redirect(url_for('auth.login'))

@staff.route('/bookings/add', methods=['GET', 'POST'])
@staff_required
def add_booking():
    """หน้าเพิ่มการจองสำหรับพนักงาน"""
    cursor = get_cursor()
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        vehicle_id = request.form['vehicle_id']
        booking_date = request.form['booking_date']
        status = request.form['status']
        cursor.execute('''INSERT INTO bookings (customer_id, vehicle_id, booking_date, status) VALUES (%s, %s, %s, %s)''',
            (customer_id, vehicle_id, booking_date, status))
        booking_id = cursor.lastrowid
        # เพิ่ม booking_items และ booking_item_options
        service_ids = request.form.getlist('service_id')
        for sid in service_ids:
            cursor.execute('''INSERT INTO booking_items (booking_id, service_id) VALUES (%s, %s)''', (booking_id, sid))
            item_id = cursor.lastrowid
            option_field = f'service_option_{sid}'
            option_ids = request.form.getlist(option_field)
            for option_id in option_ids:
                cursor.execute('''INSERT INTO booking_item_options (item_id, option_id) VALUES (%s, %s)''', (item_id, option_id))
        # --- เพิ่มการบันทึกข้อมูลยางลง service_tires ---
        tire_front_size = request.form.get('tire_front_size', '').strip()
        tire_front_brand_id = request.form.get('tire_front_brand_id', '').strip()
        tire_front_model_id = request.form.get('tire_front_model_id', '').strip()
        tire_rear_size = request.form.get('tire_rear_size', '').strip()
        tire_rear_brand_id = request.form.get('tire_rear_brand_id', '').strip()
        tire_rear_model_id = request.form.get('tire_rear_model_id', '').strip()
        tire_front_left = request.form.get('dot_front_left', '').strip()
        tire_front_right = request.form.get('dot_front_right', '').strip()
        tire_rear_left = request.form.get('dot_rear_left', '').strip()
        tire_rear_right = request.form.get('dot_rear_right', '').strip()
        
        # ดึงข้อมูลยี่ห้อและรุ่นยางจาก ID
        front_brand_name = ''
        front_model_name = ''
        rear_brand_name = ''
        rear_model_name = ''
        
        if tire_front_brand_id:
            cursor.execute('SELECT brand_name FROM brands WHERE brand_id = %s', (tire_front_brand_id,))
            brand_result = cursor.fetchone()
            if brand_result:
                front_brand_name = brand_result['brand_name']
        
        if tire_front_model_id:
            cursor.execute('SELECT model_name FROM tire_models WHERE model_id = %s', (tire_front_model_id,))
            model_result = cursor.fetchone()
            if model_result:
                front_model_name = model_result['model_name']
        
        if tire_rear_brand_id:
            cursor.execute('SELECT brand_name FROM brands WHERE brand_id = %s', (tire_rear_brand_id,))
            brand_result = cursor.fetchone()
            if brand_result:
                rear_brand_name = brand_result['brand_name']
        
        if tire_rear_model_id:
            cursor.execute('SELECT model_name FROM tire_models WHERE model_id = %s', (tire_rear_model_id,))
            model_result = cursor.fetchone()
            if model_result:
                rear_model_name = model_result['model_name']
        
        # บันทึกข้อมูลยาง 4 แถว (front_left, front_right, rear_left, rear_right) ลงในตาราง service_tires
        # Front Left
        cursor.execute('''
            INSERT INTO service_tires (booking_id, position, brand, model, size, dot) 
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (booking_id, 'front_left', front_brand_name, front_model_name, tire_front_size, tire_front_left))
        
        # Front Right
        cursor.execute('''
            INSERT INTO service_tires (booking_id, position, brand, model, size, dot) 
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (booking_id, 'front_right', front_brand_name, front_model_name, tire_front_size, tire_front_right))
        
        # Rear Left
        cursor.execute('''
            INSERT INTO service_tires (booking_id, position, brand, model, size, dot) 
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (booking_id, 'rear_left', rear_brand_name, rear_model_name, tire_rear_size, tire_rear_left))
        
        # Rear Right
        cursor.execute('''
            INSERT INTO service_tires (booking_id, position, brand, model, size, dot) 
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (booking_id, 'rear_right', rear_brand_name, rear_model_name, tire_rear_size, tire_rear_right))
        
        get_db().commit()
        flash('เพิ่มการจองสำเร็จ')
        return redirect(url_for('staff.bookings'))
    
    # GET request - แสดงฟอร์ม
    cursor.execute('SELECT * FROM customers ORDER BY first_name, last_name')
    customers = cursor.fetchall()
    
    cursor.execute('SELECT * FROM vehicles ORDER BY license_plate')
    vehicles = cursor.fetchall()
    
    cursor.execute('SELECT * FROM services ORDER BY service_name')
    services = cursor.fetchall()
    
    # ดึง options สำหรับแต่ละ service
    for service in services:
        cursor.execute('SELECT * FROM service_options WHERE service_id = %s ORDER BY option_name', (service['service_id'],))
        service['options'] = cursor.fetchall()
    
    # จัดกลุ่มบริการ
    service_groups = {}
    for service in services:
        category = service.get('category', 'บริการทั่วไป')
        if category not in service_groups:
            service_groups[category] = []
        service_groups[category].append(service)
    
    # ดึงข้อมูลยางและยี่ห้อ
    cursor.execute('SELECT * FROM brands ORDER BY brand_name')
    brands = cursor.fetchall()
    
    cursor.execute('SELECT * FROM tire_models ORDER BY model_name')
    tire_models = cursor.fetchall()
    
    # ดึงข้อมูลยี่ห้อรถ
    cursor.execute('SELECT * FROM car_brands ORDER BY car_brand_name')
    vehicle_brands = cursor.fetchall()
    
    # ดึงรายการจังหวัด
    provinces = ['กรุงเทพมหานคร', 'กระบี่', 'กาญจนบุรี', 'กาฬสินธุ์', 'กำแพงเพชร', 'ขอนแก่น', 'จันทบุรี', 'ฉะเชิงเทรา', 'ชลบุรี', 'ชัยนาท', 'ชัยภูมิ', 'ชุมพร', 'เชียงราย', 'เชียงใหม่', 'ตรัง', 'ตราด', 'ตาก', 'นครนายก', 'นครปฐม', 'นครพนม', 'นครราชสีมา', 'นครศรีธรรมราช', 'นครสวรรค์', 'นนทบุรี', 'นราธิวาส', 'น่าน', 'บึงกาฬ', 'บุรีรัมย์', 'ปทุมธานี', 'ประจวบคีรีขันธ์', 'ปราจีนบุรี', 'ปัตตานี', 'พระนครศรีอยุธยา', 'พังงา', 'พัทลุง', 'พิจิตร', 'พิษณุโลก', 'เพชรบุรี', 'เพชรบูรณ์', 'แพร่', 'พะเยา', 'ภูเก็ต', 'มหาสารคาม', 'มุกดาหาร', 'แม่ฮ่องสอน', 'ยะลา', 'ยโสธร', 'ร้อยเอ็ด', 'ระนอง', 'ระยอง', 'ราชบุรี', 'ลพบุรี', 'ลำปาง', 'ลำพูน', 'เลย', 'ศรีสะเกษ', 'สกลนคร', 'สงขลา', 'สตูล', 'สมุทรปราการ', 'สมุทรสงคราม', 'สมุทรสาคร', 'สระแก้ว', 'สระบุรี', 'สิงห์บุรี', 'สุโขทัย', 'สุพรรณบุรี', 'สุราษฎร์ธานี', 'สุรินทร์', 'หนองคาย', 'หนองบัวลำภู', 'อ่างทอง', 'อุดรธานี', 'อุทัยธานี', 'อุตรดิตถ์', 'อุบลราชธานี', 'อำนาจเจริญ']
    
    return render_template('staff/booking_form.html', 
                         booking=None,
                         customers=customers,
                         vehicles=vehicles,
                         services=services,
                         service_groups=service_groups,
                         brands=brands,
                         tire_models=tire_models,
                         vehicle_brands=vehicle_brands,
                         provinces=provinces)

@staff.route('/bookings')
@staff_required
def bookings():
    """หน้าแสดงการจองปัจจุบัน"""
    try:
        cursor = get_cursor()
        
        # รับพารามิเตอร์
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '').strip()
        
        # สร้าง query สำหรับการจองปัจจุบัน - แสดงการจองทั้งหมด
        query = '''SELECT b.booking_id, b.booking_date, b.status, c.first_name, c.last_name, v.license_plate, v.license_province
                   FROM bookings b
                   JOIN customers c ON b.customer_id = c.customer_id
                   JOIN vehicles v ON b.vehicle_id = v.vehicle_id'''
        page_title = "ข้อมูลการจอง"
        
        params = []
        where_conditions = []
        
        if search:
            where_conditions.append('(c.first_name LIKE %s OR c.last_name LIKE %s OR v.license_plate LIKE %s)')
            like = f"%{search}%"
            params.extend([like, like, like])
        
        if status_filter:
            where_conditions.append('b.status = %s')
            params.append(status_filter)
        
        if where_conditions:
            query += ' WHERE ' + ' AND '.join(where_conditions)
        
        query += ' ORDER BY b.booking_date DESC'
        
        # ดึงข้อมูลการจอง
        cursor.execute(query, params)
        bookings = cursor.fetchall()
        
        # ดึงข้อมูลบริการสำหรับแต่ละการจอง
        for booking in bookings:
            cursor.execute('''
                SELECT bi.item_id, bi.service_id, bi.quantity, 
                       s.service_name, s.category,
                       GROUP_CONCAT(so.option_name SEPARATOR ', ') as options
                FROM booking_items bi
                JOIN services s ON bi.service_id = s.service_id
                LEFT JOIN booking_item_options bio ON bi.item_id = bio.item_id
                LEFT JOIN service_options so ON bio.option_id = so.option_id
                WHERE bi.booking_id = %s
                GROUP BY bi.item_id, bi.service_id, bi.quantity, s.service_name, s.category
            ''', (booking['booking_id'],))
            booking['services'] = cursor.fetchall()
            
            # สร้าง service_options สำหรับ dropdown
            booking['service_options'] = {}
            for service in booking['services']:
                service_name = service['service_name']
                if service_name not in booking['service_options']:
                    booking['service_options'][service_name] = []
                booking['service_options'][service_name].append(service)
        
        # สถานะสำหรับ filter
        statuses = ['รอดำเนินการ', 'สำเร็จ', 'ยกเลิก']
        
        return render_template('staff/bookings.html',
                             bookings=bookings,
                             statuses=statuses,
                             page_title=page_title,
                             show_history=False,
                             search=search,
                             status_filter=status_filter)
        
    except Exception as e:
        print(f"Error in bookings: {e}")
        import traceback
        traceback.print_exc()
        flash(f'เกิดข้อผิดพลาดในการโหลดข้อมูล: {str(e)}', 'error')
        return redirect(url_for('staff.dashboard'))

@staff.route('/bookings/history')
@staff_required
def booking_history():
    """หน้าแสดงประวัติการจอง"""
    try:
        cursor = get_cursor()
        
        # รับพารามิเตอร์
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        
        # สร้าง query สำหรับประวัติการจอง - แสดงการจองทั้งหมด
        query = '''SELECT b.booking_id, b.booking_date, b.status, c.first_name, c.last_name, v.license_plate, v.license_province
                   FROM bookings b
                   JOIN customers c ON b.customer_id = c.customer_id
                   JOIN vehicles v ON b.vehicle_id = v.vehicle_id'''
        page_title = "ประวัติการจอง"
        
        params = []
        where_conditions = []
        
        if search:
            where_conditions.append('(c.first_name LIKE %s OR c.last_name LIKE %s OR v.license_plate LIKE %s)')
            like = f"%{search}%"
            params.extend([like, like, like])
        
        if status_filter:
            where_conditions.append('b.status = %s')
            params.append(status_filter)
        
        if start_date:
            where_conditions.append('DATE(b.booking_date) >= %s')
            params.append(start_date)
        
        if end_date:
            where_conditions.append('DATE(b.booking_date) <= %s')
            params.append(end_date)
        
        if where_conditions:
            query += ' WHERE ' + ' AND '.join(where_conditions)
        
        query += ' ORDER BY b.booking_date DESC'
        
        # ดึงข้อมูลการจอง
        cursor.execute(query, params)
        bookings = cursor.fetchall()
        
        # ดึงข้อมูลบริการสำหรับแต่ละการจอง
        for booking in bookings:
            cursor.execute('''
                SELECT bi.item_id, bi.service_id, bi.quantity, 
                       s.service_name, s.category,
                       GROUP_CONCAT(so.option_name SEPARATOR ', ') as options
                FROM booking_items bi
                JOIN services s ON bi.service_id = s.service_id
                LEFT JOIN booking_item_options bio ON bi.item_id = bio.item_id
                LEFT JOIN service_options so ON bio.option_id = so.option_id
                WHERE bi.booking_id = %s
                GROUP BY bi.item_id, bi.service_id, bi.quantity, s.service_name, s.category
            ''', (booking['booking_id'],))
            booking['services'] = cursor.fetchall()
            
            # สร้าง service_options สำหรับ dropdown
            booking['service_options'] = {}
            for service in booking['services']:
                service_name = service['service_name']
                if service_name not in booking['service_options']:
                    booking['service_options'][service_name] = []
                booking['service_options'][service_name].append(service)
        
        # สถานะสำหรับ filter
        statuses = ['รอดำเนินการ', 'สำเร็จ', 'ยกเลิก']
        
        return render_template('staff/booking_history.html',
                             bookings=bookings,
                             statuses=statuses,
                             page_title=page_title,
                             show_history=True,
                             search=search,
                             status_filter=status_filter,
                             start_date=start_date,
                             end_date=end_date)
        
    except Exception as e:
        print(f"Error in booking_history: {e}")
        import traceback
        traceback.print_exc()
        flash(f'เกิดข้อผิดพลาดในการโหลดข้อมูล: {str(e)}', 'error')
        return redirect(url_for('staff.dashboard'))

@staff.route('/profile', methods=['GET', 'POST'])
@staff_required
def profile():
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
                        file_path = os.path.join(current_app.config['PROFILE_UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        avatar_filename = filename
                        
                        # ลบไฟล์เก่าถ้ามี
                        cursor = get_cursor()
                        cursor.execute('SELECT avatar_filename FROM users WHERE user_id = %s', (user_id,))
                        user_data = cursor.fetchone()
                        if user_data and user_data.get('avatar_filename'):
                            old_file_path = os.path.join(current_app.config['PROFILE_UPLOAD_FOLDER'], user_data['avatar_filename'])
                            if os.path.exists(old_file_path):
                                os.remove(old_file_path)
                    else:
                        flash('นามสกุลไฟล์ไม่ถูกต้อง กรุณาใช้ไฟล์ JPG, PNG เท่านั้น', 'error')
                        return redirect(url_for('staff.profile'))
            
            # อัปเดตข้อมูลในฐานข้อมูล
            cursor = get_cursor()
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
            
            # Commit การเปลี่ยนแปลง
            get_db().commit()
            
            # อัปเดต session
            session['name'] = name
            if avatar_filename:
                session['avatar'] = avatar_filename
            
            flash('อัปเดตข้อมูลเรียบร้อยแล้ว', 'success')
            
            # ส่งพารามิเตอร์กลับไปให้ JavaScript อัปเดตรูปภาพ
            if avatar_filename:
                return redirect(url_for('staff.profile', avatar_updated='1', filename=avatar_filename))
            else:
                return redirect(url_for('staff.profile'))
            
        except Exception as e:
            print(f"Error updating staff profile: {e}")
            flash('เกิดข้อผิดพลาดในการอัปเดตข้อมูล', 'error')
            return redirect(url_for('staff.profile'))

    # GET request - แสดงฟอร์ม
    try:
        cursor = get_cursor()
        cursor.execute('''
            SELECT u.user_id, u.username, u.name, u.avatar_filename, u.created_at
            FROM users u
            WHERE u.user_id = %s
        ''', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash('ไม่พบข้อมูลผู้ใช้', 'error')
            return redirect(url_for('staff.dashboard'))
        
        return render_template('staff/profile.html', user=user)
        
    except Exception as e:
        print(f"Error loading staff profile: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดข้อมูล', 'error')
        return redirect(url_for('staff.dashboard'))





@staff.route('/bookings/<int:booking_id>/edit', methods=['GET', 'POST'])
@staff_required
def edit_booking(booking_id):
    """หน้าแก้ไขการจองสำหรับพนักงาน"""
    cursor = get_cursor()
    # ----------------------
    # ดึงข้อมูล booking หลัก
    # ----------------------
    cursor.execute('''
        SELECT b.booking_id, b.booking_date, b.service_date, b.service_time, b.status, b.note,
               c.first_name, c.last_name, c.phone, c.email, c.gender, c.birthdate,
               v.vehicle_id, v.license_plate, v.license_province, v.color, v.production_year,
               v.brand_name, v.model_name, v.engine_type_name, v.vehicle_type_id,
               COALESCE(a.address_no, '') as address_no, 
               COALESCE(a.village, '') as village, 
               COALESCE(a.road, '') as road, 
               COALESCE(a.subdistrict, '') as subdistrict, 
               COALESCE(a.district, '') as district, 
               COALESCE(a.province, '') as province, 
               COALESCE(a.zipcode, '') as zipcode
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        LEFT JOIN addresses a ON c.customer_id = a.customer_id
        WHERE b.booking_id = %s
    ''', (booking_id,))
    booking = cursor.fetchone()
    
    # Debug: แสดงข้อมูลที่ดึงมา
    print(f"Debug: Booking data: {booking}")
    
    if not booking:
        flash('ไม่พบข้อมูลการจอง')
        return redirect(url_for('staff.bookings'))
    
    if request.method == 'POST':
        # Debug: แสดงข้อมูลทั้งหมดที่ส่งมา
        print(f"Debug: All form data: {dict(request.form)}")
        
        # อัปเดตข้อมูลการจอง
        service_date = request.form.get('service_date', '')
        service_time = request.form.get('service_time', '')
        status = request.form.get('status', '')
        note = request.form.get('note', '').strip()
        
        # ตรวจสอบข้อมูลที่จำเป็น
        if not service_date or not status:
            flash('กรุณากรอกข้อมูลที่จำเป็นให้ครบถ้วน', 'error')
            return redirect(url_for('staff.edit_booking', booking_id=booking_id))
        
        # ถ้าไม่มี service_time ให้ใช้ค่าเริ่มต้น
        if not service_time:
            service_time = '09:00'
        
        cursor.execute('''
            UPDATE bookings 
            SET service_date = %s, service_time = %s, status = %s, note = %s 
            WHERE booking_id = %s
        ''', (service_date, service_time, status, note, booking_id))
        
        # --- เพิ่มการบันทึกข้อมูลยางลง service_tires ---
        # อัปเดต position ของข้อมูลยางที่มีอยู่แล้ว (ก่อนลบข้อมูล)
        cursor.execute('SELECT * FROM service_tires WHERE booking_id = %s AND (position IS NULL OR position = \'\' OR position REGEXP \'^[0-9]+$\') ORDER BY id', (booking_id,))
        existing_tires = cursor.fetchall()
        if existing_tires:
            positions = ['front_left', 'front_right', 'rear_left', 'rear_right']
            for i, tire in enumerate(existing_tires):
                if i < len(positions):
                    cursor.execute('UPDATE service_tires SET position = %s WHERE id = %s', (positions[i], tire['id']))
                    print(f"Updated tire ID {tire['id']} to position '{positions[i]}'")
        
        # ลบข้อมูลยางเก่าก่อน
        cursor.execute('DELETE FROM service_tires WHERE booking_id = %s', (booking_id,))
        
        # รับข้อมูลยางจากฟอร์ม
        tire_front_size = request.form.get('tire_front_size', '').strip()
        tire_front_brand_id = request.form.get('tire_front_brand_id', '').strip()
        tire_front_model_id = request.form.get('tire_front_model_id', '').strip()
        tire_rear_size = request.form.get('tire_rear_size', '').strip()
        tire_rear_brand_id = request.form.get('tire_rear_brand_id', '').strip()
        tire_rear_model_id = request.form.get('tire_rear_model_id', '').strip()
        tire_front_left = request.form.get('dot_front_left', '').strip()
        tire_front_right = request.form.get('dot_front_right', '').strip()
        tire_rear_left = request.form.get('dot_rear_left', '').strip()
        tire_rear_right = request.form.get('dot_rear_right', '').strip()
        
        # Debug: แสดงข้อมูลยางที่ส่งมา
        print(f"Debug: Front brand_id: {tire_front_brand_id}, model_id: {tire_front_model_id}")
        print(f"Debug: Rear brand_id: {tire_rear_brand_id}, model_id: {tire_rear_model_id}")
        
        # ดึงข้อมูลยี่ห้อและรุ่นยางจาก ID
        front_brand_name = ''
        front_model_name = ''
        rear_brand_name = ''
        rear_model_name = ''
        
        if tire_front_brand_id:
            cursor.execute('SELECT brand_name FROM brands WHERE brand_id = %s', (tire_front_brand_id,))
            brand_result = cursor.fetchone()
            if brand_result:
                front_brand_name = brand_result['brand_name']
        
        if tire_front_model_id:
            cursor.execute('SELECT model_name FROM tire_models WHERE model_id = %s', (tire_front_model_id,))
            model_result = cursor.fetchone()
            if model_result:
                front_model_name = model_result['model_name']
                print(f"Debug: Found front model: {front_model_name}")
            else:
                print(f"Debug: No front model found for ID: {tire_front_model_id}")
        
        if tire_rear_brand_id:
            cursor.execute('SELECT brand_name FROM brands WHERE brand_id = %s', (tire_rear_brand_id,))
            brand_result = cursor.fetchone()
            if brand_result:
                rear_brand_name = brand_result['brand_name']
        
        if tire_rear_model_id:
            cursor.execute('SELECT model_name FROM tire_models WHERE model_id = %s', (tire_rear_model_id,))
            model_result = cursor.fetchone()
            if model_result:
                rear_model_name = model_result['model_name']
                print(f"Debug: Found rear model: {rear_model_name}")
            else:
                print(f"Debug: No rear model found for ID: {tire_rear_model_id}")
        
        # บันทึกข้อมูลยาง 4 แถว (front_left, front_right, rear_left, rear_right) ลงในตาราง service_tires
        # Front Left
        cursor.execute('''
            INSERT INTO service_tires (booking_id, position, brand, model, size, dot) 
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (booking_id, 'front_left', front_brand_name, front_model_name, tire_front_size, tire_front_left))
        
        # Front Right
        cursor.execute('''
            INSERT INTO service_tires (booking_id, position, brand, model, size, dot) 
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (booking_id, 'front_right', front_brand_name, front_model_name, tire_front_size, tire_front_right))
        
        # Rear Left
        cursor.execute('''
            INSERT INTO service_tires (booking_id, position, brand, model, size, dot) 
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (booking_id, 'rear_left', rear_brand_name, rear_model_name, tire_rear_size, tire_rear_left))
        
        # Rear Right
        cursor.execute('''
            INSERT INTO service_tires (booking_id, position, brand, model, size, dot) 
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (booking_id, 'rear_right', rear_brand_name, rear_model_name, tire_rear_size, tire_rear_right))
        
        # ลบข้อมูลบริการเก่าก่อน
        cursor.execute('DELETE FROM booking_item_options WHERE item_id IN (SELECT item_id FROM booking_items WHERE booking_id = %s)', (booking_id,))
        cursor.execute('DELETE FROM booking_items WHERE booking_id = %s', (booking_id,))
        get_db().commit()  # Commit การลบข้อมูลเก่า
        
        # บันทึกข้อมูลบริการที่เลือก
        services = request.form.getlist('service_id')
        print(f"Debug: Selected services: {services}")  # Debug print
        
        for service_id in services:
            if service_id.strip():
                # เพิ่มข้อมูลบริการ
                cursor.execute('''
                    INSERT INTO booking_items (booking_id, service_id, quantity) 
                    VALUES (%s, %s, %s)
                ''', (booking_id, service_id, 1))
                
                item_id = cursor.lastrowid
                print(f"Debug: Inserted service {service_id} with item_id {item_id}")  # Debug print
                
                # เพิ่มข้อมูล options สำหรับบริการนี้
                options = request.form.getlist(f'service_option_{service_id}')
                print(f"Debug: Options for service {service_id}: {options}")  # Debug print
                
                for option_id in options:
                    if option_id.strip():
                        cursor.execute('''
                            INSERT INTO booking_item_options (item_id, option_id) 
                            VALUES (%s, %s)
                        ''', (item_id, option_id))
                        print(f"Debug: Inserted option {option_id} for item_id {item_id}")  # Debug print
        
        try:
            get_db().commit()
            print(f"Debug: Successfully committed all changes for booking {booking_id}")
            flash('อัปเดตข้อมูลการจองสำเร็จ')
            return redirect(url_for('staff.bookings'))
        except Exception as e:
            print(f"Debug: Error committing changes: {e}")
            get_db().rollback()
            flash('เกิดข้อผิดพลาดในการบันทึกข้อมูล', 'error')
            return redirect(url_for('staff.edit_booking', booking_id=booking_id))
    
    # GET request - แสดงฟอร์มแก้ไข
    # ดึงข้อมูลเพิ่มเติมสำหรับฟอร์ม
    cursor.execute('SELECT * FROM vehicle_types')
    vehicle_types = cursor.fetchall()
    
    cursor.execute('SELECT * FROM services ORDER BY service_name')
    services = cursor.fetchall()
    
    # ดึง options สำหรับแต่ละ service
    for service in services:
        cursor.execute('SELECT * FROM service_options WHERE service_id = %s ORDER BY option_name', (service['service_id'],))
        service['options'] = cursor.fetchall()
    
    # จัดกลุ่มบริการ
    service_groups = {}
    for service in services:
        category = service.get('category', 'บริการทั่วไป')
        if category not in service_groups:
            service_groups[category] = []
        service_groups[category].append(service)
    
    # ดึงข้อมูลยางและยี่ห้อ
    cursor.execute('SELECT * FROM brands ORDER BY brand_name')
    brands = cursor.fetchall()
    
    cursor.execute('SELECT * FROM tire_models ORDER BY model_name')
    tire_models = cursor.fetchall()
    
    # ดึงข้อมูลยี่ห้อรถ
    cursor.execute('SELECT * FROM car_brands ORDER BY car_brand_name')
    vehicle_brands = cursor.fetchall()
    
    # ดึงข้อมูลยางที่มีอยู่แล้ว
    cursor.execute('SELECT * FROM service_tires WHERE booking_id = %s ORDER BY position', (booking_id,))
    existing_tires = cursor.fetchall()
    print(f"Debug: Existing tires for booking_id {booking_id}: {existing_tires}")
    
    # จัดกลุ่มข้อมูลยางตามตำแหน่ง
    tire_data = {}
    if existing_tires:
        # ถ้า position เป็นค่าว่าง ให้กำหนดตำแหน่งตามลำดับ
        positions = ['front_left', 'front_right', 'rear_left', 'rear_right']
        for i, tire in enumerate(existing_tires):
            if tire['position'] and tire['position'].strip():  # ถ้ามี position อยู่แล้ว
                position_mapping = {
                    'FL': 'front_left',
                    'FR': 'front_right', 
                    'RL': 'rear_left',
                    'RR': 'rear_right'
                }
                new_position = position_mapping.get(tire['position'], tire['position'])
                tire_data[new_position] = tire
            else:  # ถ้า position เป็นค่าว่าง ให้กำหนดตามลำดับ
                tire_data[positions[i]] = tire
                # อัปเดต position ในฐานข้อมูลด้วย
                cursor.execute('UPDATE service_tires SET position = %s WHERE id = %s', (positions[i], tire['id']))
                print(f"Updated tire ID {tire['id']} to position '{positions[i]}'")  # Debug print
                get_db().commit()  # Commit การเปลี่ยนแปลง
        
        # เพิ่ม model_id และ brand_id สำหรับแต่ละ tire
        for position, tire in tire_data.items():
            if tire.get('brand'):
                # หา brand_id จากชื่อยี่ห้อ
                cursor.execute('SELECT brand_id FROM brands WHERE brand_name = %s', (tire['brand'],))
                brand_result = cursor.fetchone()
                if brand_result:
                    tire['brand_id'] = brand_result['brand_id']
                    print(f"Found brand_id {brand_result['brand_id']} for brand {tire['brand']}")
            
            if tire.get('model'):
                # หา model_id จากชื่อรุ่น
                cursor.execute('SELECT model_id FROM tire_models WHERE model_name = %s', (tire['model'],))
                model_result = cursor.fetchone()
                if model_result:
                    tire['model_id'] = model_result['model_id']
                    print(f"Found model_id {model_result['model_id']} for model {tire['model']}")
                else:
                    print(f"WARNING: No model_id found for model '{tire['model']}'")
                    # ลองหาแบบ case-insensitive
                    cursor.execute('SELECT model_id FROM tire_models WHERE LOWER(model_name) = LOWER(%s)', (tire['model'],))
                    model_result = cursor.fetchone()
                    if model_result:
                        tire['model_id'] = model_result['model_id']
                        print(f"Found model_id {model_result['model_id']} for model {tire['model']} (case-insensitive)")
                    else:
                        print(f"ERROR: Still no model_id found for model '{tire['model']}'")
        
        print(f"Debug: Final tire_data: {tire_data}")
        
        # Debug: แสดงข้อมูล tire_models ทั้งหมด
        cursor.execute('SELECT model_id, model_name, brand_id FROM tire_models ORDER BY model_name')
        all_models = cursor.fetchall()
        print(f"Debug: All tire models in database: {all_models}")
        
        # Debug: แสดงข้อมูล brands ทั้งหมด
        cursor.execute('SELECT brand_id, brand_name FROM brands ORDER BY brand_name')
        all_brands = cursor.fetchall()
        print(f"Debug: All brands in database: {all_brands}")
    
    # ดึงข้อมูลบริการที่ลูกค้าเลือกไว้
    cursor.execute('''
        SELECT bi.item_id, bi.service_id, bi.quantity, 
               s.service_name, s.category,
               GROUP_CONCAT(so.option_name SEPARATOR ', ') as options
        FROM booking_items bi
        JOIN services s ON bi.service_id = s.service_id
        LEFT JOIN booking_item_options bio ON bi.item_id = bio.item_id
        LEFT JOIN service_options so ON bio.option_id = so.option_id
        WHERE bi.booking_id = %s
        GROUP BY bi.item_id, bi.service_id, bi.quantity, s.service_name, s.category
    ''', (booking_id,))
    selected_services = cursor.fetchall()
    
    # สร้าง list ของ service_id ที่ลูกค้าเลือกไว้
    selected_service_ids = [service['service_id'] for service in selected_services]
    
    # สร้าง dictionary ของ options ที่ลูกค้าเลือกไว้
    selected_options = {}
    for service in selected_services:
        if service['options']:
            selected_options[service['service_id']] = service['options'].split(', ')
    
    # สร้าง dictionary ของ option_ids ที่ลูกค้าเลือกไว้
    selected_option_ids = {}
    cursor.execute('''
        SELECT bio.item_id, bio.option_id, bi.service_id
        FROM booking_item_options bio
        JOIN booking_items bi ON bio.item_id = bi.item_id
        WHERE bi.booking_id = %s
    ''', (booking_id,))
    option_results = cursor.fetchall()
    for option in option_results:
        if option['service_id'] not in selected_option_ids:
            selected_option_ids[option['service_id']] = []
        selected_option_ids[option['service_id']].append(str(option['option_id']))
    
    # ดึงข้อมูล vehicle models
    with open('static/data/vehicle_brands_models.json', encoding='utf-8') as f:
        vehicle_data = json.load(f)
    
    # สร้าง dictionary สำหรับ map brand_id ไปยัง brand_name
    brand_id_to_name = {brand['brand_id']: brand['brand_name'] for brand in vehicle_data['brands']}
    
    # สร้าง list ของ vehicle models
    vehicle_models = []
    for model in vehicle_data['models']:
        vehicle_models.append({
            'model_name': model['model_name'],
            'brand_name': brand_id_to_name.get(model['brand_id'], 'Unknown')
        })
    
    # ดึงรายการจังหวัด
    provinces = ['กรุงเทพมหานคร', 'กระบี่', 'กาญจนบุรี', 'กาฬสินธุ์', 'กำแพงเพชร', 'ขอนแก่น', 'จันทบุรี', 'ฉะเชิงเทรา', 'ชลบุรี', 'ชัยนาท', 'ชัยภูมิ', 'ชุมพร', 'เชียงราย', 'เชียงใหม่', 'ตรัง', 'ตราด', 'ตาก', 'นครนายก', 'นครปฐม', 'นครพนม', 'นครราชสีมา', 'นครศรีธรรมราช', 'นครสวรรค์', 'นนทบุรี', 'นราธิวาส', 'น่าน', 'บึงกาฬ', 'บุรีรัมย์', 'ปทุมธานี', 'ประจวบคีรีขันธ์', 'ปราจีนบุรี', 'ปัตตานี', 'พระนครศรีอยุธยา', 'พังงา', 'พัทลุง', 'พิจิตร', 'พิษณุโลก', 'เพชรบุรี', 'เพชรบูรณ์', 'แพร่', 'พะเยา', 'ภูเก็ต', 'มหาสารคาม', 'มุกดาหาร', 'แม่ฮ่องสอน', 'ยะลา', 'ยโสธร', 'ร้อยเอ็ด', 'ระนอง', 'ระยอง', 'ราชบุรี', 'ลพบุรี', 'ลำปาง', 'ลำพูน', 'เลย', 'ศรีสะเกษ', 'สกลนคร', 'สงขลา', 'สตูล', 'สมุทรปราการ', 'สมุทรสงคราม', 'สมุทรสาคร', 'สระแก้ว', 'สระบุรี', 'สิงห์บุรี', 'สุโขทัย', 'สุพรรณบุรี', 'สุราษฎร์ธานี', 'สุรินทร์', 'หนองคาย', 'หนองบัวลำภู', 'อ่างทอง', 'อุดรธานี', 'อุทัยธานี', 'อุตรดิตถ์', 'อุบลราชธานี', 'อำนาจเจริญ']
    
    return render_template('staff/edit_booking.html', 
                         booking=booking,
                         vehicle_types=vehicle_types,
                         services=services,
                         service_groups=service_groups,
                         brands=brands,
                         tire_models=tire_models,
                         vehicle_brands=vehicle_brands,
                         vehicle_models=vehicle_models,
                         provinces=provinces,
                         selected_services=selected_services,
                         selected_service_ids=selected_service_ids,
                         selected_options=selected_options,
                         selected_option_ids=selected_option_ids,
                         tire_data=tire_data)


@staff.route('/bookings/update-status/<int:booking_id>', methods=['POST'])
@staff_required
def update_booking_status(booking_id):
    """อัปเดตสถานะการจอง"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'error': 'ไม่พบสถานะใหม่'}), 400
        
        cursor = get_cursor()
        cursor.execute('UPDATE bookings SET status = %s WHERE booking_id = %s', (new_status, booking_id))
        get_db().commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error updating booking status: {e}")
        return jsonify({'success': False, 'error': 'เกิดข้อผิดพลาดในการอัปเดตสถานะ'}), 500

@staff.route('/bookings/<int:booking_id>/delete', methods=['POST'])
@staff_required
def delete_booking(booking_id):
    """ลบการจอง"""
    try:
        cursor = get_cursor()
        
        # ลบข้อมูลที่เกี่ยวข้อง
        cursor.execute('DELETE FROM booking_item_options WHERE item_id IN (SELECT item_id FROM booking_items WHERE booking_id = %s)', (booking_id,))
        cursor.execute('DELETE FROM booking_items WHERE booking_id = %s', (booking_id,))
        cursor.execute('DELETE FROM service_tires WHERE booking_id = %s', (booking_id,))
        cursor.execute('DELETE FROM bookings WHERE booking_id = %s', (booking_id,))
        
        get_db().commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error deleting booking: {e}")
        return jsonify({'success': False, 'error': 'เกิดข้อผิดพลาดในการลบการจอง'}), 500

@staff.route('/logout', methods=['POST', 'GET'])
@staff_required
def logout():
    """ออกจากระบบพนักงาน"""
    session.clear()
    session.permanent = False
    flash('ออกจากระบบพนักงานเรียบร้อย', 'success')
    return redirect(url_for('auth.login'))
