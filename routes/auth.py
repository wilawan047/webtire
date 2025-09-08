from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from database import get_cursor, get_db
from utils import verify_password, is_safe_url
from datetime import timedelta
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash
from flask_wtf.csrf import generate_csrf

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """หน้าเข้าสู่ระบบสำหรับผู้ดูแล"""
    # คำนวณ next_url ตั้งแต่ต้น (ใช้ได้ทั้ง GET/POST)
    next_url = request.args.get('next') if request.method == 'GET' else request.form.get('next')

    if request.method == 'GET':
        # เข้าหน้า login ไม่ต้องเคลียร์ session เพื่อรักษา CSRF token
        return render_template('login.html', next=next_url)

    # ---- POST ----
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    try:
        cursor = get_cursor()
        cursor.execute("""
            SELECT u.user_id, u.username, u.role_name as role, u.name, u.avatar_filename, u.password_hash
            FROM users u
            WHERE u.username = %s AND u.role_name IN ('admin','staff','owner')
            LIMIT 1
        """, (username,))
        user = cursor.fetchone()

        if not user:
            flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "error")
            return render_template('login.html', next=next_url)

        if not user.get('password_hash') or not verify_password(password, user['password_hash']):
            flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "error")
            return render_template('login.html', next=next_url)

        # รีเซ็ต session แล้วตั้งค่าใหม่แบบคุม role ให้ชัด
        session.clear()
        session.permanent = True
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['name'] = user['name']
        session['avatar'] = user['avatar_filename']

        if user['role'] == 'admin':
            session['admin_user_id'] = user['user_id']
            flash(f"เข้าสู่ระบบของผู้ดูแลระบบสำเร็จ! ยินดีต้อนรับ {user['name']}", "success")
            default_dest = 'admin.admin_dashboard'
        elif user['role'] == 'staff':
            session['staff_user_id'] = user['user_id']
            flash(f"เข้าสู่ระบบของพนักงานสำเร็จ! ยินดีต้อนรับ {user['name']}", "success")
            default_dest = 'staff.dashboard'
        elif user['role'] == 'owner':
            session['owner_user_id'] = user['user_id']
            flash(f"เข้าสู่ระบบของเจ้าของกิจการสำเร็จ! ยินดีต้อนรับ {user['name']}", "success")
            default_dest = 'owner.dashboard'
        else:
            # กันตกเผื่อ role หลุดมาจริง
            flash("สิทธิ์การเข้าใช้งานไม่ถูกต้อง", "error")
            return render_template('login.html', next=next_url)

        # ไป next_url ถ้าปลอดภัย ไม่งั้นไป dashboard ตาม role
        if next_url and is_safe_url(next_url):
            return redirect(next_url)
        return redirect(url_for(default_dest))

    except Exception as e:
        print(f"[login] error: {e}")
        flash("เกิดข้อผิดพลาดในการเข้าสู่ระบบ กรุณาลองใหม่อีกครั้ง", "error")
        return render_template('login.html', next=next_url)

