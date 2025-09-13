from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, g, current_app, send_file
from database import get_cursor, get_db
from utils import allowed_file
from decorators import login_required, admin_required
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import json
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import black, white, HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/tires')
@admin_required
def tire_list():
    cursor = get_cursor()
    search = request.args.get('search', '').strip()
    filter_by = request.args.get('filter', 'brand')
    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page
    sort = request.args.get('sort', 'tire_id')
    direction = request.args.get('direction', 'desc')
    valid_sorts = {'tire_id', 'brand_name', 'model_name', 'full_size', 'price_each', 'product_date'}
    if sort not in valid_sorts:
        sort = 'tire_id'
    if direction not in {'asc', 'desc'}:
        direction = 'desc'
    params = []
    where = ''
    filter_map = {
        'brand': 'b.brand_name LIKE %s',
        'model': 'm.model_name LIKE %s',
        'width': 't.width = %s',
        'aspect_ratio': 't.aspect_ratio = %s',
        'rim_diameter': 't.rim_diameter = %s',
        'full_size': 't.full_size LIKE %s',
        'price_each': 't.price_each = %s',
    }
    # --- Custom search and sort logic ---
    if search:
        # ใช้ search_term จาก request.args เพื่อให้ตรงกันทุกที่
        search_term = request.args.get('search', '')
        
        # ค้นหาแบบ fuzzy search ในฟิลด์ที่เลือกตาม filter_by
        if filter_by in ['brand', 'model', 'full_size']:
            if filter_by == 'brand':
                where = 'WHERE b.brand_name LIKE %s'
                params = [f"%{search_term}%"]
            elif filter_by == 'model':
                where = 'WHERE m.model_name LIKE %s'
                params = [f"%{search_term}%"]
            elif filter_by == 'full_size':
                where = 'WHERE t.full_size LIKE %s'
                params = [f"%{search_term}%"]
        else:
            # ถ้าไม่ได้เลือก filter หรือเลือก filter อื่น ให้ค้นหาในทุกฟิลด์
            where = "WHERE b.brand_name LIKE %s OR m.model_name LIKE %s OR t.full_size LIKE %s"
            params = [f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"]
        
        # 2. Get all results, then sort in Python: prefix match first, then contains
        query = f'''
            SELECT t.tire_id, t.full_size, t.price_each, t.price_set, t.product_date, t.high_speed_rating, m.model_name, b.brand_name,
                   t.width, t.aspect_ratio, t.rim_diameter, 
                   COALESCE(t.tire_image_url, 
                     (SELECT t2.tire_image_url 
                      FROM tires t2 
                      JOIN tire_models m2 ON t2.model_id = m2.model_id 
                      JOIN brands b2 ON m2.brand_id = b2.brand_id 
                      WHERE b2.brand_name = b.brand_name 
                        AND m2.model_name = m.model_name 
                        AND t2.tire_image_url IS NOT NULL 
                      LIMIT 1)) as tire_image_url
            FROM tires t
            JOIN tire_models m ON t.model_id = m.model_id
            JOIN brands b ON m.brand_id = b.brand_id
            {where}
        '''
        print(f"Debug - Query: {query}")
        print(f"Debug - Params: {params}")
        cursor.execute(query, params)
        tires = cursor.fetchall()
        print(f"Debug - Found {len(tires)} tires")
        
        def calculate_similarity(tire, search_term, filter_by):
            """คำนวณความคล้ายคลึงระหว่างยางกับคำค้นหาในฟิลด์ที่เลือก"""
            search_lower = search_term.lower()
            
            if filter_by == 'brand':
                return calculate_field_similarity(tire['brand_name'] or '', search_lower)
            elif filter_by == 'model':
                return calculate_field_similarity(tire['model_name'] or '', search_lower)
            elif filter_by == 'full_size':
                return calculate_field_similarity(tire['full_size'] or '', search_lower)
            else:
                # คำนวณ similarity สำหรับทุกฟิลด์และคืนค่าสูงสุด
                brand_score = calculate_field_similarity(tire['brand_name'] or '', search_lower)
                model_score = calculate_field_similarity(tire['model_name'] or '', search_lower)
                full_size_score = calculate_field_similarity(tire['full_size'] or '', search_lower)
                return max(brand_score, model_score, full_size_score)
        
        def calculate_field_similarity(text, search_term):
            """คำนวณความคล้ายคลึงระหว่างข้อความกับคำค้นหา"""
            text_lower = text.lower()
            
            # 1. Exact match (คะแนนสูงสุด)
            if text_lower == search_term:
                return 100
            
            # 2. Starts with (คะแนนสูง)
            if text_lower.startswith(search_term):
                return 90
            
            # 3. Contains (คะแนนปานกลาง)
            if search_term in text_lower:
                return 70
            
            # 4. Partial word match (คะแนนต่ำ)
            words = search_term.split()
            text_words = text_lower.split()
            matches = sum(1 for word in words if any(word in tw for tw in text_words))
            if matches > 0:
                return 50 + (matches * 10)
            
            # 5. Character similarity (คะแนนต่ำสุด)
            common_chars = sum(1 for c in search_term if c in text_lower)
            return min(30, common_chars * 5)
        
        # คำนวณ similarity score สำหรับแต่ละยาง
        for tire in tires:
            tire['similarity_score'] = calculate_similarity(tire, search_term, filter_by)
        
        # เรียงลำดับตาม similarity score จากสูงไปต่ำ
        tires.sort(key=lambda t: (-t['similarity_score'], t['brand_name'] or '', t['model_name'] or ''))
        
        # ลบ similarity_score ออกก่อนส่งกลับ
        for tire in tires:
            del tire['similarity_score']
        total = len(tires)
        total_pages = (total + per_page - 1) // per_page
        tires = tires[offset:offset+per_page]
    else:
        # Default logic (unchanged)
        if search:
            if filter_by in filter_map:
                if filter_by in ['width', 'aspect_ratio', 'rim_diameter', 'price_each']:
                    where = f"WHERE {filter_map[filter_by]}"
                    params.append(search)
                else:
                    where = f"WHERE {filter_map[filter_by]}"
                    params.append(f"%{search}%")
            else:
                # fallback: ค้นหาทุกอย่าง
                where = "WHERE b.brand_name LIKE %s OR m.model_name LIKE %s OR t.full_size LIKE %s"
                like = f"%{search}%"
                params = [like, like, like]
        count_query = f"""
            SELECT COUNT(*) FROM tires t
            JOIN tire_models m ON t.model_id = m.model_id
            JOIN brands b ON m.brand_id = b.brand_id
            {where}
        """
        cursor.execute(count_query, params)
        total = list(cursor.fetchone().values())[0]
        total_pages = (total + per_page - 1) // per_page
        query = f'''
            SELECT t.tire_id, t.full_size, t.price_each, t.price_set, t.product_date, t.high_speed_rating, m.model_name, b.brand_name,
                   t.width, t.aspect_ratio, t.rim_diameter, 
                   COALESCE(t.tire_image_url, 
                     (SELECT t2.tire_image_url 
                      FROM tires t2 
                      JOIN tire_models m2 ON t2.model_id = m2.model_id 
                      JOIN brands b2 ON m2.brand_id = b2.brand_id 
                      WHERE b2.brand_name = b.brand_name 
                        AND m2.model_name = m.model_name 
                        AND t2.tire_image_url IS NOT NULL 
                      LIMIT 1)) as tire_image_url
            FROM tires t
            JOIN tire_models m ON t.model_id = m.model_id
            JOIN brands b ON m.brand_id = b.brand_id
            {where}
            ORDER BY FIELD(b.brand_name, 'michelin', 'BFgoodrich', 'Maxxis'), m.model_name ASC
            LIMIT %s OFFSET %s
        '''
        print(f"Debug Default - Query: {query}")
        print(f"Debug Default - Params: {params}")
        params += [per_page, offset]
        cursor.execute(query, params)
        tires = cursor.fetchall()
        print(f"Debug Default - Found {len(tires)} tires")
    # ดึง brand/model/width/aspect_ratio/rim_diameter ทั้งหมดสำหรับ dropdown
    cursor.execute('SELECT DISTINCT brand_name FROM brands ORDER BY brand_name')
    brands = [row['brand_name'] for row in cursor.fetchall()]
    cursor.execute('SELECT DISTINCT model_name FROM tire_models ORDER BY model_name')
    models = [row['model_name'] for row in cursor.fetchall()]
    cursor.execute('SELECT DISTINCT width FROM tires ORDER BY width')
    widths = [row['width'] for row in cursor.fetchall() if row['width']]
    cursor.execute('SELECT DISTINCT aspect_ratio FROM tires ORDER BY aspect_ratio')
    aspects = [row['aspect_ratio'] for row in cursor.fetchall() if row['aspect_ratio']]
    cursor.execute('SELECT DISTINCT rim_diameter FROM tires ORDER BY rim_diameter')
    rim_diameters = [row['rim_diameter'] for row in cursor.fetchall() if row['rim_diameter']]
    return render_template('admin/tire_list.html',
        tires=tires, search=search, page=page, total_pages=total_pages, sort=sort, direction=direction,
        brands=brands, models=models, widths=widths, aspects=aspects, rim_diameters=rim_diameters,
        filter_by=filter_by
    )

@admin.route('/tires/add', methods=['GET', 'POST'])
@admin_required
def add_tire():
    cursor = get_cursor()
    if request.method == 'POST':
        try:
            # รับค่าจากฟอร์ม
            model_id = request.form.get('model_id', '')
            width = request.form.get('width', '')
            aspect_ratio = request.form.get('aspect_ratio', '')
            construction = request.form.get('construction', '')
            rim_diameter = request.form.get('rim_diameter', '')
            load_index = request.form.get('load_index', '')
            speed_symbol = request.form.get('speed_symbol', '')
            service_description = request.form.get('service_description', '')
            high_speed_rating = request.form.get('high_speed_rating', '')
            price_each = request.form.get('price_each', '')
            price_set = request.form.get('price_set', None)
            product_date = request.form.get('product_date', '')
            
            # ตรวจสอบข้อมูล
            if not all([model_id, width, aspect_ratio, rim_diameter, price_each]):
                flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'error')
                # ดึงข้อมูล models สำหรับแสดงในฟอร์ม
                cursor.execute('''
                    SELECT m.model_id, m.model_name, b.brand_name, b.brand_id
                    FROM tire_models m
                    JOIN brands b ON m.brand_id = b.brand_id
                    ORDER BY b.brand_name, m.model_name
                ''')
                models = cursor.fetchall()
                return render_template('admin/tire_form.html', 
                                     models=models, 
                                     tire=None,
                                     form_data={
                                         'model_id': model_id,
                                         'width': width,
                                         'aspect_ratio': aspect_ratio,
                                         'construction': construction,
                                         'rim_diameter': rim_diameter,
                                         'load_index': load_index,
                                         'speed_symbol': speed_symbol,
                                         'service_description': service_description,
                                         'high_speed_rating': high_speed_rating,
                                         'price_each': price_each,
                                         'price_set': price_set,
                                         'product_date': product_date
                                     })
            
            # แปลง product_date เป็น None ถ้าเป็นสตริงว่างหรือสตริง 'None'
            if product_date == '' or product_date == 'None' or product_date == 'null':
                product_date = None
            
            # ประกอบ full_size
            full_size = ''
            if width and aspect_ratio:
                full_size = f"{width}/{aspect_ratio} "
            if (speed_symbol == 'Z' or high_speed_rating):
                full_size += 'ZR'
            if construction:
                full_size += f"{construction}"
            if rim_diameter:
                full_size += f"{rim_diameter} "
            if load_index:
                full_size += f"{load_index}"
            if speed_symbol and speed_symbol != 'Z':
                full_size += f"{speed_symbol} "
            else:
                full_size += ' '
            if service_description == 'XL':
                full_size = full_size.strip() + ' XL'
            else:
                full_size = full_size.strip()
            
            # เช็คยางซ้ำก่อนเพิ่ม
            check_duplicate_query = """
                SELECT t.tire_id, t.full_size, m.model_name, b.brand_name
                FROM tires t
                JOIN tire_models m ON t.model_id = m.model_id
                JOIN brands b ON m.brand_id = b.brand_id
                WHERE t.model_id = %s 
                AND t.width = %s 
                AND t.aspect_ratio = %s 
                AND COALESCE(t.construction, '') = COALESCE(%s, '')
                AND t.rim_diameter = %s
                AND COALESCE(t.load_index, '') = COALESCE(%s, '')
                AND COALESCE(t.speed_symbol, '') = COALESCE(%s, '')
                AND COALESCE(t.service_description, '') = COALESCE(%s, '')
                AND COALESCE(t.high_speed_rating, 0) = COALESCE(%s, 0)
            """
            cursor.execute(check_duplicate_query, (model_id, width, aspect_ratio, construction, rim_diameter, load_index, speed_symbol, service_description, high_speed_rating))
            duplicate = cursor.fetchone()
            
            if duplicate:
                flash(f'ยางนี้มีอยู่ในระบบแล้ว: {duplicate["brand_name"]} {duplicate["model_name"]} {duplicate["full_size"]}', 'error')
                # ดึงข้อมูล models สำหรับแสดงในฟอร์ม
                cursor.execute('''
                    SELECT m.model_id, m.model_name, b.brand_name, b.brand_id
                    FROM tire_models m
                    JOIN brands b ON m.brand_id = b.brand_id
                    ORDER BY b.brand_name, m.model_name
                ''')
                models = cursor.fetchall()
                return render_template('admin/tire_form.html', 
                                     models=models, 
                                     tire=None,
                                     form_data={
                                         'model_id': model_id,
                                         'width': width,
                                         'aspect_ratio': aspect_ratio,
                                         'construction': construction,
                                         'rim_diameter': rim_diameter,
                                         'load_index': load_index,
                                         'speed_symbol': speed_symbol,
                                         'service_description': service_description,
                                         'high_speed_rating': high_speed_rating,
                                         'price_each': price_each,
                                         'price_set': price_set,
                                         'product_date': product_date
                                     })
            
            # จัดการไฟล์รูปภาพ
            tire_image_url = None
            file = request.files.get('tire_image')
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # สร้างโฟลเดอร์ถ้ายังไม่มี
                upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'tires')
                os.makedirs(upload_folder, exist_ok=True)
                # บันทึกไฟล์
                file.save(os.path.join(upload_folder, filename))
                tire_image_url = filename
            
            query = """
                INSERT INTO tires (model_id, width, aspect_ratio, construction, rim_diameter, load_index, speed_symbol, service_description, high_speed_rating, price_each, price_set, product_date, full_size, tire_image_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (model_id, width, aspect_ratio, construction, rim_diameter, load_index, speed_symbol, service_description, high_speed_rating, price_each, price_set, product_date, full_size, tire_image_url))
            get_db().commit()
            flash('เพิ่มยางสำเร็จ')
            return redirect(url_for('admin.tire_list'))
            
        except Exception as e:
            print(f"Error adding tire: {e}")
            flash('เกิดข้อผิดพลาดในการเพิ่มยาง', 'error')
            # ดึงข้อมูล models และ brands สำหรับแสดงในฟอร์ม
            cursor.execute('''
                SELECT m.model_id, m.model_name, b.brand_name, b.brand_id
                FROM tire_models m
                JOIN brands b ON m.brand_id = b.brand_id
                ORDER BY b.brand_name, m.model_name
            ''')
            models = cursor.fetchall()
            
            # ดึงข้อมูล brands สำหรับ dropdown
            cursor.execute('SELECT * FROM brands ORDER BY brand_name')
            brands = cursor.fetchall()
            
            return render_template('admin/tire_form.html', 
                                 models=models, 
                                 brands=brands,
                                 tire=None,
                                 form_data={
                                     'model_id': model_id,
                                     'width': width,
                                     'aspect_ratio': aspect_ratio,
                                     'construction': construction,
                                     'rim_diameter': rim_diameter,
                                     'load_index': load_index,
                                     'speed_symbol': speed_symbol,
                                     'service_description': service_description,
                                     'high_speed_rating': high_speed_rating,
                                     'price_each': price_each,
                                     'price_set': price_set,
                                     'product_date': product_date
                                 })
    
    # GET request - แสดงฟอร์มเพิ่มยาง
    cursor.execute('''
        SELECT m.model_id, m.model_name, b.brand_name, b.brand_id
        FROM tire_models m
        JOIN brands b ON m.brand_id = b.brand_id
        ORDER BY b.brand_name, m.model_name
    ''')
    models = cursor.fetchall()
    
    # ดึงข้อมูล brands สำหรับ dropdown
    cursor.execute('SELECT * FROM brands ORDER BY brand_name')
    brands = cursor.fetchall()
    
    return render_template('admin/tire_form.html', models=models, brands=brands, tire=None, form_data=None)

@admin.route('/tires/edit/<int:tire_id>', methods=['GET', 'POST'])
@admin_required
def edit_tire(tire_id):
    cursor = get_cursor()
    if request.method == 'POST':
        # --- ลบรูปภาพ ---
        cursor.execute('SELECT tire_image_url FROM tires WHERE tire_id=%s', (tire_id,))
        row = cursor.fetchone()
        if request.form.get('delete_image') == '1':
            image_url = row['tire_image_url'] if row else None
            if image_url:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], 'tires', image_url))
                except Exception:
                    pass
                cursor.execute('UPDATE tires SET tire_image_url=NULL WHERE tire_id=%s', (tire_id,))
                get_db().commit()
            return redirect(url_for('admin.edit_tire', tire_id=tire_id))
        
        try:
            model_id = request.form.get('model_id', '')
            width = request.form.get('width', '')
            aspect_ratio = request.form.get('aspect_ratio', '')
            construction = request.form.get('construction', '') or None
            rim_diameter = request.form.get('rim_diameter', '')
            load_index = request.form.get('load_index', '') or None
            speed_symbol = request.form.get('speed_symbol', '') or None
            service_description = request.form.get('service_description', '') or None
            high_speed_rating = request.form.get('high_speed_rating', '') or None
            price_each = request.form.get('price_each', '')
            price_set = request.form.get('price_set', None) or None
            product_date = request.form.get('product_date', '') or None
            ply_rating = request.form.get('ply_rating', '') or None
            tubeless_type = request.form.get('tubeless_type', '') or None
            tire_load_type = request.form.get('tire_load_type', '') or None
            
            # ตรวจสอบข้อมูล
            if not all([model_id, width, aspect_ratio, rim_diameter, price_each]):
                flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'error')
                # ดึงข้อมูล tire และ models สำหรับแสดงในฟอร์ม
                cursor.execute('''
                    SELECT t.*, m.model_id, m.model_name, b.brand_id, b.brand_name
                    FROM tires t
                    JOIN tire_models m ON t.model_id = m.model_id
                    JOIN brands b ON m.brand_id = b.brand_id
                    WHERE t.tire_id=%s
                ''', (tire_id,))
                tire = cursor.fetchone()
                cursor.execute('''
                    SELECT m.model_id, m.model_name, b.brand_name, b.brand_id
                    FROM tire_models m
                    JOIN brands b ON m.brand_id = b.brand_id
                    ORDER BY b.brand_name, m.model_name
                ''')
                models = cursor.fetchall()
                
                # ดึงข้อมูล brands สำหรับ dropdown
                cursor.execute('SELECT * FROM brands ORDER BY brand_name')
                brands = cursor.fetchall()
                
                page = request.args.get('page')
                return render_template('admin/tire_form.html', models=models, brands=brands, tire=tire, page=page)
            
            # แปลง product_date เป็น None ถ้าเป็นสตริงว่างหรือสตริง 'None'
            if product_date == '' or product_date == 'None' or product_date == 'null':
                product_date = None
            
            # จัดการไฟล์รูปภาพ
            tire_image_url = None
            file = request.files.get('tire_image')
            print(f"Debug - File received: {file}")
            print(f"Debug - File filename: {file.filename if file else 'None'}")
            
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                print(f"Debug - Secure filename: {filename}")
                
                # สร้างโฟลเดอร์ถ้ายังไม่มี
                upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'tires')
                os.makedirs(upload_folder, exist_ok=True)
                print(f"Debug - Upload folder: {upload_folder}")
                
                # บันทึกไฟล์
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                print(f"Debug - File saved to: {file_path}")
                
                # ตรวจสอบว่าไฟล์ถูกบันทึกจริงหรือไม่
                if os.path.exists(file_path):
                    tire_image_url = filename
                    print(f"Debug - File successfully saved, tire_image_url: {tire_image_url}")
                else:
                    print(f"Debug - File was not saved successfully")
            else:
                print(f"Debug - File validation failed: file={file}, filename={file.filename if file else 'None'}, allowed={allowed_file(file.filename) if file and file.filename else 'False'}")
            
            # ประกอบ full_size
            full_size = ''
            if width and aspect_ratio:
                full_size = f"{width}/{aspect_ratio} "
            if (speed_symbol == 'Z' or high_speed_rating):
                full_size += 'ZR'
            if construction:
                full_size += f"{construction}"
            if rim_diameter:
                full_size += f"{rim_diameter} "
            if load_index:
                full_size += f"{load_index}"
            if speed_symbol and speed_symbol != 'Z':
                full_size += f"{speed_symbol} "
            else:
                full_size += ' '
            if service_description == 'XL':
                full_size = full_size.strip() + ' XL'
            else:
                full_size = full_size.strip()
            
            # อัปเดตข้อมูลยางรวมถึงรูปภาพ
            if tire_image_url:
                # ถ้ามีรูปภาพใหม่ ให้อัปเดตทั้งหมดรวมถึงรูปภาพ
                query = '''
                    UPDATE tires SET model_id=%s, width=%s, aspect_ratio=%s, construction=%s, rim_diameter=%s, load_index=%s, speed_symbol=%s, service_description=%s, high_speed_rating=%s, price_each=%s, price_set=%s, product_date=%s, full_size=%s, ply_rating=%s, tubeless_type=%s, tire_load_type=%s, tire_image_url=%s
                    WHERE tire_id=%s
                '''
                cursor.execute(query, (model_id, width, aspect_ratio, construction, rim_diameter, load_index, speed_symbol, service_description, high_speed_rating, price_each, price_set, product_date, full_size, ply_rating, tubeless_type, tire_load_type, tire_image_url, tire_id))
            else:
                # ถ้าไม่มีรูปภาพใหม่ ให้อัปเดตข้อมูลอื่นๆ โดยไม่เปลี่ยนรูปภาพ
                query = '''
                    UPDATE tires SET model_id=%s, width=%s, aspect_ratio=%s, construction=%s, rim_diameter=%s, load_index=%s, speed_symbol=%s, service_description=%s, high_speed_rating=%s, price_each=%s, price_set=%s, product_date=%s, full_size=%s, ply_rating=%s, tubeless_type=%s, tire_load_type=%s
                    WHERE tire_id=%s
                '''
                cursor.execute(query, (model_id, width, aspect_ratio, construction, rim_diameter, load_index, speed_symbol, service_description, high_speed_rating, price_each, price_set, product_date, full_size, ply_rating, tubeless_type, tire_load_type, tire_id))
            
            # แก้ไขชื่อไฟล์รูปภาพเก่าที่ไม่ถูกต้อง (ใช้ชื่อเดิม)
            cursor.execute('''
                UPDATE tires 
                SET tire_image_url = 'Michelin_AGILIS_3.png' 
                WHERE tire_image_url = 'Michelin AGILIS 3.png'
            ''')
            
            # แก้ไขชื่อไฟล์รูปภาพเก่าอื่นๆ ที่ไม่ถูกต้อง (ใช้ชื่อเดิม)
            cursor.execute('''
                UPDATE tires 
                SET tire_image_url = 'Michelin_ENERGY_XM2__EXM2.png' 
                WHERE tire_image_url = 'Michelin ENERGY XM2 +_EXM2+.png'
            ''')
            
            get_db().commit()
            flash('Tire updated successfully!')
            # --- คำนวณตำแหน่งแถวของยางที่เพิ่งแก้ไข ---
            per_page = 10
            # Query หาตำแหน่ง (row number) ของ tire_id ที่เพิ่งแก้ไข
            cursor.execute('''
                SELECT COUNT(*) AS rownum
                FROM tires t
                JOIN tire_models m ON t.model_id = m.model_id
                JOIN brands b ON m.brand_id = b.brand_id
                WHERE (FIELD(b.brand_name, 'michelin', 'BFgoodrich', 'Maxxis'), m.model_name) <
                      (SELECT FIELD(b2.brand_name, 'michelin', 'BFgoodrich', 'Maxxis'), m2.model_name
                       FROM tires t2
                       JOIN tire_models m2 ON t2.model_id = m2.model_id
                       JOIN brands b2 ON m2.brand_id = b2.brand_id
                       WHERE t2.tire_id = %s)
            ''', (tire_id,))
            rownum = cursor.fetchone()['rownum']
            page = (rownum // per_page) + 1
            return redirect(url_for('admin.tire_list', page=page))
            
        except Exception as e:
            print(f"Error updating tire: {e}")
            flash('เกิดข้อผิดพลาดในการอัปเดตข้อมูลยาง', 'error')
            # ดึงข้อมูล tire และ models สำหรับแสดงในฟอร์ม
            cursor.execute('''
                SELECT t.*, m.model_id, m.model_name, b.brand_id, b.brand_name
                FROM tires t
                JOIN tire_models m ON t.model_id = m.model_id
                JOIN brands b ON m.brand_id = b.brand_id
                WHERE t.tire_id=%s
            ''', (tire_id,))
            tire = cursor.fetchone()
            cursor.execute('''
                SELECT m.model_id, m.model_name, b.brand_name, b.brand_id
                FROM tire_models m
                JOIN brands b ON m.brand_id = b.brand_id
                ORDER BY b.brand_name, m.model_name
            ''')
            models = cursor.fetchall()
            
            # ดึงข้อมูล brands สำหรับ dropdown
            cursor.execute('SELECT * FROM brands ORDER BY brand_name')
            brands = cursor.fetchall()
            
            page = request.args.get('page')
            return render_template('admin/tire_form.html', models=models, brands=brands, tire=tire, page=page)
    # GET: fetch tire and all models
    cursor.execute('''
        SELECT t.*, m.model_id, m.model_name, b.brand_id, b.brand_name
        FROM tires t
        JOIN tire_models m ON t.model_id = m.model_id
        JOIN brands b ON m.brand_id = b.brand_id
        WHERE t.tire_id=%s
    ''', (tire_id,))
    tire = cursor.fetchone()
    if not tire:
        flash('Tire not found!')
        return redirect(url_for('admin.tire_list'))
    cursor.execute('''
        SELECT m.model_id, m.model_name, b.brand_name, b.brand_id
        FROM tire_models m
        JOIN brands b ON m.brand_id = b.brand_id
        ORDER BY b.brand_name, m.model_name
    ''')
    models = cursor.fetchall()
    
    # ดึงข้อมูล brands สำหรับ dropdown
    cursor.execute('SELECT * FROM brands ORDER BY brand_name')
    brands = cursor.fetchall()
    
    print(tire)
    page = request.args.get('page')
    return render_template('admin/tire_form.html', models=models, brands=brands, tire=tire, page=page)

@admin.route('/tires/delete/<int:tire_id>', methods=['POST'])
@admin_required
def delete_tire(tire_id):
    cursor = get_cursor()
    query = "DELETE FROM tires WHERE tire_id=%s"
    cursor.execute(query, (tire_id,))
    get_db().commit()
    flash('Tire deleted successfully!')
    return redirect(url_for('admin.tire_list'))

@admin.route('/customers')
@admin_required
def customer_list():
    cursor = get_cursor()
    search = request.args.get('search', '').strip()
    filter_by = request.args.get('filter', 'first_name')
    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page
    
    # สร้าง query สำหรับค้นหา
    query = '''
        SELECT c.*
        FROM customers c
        WHERE 1=1
    '''
    params = []
    
    if search:
        if filter_by == 'first_name':
            query += ' AND c.first_name LIKE %s'
            params.append(f'%{search}%')
        elif filter_by == 'last_name':
            query += ' AND c.last_name LIKE %s'
            params.append(f'%{search}%')
        elif filter_by == 'email':
            query += ' AND c.email LIKE %s'
            params.append(f'%{search}%')
        elif filter_by == 'phone':
            query += ' AND c.phone LIKE %s'
            params.append(f'%{search}%')
    
    # นับจำนวนทั้งหมด
    count_query = f"SELECT COUNT(*) as total FROM ({query}) as subquery"
    cursor.execute(count_query, params)
    total = cursor.fetchone()['total']
    total_pages = (total + per_page - 1) // per_page
    
    # เพิ่ม ORDER BY และ LIMIT
    query += ' ORDER BY c.customer_id DESC LIMIT %s OFFSET %s'
    params.extend([per_page, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    return render_template('admin/customer_list.html', 
                         rows=rows, 
                         search=search, 
                         filter_by=filter_by,
                         page=page, 
                         total_pages=total_pages)

@admin.route('/customers/add', methods=['GET', 'POST'])
@admin_required
def add_customer():
    cursor = get_cursor()
    if request.method == 'POST':
        # Debug: Print all form data
        print("=== DEBUG ADD CUSTOMER FORM DATA ===")
        for key, value in request.form.items():
            print(f"{key}: {value}")
        print("=====================================")
        
        # รับข้อมูลจากฟอร์ม
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        
        # ตรวจสอบข้อมูล
        if not all([first_name, last_name, phone]):
            flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'error')
            return render_template('admin/customer_form.html', 
                                 customer=None,
                                 form_data={
                                     'first_name': first_name,
                                     'last_name': last_name,
                                     'phone': phone,
                                     'email': email,
                                 })
        
        try:
            # เพิ่มลูกค้า
            cursor.execute('''
                INSERT INTO customers (first_name, last_name, phone, email) 
                VALUES (%s, %s, %s, %s)
            ''', (first_name, last_name, phone, email))
            
            customer_id = cursor.lastrowid
            
            
            get_db().commit()
            flash('เพิ่มลูกค้าสำเร็จ')
            return redirect(url_for('admin.customer_list'))
            
        except Exception as e:
            print(f"Error adding customer: {e}")
            flash('เกิดข้อผิดพลาดในการเพิ่มลูกค้า', 'error')
            return render_template('admin/customer_form.html', 
                                 customer=None,
                                 form_data={
                                     'first_name': first_name,
                                     'last_name': last_name,
                                     'phone': phone,
                                     'email': email,
                                 })
    
    # สร้างรายการจังหวัด
    provinces = ['กรุงเทพมหานคร', 'กระบี่', 'กาญจนบุรี', 'กาฬสินธุ์', 'กำแพงเพชร', 'ขอนแก่น', 'จันทบุรี', 'ฉะเชิงเทรา', 'ชลบุรี', 'ชัยนาท', 'ชัยภูมิ', 'ชุมพร', 'เชียงราย', 'เชียงใหม่', 'ตรัง', 'ตราด', 'ตาก', 'นครนายก', 'นครปฐม', 'นครพนม', 'นครราชสีมา', 'นครศรีธรรมราช', 'นครสวรรค์', 'นนทบุรี', 'นราธิวาส', 'น่าน', 'บึงกาฬ', 'บุรีรัมย์', 'ปทุมธานี', 'ประจวบคีรีขันธ์', 'ปราจีนบุรี', 'ปัตตานี', 'พระนครศรีอยุธยา', 'พังงา', 'พัทลุง', 'พิจิตร', 'พิษณุโลก', 'เพชรบุรี', 'เพชรบูรณ์', 'แพร่', 'พะเยา', 'ภูเก็ต', 'มหาสารคาม', 'มุกดาหาร', 'แม่ฮ่องสอน', 'ยะลา', 'ยโสธร', 'ร้อยเอ็ด', 'ระนอง', 'ระยอง', 'ราชบุรี', 'ลพบุรี', 'ลำปาง', 'ลำพูน', 'เลย', 'ศรีสะเกษ', 'สกลนคร', 'สงขลา', 'สตูล', 'สมุทรปราการ', 'สมุทรสงคราม', 'สมุทรสาคร', 'สระแก้ว', 'สระบุรี', 'สิงห์บุรี', 'สุโขทัย', 'สุพรรณบุรี', 'สุราษฎร์ธานี', 'สุรินทร์', 'หนองคาย', 'หนองบัวลำภู', 'อ่างทอง', 'อุดรธานี', 'อุทัยธานี', 'อุตรดิตถ์', 'อุบลราชธานี', 'อำนาจเจริญ']
    
    return render_template('admin/customer_form.html', customer=None, provinces=provinces)

@admin.route('/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
@admin_required
def edit_customer(customer_id):
    cursor = get_cursor()
    cursor.execute('SELECT * FROM customers WHERE customer_id=%s', (customer_id,))
    customer = cursor.fetchone()
    if not customer:
        flash('Customer not found!')
        return redirect(url_for('admin.customer_list'))
    # ดึงรถยนต์ทั้งหมดของลูกค้า
    cursor.execute('''SELECT * FROM vehicles WHERE customer_id=%s''', (customer_id,))
    vehicles = cursor.fetchall() or []
    # โหลด brands เพื่อ map brand_name -> brand_id
    with open('static/data/vehicle_brands_models.json', encoding='utf-8') as f:
        brands_data = json.load(f)
    brand_name_to_id = {b['brand_name']: b['brand_id'] for b in brands_data['brands']}
    # เพิ่ม brand_id ให้แต่ละ vehicle
    for v in vehicles:
        v['brand_id'] = brand_name_to_id.get(v['brand_name'], '')
        # Ensure vehicle_type_id is a string for comparison
        if v.get('vehicle_type_id'):
            v['vehicle_type_id'] = str(v['vehicle_type_id'])
    if request.method == 'POST':
        # Debug: print all form keys and values
        print("=== DEBUG EDIT CUSTOMER FORM DATA ===")
        for key, value in request.form.items():
            print(f"{key}: {value}")
        print("=====================================")
        # อัปเดตข้อมูลลูกค้า
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone = request.form['phone']
        email = request.form['email']
        cursor.execute('''UPDATE customers SET first_name=%s, last_name=%s, phone=%s, email=%s WHERE customer_id=%s''',
            (first_name, last_name, phone, email, customer_id))
        # --- Vehicles: เพิ่ม/ลบ/แก้ไข ---
        print('DEBUG: Processing vehicles in edit mode...')
        
        get_db().commit()
        flash('อัปเดตข้อมูลลูกค้าสำเร็จ')
        return redirect(url_for('admin.customer_list'))
    
    # GET request - แสดงฟอร์มแก้ไข
    # สร้างรายการจังหวัด
    provinces = ['กรุงเทพมหานคร', 'กระบี่', 'กาญจนบุรี', 'กาฬสินธุ์', 'กำแพงเพชร', 'ขอนแก่น', 'จันทบุรี', 'ฉะเชิงเทรา', 'ชลบุรี', 'ชัยนาท', 'ชัยภูมิ', 'ชุมพร', 'เชียงราย', 'เชียงใหม่', 'ตรัง', 'ตราด', 'ตาก', 'นครนายก', 'นครปฐม', 'นครพนม', 'นครราชสีมา', 'นครศรีธรรมราช', 'นครสวรรค์', 'นนทบุรี', 'นราธิวาส', 'น่าน', 'บึงกาฬ', 'บุรีรัมย์', 'ปทุมธานี', 'ประจวบคีรีขันธ์', 'ปราจีนบุรี', 'ปัตตานี', 'พระนครศรีอยุธยา', 'พังงา', 'พัทลุง', 'พิจิตร', 'พิษณุโลก', 'เพชรบุรี', 'เพชรบูรณ์', 'แพร่', 'พะเยา', 'ภูเก็ต', 'มหาสารคาม', 'มุกดาหาร', 'แม่ฮ่องสอน', 'ยะลา', 'ยโสธร', 'ร้อยเอ็ด', 'ระนอง', 'ระยอง', 'ราชบุรี', 'ลพบุรี', 'ลำปาง', 'ลำพูน', 'เลย', 'ศรีสะเกษ', 'สกลนคร', 'สงขลา', 'สตูล', 'สมุทรปราการ', 'สมุทรสงคราม', 'สมุทรสาคร', 'สระแก้ว', 'สระบุรี', 'สิงห์บุรี', 'สุโขทัย', 'สุพรรณบุรี', 'สุราษฎร์ธานี', 'สุรินทร์', 'หนองคาย', 'หนองบัวลำภู', 'อ่างทอง', 'อุดรธานี', 'อุทัยธานี', 'อุตรดิตถ์', 'อุบลราชธานี', 'อำนาจเจริญ']
    
    return render_template('admin/customer_form.html', 
                         customer=customer, 
                         vehicles=vehicles,
                         provinces=provinces)

@admin.route('/customers/delete/<int:customer_id>', methods=['GET', 'POST'])
@admin_required
def delete_customer(customer_id):
    cursor = get_cursor()
    # ลบ booking_items ที่เกี่ยวข้องกับ bookings ของลูกค้านี้
    cursor.execute('SELECT booking_id FROM bookings WHERE customer_id=%s', (customer_id,))
    booking_ids = [row['booking_id'] for row in cursor.fetchall()]
    if booking_ids:
        format_strings = ','.join(['%s'] * len(booking_ids))
        # ลบ service_tires ที่เกี่ยวข้องกับ bookings ของลูกค้านี้
        cursor.execute(f'DELETE FROM service_tires WHERE booking_id IN ({format_strings})', tuple(booking_ids))
        cursor.execute(f'DELETE FROM booking_items WHERE booking_id IN ({format_strings})', tuple(booking_ids))
    # ลบ bookings ของลูกค้านี้
    cursor.execute('DELETE FROM bookings WHERE customer_id=%s', (customer_id,))
    # ลบ service_record_items ที่เกี่ยวข้องกับ service_records ของรถลูกค้านี้
    cursor.execute('SELECT vehicle_id FROM vehicles WHERE customer_id=%s', (customer_id,))
    vehicle_ids = [row['vehicle_id'] for row in cursor.fetchall()]
    if vehicle_ids:
        format_strings = ','.join(['%s'] * len(vehicle_ids))
        cursor.execute(f'SELECT service_record_id FROM service_records WHERE vehicle_id IN ({format_strings})', tuple(vehicle_ids))
        sr_ids = [row['service_record_id'] for row in cursor.fetchall()]
        if sr_ids:
            format_sr = ','.join(['%s'] * len(sr_ids))
            cursor.execute(f'DELETE FROM service_record_items WHERE service_record_id IN ({format_sr})', tuple(sr_ids))
        # ลบ service_records ของรถลูกค้านี้
        cursor.execute(f'DELETE FROM service_records WHERE vehicle_id IN ({format_strings})', tuple(vehicle_ids))
        # ลบ vehicles ของลูกค้านี้
        cursor.execute(f'DELETE FROM vehicles WHERE customer_id=%s', (customer_id,))
    
    # ดึง user_id ของลูกค้าก่อนลบ
    cursor.execute('SELECT user_id FROM customers WHERE customer_id=%s', (customer_id,))
    customer = cursor.fetchone()
    user_id = customer['user_id'] if customer else None
    
    # ลบ customers
    cursor.execute('DELETE FROM customers WHERE customer_id=%s', (customer_id,))
    
    # ลบ users ที่เกี่ยวข้องกับลูกค้า
    if user_id:
        cursor.execute('DELETE FROM users WHERE user_id=%s', (user_id,))
    
    get_db().commit()
    flash('ลบลูกค้าสำเร็จ')
    return redirect(url_for('admin.customer_list'))

@admin.route('/check-queue')
@admin_required
def check_queue():
    """หน้าเช็คสถานะคิว"""
    return render_template('admin/check_queue.html')

@admin.route('/check-queue-detail')
@admin_required
def check_queue_detail():
    """หน้ารายละเอียดคิว"""
    return render_template('admin/check_queue_detail.html')

@admin.route('/bookings')
@admin_required
def booking_list():
    cursor = get_cursor()
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page
    
    # สร้าง query สำหรับนับจำนวนทั้งหมด
    count_query = '''SELECT COUNT(*) as total
                     FROM bookings b
                     JOIN customers c ON b.customer_id = c.customer_id
                     JOIN vehicles v ON b.vehicle_id = v.vehicle_id'''
    count_params = []
    where_conditions = []
    
    if search:
        where_conditions.append("(c.first_name LIKE %s OR c.last_name LIKE %s OR v.license_plate LIKE %s)")
        search_param = f"%{search}%"
        count_params.extend([search_param, search_param, search_param])
    
    if status_filter:
        where_conditions.append("b.status = %s")
        count_params.append(status_filter)
    
    if where_conditions:
        count_query += " WHERE " + " AND ".join(where_conditions)
    
    cursor.execute(count_query, count_params)
    total = cursor.fetchone()['total']
    total_pages = (total + per_page - 1) // per_page
    
    # สร้าง query สำหรับดึงข้อมูลพร้อม pagination
    query = '''SELECT b.booking_id, b.service_date, b.service_time, b.status, c.first_name, c.last_name, v.license_plate, v.license_province
               FROM bookings b
               JOIN customers c ON b.customer_id = c.customer_id
               JOIN vehicles v ON b.vehicle_id = v.vehicle_id'''
    params = []
    
    if where_conditions:
        query += " WHERE " + " AND ".join(where_conditions)
    
    query += " ORDER BY b.booking_date DESC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    
    cursor.execute(query, params)
    bookings = cursor.fetchall()
    
    # ดึงรายการบริการสำหรับทุก booking ในครั้งเดียว (แก้ปัญหา N+1 query)
    if bookings:
        booking_ids = [str(booking['booking_id']) for booking in bookings]
        booking_ids_str = ','.join(booking_ids)
        
        cursor.execute(f'''
            SELECT bi.booking_id, bi.item_id, bi.service_id, bi.quantity, 
                   s.service_name, s.category,
                   GROUP_CONCAT(so.option_name SEPARATOR ', ') as options
            FROM booking_items bi
            JOIN services s ON bi.service_id = s.service_id
            LEFT JOIN booking_item_options bio ON bi.item_id = bio.item_id
            LEFT JOIN service_options so ON bio.option_id = so.option_id
            WHERE bi.booking_id IN ({booking_ids_str})
            GROUP BY bi.booking_id, bi.item_id, bi.service_id, bi.quantity, s.service_name, s.category
        ''')
        services_data = cursor.fetchall()
        
        # จัดกลุ่มข้อมูลบริการตาม booking_id
        services_by_booking = {}
        for service in services_data:
            booking_id = service['booking_id']
            if booking_id not in services_by_booking:
                services_by_booking[booking_id] = []
            services_by_booking[booking_id].append(service)
        
        # เพิ่มข้อมูลบริการให้กับแต่ละ booking
        for booking in bookings:
            booking_id = booking['booking_id']
            booking['services'] = services_by_booking.get(booking_id, [])
            booking['service_options'] = {}
    
    # สถานะที่ใช้ได้
    statuses = ['รอดำเนินการ', 'สำเร็จ', 'ยกเลิก']
    
    return render_template('admin/booking_list.html', 
                         bookings=bookings, 
                         search=search, 
                         status_filter=status_filter,
                         statuses=statuses,
                         page=page,
                         total_pages=total_pages)

@admin.route('/bookings/update-status/<int:booking_id>', methods=['POST'])
@admin_required
def update_booking_status(booking_id):
    cursor = get_cursor()
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status:
        cursor.execute('UPDATE bookings SET status = %s WHERE booking_id = %s', (new_status, booking_id))
        get_db().commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Invalid status'}), 400

@admin.route('/bookings/add', methods=['GET', 'POST'])
@admin_required
def add_booking():
    cursor = get_cursor()
    if request.method == 'POST':
        try:
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
            
            get_db().commit()
            flash('เพิ่มการจองสำเร็จ')
            return redirect(url_for('admin.booking_list'))
        except Exception as e:
            print(f"Error adding booking: {e}")
            flash('เกิดข้อผิดพลาดในการเพิ่มการจอง', 'error')
            # ดึงข้อมูลสำหรับแสดงฟอร์มใหม่
            cursor.execute('SELECT * FROM customers ORDER BY first_name, last_name')
            customers = cursor.fetchall()
            
            cursor.execute('SELECT * FROM vehicles ORDER BY license_plate')
            vehicles = cursor.fetchall()
            
            cursor.execute('SELECT * FROM services ORDER BY service_name')
            services = cursor.fetchall()
            
            cursor.execute('SELECT * FROM vehicle_types')
            vehicle_types = cursor.fetchall()
            
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
            
            return render_template('admin/booking_form.html', 
                                 booking=None,
                                 customers=customers,
                                 vehicles=vehicles,
                                 services=services,
                                 service_groups=service_groups,
                                 brands=brands,
                                 tire_models=tire_models,
                                 vehicle_types=vehicle_types,
                                 vehicle_brands=vehicle_brands,
                                 provinces=provinces)
    
    # GET request - แสดงฟอร์มเพิ่มการจอง
    # ดึงข้อมูลสำหรับฟอร์ม
    cursor.execute('SELECT * FROM customers ORDER BY first_name, last_name')
    customers = cursor.fetchall()
    
    cursor.execute('SELECT * FROM vehicles ORDER BY license_plate')
    vehicles = cursor.fetchall()
    
    cursor.execute('SELECT * FROM services ORDER BY service_name')
    services = cursor.fetchall()
    
    cursor.execute('SELECT * FROM vehicle_types')
    vehicle_types = cursor.fetchall()
    
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
    
    return render_template('admin/booking_form.html', 
                         booking=None,
                         customers=customers,
                         vehicles=vehicles,
                         services=services,
                         service_groups=service_groups,
                         brands=brands,
                         tire_models=tire_models,
                         vehicle_types=vehicle_types,
                         vehicle_brands=vehicle_brands,
                         provinces=provinces)

@admin.route('/bookings/edit/<int:booking_id>', methods=['GET', 'POST'])
@admin_required
def edit_booking(booking_id):
    cursor = get_cursor()
    # ----------------------
    # ดึงข้อมูล booking หลัก
    # ----------------------
    cursor.execute('''
        SELECT b.booking_id, b.booking_date, b.service_date, b.service_time, b.status, b.note,
               c.first_name, c.last_name, c.phone, c.email,
               v.vehicle_id, v.license_plate, v.license_province, v.color, v.production_year,
               v.brand_name, v.model_name, v.engine_type_name, v.vehicle_type_id
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        WHERE b.booking_id = %s
    ''', (booking_id,))
    booking = cursor.fetchone()
    
    if not booking:
        flash('ไม่พบข้อมูลการจอง')
        return redirect(url_for('admin.booking_list'))
    
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
            return redirect(url_for('admin.edit_booking', booking_id=booking_id))
        
        # ถ้าไม่มี service_time ให้ใช้ค่าเริ่มต้น
        if not service_time:
            service_time = '09:00'
        
        cursor.execute('''
            UPDATE bookings 
            SET service_date = %s, service_time = %s, status = %s, note = %s 
            WHERE booking_id = %s
        ''', (service_date, service_time, status, note, booking_id))
        
        # อัปเดตข้อมูลรถในตาราง vehicles
        vehicle_id = booking['vehicle_id']
        license_plate = request.form.get('license_plate', '').strip()
        license_province = request.form.get('license_province', '').strip()
        brand_name = request.form.get('brand_name', '').strip()
        model_name = request.form.get('model_name', '').strip()
        color = request.form.get('color', '').strip()
        production_year = request.form.get('production_year', '').strip()
        vehicle_type_id = request.form.get('vehicle_type_id', '').strip()
        
        print(f"Debug: Updating vehicle {vehicle_id} with:")
        print(f"  license_plate: {license_plate}")
        print(f"  license_province: {license_province}")
        print(f"  brand_name: '{brand_name}' (type: {type(brand_name)})")
        print(f"  model_name: '{model_name}' (type: {type(model_name)})")
        print(f"  color: {color}")
        print(f"  production_year: {production_year}")
        print(f"  vehicle_type_id: {vehicle_type_id}")
        
        # ตรวจสอบว่าข้อมูลยี่ห้อและรุ่นไม่เป็นค่าว่าง
        if not brand_name or brand_name.strip() == '':
            print("WARNING: brand_name is empty!")
        if not model_name or model_name.strip() == '':
            print("WARNING: model_name is empty!")
        
        cursor.execute('''
            UPDATE vehicles 
            SET license_plate = %s, license_province = %s, brand_name = %s, 
                model_name = %s, color = %s, production_year = %s, vehicle_type_id = %s
            WHERE vehicle_id = %s
        ''', (license_plate, license_province, brand_name, model_name, 
              color, production_year, vehicle_type_id, vehicle_id))
        
        print(f"Debug: Vehicle {vehicle_id} updated successfully")
        
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
            return redirect(url_for('admin.booking_list'))
        except Exception as e:
            print(f"Debug: Error committing changes: {e}")
            get_db().rollback()
            flash('เกิดข้อผิดพลาดในการบันทึกข้อมูล', 'error')
            return redirect(url_for('admin.edit_booking', booking_id=booking_id))
    
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
    print(f"Debug: Available brands: {[(b['brand_id'], b['brand_name']) for b in brands]}")
    
    cursor.execute('SELECT * FROM tire_models ORDER BY model_name')
    tire_models = cursor.fetchall()
    print(f"Debug: Available tire models: {[(m['model_id'], m['model_name']) for m in tire_models]}")
    
    # ดึงข้อมูลยี่ห้อรถ
    cursor.execute('SELECT * FROM car_brands ORDER BY car_brand_name')
    vehicle_brands = cursor.fetchall()
    
    # ดึงข้อมูลรุ่นรถตามยี่ห้อรถที่เลือกไว้
    car_models = []
    if booking and booking.get('brand_name'):
        # หา brand_id จาก brand_name
        brand_id = None
        for brand in vehicle_brands:
            if brand['car_brand_name'] == booking['brand_name']:
                brand_id = brand['car_brand_id']
                break
        
        if brand_id:
            cursor.execute('SELECT * FROM car_models WHERE car_brand_id = %s ORDER BY car_model_name', (brand_id,))
            car_models = cursor.fetchall()
            print(f"Debug: Found {len(car_models)} car models for brand {booking['brand_name']} (ID: {brand_id})")
            print(f"Debug: Car models: {[(m['car_model_id'], m['car_model_name']) for m in car_models]}")
            print(f"Debug: Booking model_name: '{booking.get('model_name')}'")
            print(f"Debug: Booking model_name type: {type(booking.get('model_name'))}")
            
            # ตรวจสอบว่ารุ่นรถที่เลือกไว้มีอยู่ในรายการหรือไม่
            selected_model = booking.get('model_name')
            if selected_model:
                model_found = False
                for model in car_models:
                    if model['car_model_name'] == selected_model:
                        model_found = True
                        print(f"Debug: Selected model '{selected_model}' found in car_models")
                        break
                if not model_found:
                    print(f"Debug: Selected model '{selected_model}' NOT found in car_models")
                    print(f"Debug: Available models: {[m['car_model_name'] for m in car_models]}")
        else:
            print(f"Debug: Brand ID not found for brand name: {booking['brand_name']}")
    else:
        print("Debug: No brand_name in booking data")
    
    # ดึงข้อมูลยางที่มีอยู่แล้ว
    cursor.execute('SELECT * FROM service_tires WHERE booking_id = %s ORDER BY position', (booking_id,))
    existing_tires = cursor.fetchall()
    print(f"Debug: Found {len(existing_tires)} existing tires for booking {booking_id}")
    
    # จัดกลุ่มข้อมูลยางตามตำแหน่ง
    tire_data = {}
    if existing_tires:
        # ถ้า position เป็นค่าว่าง ให้กำหนดตำแหน่งตามลำดับ
        positions = ['front_left', 'front_right', 'rear_left', 'rear_right']
        for i, tire in enumerate(existing_tires):
            print(f"Debug: Tire {i}: id={tire['id']}, position='{tire['position']}', brand='{tire['brand']}', model='{tire['model']}', size='{tire['size']}'")
            if tire['position'] and tire['position'].strip():  # ถ้ามี position อยู่แล้ว
                position_mapping = {
                    'FL': 'front_left',
                    'FR': 'front_right', 
                    'RL': 'rear_left',
                    'RR': 'rear_right'
                }
                new_position = position_mapping.get(tire['position'], tire['position'])
                tire_data[new_position] = tire
                print(f"Debug: Added tire to {new_position}")
            else:  # ถ้า position เป็นค่าว่าง ให้กำหนดตามลำดับ
                tire_data[positions[i]] = tire
                # อัปเดต position ในฐานข้อมูลด้วย
                cursor.execute('UPDATE service_tires SET position = %s WHERE id = %s', (positions[i], tire['id']))
                print(f"Updated tire ID {tire['id']} to position '{positions[i]}'")  # Debug print
                get_db().commit()  # Commit การเปลี่ยนแปลง
    
    print(f"Debug: Final tire_data keys: {list(tire_data.keys())}")
    for pos, tire in tire_data.items():
        print(f"Debug: {pos}: brand='{tire['brand']}', model='{tire['model']}'")
        # หา brand_id ที่ตรงกับ brand name
        for brand in brands:
            if brand['brand_name'] == tire['brand']:
                tire['brand_id'] = brand['brand_id']
                print(f"Debug: Found brand_id {brand['brand_id']} for brand '{tire['brand']}'")
                break
        # หา model_id ที่ตรงกับ model name
        for model in tire_models:
            if model['model_name'] == tire['model']:
                tire['model_id'] = model['model_id']
                print(f"Debug: Found model_id {model['model_id']} for model '{tire['model']}'")
                break
    
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
    
    # ดึงรายการจังหวัด
    provinces = ['กรุงเทพมหานคร', 'กระบี่', 'กาญจนบุรี', 'กาฬสินธุ์', 'กำแพงเพชร', 'ขอนแก่น', 'จันทบุรี', 'ฉะเชิงเทรา', 'ชลบุรี', 'ชัยนาท', 'ชัยภูมิ', 'ชุมพร', 'เชียงราย', 'เชียงใหม่', 'ตรัง', 'ตราด', 'ตาก', 'นครนายก', 'นครปฐม', 'นครพนม', 'นครราชสีมา', 'นครศรีธรรมราช', 'นครสวรรค์', 'นนทบุรี', 'นราธิวาส', 'น่าน', 'บึงกาฬ', 'บุรีรัมย์', 'ปทุมธานี', 'ประจวบคีรีขันธ์', 'ปราจีนบุรี', 'ปัตตานี', 'พระนครศรีอยุธยา', 'พังงา', 'พัทลุง', 'พิจิตร', 'พิษณุโลก', 'เพชรบุรี', 'เพชรบูรณ์', 'แพร่', 'พะเยา', 'ภูเก็ต', 'มหาสารคาม', 'มุกดาหาร', 'แม่ฮ่องสอน', 'ยะลา', 'ยโสธร', 'ร้อยเอ็ด', 'ระนอง', 'ระยอง', 'ราชบุรี', 'ลพบุรี', 'ลำปาง', 'ลำพูน', 'เลย', 'ศรีสะเกษ', 'สกลนคร', 'สงขลา', 'สตูล', 'สมุทรปราการ', 'สมุทรสงคราม', 'สมุทรสาคร', 'สระแก้ว', 'สระบุรี', 'สิงห์บุรี', 'สุโขทัย', 'สุพรรณบุรี', 'สุราษฎร์ธานี', 'สุรินทร์', 'หนองคาย', 'หนองบัวลำภู', 'อ่างทอง', 'อุดรธานี', 'อุทัยธานี', 'อุตรดิตถ์', 'อุบลราชธานี', 'อำนาจเจริญ']
    
    return render_template('admin/booking_form.html', 
                         booking=booking,
                         vehicle_types=vehicle_types,
                         services=services,
                         service_groups=service_groups,
                         brands=brands,
                         tire_models=tire_models,
                         vehicle_brands=vehicle_brands,
                         car_models=car_models,
                         provinces=provinces,
                         selected_services=selected_services,
                         selected_service_ids=selected_service_ids,
                         selected_options=selected_options,
                         selected_option_ids=selected_option_ids,
                         tire_data=tire_data)

@admin.route('/bookings/delete/<int:booking_id>', methods=['POST'])
@admin_required
def delete_booking(booking_id):
    cursor = get_cursor()
    cursor.execute('DELETE FROM booking_items WHERE booking_id=%s', (booking_id,))
    cursor.execute('DELETE FROM bookings WHERE booking_id=%s', (booking_id,))
    get_db().commit()
    flash('ลบการจองสำเร็จ')
    return redirect(url_for('admin.booking_list'))

@admin.route('/service_records/edit/<int:service_record_id>', methods=['GET', 'POST'])
@admin_required
def edit_service_record(service_record_id):
    cursor = get_cursor()
    # ดึง customer_id ของ service record นี้
    cursor.execute('SELECT v.customer_id FROM service_records sr JOIN vehicles v ON sr.vehicle_id = v.vehicle_id WHERE sr.service_record_id=%s', (service_record_id,))
    row = cursor.fetchone()
    if not row:
        flash('Service record not found!')
        return redirect(url_for('admin.customer_list'))
    customer_id = row['customer_id']
    if request.method == 'POST':
        # ตัวอย่าง: อัปเดตสถานะและหมายเหตุ
        status = request.form['status']
        note = request.form['note']
        cursor.execute('UPDATE service_records SET status=%s, note=%s WHERE service_record_id=%s', (status, note, service_record_id))
        get_db().commit()
        flash('Service record updated successfully!')
        return redirect(url_for('admin.customer_list'))
    # GET: fetch service record
    cursor.execute('SELECT * FROM service_records WHERE service_record_id=%s', (service_record_id,))
    record = cursor.fetchone()
    return render_template('admin/service_record_form.html', record=record)

@admin.route('/customers/<int:customer_id>/bookings')
@admin_required
def customer_bookings(customer_id):
    cursor = get_cursor()
    # ดึง bookings ของลูกค้า
    cursor.execute('''
        SELECT booking_id, booking_date, appointment_date, note, status
        FROM bookings
        WHERE customer_id = %s
        ORDER BY booking_date DESC
    ''', (customer_id,))
    bookings = cursor.fetchall()
    # ดึงบริการแต่ละ booking
    for b in bookings:
        cursor.execute('''
            SELECT s.service_name FROM booking_items bi
            JOIN services s ON bi.service_id = s.service_id
            WHERE bi.booking_id = %s
        ''', (b['booking_id'],))
        b['services'] = [row['service_name'] for row in cursor.fetchall()]
    return render_template('admin/customer_bookings.html', bookings=bookings, customer_id=customer_id)

@admin.route('/service-records')
@admin_required
def service_record_list():
    cursor = get_cursor()
    customer_id = request.args.get('customer_id', type=int)
    records = []
    if customer_id:
        # ดึง service_records ของรถลูกค้าคนนี้
        cursor.execute('''
            SELECT sr.service_record_id, sr.service_date, v.license_plate
            FROM service_records sr
            JOIN vehicles v ON sr.vehicle_id = v.vehicle_id
            WHERE v.customer_id = %s
            ORDER BY sr.service_date DESC
        ''', (customer_id,))
        records = cursor.fetchall()
        for r in records:
            # ดึงบริการแต่ละ service_record (ผ่าน booking_items -> services)
            cursor.execute('''
                SELECT s.service_name FROM service_record_items sri
                JOIN services s ON sri.service_id = s.service_id
                WHERE sri.service_record_id = %s
            ''', (r['service_record_id'],))
            r['services'] = [row['service_name'] for row in cursor.fetchall()]
    return render_template('admin/service_record_list.html', records=records, customer_id=customer_id)

@admin.route('/profile', methods=['GET', 'POST'])
@admin_required
def admin_profile():
    if not session.get('admin_user_id') or session.get('role') != 'admin':
        return redirect(url_for('auth.login'))
    
    # ดึงข้อมูลผู้ใช้
    cursor = get_cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = %s', (session.get('admin_user_id'),))
    user = cursor.fetchone()
    
    if not user:
        flash('ไม่พบข้อมูลผู้ใช้')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        try:
            # จัดการไฟล์รูปภาพ
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and file.filename != '':
                    # ตรวจสอบนามสกุลไฟล์
                    if allowed_file(file.filename):
                        # สร้างชื่อไฟล์ใหม่
                        timestamp = int(datetime.now().timestamp() * 1000)
                        filename = f"{session.get('admin_user_id')}_{timestamp}_{secure_filename(file.filename)}"
                        
                        # บันทึกไฟล์
                        file_path = os.path.join(current_app.config['PROFILE_UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        
                        # ลบไฟล์เก่าถ้ามี
                        if user.get('avatar_filename'):
                            old_file_path = os.path.join(current_app.config['PROFILE_UPLOAD_FOLDER'], user['avatar_filename'])
                            if os.path.exists(old_file_path):
                                os.remove(old_file_path)
                        
                        # อัปเดตฐานข้อมูล
                        cursor.execute('UPDATE users SET avatar_filename = %s WHERE user_id = %s', 
                                      (filename, session.get('admin_user_id')))
                        get_db().commit()
                        
                        # อัปเดต session
                        session['avatar'] = filename
                        flash('อัปเดตรูปโปรไฟล์สำเร็จ', 'success')
                        
                        # รีเฟรชข้อมูลผู้ใช้
                        cursor.execute('SELECT * FROM users WHERE user_id = %s', (session.get('admin_user_id'),))
                        user = cursor.fetchone()
                    else:
                        flash('นามสกุลไฟล์ไม่ถูกต้อง กรุณาใช้ไฟล์ JPG, PNG เท่านั้น', 'error')
            
            # อัปเดตข้อมูลส่วนตัว
            name = request.form.get('name', '').strip()
            if name:
                cursor.execute('UPDATE users SET name = %s WHERE user_id = %s', (name, session.get('admin_user_id')))
                get_db().commit()
                session['name'] = name
                flash('อัปเดตข้อมูลสำเร็จ', 'success')
                
                # รีเฟรชข้อมูลผู้ใช้
                cursor.execute('SELECT * FROM users WHERE user_id = %s', (session.get('admin_user_id'),))
                user = cursor.fetchone()
                
        except Exception as e:
            flash('เกิดข้อผิดพลาดในการอัปเดตข้อมูล', 'error')
        
        # Redirect หลัง submit เพื่อป้องกัน form resubmission warning
        return redirect(url_for('admin.admin_profile'))
    
    return render_template('admin/profile.html', user=user)



@admin.route('/change-password', methods=['GET', 'POST'])
@admin_required
def admin_change_password():
    if not session.get('user'):
        return redirect(url_for('auth.login'))  # ใช้ route login เดียวกัน
    
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('รหัสผ่านใหม่ไม่ตรงกัน')
            return redirect(url_for('admin.admin_change_password'))
        
        # ตรวจสอบรหัสผ่านปัจจุบัน
        cursor = get_cursor()
        cursor.execute('SELECT password_hash FROM users WHERE user_id = %s', (session.get('user_id'),))
        user = cursor.fetchone()
        
        if not user:
            flash('ไม่พบข้อมูลผู้ใช้')
            return redirect(url_for('auth.login'))
        
        # อัปเดตรหัสผ่าน
        from werkzeug.security import generate_password_hash
        new_password_hash = generate_password_hash(new_password, method='scrypt')
        
        cursor.execute('UPDATE users SET password_hash = %s WHERE user_id = %s', 
                      (new_password_hash, session.get('user_id')))
        get_db().commit()
        
        flash('เปลี่ยนรหัสผ่านสำเร็จ')
        return redirect(url_for('admin.admin_profile'))
    
    return render_template('admin/change_password.html')

@admin.route('/edit-profile', methods=['GET', 'POST'])
@admin_required
def admin_edit_profile():
    if not session.get('user'):
        return redirect(url_for('auth.login'))
    
    cursor = get_cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = %s', (session.get('user_id'),))
    user = cursor.fetchone()
    
    if not user:
        flash('ไม่พบข้อมูลผู้ใช้')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form.get('email', '')
        
        cursor.execute('UPDATE users SET name = %s WHERE user_id = %s', (name, session.get('user_id')))
        get_db().commit()
        
        session['name'] = name
        flash('อัปเดตข้อมูลสำเร็จ')
        return redirect(url_for('admin.admin_profile'))
    
    return render_template('admin/edit_profile.html', user=user)

@admin.route('/users')
@admin_required
def user_list():
    # รับพารามิเตอร์การค้นหา
    search = request.args.get('search', '').strip()
    filter_by = request.args.get('filter_by', 'all')
    
    cursor = get_cursor()
    
    # สร้าง query พื้นฐาน
    base_query = """
        SELECT u.user_id, u.username, u.name, u.role_name, u.created_at
        FROM users u
        WHERE 1=1
    """
    params = []
    
    # เพิ่มเงื่อนไขการค้นหา
    if search and filter_by != 'all':
        if filter_by == 'username':
            base_query += " AND u.username LIKE %s"
            params.append(f"%{search}%")
        elif filter_by == 'name':
            base_query += " AND u.name LIKE %s"
            params.append(f"%{search}%")
        elif filter_by == 'role':
            base_query += " AND u.role_name LIKE %s"
            params.append(f"%{search}%")
    elif search and filter_by == 'all':
        # ค้นหาทั้งหมด
        base_query += " AND (u.username LIKE %s OR u.name LIKE %s OR u.role_name LIKE %s)"
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern, search_pattern])
    
    # เพิ่ม ORDER BY
    base_query += " ORDER BY u.created_at DESC"
    
    # Execute query
    cursor.execute(base_query, params)
    users = cursor.fetchall()
    
    return render_template('admin/user_list.html', 
                         users=users, 
                         search=search, 
                         filter_by=filter_by)

@admin.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    cursor = get_cursor()
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', '')
        
        # ตรวจสอบข้อมูล
        if not all([username, password, first_name, last_name, role]):
            error = 'กรุณากรอกข้อมูลให้ครบถ้วน'
            return render_template('admin/user_form.html', 
                                 user=None, 
                                 error=error,
                                 form_data={
                                     'username': username,
                                     'first_name': first_name,
                                     'last_name': last_name,
                                     'email': email,
                                     'role': role
                                 })
        
        cursor.execute('SELECT * FROM users WHERE username=%s', (username,))
        if cursor.fetchone():
            error = 'Username already exists.'
            return render_template('admin/user_form.html', 
                                 user=None, 
                                 error=error,
                                 form_data={
                                     'username': username,
                                     'first_name': first_name,
                                     'last_name': last_name,
                                     'email': email,
                                     'role': role
                                 })
        else:
            try:
                from werkzeug.security import generate_password_hash
                password_hash = generate_password_hash(password, method='scrypt')
                
                # สร้างชื่อเต็มสำหรับตาราง users
                full_name = f"{first_name} {last_name}"
                
                # เพิ่มข้อมูลลงตาราง users
                cursor.execute('INSERT INTO users (username, password_hash, name, role_name) VALUES (%s, %s, %s, %s)', 
                             (username, password_hash, full_name, role))
                user_id = cursor.lastrowid
                
                # ถ้าเป็น customer ให้เพิ่มข้อมูลลงตาราง customers
                if role == 'customer':
                    # ตรวจสอบว่ามีข้อมูลในตาราง customers อยู่แล้วหรือไม่
                    cursor.execute('SELECT customer_id FROM customers WHERE email = %s AND first_name = %s AND last_name = %s', 
                                 (email, first_name, last_name))
                    existing_customer = cursor.fetchone()
                    
                    if not existing_customer:
                        # เพิ่มข้อมูลใหม่ลงตาราง customers
                        cursor.execute('INSERT INTO customers (user_id, first_name, last_name, email) VALUES (%s, %s, %s, %s)', 
                                     (user_id, first_name, last_name, email))
                
                get_db().commit()
                flash('เพิ่มผู้ใช้สำเร็จ')
                return redirect(url_for('admin.user_list'))
            except Exception as e:
                print(f"Error adding user: {e}")
                error = 'เกิดข้อผิดพลาดในการเพิ่มผู้ใช้'
                return render_template('admin/user_form.html', 
                                     user=None, 
                                     error=error,
                                     form_data={
                                         'username': username,
                                         'first_name': first_name,
                                         'last_name': last_name,
                                         'email': email,
                                         'role': role
                                     })
    return render_template('admin/user_form.html', user=None, error=error)

@admin.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    cursor = get_cursor()
    cursor.execute('SELECT * FROM users WHERE user_id=%s', (user_id,))
    user = cursor.fetchone()
    if not user:
        return redirect(url_for('admin.user_list'))
    
    # แยกชื่อ-นามสกุลจาก name
    if user and user.get('name'):
        name_parts = user['name'].split(' ', 1)
        user['first_name'] = name_parts[0] if name_parts else ''
        user['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
    else:
        user['first_name'] = ''
        user['last_name'] = ''
    
    # ดึงข้อมูล customer ถ้ามี
    if user and user.get('role_name') == 'customer':
        cursor.execute('SELECT email FROM customers WHERE user_id=%s', (user_id,))
        customer_data = cursor.fetchone()
        if customer_data:
            user['email'] = customer_data['email']
        else:
            user['email'] = ''
    else:
        user['email'] = ''
    
    error = None
    if request.method == 'POST':
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        role = request.form['role']
        password = request.form.get('password', '').strip()
        
        # Check for username conflict
        cursor.execute('SELECT * FROM users WHERE username=%s AND user_id!=%s', (username, user_id))
        if cursor.fetchone():
            error = 'Username already exists.'
        else:
            try:
                # สร้างชื่อเต็มสำหรับตาราง users
                full_name = f"{first_name} {last_name}"
                
                if password:
                    from werkzeug.security import generate_password_hash
                    password_hash = generate_password_hash(password, method='scrypt')
                    cursor.execute('UPDATE users SET username=%s, name=%s, role_name=%s, password_hash=%s WHERE user_id=%s', 
                                 (username, full_name, role, password_hash, user_id))
                else:
                    cursor.execute('UPDATE users SET username=%s, name=%s, role_name=%s WHERE user_id=%s', 
                                 (username, full_name, role, user_id))
                
                # อัปเดตข้อมูล customer ถ้าเป็น customer
                if role == 'customer':
                    cursor.execute('SELECT customer_id FROM customers WHERE user_id=%s', (user_id,))
                    existing_customer = cursor.fetchone()
                    
                    if existing_customer:
                        # อัปเดตข้อมูลที่มีอยู่
                        cursor.execute('UPDATE customers SET first_name=%s, last_name=%s, email=%s WHERE user_id=%s', 
                                     (first_name, last_name, email, user_id))
                    else:
                        # เพิ่มข้อมูลใหม่
                        cursor.execute('INSERT INTO customers (user_id, first_name, last_name, email) VALUES (%s, %s, %s, %s)', 
                                     (user_id, first_name, last_name, email))
                else:
                    # ถ้าเปลี่ยนจาก customer เป็น role อื่น ให้ลบข้อมูล customer และข้อมูลที่เกี่ยวข้อง
                    # ตรวจสอบว่ามีข้อมูล customer หรือไม่
                    cursor.execute('SELECT customer_id FROM customers WHERE user_id=%s', (user_id,))
                    existing_customer = cursor.fetchone()
                    
                    if existing_customer:
                        customer_id = existing_customer['customer_id']
                        
                        # ลบข้อมูลที่เกี่ยวข้องกับ customer ตามลำดับ
                        # 1. ลบ service_tires ที่เกี่ยวข้องกับ bookings ของ customer นี้
                        cursor.execute('SELECT booking_id FROM bookings WHERE customer_id=%s', (customer_id,))
                        booking_ids = [row['booking_id'] for row in cursor.fetchall()]
                        if booking_ids:
                            format_strings = ','.join(['%s'] * len(booking_ids))
                            cursor.execute(f'DELETE FROM service_tires WHERE booking_id IN ({format_strings})', tuple(booking_ids))
                            cursor.execute(f'DELETE FROM booking_item_options WHERE item_id IN (SELECT item_id FROM booking_items WHERE booking_id IN ({format_strings}))', tuple(booking_ids))
                            cursor.execute(f'DELETE FROM booking_items WHERE booking_id IN ({format_strings})', tuple(booking_ids))
                        
                        # 2. ลบ bookings ของ customer นี้
                        cursor.execute('DELETE FROM bookings WHERE customer_id=%s', (customer_id,))
                        
                        # 3. ลบ service_record_items ที่เกี่ยวข้องกับ service_records ของรถ customer นี้
                        cursor.execute('SELECT vehicle_id FROM vehicles WHERE customer_id=%s', (customer_id,))
                        vehicle_ids = [row['vehicle_id'] for row in cursor.fetchall()]
                        if vehicle_ids:
                            format_strings = ','.join(['%s'] * len(vehicle_ids))
                            cursor.execute(f'SELECT service_record_id FROM service_records WHERE vehicle_id IN ({format_strings})', tuple(vehicle_ids))
                            sr_ids = [row['service_record_id'] for row in cursor.fetchall()]
                            if sr_ids:
                                format_sr = ','.join(['%s'] * len(sr_ids))
                                cursor.execute(f'DELETE FROM service_record_items WHERE service_record_id IN ({format_sr})', tuple(sr_ids))
                            # ลบ service_records ของรถ customer นี้
                            cursor.execute(f'DELETE FROM service_records WHERE vehicle_id IN ({format_strings})', tuple(vehicle_ids))
                            # ลบ vehicles ของ customer นี้
                            cursor.execute(f'DELETE FROM vehicles WHERE customer_id=%s', (customer_id,))
                        
                        # 4. ลบข้อมูล customer
                        cursor.execute('DELETE FROM customers WHERE user_id=%s', (user_id,))
                
                get_db().commit()
                flash('อัปเดตผู้ใช้สำเร็จ')
                return redirect(url_for('admin.user_list'))
            except Exception as e:
                print(f"Error updating user: {e}")
                error = 'เกิดข้อผิดพลาดในการอัปเดตผู้ใช้'
    
    return render_template('admin/user_form.html', user=user, error=error)

@admin.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    cursor = get_cursor()
    cursor.execute('DELETE FROM users WHERE user_id=%s', (user_id,))
    get_db().commit()
    return redirect(url_for('admin.user_list'))

@admin.route('/dashboard')
@admin_required
def admin_dashboard():
    try:
        cursor = get_cursor()
        cursor.execute('SELECT COUNT(*) AS count FROM customers')
        total_customers = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) AS count FROM tires')
        total_tires = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) AS count FROM bookings')
        total_bookings = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) AS count FROM promotions")
        total_promotions = cursor.fetchone()['count']
        return render_template('admin/dashboard.html',
                             total_customers=total_customers,
                             total_tires=total_tires,
                             total_bookings=total_bookings,
                             total_promotions=total_promotions)
    except Exception as e:
        print(f"Error in admin_dashboard: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดข้อมูล', 'error')
        return redirect(url_for('auth.login'))

@admin.route('/promotions')
@admin_required
def promotion_list():
    cursor = get_cursor()
    cursor.execute('SELECT * FROM promotions ORDER BY promotion_id DESC')
    promotions = cursor.fetchall()
    return render_template('admin/promotion_list.html', promotions=promotions)

@admin.route('/promotions/add', methods=['GET', 'POST'])
@admin_required
def add_promotion():
    cursor = get_cursor()
    error = None
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        image_url = None
        # อัปโหลดรูปภาพ
        file = request.files.get('promotion_image')
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # สร้างโฟลเดอร์ promotions ถ้ายังไม่มี
            promotions_folder = current_app.config['PROMOTION_UPLOAD_FOLDER']
            os.makedirs(promotions_folder, exist_ok=True)
            file.save(os.path.join(promotions_folder, filename))
            image_url = filename
        try:
            cursor.execute('''INSERT INTO promotions (title, description, start_date, end_date, image_url) VALUES (%s, %s, %s, %s, %s)''',
                (title, description, start_date, end_date, image_url))
            get_db().commit()
            flash('เพิ่มโปรโมชันเรียบร้อยแล้ว', 'success')
            return redirect(url_for('admin.promotion_list'))
        except Exception as e:
            error = 'เกิดข้อผิดพลาดในการบันทึกข้อมูล: ' + str(e)
    return render_template('admin/promotion_form.html', promotion=None, error=error)

@admin.route('/promotions/edit/<int:promotion_id>', methods=['GET', 'POST'])
@admin_required
def edit_promotion(promotion_id):
    cursor = get_cursor()
    error = None
    cursor.execute('SELECT * FROM promotions WHERE promotion_id=%s', (promotion_id,))
    promotion = cursor.fetchone()
    if not promotion:
        return redirect(url_for('admin.promotion_list'))
    if request.method == 'POST':
        # --- ลบรูปภาพ ---
        if request.form.get('delete_image') == '1':
            image_url = promotion['image_url']
            if image_url:
                try:
                    promotions_folder = current_app.config['PROMOTION_UPLOAD_FOLDER']
                    os.remove(os.path.join(promotions_folder, image_url))
                except Exception:
                    pass
                cursor.execute('UPDATE promotions SET image_url=NULL WHERE promotion_id=%s', (promotion_id,))
                get_db().commit()
            return redirect(url_for('admin.edit_promotion', promotion_id=promotion_id))
        title = request.form['title']
        description = request.form['description']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        image_url = promotion['image_url']
        file = request.files.get('promotion_image')
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # สร้างโฟลเดอร์ promotions ถ้ายังไม่มี
            promotions_folder = current_app.config['PROMOTION_UPLOAD_FOLDER']
            os.makedirs(promotions_folder, exist_ok=True)
            file.save(os.path.join(promotions_folder, filename))
            image_url = filename
        try:
            cursor.execute('''UPDATE promotions SET title=%s, description=%s, start_date=%s, end_date=%s, image_url=%s WHERE promotion_id=%s''',
                (title, description, start_date, end_date, image_url, promotion_id))
            get_db().commit()
            flash('บันทึกโปรโมชันเรียบร้อยแล้ว', 'success')
            return redirect(url_for('admin.promotion_list'))
        except Exception as e:
            error = 'เกิดข้อผิดพลาดในการบันทึกข้อมูล: ' + str(e)
        # ดึงข้อมูลใหม่หลัง error
        cursor.execute('SELECT * FROM promotions WHERE promotion_id=%s', (promotion_id,))
        promotion = cursor.fetchone()
    return render_template('admin/promotion_form.html', promotion=promotion, error=error)

@admin.route('/promotions/delete/<int:promotion_id>', methods=['POST'])
@admin_required
def delete_promotion(promotion_id):
    cursor = get_cursor()
    # ลบไฟล์รูปภาพถ้ามี
    cursor.execute('SELECT image_url FROM promotions WHERE promotion_id=%s', (promotion_id,))
    row = cursor.fetchone()
    if row and row['image_url']:
        try:
            promotions_folder = current_app.config['PROMOTION_UPLOAD_FOLDER']
            os.remove(os.path.join(promotions_folder, row['image_url']))
            # ปกติ
        except Exception:
            pass
    cursor.execute('DELETE FROM promotions WHERE promotion_id=%s', (promotion_id,))
    get_db().commit()
    flash('ลบโปรโมชันเรียบร้อยแล้ว', 'success')
    return redirect(url_for('admin.promotion_list'))

@admin.route('/dashboard/chart-data')
@admin_required
def dashboard_chart_data():
    try:
        cursor = get_cursor()
        # กำหนดช่วง 12 เดือนล่าสุด
        now = datetime.now()
        months = []
        for i in range(11, -1, -1):
            d = now - timedelta(days=30*i)
            months.append(d.strftime('%Y-%m'))
        months = sorted(list(set(months)))
        
        # ดึงข้อมูลการจองรายเดือน
        bookings_data = []
        for month in months:
            try:
                cursor.execute('''
                    SELECT COUNT(*) as count 
                    FROM bookings 
                    WHERE DATE_FORMAT(booking_date, '%Y-%m') = %s
                ''', (month,))
                result = cursor.fetchone()
                bookings_data.append(result['count'] if result else 0)
            except Exception as e:
                print(f"Error getting bookings for {month}: {e}")
                bookings_data.append(0)
        
        # ดึงข้อมูลลูกค้าใหม่รายเดือน
        customers_data = []
        for month in months:
            try:
                cursor.execute('''
                    SELECT COUNT(*) as count 
                    FROM customers 
                    WHERE DATE_FORMAT(NOW(), '%Y-%m') = %s
                ''', (month,))
                result = cursor.fetchone()
                customers_data.append(result['count'] if result else 0)
            except Exception as e:
                print(f"Error getting customers for {month}: {e}")
                customers_data.append(0)
        
        # แปลงเดือนเป็นชื่อภาษาไทย
        thai_months = []
        for month in months:
            try:
                year, month_num = month.split('-')
                month_names = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 
                              'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
                thai_months.append(f"{month_names[int(month_num)-1]} {year}")
            except Exception as e:
                print(f"Error formatting month {month}: {e}")
                thai_months.append(month)
        
        # ดึงข้อมูลสำหรับกราฟ
        chart_data = {
            'labels': thai_months,
            'bookings': bookings_data,
            'customers': customers_data
        }
        
        return jsonify(chart_data)
        
    except Exception as e:
        print(f"Error in dashboard_chart_data: {e}")
        # ส่งข้อมูล default กลับไป
        default_data = {
            'labels': ['ม.ค. 2024', 'ก.พ. 2024', 'มี.ค. 2024', 'เม.ย. 2024', 'พ.ค. 2024', 'มิ.ย. 2024', 
                      'ก.ค. 2024', 'ส.ค. 2024', 'ก.ย. 2024', 'ต.ค. 2024', 'พ.ย. 2024', 'ธ.ค. 2024'],
            'bookings': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            'customers': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        }
        return jsonify(default_data)

@admin.route('/home-slider')
@admin_required
def home_slider():
    # สร้างโฟลเดอร์ถ้ายังไม่มี
    slider_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'home_slider')
    os.makedirs(slider_folder, exist_ok=True)
    
    # ดึงรายการไฟล์รูปภาพ
    slider_images = []
    if os.path.exists(slider_folder):
        for filename in os.listdir(slider_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                slider_images.append(filename)
    
    # เรียงลำดับไฟล์ตามชื่อ
    slider_images.sort()
    
    return render_template('admin/home_slider.html', slider_images=slider_images)

@admin.route('/home-slider/upload', methods=['POST'])
@admin_required
def upload_slider_image():
    file = request.files.get('slider_image')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        slider_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'home_slider')
        os.makedirs(slider_folder, exist_ok=True)
        
        file.save(os.path.join(slider_folder, filename))
        flash('อัปโหลดรูปภาพสำเร็จ')
    else:
        flash('ไฟล์ไม่ถูกต้อง')
    
    return redirect(url_for('admin.home_slider'))

@admin.route('/home-slider/delete/<filename>', methods=['POST'])
@admin_required
def delete_slider_image(filename):
    slider_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'home_slider')
    file_path = os.path.join(slider_folder, filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        flash('ลบรูปภาพสำเร็จ')
    else:
        flash('ไม่พบไฟล์')
    
    return redirect(url_for('admin.home_slider'))

@admin.route('/website-stats')
@admin_required
def website_stats():
    """หน้ารายงานสถิติการเข้าชมสำหรับผู้ดูแลระบบ"""
    try:
        cursor = get_cursor()
        
        # สถิติสรุป - นับเฉพาะหน้าในส่วนของลูกค้า
        cursor.execute('''
            SELECT COUNT(DISTINCT page_id) as total 
            FROM page_views 
            WHERE page_id LIKE 'customer/%' 
               OR page_id LIKE 'customer_%'
        ''')
        result = cursor.fetchone()
        total_page_views = result['total'] if result else 0
        
        cursor.execute('''
            SELECT SUM(views) as total 
            FROM page_views 
            WHERE page_id LIKE 'customer/%' 
               OR page_id LIKE 'customer_%'
        ''')
        result = cursor.fetchone()
        total_visits = result['total'] if result and result['total'] else 0
        
        # ดึงข้อมูลสถิติการเข้าชมจากตาราง page_views (top pages)
        cursor.execute('''
            SELECT page_id, views, last_viewed_at
            FROM page_views 
            ORDER BY views DESC
            LIMIT 10
        ''')
        top_pages = cursor.fetchall()
        
        # ดึงข้อมูลสถิติตามอุปกรณ์จากตาราง page_view_logs
        cursor.execute('''
            SELECT device_type, COUNT(*) as count
            FROM page_view_logs
            GROUP BY device_type
            ORDER BY count DESC
        ''')
        device_stats = cursor.fetchall()
        
        # ดึงข้อมูลการเข้าชมรายวัน (7 วันล่าสุด)
        cursor.execute('''
            SELECT DATE(viewed_at) as date, COUNT(*) as count
            FROM page_view_logs
            WHERE viewed_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(viewed_at)
            ORDER BY date DESC
        ''')
        daily_visits = cursor.fetchall()
        





        

        
        return render_template('admin/website_stats.html', 
                             total_page_views=total_page_views,
                             total_visits=total_visits,
                             top_pages=top_pages,
                             device_stats=device_stats,
                             daily_visits=daily_visits)
        
    except Exception as e:
        print(f"Error in admin website_stats: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดรายงาน', 'error')
        return redirect(url_for('admin.admin_dashboard'))

@admin.route('/booking-report')
# @admin_required  # ชั่วคราวปิด decorator เพื่อทดสอบ
def booking_report():
    """หน้ารายงานการจองสำหรับผู้ดูแลระบบ"""
    try:
        cursor = get_cursor()
        
        # สถิติสรุป
        cursor.execute('SELECT COUNT(*) as total FROM bookings')
        total_bookings = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM bookings WHERE status = 'สำเร็จ'")
        completed_bookings = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM bookings WHERE status = 'รอดำเนินการ'")
        pending_bookings = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM bookings WHERE status = 'ยกเลิก'")
        cancelled_bookings = cursor.fetchone()['total']
        
        # ดึงข้อมูลการจองรายเดือน (6 เดือนล่าสุด)
        cursor.execute('''
            SELECT DATE_FORMAT(booking_date, '%Y-%m') as month, COUNT(*) as count
            FROM bookings
            WHERE booking_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(booking_date, '%Y-%m')
            ORDER BY month DESC
        ''')
        monthly_bookings = cursor.fetchall()
        
        # ดึงข้อมูลการจองล่าสุด 10 รายการ
        cursor.execute('''
            SELECT b.*, 
                   c.first_name, c.last_name, c.phone,
                   v.brand_name, v.model_name, v.license_plate, v.license_province
            FROM bookings b
            JOIN customers c ON b.customer_id = c.customer_id
            JOIN vehicles v ON b.vehicle_id = v.vehicle_id
            ORDER BY b.service_date DESC, b.booking_id DESC
            LIMIT 10
        ''')
        bookings = cursor.fetchall()
        
        # เพิ่มข้อมูล timestamp สำหรับการอัปเดต
        from datetime import datetime
        current_time = datetime.now()
        
        return render_template('admin/booking_report.html', 
                             bookings=bookings,
                             total_bookings=total_bookings,
                             completed_bookings=completed_bookings,
                             pending_bookings=pending_bookings,
                             cancelled_bookings=cancelled_bookings,
                             monthly_bookings=monthly_bookings,
                             last_updated=current_time)
        
    except Exception as e:
        print(f"Error in admin booking_report: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดรายงาน', 'error')
        return redirect(url_for('admin.admin_dashboard'))

@admin.route('/booking-report-pdf')
@admin_required
def booking_report_pdf():
    """หน้ารายงานการจอง PDF สำหรับผู้ดูแลระบบ"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        report_type = request.args.get('report_type', 'all')  # เพิ่มการรับ report_type
        
        cursor = get_cursor()
        
        # ดึงข้อมูลการจองตามช่วงวันที่ พร้อมบริการที่จอง หมายเหตุ และข้อมูลยาง
        query = '''
            SELECT b.*, 
                   c.first_name, c.last_name, c.phone,
                   v.brand_name, v.model_name, v.license_plate, v.license_province,
                   GROUP_CONCAT(DISTINCT s.service_name ORDER BY s.service_name SEPARATOR ', ') AS service_names,
                   GROUP_CONCAT(DISTINCT CONCAT(s.service_name, 
                       CASE WHEN so.option_name IS NOT NULL 
                            THEN CONCAT(' (', so.option_name, ')') 
                            ELSE '' 
                       END) ORDER BY s.service_name, so.option_name SEPARATOR ', ') AS service_details,
                   b.note
            FROM bookings b
            JOIN customers c ON b.customer_id = c.customer_id
            JOIN vehicles v ON b.vehicle_id = v.vehicle_id
            LEFT JOIN booking_items bi ON bi.booking_id = b.booking_id
            LEFT JOIN services s ON bi.service_id = s.service_id
            LEFT JOIN booking_item_options bio ON bi.item_id = bio.item_id
            LEFT JOIN service_options so ON bio.option_id = so.option_id
        '''
        params = []
        
        if start_date and end_date:
            query += ' WHERE DATE(b.booking_date) BETWEEN %s AND %s'
            params.extend([start_date, end_date])
        
        query += ' GROUP BY b.booking_id ORDER BY b.booking_date DESC'
        cursor.execute(query, params)
        bookings = cursor.fetchall()
        
        # แปลงข้อมูลให้เป็น JSON serializable และดึงข้อมูลยาง
        bookings_data = []
        processed_booking_ids = set()  # เก็บ booking_id ที่ประมวลผลแล้ว
        
        for booking in bookings:
            booking_id = booking['booking_id']
            
            # ตรวจสอบว่า booking_id นี้ประมวลผลแล้วหรือยัง
            if booking_id in processed_booking_ids:
                continue  # ข้ามถ้าประมวลผลแล้ว
            
            processed_booking_ids.add(booking_id)
            booking_id = booking['booking_id']
            
            # ดึงข้อมูลยางจากตาราง service_tires
            tire_query = '''
                SELECT position, brand, model, size, dot 
                FROM service_tires 
                WHERE booking_id = %s
            '''
            cursor.execute(tire_query, (booking_id,))
            tire_data = cursor.fetchall()
            
            # จัดกลุ่มข้อมูลยางตาม position
            tire_info = {
                'front_left': None,
                'front_right': None,
                'rear_left': None,
                'rear_right': None
            }
            
            for tire in tire_data:
                position = tire['position']
                tire_info[position] = {
                    'brand': tire['brand'],
                    'model': tire['model'],
                    'size': tire['size'],
                    'dot': tire['dot']
                }
            
            booking_dict = {
                'booking_id': booking_id,
                'booking_date': booking['booking_date'].strftime('%Y-%m-%d') if booking['booking_date'] else None,
                'service_date': booking['service_date'].strftime('%Y-%m-%d') if booking['service_date'] else None,
                'service_time': str(booking['service_time']) if booking['service_time'] else None,
                'status': booking['status'],
                'first_name': booking['first_name'],
                'last_name': booking['last_name'],
                'phone': booking['phone'],
                'brand_name': booking['brand_name'],
                'model_name': booking['model_name'],
                'license_plate': booking['license_plate'],
                'license_province': booking['license_province'],
                'service_names': booking.get('service_names') if isinstance(booking, dict) else booking['service_names'],
                'service_details': booking.get('service_details') if isinstance(booking, dict) else booking['service_details'],
                'note': booking.get('note') if isinstance(booking, dict) else booking['note'],
                'tire_info': tire_info
            }
            bookings_data.append(booking_dict)
        
        # สร้าง PDF ด้วย ReportLab
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io
        import os
        
        # สร้าง buffer สำหรับ PDF
        buffer = io.BytesIO()
        
        # ฟังก์ชันสำหรับเพิ่มเส้นขีดและเลขหน้า
        def add_page_number(canvas, doc):
            canvas.saveState()
            # วาดเส้นขีดสีเขียว green-700
            canvas.setStrokeColor(HexColor('#15803d'))  # green-700
            canvas.setLineWidth(1.2)
            
            # เส้นวาดเหนือ margin (เช่น y=doc.bottomMargin-10)
            y_line = doc.bottomMargin - 10
            canvas.line(doc.leftMargin, y_line, A4[0] - doc.rightMargin, y_line)
            
            # วันที่และเวลาปัจจุบัน
            canvas.setFont('Helvetica', 10)
            current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            canvas.drawString(doc.leftMargin, y_line - 12, f"This report was created {current_time}")
            
            #เลขหน้า
            page_num = canvas.getPageNumber()
            canvas.drawRightString(A4[0] - doc.rightMargin, y_line - 12, f"หน้าที่ {page_num}")
            
            canvas.restoreState()
        
        # ตั้ง margin ให้มีพื้นที่ว่างรอบขอบกระดาษเพื่อความอ่านง่าย
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,   # 0.5 inch
            rightMargin=36,  # 0.5 inch
            topMargin=36,    # 0.5 inch
            bottomMargin=36,  # 0.5 inch
            onFirstPage=add_page_number,
            onLaterPages=add_page_number
        )
        elements = []
        
        # ลงทะเบียนฟอนต์ภาษาไทย
        font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'Noto_Sans_Thai', 'static', 'NotoSansThai-Regular.ttf')
        pdfmetrics.registerFont(TTFont('NotoSansThai', font_path))
        
        # ลงทะเบียนฟอนต์ภาษาไทย Bold
        bold_font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'Noto_Sans_Thai', 'static', 'NotoSansThai-Bold.ttf')
        if os.path.exists(bold_font_path):
            pdfmetrics.registerFont(TTFont('NotoSansThai-Bold', bold_font_path))
        else:
            # ถ้าไม่มี Bold font ให้ใช้ font ปกติ
            pdfmetrics.registerFont(TTFont('NotoSansThai-Bold', font_path))
        
        # สร้างสไตล์
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='NotoSansThai',
            fontSize=18,
            spaceAfter=30,
            alignment=1  # center
        )
        
        # สร้างสไตล์สำหรับข้อความปกติ
        normal_style = ParagraphStyle(
            'ThaiNormal',
            parent=styles['Normal'],
            fontName='NotoSansThai',
            fontSize=10,
            leading=13,
            wordWrap='CJK'
        )
        
        # สร้างสไตล์สำหรับข้อความตัวหนา
        bold_style = ParagraphStyle(
            'ThaiBold',
            parent=styles['Normal'],
            fontName='NotoSansThai-Bold',
            fontSize=10,
            leading=13,
            wordWrap='CJK'
        )
        
        # สร้างสไตล์สำหรับลำดับ (จัดกึ่งกลาง)
        center_style = ParagraphStyle(
            'ThaiCenter',
            parent=styles['Normal'],
            fontName='NotoSansThai',
            fontSize=10,
            leading=13,
            alignment=1,  # จัดกึ่งกลาง
            wordWrap='CJK'
        )
        
        # สร้างสไตล์สำหรับชื่อร้าน (กลางหน้ากระดาษ, สีเขียว, ตัวหนา)
        shop_name_style = ParagraphStyle(
            'ShopName',
            parent=styles['Heading1'],
            fontName='NotoSansThai-Bold',
            fontSize=20,
            textColor=HexColor('#14532d'),  # green-900
            spaceAfter=15,
            alignment=1,  # center
            leading=24
        )
        
        # สไตล์สำหรับหัวข้อหลัก
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='NotoSansThai-Bold',
            fontSize=14,  # ลดขนาดลง
            textColor=black,  # สีดำ
            spaceAfter=15,  # ลดระยะห่าง
            alignment=1,  # center
            leading=18
        )
        
        # สไตล์สำหรับ Selected Period (ตัวปกติ, ขนาดเล็กมาก, จัดกึ่งกลาง)
        selected_period_style = ParagraphStyle(
            'SelectedPeriod',
            parent=styles['Heading1'],
            fontName='Helvetica',  # ใช้ฟอนต์ภาษาอังกฤษ
            fontSize=10,  # ขนาดเล็กมาก
            textColor=black,  # สีดำ
            spaceAfter=8,  # ลดระยะห่าง
            alignment=1,  # center
            leading=14
        )
        
        # ชื่อร้านที่กลางหน้ากระดาษ
        shop_name = Paragraph("TYRE PLUS BURIRAM SANGJAROENKARNYANG", shop_name_style)
        elements.append(shop_name)
        
        # ข้อมูลช่วงวันที่ (ย้ายมาอยู่บนชื่อรายงาน)
        if start_date and end_date:
            # แปลงวันที่เป็นรูปแบบไทย (วว/ดด/ปปปป)
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                thai_start_date = start_date_obj.strftime('%d/%m/%Y')
                thai_end_date = end_date_obj.strftime('%d/%m/%Y')
                date_text = f"Selected Period: {thai_start_date} to {thai_end_date}"
            except:
                date_text = f"Selected Period: {start_date} to {end_date}"
            
            # สร้าง Paragraph สำหรับวันที่ (ตัวปกติ, ขนาดเล็กมาก, จัดกึ่งกลาง)
            date_paragraph = Paragraph(date_text, selected_period_style)
            elements.append(date_paragraph)
            elements.append(Spacer(1, 2))  # ลดระยะห่าง
        
        # หัวเรื่อง
        title = Paragraph("รายงานการจองบริการ", title_style)
        elements.append(title)
        elements.append(Spacer(1, 3))  # ลดระยะห่างหลังหัวเรื่อง
        
        # สร้างตารางข้อมูล
        if bookings_data:
            # สร้างสไตล์สำหรับหัวตาราง (สีขาว, จัดกึ่งกลาง)
            header_style = ParagraphStyle(
                'TableHeader',
                parent=styles['Normal'],
                fontName='NotoSansThai-Bold',
                fontSize=11,
                textColor=white,  # สีขาว
                leading=14,
                alignment=1  # จัดกึ่งกลาง
            )
            
            # หัวตาราง
            table_data = [
                [
                    Paragraph('ลำดับ', header_style),
                    Paragraph('ลูกค้า', header_style),
                    Paragraph('รถยนต์', header_style),
                    Paragraph('บริการที่จอง', header_style),
                    Paragraph('หมายเหตุ', header_style),
                    Paragraph('วันที่จอง', header_style),
                    Paragraph('สถานะ', header_style)
                ]
            ]
            
            # ข้อมูลในตาราง
            row_number = 1  # ตัวนับลำดับแยก
            for booking in bookings_data:
                # จัดรูปแบบชื่อลูกค้า - แยกชื่อและนามสกุล
                first_name = booking['first_name'] or ''
                last_name = booking['last_name'] or ''
                full_name = f"{first_name} {last_name}".strip()
                
                # ถ้าชื่อยาวเกิน 15 ตัวอักษร ให้แยกบรรทัด
                if len(full_name) > 15:
                    customer_name = Paragraph(f"{first_name}<br/>{last_name}", normal_style)
                else:
                    customer_name = Paragraph(full_name, normal_style)
                # จัดรูปแบบข้อมูลรถยนต์ - แยกยี่ห้อ รุ่น ทะเบียนรถ และจังหวัด
                brand_name = booking['brand_name'] or ''
                model_name = booking['model_name'] or ''
                license_plate = booking['license_plate'] or ''
                license_province = booking['license_province'] or ''
                
                vehicle_parts = []
                if brand_name:
                    vehicle_parts.append(f"ยี่ห้อ : {brand_name}")
                if model_name:
                    vehicle_parts.append(f"รุ่น : {model_name}")
                if license_plate:
                    vehicle_parts.append(f"ทะเบียน : {license_plate}")
                if license_province:
                    vehicle_parts.append(f"{license_province}")
                
                if vehicle_parts:
                    vehicle_info = Paragraph("<br/>".join(vehicle_parts), normal_style)
                else:
                    vehicle_info = Paragraph('-', normal_style)
                # แปลงวันที่เป็นรูปแบบไทย (วว/ดด/ปป)
                if booking['booking_date']:
                    try:
                        # แปลงจาก YYYY-MM-DD เป็น DD/MM/YY
                        date_obj = datetime.strptime(booking['booking_date'], '%Y-%m-%d')
                        thai_date = date_obj.strftime('%d/%m/%y')
                        booking_date = Paragraph(thai_date, center_style)
                    except:
                        booking_date = Paragraph(booking['booking_date'] or '-', center_style)
                else:
                    booking_date = Paragraph('-', center_style)
                status = Paragraph(booking['status'], center_style)
                
                # ใช้ service_details ถ้ามี (รวมบริการย่อย) ไม่งั้นใช้ service_names
                service_text = booking.get('service_details') or booking.get('service_names') or '-'
                
                # จัดรูปแบบการแสดงผลบริการและข้อมูลยาง
                all_content = []
                
                # เพิ่มบริการหลักและบริการย่อย
                if service_text and service_text != '-':
                    # แยกบริการหลักและบริการย่อย
                    services_list = service_text.split(', ')
                    formatted_services = []
                    
                    for service in services_list:
                        if '(' in service and ')' in service:
                            # มีบริการย่อย
                            main_service = service.split(' (')[0]
                            sub_service = service.split(' (')[1].rstrip(')')
                            formatted_services.append(f"๐ {main_service}")
                            formatted_services.append(f"  - {sub_service}")
                        else:
                            # ไม่มีบริการย่อย
                            formatted_services.append(f"๐ {service}")
                    
                    all_content.extend(formatted_services)
                
                # เพิ่มข้อมูลยางจาก tire_info
                tire_info = booking.get('tire_info', {})
                
                # ตรวจสอบว่ามีข้อมูลยางหรือไม่
                has_tire_data = any(tire_info.get(pos) for pos in ['front_left', 'front_right', 'rear_left', 'rear_right'])
                
                if has_tire_data:
                    # ตรวจสอบยางด้านหน้า
                    front_tires = []
                    if tire_info.get('front_left'):
                        front_tires.append(tire_info['front_left'])
                    if tire_info.get('front_right'):
                        front_tires.append(tire_info['front_right'])
                    
                    if front_tires:
                        all_content.append("๐ ยางด้านหน้า")
                        for i, tire in enumerate(front_tires, 1):
                            if tire.get('size'):
                                all_content.append(f"  - ขนาด: {tire['size']}")
                            if tire.get('brand'):
                                all_content.append(f"  - ยี่ห้อ: {tire['brand']}")
                            if tire.get('model'):
                                all_content.append(f"  - รุ่น: {tire['model']}")
                    
                    # ตรวจสอบยางด้านหลัง
                    rear_tires = []
                    if tire_info.get('rear_left'):
                        rear_tires.append(tire_info['rear_left'])
                    if tire_info.get('rear_right'):
                        rear_tires.append(tire_info['rear_right'])
                    
                    if rear_tires:
                        all_content.append("๐ ยางด้านหลัง")
                        for i, tire in enumerate(rear_tires, 1):
                            if tire.get('size'):
                                all_content.append(f"  - ขนาด: {tire['size']}")
                            if tire.get('brand'):
                                all_content.append(f"  - ยี่ห้อ: {tire['brand']}")
                            if tire.get('model'):
                                all_content.append(f"  - รุ่น: {tire['model']}")
                    
                    # ตรวจสอบข้อมูล DOT
                    dot_data = []
                    for pos, tire in tire_info.items():
                        if tire and tire.get('dot'):
                            pos_name = {
                                'front_left': 'หน้าซ้าย',
                                'front_right': 'หน้าขวา',
                                'rear_left': 'หลังซ้าย',
                                'rear_right': 'หลังขวา'
                            }.get(pos, pos)
                            dot_data.append(f"  - {pos_name}: {tire['dot']}")
                    
                    if dot_data:
                        all_content.append("๐ DOT ของยาง")
                        all_content.extend(dot_data)
                
                if all_content:
                    # สร้าง Paragraph แยกสำหรับบริการหลักและบริการย่อย
                    services_list = []
                    
                    for content in all_content:
                        if content.startswith('๐ '):
                            # บริการหลัก - ใช้ bold_style
                            services_list.append(Paragraph(content, bold_style))
                        else:
                            # บริการย่อย - ใช้ normal_style
                            services_list.append(Paragraph(content, normal_style))
                    
                    services = services_list
                else:
                    services = Paragraph('-', normal_style)
                
                note_text = Paragraph((booking.get('note') or '-'), normal_style)
                
                table_data.append([
                    Paragraph(str(row_number), center_style),
                    customer_name,
                    vehicle_info,
                    services,
                    note_text,
                    booking_date,
                    status
                ])
                
                row_number += 1  # เพิ่มลำดับ
            
            # สร้างตาราง - ปรับความกว้างคอลัมน์ให้เหมาะสมกับขนาดกระดาษ
            table = Table(
                table_data,
                colWidths=[35, 70, 100, 150, 60, 60, 70]  # เพิ่มความกว้างคอลัมน์สถานะจาก 50 เป็น 70
            )
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#166534')),  # green-800
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 0), (-1, 0), 'NotoSansThai-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # จัดกึ่งกลางหัวตารางทั้งหมด
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),  # จัดกึ่งกลางแนวตั้งหัวตาราง

                ('BACKGROUND', (0, 1), (-1, -1), HexColor('#fefce8')),  # yellow-50
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#166534')),  # green-800
                ('FONTNAME', (0, 1), (-1, -1), 'NotoSansThai'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('VALIGN', (0, 1), (-1, -1), 'TOP'),

                # จัดชิดซ้ายให้คอลัมน์ข้อความยาว
                ('ALIGN', (1, 1), (4, -1), 'LEFT'),  # ลูกค้า, รถยนต์, บริการ, หมายเหตุ
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # ลำดับ
                ('ALIGN', (5, 1), (5, -1), 'CENTER'),  # วันที่จอง
                ('ALIGN', (6, 1), (6, -1), 'CENTER'),  # สถานะ

                # Padding ให้พอดีอ่านง่าย - ลด padding เพื่อประหยัดพื้นที่
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            table.repeatRows = 1
            
            elements.append(table)
        else:
            no_data = Paragraph("ไม่พบข้อมูลการจองในช่วงวันที่ที่เลือก", normal_style)
            no_data.leftIndent = 40
            elements.append(no_data)
        
        elements.append(Spacer(1, 8))  # ลดระยะห่างก่อนข้อมูลเพิ่มเติม
        
        # สร้าง PDF
        doc.build(elements)
        buffer.seek(0)
        
        # ส่งกลับไฟล์ PDF
        from flask import send_file
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'admin_booking_report_{start_date}_to_{end_date}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error in admin booking_report_pdf: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin.route('/website-stats-pdf')
@admin_required
def website_stats_pdf():
    """หน้ารายงานสถิติการเข้าชม PDF สำหรับผู้ดูแลระบบ"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        report_type = request.args.get('report_type', 'device')  # เปลี่ยนค่าเริ่มต้นเป็น device
        
        cursor = get_cursor()
        
        # ดึงข้อมูลสถิติการเข้าชมตามช่วงวันที่
        query = '''
            SELECT page_id, COUNT(*) as total_visits
            FROM page_view_logs
        '''
        params = []
        
        if start_date and end_date:
            query += ' WHERE DATE(viewed_at) BETWEEN %s AND %s'
            params.extend([start_date, end_date])
        
        query += ' GROUP BY page_id ORDER BY total_visits DESC'
        cursor.execute(query, params)
        page_views = cursor.fetchall()
        
        # ดึงข้อมูลสถิติตามอุปกรณ์
        device_query = '''
            SELECT device_type, COUNT(*) as count
            FROM page_view_logs
        '''
        device_params = []
        
        if start_date and end_date:
            device_query += ' WHERE DATE(viewed_at) BETWEEN %s AND %s'
            device_params.extend([start_date, end_date])
        
        device_query += ' GROUP BY device_type ORDER BY count DESC'
        cursor.execute(device_query, device_params)
        device_stats = cursor.fetchall()
        
        # ดึงข้อมูลการเข้าชมรายวัน
        daily_query = '''
            SELECT DATE(viewed_at) as date, COUNT(*) as count
            FROM page_view_logs
        '''
        daily_params = []
        
        if start_date and end_date:
            daily_query += ' WHERE DATE(viewed_at) BETWEEN %s AND %s'
            daily_params.extend([start_date, end_date])
        
        daily_query += ' GROUP BY DATE(viewed_at) ORDER BY date ASC'
        cursor.execute(daily_query, daily_params)
        daily_visits = cursor.fetchall()
        
        # สร้างไฟล์ PDF
        buffer = io.BytesIO()
        
        # ลงทะเบียน font ภาษาไทยก่อน
        font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'Noto_Sans_Thai', 'NotoSansThai-VariableFont_wdth,wght.ttf')
        pdfmetrics.registerFont(TTFont('NotoSansThai', font_path))
        
        # ฟังก์ชันสำหรับเพิ่มเส้นขีดและเลขหน้า
        def add_page_number(canvas, doc):
            canvas.saveState()
            # วาดเส้นขีดสีเขียว green-700
            canvas.setStrokeColor(HexColor('#15803d'))  # green-700
            canvas.setLineWidth(1.5)
            canvas.line(36, 60, A4[0]-36, 60)  # เส้นอยู่เหนือ margin เล็กน้อย
                      
            # ตั้งฟอนต์สำหรับข้อความภาษาอังกฤษ
            canvas.setFont('Helvetica', 10)
            canvas.setFillColor(HexColor('#15803d'))  # green-700
            
            # วันที่และเวลาปัจจุบัน
            current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            
            # มุมล่างซ้าย: วันที่ที่สร้างรายงาน (เปลี่ยนเป็นภาษาอังกฤษ)
            canvas.drawString(40, 45, f"This report was created {current_time}")
            
            # มุมล่างขวา: เลขหน้า
            page_num = canvas.getPageNumber()
            canvas.drawRightString(A4[0]-40, 45, f"หน้าที่ {page_num}")
            
            canvas.restoreState()
        
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36, onFirstPage=add_page_number, onLaterPages=add_page_number)
        elements = []
        
        # ลงทะเบียน font ภาษาไทย Bold
        bold_font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'Noto_Sans_Thai', 'static', 'NotoSansThai-Bold.ttf')
        if os.path.exists(bold_font_path):
            pdfmetrics.registerFont(TTFont('NotoSansThai-Bold', bold_font_path))
        else:
            # ถ้าไม่มี Bold font ให้ใช้ font ปกติ
            pdfmetrics.registerFont(TTFont('NotoSansThai-Bold', font_path))
        
        # สร้าง styles ด้วย font ภาษาไทย
        styles = getSampleStyleSheet()
        
        # สไตล์สำหรับชื่อร้าน (กลางหน้ากระดาษ, สีเขียว, ตัวหนา)
        shop_name_style = ParagraphStyle(
            'ShopName',
            parent=styles['Heading1'],
            fontName='NotoSansThai-Bold',
            fontSize=20,
            textColor=HexColor('#14532d'),  # green-900
            spaceAfter=15,
            alignment=1,  # center
            leading=24
        )
        
        # สไตล์สำหรับหัวข้อหลัก
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='NotoSansThai-Bold',
            fontSize=14,  # ลดขนาดลง
            textColor=black,  # สีดำ
            spaceAfter=15,  # ลดระยะห่าง
            alignment=1,  # center
            leading=18
        )
        
        # สไตล์สำหรับ Selected Period (ตัวปกติ, ขนาดเล็กมาก, จัดกึ่งกลาง)
        selected_period_style = ParagraphStyle(
            'SelectedPeriod',
            parent=styles['Heading1'],
            fontName='Helvetica',  # ใช้ฟอนต์ภาษาอังกฤษ
            fontSize=10,  # ขนาดเล็กมาก
            textColor=black,  # สีดำ
            spaceAfter=8,  # ลดระยะห่าง
            alignment=1,  # center
            leading=14
        )
        
        # สไตล์สำหรับหัวข้อย่อย
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName='NotoSansThai-Bold',
            fontSize=13,
            textColor=HexColor('#166534'),  # green-800
            spaceAfter=8,
            spaceBefore=5,  # ลดระยะห่างด้านบน
            leading=16
        )
        
        # สไตล์สำหรับข้อความปกติ
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName='NotoSansThai',
            fontSize=11,
            textColor=HexColor('#374151'),  # gray-700
            leading=16,
            spaceAfter=6
        )
        
        # สไตล์สำหรับข้อความตัวหนา
        bold_style = ParagraphStyle(
            'CustomBold',
            parent=styles['Normal'],
            fontName='NotoSansThai-Bold',
            fontSize=11,
            textColor=HexColor('#374151'),  # gray-700
            leading=16,
            spaceAfter=6
        )
        
        # ชื่อร้านที่กลางหน้ากระดาษ
        shop_name = Paragraph("TYRE PLUS BURIRAM SANGJAROENKARNYANG", shop_name_style)
        elements.append(shop_name)
        
        # ข้อมูลช่วงวันที่ (ย้ายมาอยู่บนชื่อรายงาน)
        if start_date and end_date:
            # แปลงวันที่เป็นรูปแบบไทย (วว/ดด/ปปปป)
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                thai_start_date = start_date_obj.strftime('%d/%m/%Y')
                thai_end_date = end_date_obj.strftime('%d/%m/%Y')
                date_text = f"Selected Period: {thai_start_date} to {thai_end_date}"
            except:
                date_text = f"Selected Period: {start_date} to {end_date}"
            
            # สร้าง Paragraph สำหรับวันที่ (ตัวปกติ, ขนาดเล็กมาก, จัดกึ่งกลาง)
            date_paragraph = Paragraph(date_text, selected_period_style)
            elements.append(date_paragraph)
            elements.append(Spacer(1, 2))  # ลดระยะห่าง
        
        # หัวเรื่อง
        if report_type == 'device':
            title_text = "รายงานอุปกรณ์ผู้เข้าชมเว็บไซต์"
        elif report_type == 'daily':
            title_text = "รายงานสถิติการเข้าชมรายวัน"
        elif report_type == 'pages':
            title_text = "รายงานสถิติหน้าที่เข้าชมมากที่สุด"
        else:
            title_text = "รายงานอุปกรณ์ผู้เข้าชมเว็บไซต์"
            
        title = Paragraph(title_text, title_style)
        elements.append(title)
        elements.append(Spacer(1, 3))  # ลดระยะห่างหลังหัวเรื่อง
        
        # ส่วนอุปกรณ์ที่ใช้เข้าชม
        if device_stats and report_type == 'device':
            
            # สร้างตารางอุปกรณ์
            device_table_data = [['อุปกรณ์', 'จำนวนการเข้าชม']]
            for device in device_stats:
                device_name = device['device_type']
                if device_name == 'mobile':
                    device_name = 'มือถือ'
                elif device_name == 'desktop':
                    device_name = 'เดสก์ท็อป'
                elif device_name == 'tablet':
                    device_name = 'แท็บเล็ต'
                elif device_name == 'unknown':
                    device_name = 'อื่นๆ'
                
                device_table_data.append([device_name, str(device['count'])])
            
            device_table = Table(device_table_data, colWidths=[3*inch, 3*inch])
            device_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#166534')),  # green-800
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'NotoSansThai-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f0fdf4')),  # green-50
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#166534')),  # green-800
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'NotoSansThai'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ]))
            
            elements.append(device_table)
            elements.append(Spacer(1, 5))  # ลดระยะห่างหลังตารางอุปกรณ์
        
        # ส่วนการเข้าชมรายวัน
        if daily_visits and report_type == 'daily':
            
            # สร้างตารางการเข้าชมรายวัน
            daily_table_data = [['วันที่', 'จำนวนการเข้าชม']]
            for daily in daily_visits:
                date_str = daily['date'].strftime('%d/%m/%Y') if daily['date'] else 'ไม่ระบุ'
                daily_table_data.append([date_str, str(daily['count'])])
            
            daily_table = Table(daily_table_data, colWidths=[3*inch, 3*inch])
            daily_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#166534')),  # green-800
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'NotoSansThai-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), HexColor('#fefce8')),  # yellow-50
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#166534')),  # green-800
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'NotoSansThai'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ]))
            
            elements.append(daily_table)
            elements.append(Spacer(1, 5))  # ลดระยะห่างหลังตารางรายวัน
        
        # สร้างตารางข้อมูลหน้าเว็บ
        if page_views and report_type == 'pages':
            
            # หัวตาราง
            table_data = [['หน้าเว็บ', 'จำนวนการเข้าชม']]
            
            # ข้อมูลในตาราง
            for page in page_views:
                page_name = page['page_id']
                # แปลงชื่อหน้าให้อ่านง่าย
                if page_name == 'index.html':
                    page_name = 'หน้าหลัก'
                elif page_name == 'tires.html':
                    page_name = 'หน้ายางทั้งหมด'
                elif page_name == 'customer/recommend.html':
                    page_name = 'หน้าแนะนำยาง'
                elif page_name == 'customer/compare.html':
                    page_name = 'หน้าเปรียบเทียบยาง'
                elif page_name == 'customer/profile.html':
                    page_name = 'หน้าโปรไฟล์ลูกค้า'
                elif page_name == 'customer/bookings.html':
                    page_name = 'หน้าการจอง'
                elif page_name == 'customer/booking-history.html':
                    page_name = 'หน้าประวัติการจอง'
                elif page_name == 'customer/booking.html':
                    page_name = 'หน้าการจอง'
                elif page_name == 'customer/home.html':
                    page_name = 'หน้าหลักลูกค้า'
                elif page_name == 'customer/promotions.html':
                    page_name = 'หน้าโปรโมชั่น'
                elif page_name == 'customer/guide.html':
                    page_name = 'หน้าแนะนำยาง'
                elif page_name == 'customer/contact.html':
                    page_name = 'หน้าติดต่อ'
                elif page_name == 'customer/tires_michelin.html':
                    page_name = 'หน้ายางมิชลิน'
                elif page_name == 'customer/promotion_detail.html':
                    page_name = 'หน้ารายละเอียดโปรโมชั่น'
                elif page_name == 'customer/tires.html':
                    page_name = 'หน้ายางทั้งหมด'
                elif page_name == 'customer/tires_bfgoodrich.html':
                    page_name = 'หน้ายางบีเอฟกู๊ดริช'
                elif page_name == 'customer/tires_maxxis.html':
                    page_name = 'หน้ายางแม็กซิส'
                elif page_name == 'login.html':
                    page_name = 'หน้าเข้าสู่ระบบ'
                elif page_name == 'register.html':
                    page_name = 'หน้าลงทะเบียน'
                
                table_data.append([page_name, str(page['total_visits'])])
            
            # สร้างตาราง
            table = Table(table_data, colWidths=[4*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#166534')),  # green-800
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # หัวตารางอยู่กึ่งกลาง
                ('FONTNAME', (0, 0), (-1, 0), 'NotoSansThai-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f0fdf4')),  # green-50
                ('GRID', (0, 0), (-1, -1), 1, HexColor('#166534')),  # green-800
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # คอลัมน์ชื่อหน้าชิดซ้าย
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # คอลัมน์จำนวนอยู่กึ่งกลาง
                ('FONTNAME', (0, 1), (-1, -1), 'NotoSansThai'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ]))
            
            elements.append(table)
        else:
            # ถ้าไม่มีข้อมูลในตารางหน้าเว็บ และไม่มีข้อมูลในส่วนอื่นๆ ด้วย
            if not device_stats and not daily_visits:
                no_data = Paragraph("ไม่พบข้อมูลการเข้าชมในช่วงวันที่ที่เลือก", normal_style)
                elements.append(no_data)
        
        elements.append(Spacer(1, 8))  # ลดระยะห่างก่อนข้อมูลเพิ่มเติม
        
        # สร้าง PDF
        doc.build(elements)
        buffer.seek(0)
        
        # ส่งไฟล์ PDF กลับไป
        filename = f"website_stats_{start_date}_to_{end_date}.pdf" if start_date and end_date else "website_stats.pdf"
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error in admin website_stats_pdf: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ===== BRAND MANAGEMENT ROUTES =====
@admin.route('/brands')
@admin_required
def brand_list():
    """หน้ารายการยี่ห้อยาง"""
    cursor = get_cursor()
    search = request.args.get('search', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page
    
    where = ''
    params = []
    
    if search:
        where = 'WHERE brand_name LIKE %s'
        params = [f"%{search}%"]
    
    # นับจำนวนทั้งหมด
    count_query = f"SELECT COUNT(*) FROM brands {where}"
    cursor.execute(count_query, params)
    total = list(cursor.fetchone().values())[0]
    total_pages = (total + per_page - 1) // per_page
    
    # ดึงข้อมูลยี่ห้อ
    query = f"""
        SELECT b.brand_id, b.brand_name,
               COUNT(t.tire_id) as tire_count,
               COUNT(DISTINCT tm.model_id) as model_count
        FROM brands b
        LEFT JOIN tire_models tm ON b.brand_id = tm.brand_id
        LEFT JOIN tires t ON tm.model_id = t.model_id
        {where}
        GROUP BY b.brand_id, b.brand_name
        ORDER BY b.brand_name
        LIMIT %s OFFSET %s
    """
    params += [per_page, offset]
    cursor.execute(query, params)
    brands = cursor.fetchall()
    
    return render_template('admin/brand_list.html',
        brands=brands, search=search, page=page, total_pages=total_pages
    )

@admin.route('/brands/add', methods=['GET', 'POST'])
@admin_required
def add_brand():
    """เพิ่มยี่ห้อยาง"""
    cursor = get_cursor()
    
    if request.method == 'POST':
        brand_name = request.form.get('brand_name', '').strip()
        
        if not brand_name:
            flash('กรุณากรอกชื่อยี่ห้อ', 'error')
            return render_template('admin/brand_form.html', brand=None)
        
        # ตรวจสอบว่ามียี่ห้อนี้อยู่แล้วหรือไม่
        cursor.execute('SELECT brand_id FROM brands WHERE brand_name = %s', (brand_name,))
        if cursor.fetchone():
            flash('ยี่ห้อนี้มีอยู่แล้วในระบบ', 'error')
            return render_template('admin/brand_form.html', brand=None)
        
        try:
            cursor.execute('INSERT INTO brands (brand_name) VALUES (%s)', (brand_name,))
            brand_id = cursor.lastrowid
            get_db().commit()
            flash('เพิ่มยี่ห้อยางสำเร็จ', 'success')
            return redirect(url_for('admin.add_brand', success=1))
        except Exception as e:
            get_db().rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
            return render_template('admin/brand_form.html', brand=None)
    
    return render_template('admin/brand_form.html', brand=None)

@admin.route('/brands/edit/<int:brand_id>', methods=['GET', 'POST'])
@admin_required
def edit_brand(brand_id):
    """แก้ไขยี่ห้อยาง"""
    cursor = get_cursor()
    
    if request.method == 'POST':
        brand_name = request.form.get('brand_name', '').strip()
        
        if not brand_name:
            flash('กรุณากรอกชื่อยี่ห้อ', 'error')
            return render_template('admin/brand_form.html', brand={'brand_id': brand_id, 'brand_name': brand_name})
        
        # ตรวจสอบว่ามียี่ห้อนี้อยู่แล้วหรือไม่ (ยกเว้นตัวเอง)
        cursor.execute('SELECT brand_id FROM brands WHERE brand_name = %s AND brand_id != %s', (brand_name, brand_id))
        if cursor.fetchone():
            flash('ยี่ห้อนี้มีอยู่แล้วในระบบ', 'error')
            return render_template('admin/brand_form.html', brand={'brand_id': brand_id, 'brand_name': brand_name})
        
        try:
            cursor.execute('UPDATE brands SET brand_name = %s WHERE brand_id = %s', (brand_name, brand_id))
            get_db().commit()
            flash('แก้ไขยี่ห้อยางสำเร็จ', 'success')
            return redirect(url_for('admin.edit_brand', brand_id=brand_id, success=1))
        except Exception as e:
            get_db().rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
            return render_template('admin/brand_form.html', brand={'brand_id': brand_id, 'brand_name': brand_name})
    
    # ดึงข้อมูลยี่ห้อ
    cursor.execute('SELECT * FROM brands WHERE brand_id = %s', (brand_id,))
    brand = cursor.fetchone()
    
    if not brand:
        flash('ไม่พบยี่ห้อที่ต้องการแก้ไข', 'error')
        return redirect(url_for('admin.brand_list'))
    
    return render_template('admin/brand_form.html', brand=brand)

@admin.route('/brands/delete/<int:brand_id>', methods=['POST'])
@admin_required
def delete_brand(brand_id):
    """ลบยี่ห้อยาง"""
    cursor = get_cursor()
    
    try:
        # ตรวจสอบว่ามียางที่ใช้ยี่ห้อนี้หรือไม่
        cursor.execute('''
            SELECT COUNT(*) as count FROM tires t
            JOIN tire_models tm ON t.model_id = tm.model_id
            WHERE tm.brand_id = %s
        ''', (brand_id,))
        tire_count = cursor.fetchone()['count']
        
        if tire_count > 0:
            flash(f'ไม่สามารถลบยี่ห้อนี้ได้ เนื่องจากมียาง {tire_count} เส้นที่ใช้ยี่ห้อนี้', 'error')
            return redirect(url_for('admin.brand_list'))
        
        cursor.execute('DELETE FROM brands WHERE brand_id = %s', (brand_id,))
        get_db().commit()
        flash('ลบยี่ห้อยางสำเร็จ', 'success')
    except Exception as e:
        get_db().rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return redirect(url_for('admin.brand_list'))

# ===== TIRE MODEL MANAGEMENT ROUTES =====
@admin.route('/tire-models')
@admin_required
def tire_model_list():
    """หน้ารายการรุ่นยาง"""
    cursor = get_cursor()
    search = request.args.get('search', '').strip()
    brand_filter = request.args.get('brand', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page
    
    where_conditions = []
    params = []
    
    if search:
        where_conditions.append('tm.model_name LIKE %s')
        params.append(f"%{search}%")
    
    if brand_filter:
        where_conditions.append('b.brand_name = %s')
        params.append(brand_filter)
    
    where = 'WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
    
    # นับจำนวนทั้งหมด
    count_query = f"""
        SELECT COUNT(*) FROM tire_models tm
        JOIN brands b ON tm.brand_id = b.brand_id
        {where}
    """
    cursor.execute(count_query, params)
    total = list(cursor.fetchone().values())[0]
    total_pages = (total + per_page - 1) // per_page
    
    # ดึงข้อมูลรุ่นยาง
    query = f"""
        SELECT tm.model_id, tm.model_name, tm.tire_category,
               b.brand_name, b.brand_id,
               COUNT(t.tire_id) as tire_count
        FROM tire_models tm
        JOIN brands b ON tm.brand_id = b.brand_id
        LEFT JOIN tires t ON tm.model_id = t.model_id
        {where}
        GROUP BY tm.model_id, tm.model_name, tm.tire_category, b.brand_name, b.brand_id
        ORDER BY b.brand_name, tm.model_name
        LIMIT %s OFFSET %s
    """
    params += [per_page, offset]
    cursor.execute(query, params)
    models = cursor.fetchall()
    
    # ดึงรายการยี่ห้อสำหรับ filter
    cursor.execute('SELECT brand_name FROM brands ORDER BY brand_name')
    brands = [row['brand_name'] for row in cursor.fetchall()]
    
    return render_template('admin/tire_model_list.html',
        models=models, brands=brands, search=search, brand_filter=brand_filter,
        page=page, total_pages=total_pages
    )

@admin.route('/tire-models/add', methods=['GET', 'POST'])
@admin_required
def add_tire_model():
    """เพิ่มรุ่นยาง"""
    cursor = get_cursor()
    
    if request.method == 'POST':
        model_name = request.form.get('model_name', '').strip()
        brand_id = request.form.get('brand_id', '').strip()
        tire_category = request.form.get('tire_category', '').strip()
        
        if not model_name or not brand_id or not tire_category:
            flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'error')
            return render_template('admin/tire_model_form.html', model=None, brands=get_brands())
        
        # ตรวจสอบว่ารุ่นนี้มีอยู่แล้วหรือไม่
        cursor.execute('SELECT model_id FROM tire_models WHERE model_name = %s AND brand_id = %s', (model_name, brand_id))
        if cursor.fetchone():
            flash('รุ่นยางนี้มีอยู่แล้วในยี่ห้อนี้', 'error')
            return render_template('admin/tire_model_form.html', model=None, brands=get_brands())
        
        try:
            cursor.execute('INSERT INTO tire_models (model_name, brand_id, tire_category) VALUES (%s, %s, %s)', 
                         (model_name, brand_id, tire_category))
            model_id = cursor.lastrowid
            get_db().commit()
            flash('เพิ่มรุ่นยางสำเร็จ', 'success')
            return redirect(url_for('admin.add_tire_model', success=1))
        except Exception as e:
            get_db().rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
            return render_template('admin/tire_model_form.html', model=None, brands=get_brands())
    
    return render_template('admin/tire_model_form.html', model=None, brands=get_brands())

@admin.route('/tire-models/edit/<int:model_id>', methods=['GET', 'POST'])
@admin_required
def edit_tire_model(model_id):
    """แก้ไขรุ่นยาง"""
    cursor = get_cursor()
    
    if request.method == 'POST':
        model_name = request.form.get('model_name', '').strip()
        brand_id = request.form.get('brand_id', '').strip()
        tire_category = request.form.get('tire_category', '').strip()
        
        if not model_name or not brand_id or not tire_category:
            flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'error')
            return render_template('admin/tire_model_form.html', 
                                 model={'model_id': model_id, 'model_name': model_name, 'brand_id': brand_id, 'tire_category': tire_category}, 
                                 brands=get_brands())
        
        # ตรวจสอบว่ารุ่นนี้มีอยู่แล้วหรือไม่ (ยกเว้นตัวเอง)
        cursor.execute('SELECT model_id FROM tire_models WHERE model_name = %s AND brand_id = %s AND model_id != %s', 
                      (model_name, brand_id, model_id))
        if cursor.fetchone():
            flash('รุ่นยางนี้มีอยู่แล้วในยี่ห้อนี้', 'error')
            return render_template('admin/tire_model_form.html', 
                                 model={'model_id': model_id, 'model_name': model_name, 'brand_id': brand_id, 'tire_category': tire_category}, 
                                 brands=get_brands())
        
        try:
            cursor.execute('UPDATE tire_models SET model_name = %s, brand_id = %s, tire_category = %s WHERE model_id = %s', 
                         (model_name, brand_id, tire_category, model_id))
            get_db().commit()
            flash('แก้ไขรุ่นยางสำเร็จ', 'success')
            return redirect(url_for('admin.edit_tire_model', model_id=model_id, success=1))
        except Exception as e:
            get_db().rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
            return render_template('admin/tire_model_form.html', 
                                 model={'model_id': model_id, 'model_name': model_name, 'brand_id': brand_id, 'tire_category': tire_category}, 
                                 brands=get_brands())
    
    # ดึงข้อมูลรุ่นยาง
    cursor.execute('SELECT * FROM tire_models WHERE model_id = %s', (model_id,))
    model = cursor.fetchone()
    
    if not model:
        flash('ไม่พบรุ่นยางที่ต้องการแก้ไข', 'error')
        return redirect(url_for('admin.tire_model_list'))
    
    return render_template('admin/tire_model_form.html', model=model, brands=get_brands())

@admin.route('/tire-models/delete/<int:model_id>', methods=['POST'])
@admin_required
def delete_tire_model(model_id):
    """ลบรุ่นยาง"""
    cursor = get_cursor()
    
    try:
        # ตรวจสอบว่ามียางที่ใช้รุ่นนี้หรือไม่
        cursor.execute('SELECT COUNT(*) as count FROM tires WHERE model_id = %s', (model_id,))
        tire_count = cursor.fetchone()['count']
        
        if tire_count > 0:
            flash(f'ไม่สามารถลบรุ่นยางนี้ได้ เนื่องจากมียาง {tire_count} เส้นที่ใช้รุ่นนี้', 'error')
            return redirect(url_for('admin.tire_model_list'))
        
        cursor.execute('DELETE FROM tire_models WHERE model_id = %s', (model_id,))
        get_db().commit()
        flash('ลบรุ่นยางสำเร็จ', 'success')
    except Exception as e:
        get_db().rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return redirect(url_for('admin.tire_model_list'))

def get_brands():
    """ฟังก์ชันช่วยสำหรับดึงรายการยี่ห้อ"""
    cursor = get_cursor()
    cursor.execute('SELECT brand_id, brand_name FROM brands ORDER BY brand_name')
    return cursor.fetchall()

@admin.route('/logout', methods=['POST', 'GET'])
@admin_required
def admin_logout():
    session.clear()
    flash('ออกจากระบบผู้ดูแลระบบเรียบร้อย', 'success')
    return redirect(url_for('auth.login'))  # กลับไปหน้า /login ที่มีอยู่แล้ว