@auth.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    """หน้าเข้าสู่ระบบสำหรับลูกค้า"""
    # รับ next_url จาก form หรือ args
    next_url = request.form.get('next') or request.args.get('next', '')
    
    if request.method == 'GET':
        # แสดงหน้า login สำหรับลูกค้า
        return render_template('customer/login.html', next=next_url)
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember_me = request.form.get('remember_me') == 'on'

        if not username or not password:
            flash("กรุณากรอกชื่อผู้ใช้และรหัสผ่าน", "error")
            return render_template('login.html', next=next_url)

        try:
            cursor = get_cursor()
            cursor.execute("""
                SELECT u.user_id, u.username, u.password_hash, u.name, u.avatar_filename, c.customer_id
                FROM users u
                JOIN customers c ON u.user_id = c.user_id
                WHERE u.username = %s AND u.role_name = 'customer'
            """, (username,))
            user = cursor.fetchone()

            if user and user['password_hash'] and verify_password(password, user['password_hash']):
                session.clear()
                # ✅ เก็บ session ของลูกค้า
                session['user_id'] = user['user_id']        # ใช้เช็ค login ทั่วไป
                session['customer_id'] = user['customer_id']
                session['customer_username'] = user['username']
                session['role'] = 'customer'
                session['customer_name'] = user['name']
                session['customer_avatar'] = user['avatar_filename']

                # ตั้งค่าอายุ session
                session.permanent = True
                from flask import current_app
                current_app.permanent_session_lifetime = timedelta(days=30 if remember_me else 7)

                flash(f"เข้าสู่ระบบสำเร็จ! ยินดีต้อนรับ {user['name']}")
                
                # ตรวจสอบและ redirect ไปยังหน้าเดิม
                if next_url and is_safe_url(next_url) and next_url != '/':
                    return redirect(next_url)
                else:
                    return redirect(url_for('customer.home'))
            else:
                flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "error")
                return render_template('login.html', next=next_url)

        except Exception as e:
            print(f"Customer login error: {e}")
            flash("เกิดข้อผิดพลาดในการเข้าสู่ระบบ กรุณาลองใหม่อีกครั้ง", "error")
            return render_template('login.html', next=next_url)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """หน้าลงทะเบียน"""
    if request.method == 'POST':
        # โค้ดการลงทะเบียน
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        
        # แปลง email เป็น None ถ้าเป็นสตริงว่าง
        if email == '':
            email = None
        gender = request.form.get('gender', '').strip()
        
        # แปลง gender เป็น 'ไม่ระบุ' ถ้าเป็นสตริงว่าง
        if gender == '':
            gender = 'ไม่ระบุ'
        birthdate = request.form.get('birthdate', '').strip()
        
        # แปลง birthdate เป็น None ถ้าเป็นสตริงว่าง
        if birthdate == '':
            birthdate = None
        
        # ตรวจสอบข้อมูล
        errors = {}
        
        # ตรวจสอบข้อมูลที่จำเป็น
        if not username:
            errors['username'] = 'กรุณากรอกชื่อผู้ใช้'
        elif len(username) < 3 or len(username) > 20:
            errors['username'] = 'ชื่อผู้ใช้ต้องมี 3-20 ตัวอักษร'
        elif not username.replace('_', '').isalnum():
            errors['username'] = 'ชื่อผู้ใช้ใช้ได้เฉพาะตัวอักษร ตัวเลข และ _ เท่านั้น'
        if not password:
            errors['password'] = 'กรุณากรอกรหัสผ่าน'
        if not confirm_password:
            errors['confirm_password'] = 'กรุณายืนยันรหัสผ่าน'
        if not first_name:
            errors['first_name'] = 'กรุณากรอกชื่อ'
        if not last_name:
            errors['last_name'] = 'กรุณากรอกนามสกุล'
        if not phone:
            errors['phone'] = 'กรุณากรอกเบอร์โทรศัพท์'
        elif not phone.isdigit() or len(phone) != 10:
            errors['phone'] = 'เบอร์โทรศัพท์ต้องเป็นตัวเลข 10 หลัก'
        
        # ตรวจสอบ terms (ถ้ามี checkbox terms ใน form)
        # terms = request.form.get('terms')
        # if not terms:
        #     errors['terms'] = 'กรุณายอมรับเงื่อนไขการใช้งาน'
        
        # ตรวจสอบ email format (ถ้ามี email)
        if email and ('@' not in email or '.' not in email):
            errors['email'] = 'รูปแบบอีเมลไม่ถูกต้อง'
        
        if password != confirm_password:
            errors['confirm_password'] = 'รหัสผ่านไม่ตรงกัน'
        
        if len(password) < 8:
            errors['password'] = 'รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร'
        
        # ถ้ามี error และเป็น AJAX request
        if errors and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'errors': errors}), 400
        
        # ถ้ามี error และเป็น normal request
        if errors:
            if 'general' in errors:
                flash(errors['general'], 'error')
            else:
                # ส่ง error แรกที่เจอ
                first_error = list(errors.values())[0]
                flash(first_error, 'error')
            return redirect(url_for('customer.home') + "#register")
        
        try:
            cursor = get_cursor()
            
            # ตรวจสอบ username ซ้ำ
            cursor.execute('SELECT user_id FROM users WHERE username = %s', (username,))
            if cursor.fetchone():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'errors': {'username': 'ชื่อผู้ใช้นี้มีอยู่ในระบบแล้ว กรุณาเลือกชื่อผู้ใช้อื่น'}}), 400
                else:
                    flash('ชื่อผู้ใช้นี้มีอยู่ในระบบแล้ว กรุณาเลือกชื่อผู้ใช้อื่น', 'error')
                    return redirect(url_for('customer.home') + "#register")
            
            # ตรวจสอบ phone ซ้ำ
            cursor.execute('SELECT customer_id FROM customers WHERE phone = %s', (phone,))
            if cursor.fetchone():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'errors': {'phone': 'เบอร์โทรศัพท์นี้มีอยู่ในระบบแล้ว กรุณาใช้เบอร์โทรศัพท์อื่น'}}), 400
                else:
                    flash('เบอร์โทรศัพท์นี้มีอยู่ในระบบแล้ว กรุณาใช้เบอร์โทรศัพท์อื่น', 'error')
                    return redirect(url_for('customer.home') + "#register")
            
            # ตรวจสอบ email ซ้ำ (ถ้ามี)
            if email:
                cursor.execute('SELECT customer_id FROM customers WHERE email = %s', (email,))
                if cursor.fetchone():
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'errors': {'email': 'อีเมลนี้มีอยู่ในระบบแล้ว กรุณาใช้อีเมลอื่น'}}), 400
                    else:
                        flash('อีเมลนี้มีอยู่ในระบบแล้ว กรุณาใช้อีเมลอื่น', 'error')
                        return redirect(url_for('customer.home') + "#register")
            
            # สร้าง user ใหม่
            from werkzeug.security import generate_password_hash
            password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            
            # เพิ่ม user (ใช้ role_name แทน role_id)
            cursor.execute('''
                INSERT INTO users (username, password_hash, name, role_name) 
                VALUES (%s, %s, %s, %s)
            ''', (username, password_hash, f"{first_name} {last_name}", 'customer'))
            
            user_id = cursor.lastrowid
            
            # เพิ่ม customer
            cursor.execute('''
                INSERT INTO customers (user_id, first_name, last_name, phone, email, gender, birthdate) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (user_id, first_name, last_name, phone, email, gender, birthdate))
            
            # Commit transaction
            get_db().commit()
            
            # ถ้าเป็น AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'ลงทะเบียนสำเร็จ กรุณาเข้าสู่ระบบ'})
            else:
                flash('ลงทะเบียนสำเร็จ กรุณาเข้าสู่ระบบ', 'success')
                return redirect(url_for('customer.home') + "#login")
            
        except Exception as e:
            print(f"Registration error: {e}")
            # Rollback transaction
            try:
                get_db().rollback()
            except:
                pass
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'errors': {'general': 'เกิดข้อผิดพลาดในการลงทะเบียน กรุณาลองใหม่อีกครั้ง'}}), 500
            else:
                flash('เกิดข้อผิดพลาดในการลงทะเบียน กรุณาลองใหม่อีกครั้ง', 'error')
                return redirect(url_for('customer.home') + "#register")
    
    # สำหรับ GET request ให้ redirect ไปหน้า home
    return redirect(url_for('customer.home') + "#register")

@auth.route('/forgot-password', methods=['POST'])
def forgot_password():
    """ส่งลิงก์รีเซ็ตรหัสผ่านไปยังอีเมล"""
    try:
        email = request.form.get('email', '').strip()
        
        if not email:
            return jsonify({'success': False, 'message': 'กรุณากรอกอีเมล'}), 400
        
        cursor = get_cursor()
        
        # ตรวจสอบว่ามีอีเมลนี้ในระบบหรือไม่
        cursor.execute("""
            SELECT c.customer_id, c.first_name, c.last_name, u.username, u.user_id
            FROM customers c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.email = %s AND u.role_name = 'customer'
        """, (email,))
        customer = cursor.fetchone()
        
        if not customer:
            return jsonify({'success': False, 'message': 'ไม่พบอีเมลนี้ในระบบ'}), 400
        
        # สร้าง token สำหรับรีเซ็ตรหัสผ่าน
        reset_token = secrets.token_urlsafe(32)
        
        # ลบ token เก่าที่หมดอายุ
        cursor.execute("DELETE FROM password_reset_tokens WHERE expires_at < NOW() OR used = TRUE")
        
        # บันทึก token ใหม่ (หมดอายุใน 1 ชั่วโมง)
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(hours=1)
        
        cursor.execute("""
            INSERT INTO password_reset_tokens (email, token, expires_at)
            VALUES (%s, %s, %s)
        """, (email, reset_token, expires_at))
        
        get_db().commit()
        
        # ส่งอีเมล
        try:
            send_reset_email(email, customer['first_name'], reset_token)
            return jsonify({'success': True, 'message': 'ส่งลิงก์รีเซ็ตรหัสผ่านไปยังอีเมลของคุณแล้ว กรุณาตรวจสอบอีเมล'})
        except Exception as e:
            print(f"Error sending email: {e}")
            return jsonify({'success': False, 'message': 'เกิดข้อผิดพลาดในการส่งอีเมล กรุณาลองใหม่อีกครั้ง'}), 500
            
    except Exception as e:
        print(f"Forgot password error: {e}")
        return jsonify({'success': False, 'message': 'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง'}), 500

@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """รีเซ็ตรหัสผ่านด้วย token"""
    if request.method == 'GET':
        # ตรวจสอบ token และแสดง modal
        try:
            cursor = get_cursor()
            cursor.execute("""
                SELECT prt.email, prt.expires_at, prt.used
                FROM password_reset_tokens prt
                WHERE prt.token = %s AND prt.expires_at > NOW() AND prt.used = FALSE
            """, (token,))
            token_data = cursor.fetchone()
            
            if not token_data:
                flash('ลิงก์รีเซ็ตรหัสผ่านไม่ถูกต้องหรือหมดอายุแล้ว', 'error')
                return redirect(url_for('customer.home'))
            
            # แสดงหน้า home พร้อมเปิด reset password modal
            return redirect(url_for('customer.home') + f'#reset-password-{token}')
            
        except Exception as e:
            print(f"Token validation error: {e}")
            flash('เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง', 'error')
            return redirect(url_for('customer.home'))
    
    # POST request - ประมวลผลการรีเซ็ตรหัสผ่าน
    try:
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not new_password or not confirm_password:
            return jsonify({'success': False, 'message': 'กรุณากรอกข้อมูลให้ครบถ้วน'}), 400
        
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': 'รหัสผ่านใหม่ไม่ตรงกัน'}), 400
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'รหัสผ่านใหม่ต้องมีอย่างน้อย 6 ตัวอักษร'}), 400
        
        cursor = get_cursor()
        
        # ตรวจสอบ token
        cursor.execute("""
            SELECT prt.email, prt.expires_at, prt.used
            FROM password_reset_tokens prt
            WHERE prt.token = %s AND prt.expires_at > NOW() AND prt.used = FALSE
        """, (token,))
        token_data = cursor.fetchone()
        
        if not token_data:
            return jsonify({'success': False, 'message': 'ลิงก์รีเซ็ตรหัสผ่านไม่ถูกต้องหรือหมดอายุแล้ว'}), 400
        
        # อัปเดตรหัสผ่าน
        password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        
        cursor.execute("""
            UPDATE users u
            JOIN customers c ON u.user_id = c.user_id
            SET u.password_hash = %s
            WHERE c.email = %s
        """, (password_hash, token_data['email']))
        
        # ทำเครื่องหมายว่า token ถูกใช้แล้ว
        cursor.execute("""
            UPDATE password_reset_tokens
            SET used = TRUE
            WHERE token = %s
        """, (token,))
        
        get_db().commit()
        
        return jsonify({'success': True, 'message': 'รีเซ็ตรหัสผ่านสำเร็จ กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่'})
        
    except Exception as e:
        print(f"Reset password error: {e}")
        return jsonify({'success': False, 'message': 'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง'}), 500

def send_reset_email(email, first_name, token):
    """ส่งอีเมลรีเซ็ตรหัสผ่าน"""
    try:
        # ตั้งค่าอีเมล (ใช้ Gmail SMTP)
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "computersci65@gmail.com"  # อีเมลจาก .env
        sender_password = "xmkw jdpk aaof fsrs"  # App Password จาก .env
        
        # สร้างลิงก์รีเซ็ต
        reset_link = f"http://localhost:5000/reset-password/{token}"
        
        # สร้างเนื้อหาอีเมล
        subject = "รีเซ็ตรหัสผ่าน - ไทร์พลัส บุรีรัมย์แสงเจริญการยาง"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h2 style="color: #0c5e28;">รีเซ็ตรหัสผ่าน</h2>
                </div>
                
                <p>สวัสดีคุณ {first_name},</p>
                
                <p>เราได้รับคำขอรีเซ็ตรหัสผ่านสำหรับบัญชีของคุณ กรุณาคลิกลิงก์ด้านล่างเพื่อตั้งรหัสผ่านใหม่:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" 
                       style="background-color: #0c5e28; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        รีเซ็ตรหัสผ่าน
                    </a>
                </div>
                
                <p>หรือคัดลอกลิงก์นี้ไปวางในเบราว์เซอร์:</p>
                <p style="word-break: break-all; background-color: #f5f5f5; padding: 10px; border-radius: 3px;">
                    {reset_link}
                </p>
                
                <p><strong>หมายเหตุ:</strong> ลิงก์นี้จะหมดอายุใน 1 ชั่วโมง</p>
                
                <p>หากคุณไม่ได้ขอรีเซ็ตรหัสผ่าน กรุณาเพิกเฉยต่ออีเมลนี้</p>
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                <p style="font-size: 12px; color: #666; text-align: center;">
                    ไทร์พลัส บุรีรัมย์แสงเจริญการยาง<br>
                    อีเมลนี้ส่งโดยอัตโนมัติ กรุณาอย่าตอบกลับ
                </p>
            </div>
        </body>
        </html>
        """
        
        # สร้างอีเมล
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = email
        
        # เพิ่มเนื้อหา HTML
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # ส่งอีเมล
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        print(f"Reset email sent to {email}")
        
    except Exception as e:
        print(f"Error sending reset email: {e}")
        raise e

@auth.route('/get-csrf-token')
def get_csrf_token():
    """API สำหรับดึง CSRF token ใหม่"""
    try:
        csrf_token = generate_csrf()
        return jsonify({'csrf_token': csrf_token})
    except Exception as e:
        print(f"Error generating CSRF token: {e}")
        return jsonify({'error': 'Failed to generate CSRF token'}), 500