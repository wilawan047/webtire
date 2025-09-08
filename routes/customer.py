from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, current_app, jsonify
from database import get_cursor, get_db
from utils import allowed_file, verify_password
from decorators import customer_login_required, customer_required
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import time

customer = Blueprint('customer', __name__)

@customer.route('/')
def home():
    """หน้าแรกสำหรับลูกค้า"""
    try:
        cursor = get_cursor()
        
        # ดึงข้อมูลโปรโมชันที่ใช้งานได้ (มีวันที่ปัจจุบันอยู่ในช่วงโปรโมชัน)
        cursor.execute("""
            SELECT promotion_id, title, description, image_url,
                   start_date, end_date
            FROM promotions
            WHERE start_date <= CURDATE() AND end_date >= CURDATE()
            ORDER BY start_date DESC
        """)
        promotions = cursor.fetchall()
        print(f"Found {len(promotions)} active promotions: {promotions}")
        
        # Debug: ดูโปรโมชันทั้งหมด
        cursor.execute("SELECT promotion_id, title, image_url, start_date, end_date FROM promotions ORDER BY start_date DESC")
        all_promotions = cursor.fetchall()
        print(f"All promotions in database: {all_promotions}")
        
        return render_customer_template('customer/home.html', promotions=promotions)
        
    except Exception as e:
        print(f"Error loading promotions: {e}")
        return render_customer_template('customer/home.html', promotions=[])

@customer.route('/api/tire-sizes')
def get_tire_sizes():
    """API สำหรับดึงข้อมูล tire sizes จากฐานข้อมูล"""
    try:
        cursor = get_cursor()
        
        # ดึงข้อมูล tire sizes ที่มีอยู่จริงในฐานข้อมูล
        cursor.execute("""
            SELECT DISTINCT width, aspect_ratio, rim_diameter
            FROM tires
            WHERE width IS NOT NULL AND aspect_ratio IS NOT NULL AND rim_diameter IS NOT NULL
            ORDER BY width ASC, aspect_ratio ASC, rim_diameter ASC
        """)
        
        tire_sizes = cursor.fetchall()
        
        # จัดกลุ่มข้อมูลตาม width, aspect_ratio, rim_diameter
        combinations = []
        for tire in tire_sizes:
            combinations.append({
                'width': int(tire['width']),
                'aspect': int(tire['aspect_ratio']),
                'rim': int(tire['rim_diameter'])
            })
        
        return jsonify({
            'combinations': combinations
        })
        
    except Exception as e:
        print(f"Error fetching tire sizes: {e}")
        return jsonify({'combinations': []})

@customer.route('/api/car-brands')
def get_car_brands():
    """API สำหรับดึงข้อมูลยี่ห้อรถจากฐานข้อมูล"""
    try:
        cursor = get_cursor()
        
        # ดึงข้อมูลยี่ห้อรถที่มีการแมทซ์ในตาราง tire_model_vehicle_targets
        cursor.execute("""
            SELECT DISTINCT cb.car_brand_id, cb.car_brand_name
            FROM car_brands cb
            JOIN car_models cm ON cb.car_brand_id = cm.car_brand_id
            JOIN car_model_years cmy ON cm.car_model_id = cmy.car_model_id
            JOIN tire_model_vehicle_targets tvt ON cmy.car_model_year_id = tvt.car_model_year_id
            ORDER BY cb.car_brand_name ASC
        """)
        
        brands = cursor.fetchall()
        print(f"Found {len(brands)} matched car brands: {brands}")
        
        return jsonify({
            'brands': [{'id': brand['car_brand_id'], 'name': brand['car_brand_name']} for brand in brands]
        })
        
    except Exception as e:
        print(f"Error fetching car brands: {e}")
        return jsonify({'brands': []})

@customer.route('/api/car-models/<int:brand_id>')
def get_car_models(brand_id):
    """API สำหรับดึงข้อมูลรุ่นรถตามยี่ห้อ"""
    try:
        print(f"API called: /api/car-models/{brand_id}")
        cursor = get_cursor()
        
        # ดึงข้อมูลรุ่นรถจากตาราง car_models โดยตรง
        cursor.execute("""
            SELECT car_model_id, car_model_name
            FROM car_models
            WHERE car_brand_id = %s
            ORDER BY car_model_name ASC
        """, (brand_id,))
        
        models = cursor.fetchall()
        print(f"Found {len(models)} car models for brand {brand_id}: {models}")
        
        result = {
            'models': [{'id': model['car_model_id'], 'name': model['car_model_name']} for model in models]
        }
        print(f"Returning result: {result}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error fetching car models: {e}")
        # Fallback data สำหรับรุ่นรถ
        fallback_models = {
            1: [{'id': 1, 'name': 'Camry'}, {'id': 2, 'name': 'Corolla'}, {'id': 3, 'name': 'Yaris'}, {'id': 4, 'name': 'Vios'}, {'id': 5, 'name': 'Altis'}],  # Toyota
            2: [{'id': 6, 'name': 'Civic'}, {'id': 7, 'name': 'City'}, {'id': 8, 'name': 'Accord'}, {'id': 9, 'name': 'CR-V'}, {'id': 10, 'name': 'HR-V'}],  # Honda
            3: [{'id': 11, 'name': 'March'}, {'id': 12, 'name': 'Almera'}, {'id': 13, 'name': 'Note'}, {'id': 14, 'name': 'X-Trail'}, {'id': 15, 'name': 'Teana'}],  # Nissan
            4: [{'id': 16, 'name': 'Mazda2'}, {'id': 17, 'name': 'Mazda3'}, {'id': 18, 'name': 'CX-3'}, {'id': 19, 'name': 'CX-5'}, {'id': 20, 'name': 'CX-30'}],  # Mazda
            5: [{'id': 21, 'name': 'Mirage'}, {'id': 22, 'name': 'Attrage'}, {'id': 23, 'name': 'Pajero Sport'}, {'id': 24, 'name': 'Triton'}, {'id': 25, 'name': 'Lancer'}],  # Mitsubishi
            6: [{'id': 26, 'name': 'Swift'}, {'id': 27, 'name': 'Ciaz'}, {'id': 28, 'name': 'Vitara'}, {'id': 29, 'name': 'Jimny'}, {'id': 30, 'name': 'Ignis'}],  # Suzuki
            7: [{'id': 31, 'name': 'D-Max'}, {'id': 32, 'name': 'MU-X'}, {'id': 33, 'name': 'Hi-Lander'}, {'id': 34, 'name': 'Rodeo'}, {'id': 35, 'name': 'PICKUP'}],  # Isuzu
            8: [{'id': 36, 'name': 'Ranger'}, {'id': 37, 'name': 'Everest'}, {'id': 38, 'name': 'EcoSport'}, {'id': 39, 'name': 'Focus'}, {'id': 40, 'name': 'Fiesta'}],  # Ford
            9: [{'id': 41, 'name': 'Colorado'}, {'id': 42, 'name': 'Trailblazer'}, {'id': 43, 'name': 'Cruze'}, {'id': 44, 'name': 'Sonic'}, {'id': 45, 'name': 'Spark'}],  # Chevrolet
            10: [{'id': 46, 'name': 'X1'}, {'id': 47, 'name': 'X3'}, {'id': 48, 'name': 'X5'}, {'id': 49, 'name': '3 Series'}, {'id': 50, 'name': '5 Series'}],  # BMW
            11: [{'id': 51, 'name': 'A-Class'}, {'id': 52, 'name': 'C-Class'}, {'id': 53, 'name': 'E-Class'}, {'id': 54, 'name': 'GLA'}, {'id': 55, 'name': 'GLC'}],  # Mercedes-Benz
            12: [{'id': 56, 'name': 'A3'}, {'id': 57, 'name': 'A4'}, {'id': 58, 'name': 'Q3'}, {'id': 59, 'name': 'Q5'}, {'id': 60, 'name': 'Q7'}],  # Audi
            13: [{'id': 61, 'name': 'Golf'}, {'id': 62, 'name': 'Passat'}, {'id': 63, 'name': 'Tiguan'}, {'id': 64, 'name': 'Polo'}, {'id': 65, 'name': 'Jetta'}],  # Volkswagen
            14: [{'id': 66, 'name': 'XC40'}, {'id': 67, 'name': 'XC60'}, {'id': 68, 'name': 'XC90'}, {'id': 69, 'name': 'S60'}, {'id': 70, 'name': 'S90'}],  # Volvo
            15: [{'id': 71, 'name': 'i10'}, {'id': 72, 'name': 'i20'}, {'id': 73, 'name': 'i30'}, {'id': 74, 'name': 'Tucson'}, {'id': 75, 'name': 'Santa Fe'}],  # Hyundai
            16: [{'id': 76, 'name': 'Picanto'}, {'id': 77, 'name': 'Rio'}, {'id': 78, 'name': 'Cerato'}, {'id': 79, 'name': 'Sportage'}, {'id': 80, 'name': 'Sorento'}],  # Kia
            17: [{'id': 81, 'name': 'MG3'}, {'id': 82, 'name': 'MG5'}, {'id': 83, 'name': 'MG ZS'}, {'id': 84, 'name': 'MG HS'}, {'id': 85, 'name': 'MG RX5'}],  # MG
            18: [{'id': 86, 'name': 'Impreza'}, {'id': 87, 'name': 'Forester'}, {'id': 88, 'name': 'XV'}, {'id': 89, 'name': 'Outback'}, {'id': 90, 'name': 'BRZ'}],  # Subaru
            19: [{'id': 91, 'name': 'ES'}, {'id': 92, 'name': 'IS'}, {'id': 93, 'name': 'LS'}, {'id': 94, 'name': 'NX'}, {'id': 95, 'name': 'RX'}],  # Lexus
            20: [{'id': 96, 'name': 'Q50'}, {'id': 97, 'name': 'Q60'}, {'id': 98, 'name': 'QX30'}, {'id': 99, 'name': 'QX50'}, {'id': 100, 'name': 'QX70'}]  # Infiniti
        }
        
        if brand_id in fallback_models:
            return jsonify({'models': fallback_models[brand_id]})
        else:
            return jsonify({'models': []})

@customer.route('/api/car-years/<int:model_id>')
def get_car_years(model_id):
    """API สำหรับดึงข้อมูลปีที่ผลิตตามรุ่นรถ"""
    try:
        cursor = get_cursor()
        
        # ดึงข้อมูลปีที่ผลิตที่มีการแมทซ์ในตาราง tire_model_vehicle_targets
        cursor.execute("""
            SELECT DISTINCT cmy.production_year
            FROM car_model_years cmy
            JOIN tire_model_vehicle_targets tvt ON cmy.car_model_year_id = tvt.car_model_year_id
            WHERE cmy.car_model_id = %s
            ORDER BY cmy.production_year DESC
        """, (model_id,))
        
        years = cursor.fetchall()
        print(f"Found {len(years)} matched years for model {model_id}: {years}")
        
        # ส่งกลับเฉพาะปี
        year_list = [year['production_year'] for year in years]
        
        return jsonify({
            'years': year_list
        })
        
    except Exception as e:
        print(f"Error fetching car years: {e}")
        return jsonify({'years': []})

@customer.route('/tires')
def tires():
    """หน้ายางสำหรับลูกค้า"""
    # รับพารามิเตอร์การค้นหา
    width = request.args.get('width')
    aspect_ratio = request.args.get('aspect_ratio')
    rim_diameter = request.args.get('rim_diameter')
    brand_id = request.args.get('brand_id')
    search_query = request.args.get('search_query')
    usage_type_id = request.args.get('usage_type_id')
    car_brand_id = request.args.get('car_brand_id')
    car_model_id = request.args.get('car_model_id')
    car_year_id = request.args.get('car_year_id')  # เพิ่มการรับ car_year_id
    
    try:
        cursor = get_cursor()
        
        # สร้าง query พื้นฐาน
        base_query = """
            SELECT t.*, b.brand_name, b.brand_id, m.model_name
            FROM tires t
            JOIN tire_models m ON t.model_id = m.model_id
            JOIN brands b ON m.brand_id = b.brand_id
            WHERE 1=1
        """
        
        params = []
        
        # เพิ่มเงื่อนไขการกรอง
        if width:
            base_query += " AND t.width = %s"
            params.append(width)
        
        if aspect_ratio:
            base_query += " AND t.aspect_ratio = %s"
            params.append(aspect_ratio)
        
        if rim_diameter:
            base_query += " AND t.rim_diameter = %s"
            params.append(rim_diameter)
        
        if brand_id:
            base_query += " AND b.brand_id = %s"
            params.append(brand_id)
        
        # เพิ่มเงื่อนไขการค้นหาแบบ general search
        if search_query:
            base_query += """ AND (
                t.full_size LIKE %s OR 
                CAST(t.width AS CHAR) LIKE %s OR 
                CAST(t.aspect_ratio AS CHAR) LIKE %s OR 
                CAST(t.rim_diameter AS CHAR) LIKE %s OR
                t.load_index LIKE %s OR
                t.speed_symbol LIKE %s OR
                b.brand_name LIKE %s OR
                m.model_name LIKE %s OR
                t.service_description LIKE %s OR
                t.notes LIKE %s OR
                CONCAT(CAST(t.width AS CHAR), '/', CAST(t.aspect_ratio AS CHAR), 'R', CAST(t.rim_diameter AS CHAR)) LIKE %s OR
                CONCAT(b.brand_name, ' ', m.model_name) LIKE %s OR
                CONCAT(b.brand_name, ' ', t.full_size) LIKE %s
            )"""
            search_pattern = f"%{search_query}%"
            params.extend([search_pattern] * 13)
        
        # เพิ่มเงื่อนไขการค้นหาจากหน้า recommend
        if usage_type_id or car_brand_id or car_model_id or car_year_id:
            base_query += """ AND t.model_id IN (
                SELECT DISTINCT tm.model_id 
                FROM tire_models tm
                JOIN tire_model_vehicle_targets tvt ON tm.model_id = tvt.model_id
                WHERE 1=1
            """
            
            if usage_type_id:
                base_query += " AND tvt.usage_type_id = %s"
                params.append(usage_type_id)
            
            # ค้นหาตามลำดับ: car_brands → car_models → car_model_years → tire_model_vehicle_targets
            if car_brand_id and car_model_id and car_year_id:
                # ค้นหาตามยี่ห้อ รุ่น และปีที่ผลิต
                base_query += """ AND tvt.car_model_year_id IN (
                    SELECT cmy.car_model_year_id 
                    FROM car_model_years cmy
                    JOIN car_models cm ON cmy.car_model_id = cm.car_model_id
                    JOIN car_brands cb ON cm.car_brand_id = cb.car_brand_id
                    WHERE cb.car_brand_id = %s 
                    AND cm.car_model_id = %s 
                    AND cmy.production_year = %s
                )"""
                params.extend([car_brand_id, car_model_id, car_year_id])
            elif car_brand_id and car_model_id:
                # ค้นหาตามยี่ห้อและรุ่น
                base_query += """ AND tvt.car_model_year_id IN (
                    SELECT cmy.car_model_year_id 
                    FROM car_model_years cmy
                    JOIN car_models cm ON cmy.car_model_id = cm.car_model_id
                    JOIN car_brands cb ON cm.car_brand_id = cb.car_brand_id
                    WHERE cb.car_brand_id = %s 
                    AND cm.car_model_id = %s
                )"""
                params.extend([car_brand_id, car_model_id])
            elif car_brand_id:
                # ค้นหาตามยี่ห้อเท่านั้น
                base_query += """ AND tvt.car_model_year_id IN (
                    SELECT cmy.car_model_year_id 
                    FROM car_model_years cmy
                    JOIN car_models cm ON cmy.car_model_id = cm.car_model_id
                    JOIN car_brands cb ON cm.car_brand_id = cb.car_brand_id
                    WHERE cb.car_brand_id = %s
                )"""
                params.append(car_brand_id)
            
            base_query += ")"
            
            # เพิ่ม ORDER BY
            base_query += " ORDER BY t.full_size ASC, t.price_each ASC, t.price_set ASC"
            
            # Execute query หลัก
            print(f"Car search query: {base_query}")
            print(f"Car search params: {params}")
            cursor.execute(base_query, params)
            tires = cursor.fetchall()
            print(f"Found {len(tires)} tires for car search")
            
            # ถ้าไม่พบผลลัพธ์ ให้ลองค้นหาตามลักษณะการใช้งานเท่านั้น
            if not tires and usage_type_id:
                # ลองค้นหาตามลักษณะการใช้งานเท่านั้น
                fallback_query = """
                    SELECT t.*, b.brand_name, b.brand_id, m.model_name
                    FROM tires t
                    JOIN tire_models m ON t.model_id = m.model_id
                    JOIN brands b ON m.brand_id = b.brand_id
                    JOIN tire_model_vehicle_targets tvt ON m.model_id = tvt.model_id
                    WHERE tvt.usage_type_id = %s
                    ORDER BY t.full_size ASC, t.price_each ASC, t.price_set ASC
                """
                cursor.execute(fallback_query, (usage_type_id,))
                tires = cursor.fetchall()
                
                # ถ้ายังไม่พบ ให้แสดงยางทั่วไปทั้งหมด
                if not tires:
                    general_query = """
                        SELECT t.*, b.brand_name, b.brand_id, m.model_name
                        FROM tires t
                        JOIN tire_models m ON t.model_id = m.model_id
                        JOIN brands b ON m.brand_id = b.brand_id
                        ORDER BY t.full_size ASC, t.price_each ASC, t.price_set ASC
                        LIMIT 20
                    """
                    cursor.execute(general_query)
                    tires = cursor.fetchall()
        else:
            # เพิ่ม ORDER BY สำหรับการค้นหาทั่วไป
            base_query += " ORDER BY t.full_size ASC, t.price_each ASC, t.price_set ASC"
            
            # Execute query ทั่วไป
            print(f"General search query: {base_query}")
            print(f"General search params: {params}")
            cursor.execute(base_query, params)
            tires = cursor.fetchall()
            print(f"Found {len(tires)} tires for general search")
        
        # สร้างข้อความแสดงเงื่อนไขการค้นหา
        search_criteria = []
        
        # ถ้าไม่พบผลลัพธ์จากการค้นหาขนาดยาง ให้แสดงยางทั่วไป
        if not tires and (width or aspect_ratio or rim_diameter):
            print(f"No tires found for search criteria: width={width}, aspect_ratio={aspect_ratio}, rim_diameter={rim_diameter}")
            print(f"Query: {base_query}")
            print(f"Params: {params}")
            
            # แสดงยางทั่วไปทั้งหมด
            general_query = """
                SELECT t.*, b.brand_name, b.brand_id, m.model_name
                FROM tires t
                JOIN tire_models m ON t.model_id = m.model_id
                JOIN brands b ON m.brand_id = b.brand_id
                ORDER BY t.full_size ASC, t.price_each ASC, t.price_set ASC
                LIMIT 20
            """
            cursor.execute(general_query)
            tires = cursor.fetchall()
            print(f"Found {len(tires)} general tires")
            
            # เพิ่มข้อความแจ้งเตือนว่าพบยางทั่วไป
            if tires:
                search_criteria.append("แสดงยางทั่วไป (ไม่พบขนาดที่ตรงกัน)")
        if width:
            search_criteria.append(f"หน้ากว้าง: {width}")
        if aspect_ratio:
            search_criteria.append(f"แก้มยาง: {aspect_ratio}")
        if rim_diameter:
            search_criteria.append(f"กระทะล้อ: {rim_diameter}")
        if search_query:
            search_criteria.append(f"คำค้นหา: {search_query}")
        if usage_type_id:
            # ดึงชื่อลักษณะการใช้งาน
            cursor.execute("SELECT usage_type_name FROM usage_types WHERE usage_type_id = %s", (usage_type_id,))
            usage_type = cursor.fetchone()
            if usage_type:
                search_criteria.append(f"ลักษณะการใช้งาน: {usage_type['usage_type_name']}")
        if car_brand_id:
            # ดึงชื่อยี่ห้อรถ
            cursor.execute("SELECT car_brand_name FROM car_brands WHERE car_brand_id = %s", (car_brand_id,))
            car_brand = cursor.fetchone()
            if car_brand:
                search_criteria.append(f"ยี่ห้อรถ: {car_brand['car_brand_name']}")
        if car_model_id:
            # ดึงชื่อรุ่นรถ
            cursor.execute("SELECT car_model_name FROM car_models WHERE car_model_id = %s", (car_model_id,))
            car_model = cursor.fetchone()
            if car_model:
                search_criteria.append(f"รุ่นรถ: {car_model['car_model_name']}")
        
        if car_year_id:
            # ดึงข้อมูลปีที่ผลิต
            search_criteria.append(f"ปีที่ผลิต: {car_year_id}")
        
        search_summary = " x ".join(search_criteria) if search_criteria else "ทั้งหมด"
        
        return render_customer_template('customer/tires.html', 
                                      tires=tires, 
                                      brand=search_summary,
                                      search_criteria=search_criteria,
                                      has_search=bool(width or aspect_ratio or rim_diameter or brand_id or search_query or usage_type_id or car_brand_id or car_model_id or car_year_id),
                                      usage_type_id=usage_type_id,
                                      car_brand_id=car_brand_id,
                                      car_model_id=car_model_id,
                                      car_year_id=car_year_id)
        
    except Exception as e:
        print(f"Error in tires search: {e}")
        return render_customer_template('customer/tires.html', 
                                      tires=[], 
                                      brand="ไม่พบข้อมูล",
                                      search_criteria=[],
                                      has_search=False)

@customer.route('/tires/<brand>')
def tires_by_brand(brand):
    """หน้ายางตามแบรนด์"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # แปลงชื่อแบรนด์ให้ตรงกับฐานข้อมูล
        brand_mapping = {
            'bfgoodrich': 'BFGoodrich',
            'michelin': 'Michelin',
            'maxxis': 'Maxxis'
        }
        
        brand_name = brand_mapping.get(brand.lower(), brand.title())
        
        print(f"Loading tires for brand: {brand_name}")
        
        # ตรวจสอบโครงสร้างตาราง tires ก่อน
        cursor.execute("DESCRIBE tires")
        columns = cursor.fetchall()
        print(f"Tire table columns: {[col['Field'] for col in columns]}")
        
        # ลองดึงข้อมูลทั้งหมดก่อน
        cursor.execute("SELECT * FROM tires LIMIT 5")
        sample_tires = cursor.fetchall()
        print(f"Sample tires: {sample_tires}")
        
        # ดึงข้อมูลยางตามแบรนด์
        cursor.execute('''
            SELECT t.*, b.brand_name, m.model_name
            FROM tires t
            JOIN tire_models m ON t.model_id = m.model_id
            JOIN brands b ON m.brand_id = b.brand_id
            WHERE b.brand_name = %s 
            ORDER BY t.full_size ASC, t.price_each ASC, t.price_set ASC
        ''', (brand_name,))
        
        tires = cursor.fetchall()
        print(f"Found {len(tires)} tires for {brand_name}")
        
        cursor.close()
        
        # เลือก template ตามแบรนด์
        if brand.lower() == 'bfgoodrich':
            template_name = 'customer/tires_bfgoodrich.html'
        elif brand.lower() == 'michelin':
            template_name = 'customer/tires_michelin.html'
        elif brand.lower() == 'maxxis':
            template_name = 'customer/tires_maxxis.html'
        else:
            template_name = 'customer/tires.html'
        
        return render_customer_template(template_name, tires=tires, brand=brand_name)
        
    except Exception as e:
        print(f"Error loading {brand} tires: {e}")
        # เลือก template ตามแบรนด์
        if brand.lower() == 'bfgoodrich':
            template_name = 'customer/tires_bfgoodrich.html'
        elif brand.lower() == 'michelin':
            template_name = 'customer/tires_michelin.html'
        elif brand.lower() == 'maxxis':
            template_name = 'customer/tires_maxxis.html'
        else:
            template_name = 'customer/tires.html'
        
        return render_customer_template(template_name, tires=[], brand=brand)

@customer.route('/compare')
def compare():
    """หน้าเปรียบเทียบยาง"""
    return render_customer_template('customer/compare.html')

@customer.route('/booking', methods=['GET', 'POST'])
@customer_login_required
def booking():
    """หน้าจองบริการ"""
    
    if request.method == 'POST':
        try:
            customer_id = session.get('customer_id')
            if not customer_id:
                flash('กรุณาเข้าสู่ระบบก่อนจองบริการ', 'error')
                return redirect(url_for('customer.login'))
            
            # ดึงข้อมูลจากฟอร์ม
            preferred_date = request.form.get('preferred_date', '')
            preferred_time = request.form.get('preferred_time', '')
            notes = request.form.get('notes', '').strip()
            
            # ตรวจสอบข้อมูลที่จำเป็น
            if not preferred_date:
                flash('กรุณาเลือกวันที่ที่ต้องการจอง', 'error')
                return redirect(url_for('customer.booking'))
            
            # ถ้าไม่มี preferred_time ให้ใช้ค่าเริ่มต้น
            if not preferred_time:
                preferred_time = '09:00'
            
            # วันที่และเวลาปัจจุบัน (วันที่จอง)
            current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # ดึงข้อมูลรถจากฟอร์ม
            vehicle_type_id = request.form.get('vehicle_type_id', '').strip()
            engine_type = request.form.get('engine_type', '').strip()
            license_plate = request.form.get('license_plate', '').strip()
            license_province = request.form.get('license_province', '').strip()
            brand_id = request.form.get('brand_id', '').strip()
            model_name = request.form.get('model_name', '').strip()
            color = request.form.get('color', '').strip()
            production_year = request.form.get('production_year', '').strip()
            
            # หา vehicle_id ที่มีอยู่แล้วหรือสร้างใหม่
            vehicle_id = None
            
            # ตรวจสอบว่ามีรถที่มีข้อมูลเดียวกันอยู่แล้วหรือไม่
            if license_plate and license_province:
                cursor = get_cursor()
                cursor.execute('''
                    SELECT vehicle_id FROM vehicles 
                    WHERE customer_id = %s AND license_plate = %s AND license_province = %s
                    LIMIT 1
                ''', (customer_id, license_plate, license_province))
                existing_vehicle = cursor.fetchone()
                
                if existing_vehicle:
                    vehicle_id = existing_vehicle['vehicle_id']
                else:
                    # ดึงชื่อยี่ห้อรถจาก brand_id
                    brand_name = ''
                    if brand_id:
                        cursor.execute('SELECT car_brand_name FROM car_brands WHERE car_brand_id = %s', (brand_id,))
                        brand_result = cursor.fetchone()
                        if brand_result:
                            brand_name = brand_result['car_brand_name']
                    
                    # สร้างรถใหม่
                    cursor.execute('''
                        INSERT INTO vehicles (customer_id, vehicle_type_id, engine_type_name, license_plate, license_province, brand_name, model_name, color, production_year)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (customer_id, vehicle_type_id, engine_type, license_plate, license_province, 
                          brand_name, model_name, color, production_year))
                    vehicle_id = cursor.lastrowid
            
            # ถ้าไม่มีข้อมูลรถ ให้ใช้ vehicle_id = 1 (default)
            if not vehicle_id:
                vehicle_id = 1
            
            # บันทึกข้อมูลการจอง
            cursor.execute('''
                INSERT INTO bookings (customer_id, vehicle_id, booking_date, service_date, service_time, status, note) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (customer_id, vehicle_id, current_datetime, preferred_date, preferred_time, 'รอดำเนินการ', notes))
            
            booking_id = cursor.lastrowid
            
            # บันทึกข้อมูลบริการที่เลือก
            service_ids = request.form.getlist('service_id')
            for service_id in service_ids:
                cursor.execute('''
                    INSERT INTO booking_items (booking_id, service_id, quantity) 
                    VALUES (%s, %s, %s)
                ''', (booking_id, service_id, 1))
                
                # บันทึกตัวเลือกของบริการ
                option_ids = request.form.getlist(f'service_option_{service_id}')
                for option_id in option_ids:
                    cursor.execute('''
                        INSERT INTO booking_item_options (item_id, option_id) 
                        VALUES (LAST_INSERT_ID(), %s)
                    ''', (option_id,))
            
            # บันทึกข้อมูลยาง
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
            flash('จองบริการสำเร็จแล้ว', 'success')
            return redirect(url_for('customer.home'))
            
        except Exception as e:
            print(f"Error in booking: {e}")
            flash('เกิดข้อผิดพลาดในการจองบริการ', 'error')
            return redirect(url_for('customer.booking'))

    try:
        cursor = get_cursor()
        
        # ดึงข้อมูลที่จำเป็นสำหรับฟอร์ม
        # 1. ประเภทรถ
        cursor.execute('SELECT vehicle_type_id, vehicle_type_name FROM vehicle_types ORDER BY vehicle_type_name')
        vehicle_types = cursor.fetchall()
        print(f"Vehicle types found: {vehicle_types}")  # Debug print
        print(f"Vehicle types count: {len(vehicle_types)}")  # Debug print
        
        # ถ้าไม่มีข้อมูลในฐานข้อมูล ให้ใช้ข้อมูลตัวอย่าง
        if not vehicle_types:
            vehicle_types = [
                {'vehicle_type_id': 1, 'vehicle_type_name': 'รถเก๋ง'},
                {'vehicle_type_id': 2, 'vehicle_type_name': 'SUV'},
                {'vehicle_type_id': 3, 'vehicle_type_name': 'กระบะ/รถตู้'}
            ]
            print("Using fallback vehicle types")

        # 2. จังหวัด
        try:
            cursor.execute('SELECT province_name FROM provinces ORDER BY province_name')
            provinces = [row['province_name'] for row in cursor.fetchall()]
        except:
            # ถ้าไม่มีตาราง provinces ให้ใช้ข้อมูลตัวอย่าง
            provinces = ['กรุงเทพมหานคร', 'กระบี่', 'กาญจนบุรี', 'กาฬสินธุ์', 'กำแพงเพชร', 'ขอนแก่น', 'จันทบุรี', 'ฉะเชิงเทรา', 'ชลบุรี', 'ชัยนาท', 'ชัยภูมิ', 'ชุมพร', 'เชียงราย', 'เชียงใหม่', 'ตรัง', 'ตราด', 'ตาก', 'นครนายก', 'นครปฐม', 'นครพนม', 'นครราชสีมา', 'นครศรีธรรมราช', 'นครสวรรค์', 'นนทบุรี', 'นราธิวาส', 'น่าน', 'บึงกาฬ', 'บุรีรัมย์', 'ปทุมธานี', 'ประจวบคีรีขันธ์', 'ปราจีนบุรี', 'ปัตตานี', 'พระนครศรีอยุธยา', 'พังงา', 'พัทลุง', 'พิจิตร', 'พิษณุโลก', 'เพชรบุรี', 'เพชรบูรณ์', 'แพร่', 'พะเยา', 'ภูเก็ต', 'มหาสารคาม', 'มุกดาหาร', 'แม่ฮ่องสอน', 'ยะลา', 'ยโสธร', 'ร้อยเอ็ด', 'ระนอง', 'ระยอง', 'ราชบุรี', 'ลพบุรี', 'ลำปาง', 'ลำพูน', 'เลย', 'ศรีสะเกษ', 'สกลนคร', 'สงขลา', 'สตูล', 'สมุทรปราการ', 'สมุทรสงคราม', 'สมุทรสาคร', 'สระแก้ว', 'สระบุรี', 'สิงห์บุรี', 'สุโขทัย', 'สุพรรณบุรี', 'สุราษฎร์ธานี', 'สุรินทร์', 'หนองคาย', 'หนองบัวลำภู', 'อ่างทอง', 'อุดรธานี', 'อุทัยธานี', 'อุตรดิตถ์', 'อุบลราชธานี', 'อำนาจเจริญ']
            print("Using fallback provinces")
        
        # 3. ยี่ห้อรถ
        try:
            cursor.execute('SELECT car_brand_id as brand_id, car_brand_name as brand_name FROM car_brands ORDER BY car_brand_name')
            vehicle_brands = cursor.fetchall()
            print(f"Vehicle brands found: {len(vehicle_brands)} brands")
        except Exception as e:
            print(f"Error fetching vehicle brands: {e}")
            vehicle_brands = [
                {'brand_id': 1, 'brand_name': 'Toyota'},
                {'brand_id': 2, 'brand_name': 'Honda'},
                {'brand_id': 3, 'brand_name': 'Nissan'},
                {'brand_id': 4, 'brand_name': 'Mazda'},
                {'brand_id': 5, 'brand_name': 'Mitsubishi'},
                {'brand_id': 6, 'brand_name': 'Suzuki'},
                {'brand_id': 7, 'brand_name': 'Isuzu'},
                {'brand_id': 8, 'brand_name': 'Ford'},
                {'brand_id': 9, 'brand_name': 'Chevrolet'},
                {'brand_id': 10, 'brand_name': 'BMW'},
                {'brand_id': 11, 'brand_name': 'Mercedes-Benz'},
                {'brand_id': 12, 'brand_name': 'Audi'},
                {'brand_id': 13, 'brand_name': 'Volkswagen'},
                {'brand_id': 14, 'brand_name': 'Volvo'},
                {'brand_id': 15, 'brand_name': 'Hyundai'},
                {'brand_id': 16, 'brand_name': 'Kia'},
                {'brand_id': 17, 'brand_name': 'MG'},
                {'brand_id': 18, 'brand_name': 'Subaru'},
                {'brand_id': 19, 'brand_name': 'Lexus'},
                {'brand_id': 20, 'brand_name': 'Infiniti'}
            ]
            print("Using fallback vehicle_brands")
        
        # 4. ยี่ห้อยาง
        try:
            cursor.execute('SELECT brand_id, brand_name FROM brands ORDER BY brand_name')
            brands = cursor.fetchall()
        except:
            brands = []
            print("Using fallback brands")
        
        # 5. บริการที่จัดกลุ่ม
        try:
            cursor.execute('''
                SELECT s.service_id, s.service_name, s.service_category, s.service_description,
                       so.option_id, so.option_name, so.option_price
                FROM services s
                LEFT JOIN service_options so ON s.service_id = so.service_id
                WHERE s.is_active = 1
                ORDER BY s.service_category, s.service_name, so.option_name
            ''')
            services_data = cursor.fetchall()
        except:
            # ถ้าไม่มีตาราง services ให้ใช้ข้อมูลตัวอย่าง
            services_data = [
                # ยาง
                {'service_id': 1, 'service_name': 'ขับปอนด์ล้อ', 'service_category': 'ยาง', 'service_description': 'ขับปอนด์ล้อ', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 2, 'service_name': 'จุ๊บ', 'service_category': 'ยาง', 'service_description': 'จุ๊บลมยาง', 'option_id': 1, 'option_name': 'ยาง', 'option_price': 0},
                {'service_id': 2, 'service_name': 'จุ๊บ', 'service_category': 'ยาง', 'service_description': 'จุ๊บลมยาง', 'option_id': 2, 'option_name': 'เซ็นเซอร์', 'option_price': 0},
                {'service_id': 2, 'service_name': 'จุ๊บ', 'service_category': 'ยาง', 'service_description': 'จุ๊บลมยาง', 'option_id': 3, 'option_name': 'เหล็ก', 'option_price': 0},
                {'service_id': 3, 'service_name': 'ตั้งศูนย์', 'service_category': 'ยาง', 'service_description': 'ตั้งศูนย์ล้อ', 'option_id': 4, 'option_name': '2 ล้อ', 'option_price': 0},
                {'service_id': 3, 'service_name': 'ตั้งศูนย์', 'service_category': 'ยาง', 'service_description': 'ตั้งศูนย์ล้อ', 'option_id': 5, 'option_name': '4 ล้อ', 'option_price': 0},
                {'service_id': 4, 'service_name': 'ถ่วงล้อ', 'service_category': 'ยาง', 'service_description': 'ถ่วงล้อ', 'option_id': 6, 'option_name': '2 ล้อ', 'option_price': 0},
                {'service_id': 4, 'service_name': 'ถ่วงล้อ', 'service_category': 'ยาง', 'service_description': 'ถ่วงล้อ', 'option_id': 7, 'option_name': '4 ล้อ', 'option_price': 0},
                {'service_id': 4, 'service_name': 'ถ่วงล้อ', 'service_category': 'ยาง', 'service_description': 'ถ่วงล้อ', 'option_id': 8, 'option_name': 'กระทะ', 'option_price': 0},
                {'service_id': 4, 'service_name': 'ถ่วงล้อ', 'service_category': 'ยาง', 'service_description': 'ถ่วงล้อ', 'option_id': 9, 'option_name': 'แม็ก', 'option_price': 0},
                {'service_id': 5, 'service_name': 'ถอดใส่ยาง', 'service_category': 'ยาง', 'service_description': 'ถอดใส่ยาง', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 6, 'service_name': 'ปะยาง', 'service_category': 'ยาง', 'service_description': 'ปะยาง', 'option_id': 10, 'option_name': 'ดอกเห็ด PRP', 'option_price': 0},
                {'service_id': 6, 'service_name': 'ปะยาง', 'service_category': 'ยาง', 'service_description': 'ปะยาง', 'option_id': 11, 'option_name': 'แผ่นปะ', 'option_price': 0},
                {'service_id': 6, 'service_name': 'ปะยาง', 'service_category': 'ยาง', 'service_description': 'ปะยาง', 'option_id': 12, 'option_name': 'ใยไหม', 'option_price': 0},
                {'service_id': 7, 'service_name': 'ยางเก่า', 'service_category': 'ยาง', 'service_description': 'จัดการยางเก่า', 'option_id': 13, 'option_name': 'ทิ้งไว้ที่ร้าน', 'option_price': 0},
                {'service_id': 7, 'service_name': 'ยางเก่า', 'service_category': 'ยาง', 'service_description': 'จัดการยางเก่า', 'option_id': 14, 'option_name': 'นำกลับ', 'option_price': 0},
                {'service_id': 8, 'service_name': 'สลับยาง', 'service_category': 'ยาง', 'service_description': 'สลับยาง', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 9, 'service_name': 'เติมลม', 'service_category': 'ยาง', 'service_description': 'เติมลมยาง', 'option_id': 15, 'option_name': 'ธรรมดา', 'option_price': 0},
                {'service_id': 9, 'service_name': 'เติมลม', 'service_category': 'ยาง', 'service_description': 'เติมลมยาง', 'option_id': 16, 'option_name': 'ไนโตรเจน', 'option_price': 50},
                
                # ระบบเบรก
                {'service_id': 10, 'service_name': 'ตรวจเช็กทำความสะอาดเบรก', 'service_category': 'ระบบเบรก', 'service_description': 'ตรวจเช็กทำความสะอาดเบรก', 'option_id': 17, 'option_name': 'น้ำยาล้างเบรก', 'option_price': 0},
                {'service_id': 11, 'service_name': 'น้ำมันเบรก DOT', 'service_category': 'ระบบเบรก', 'service_description': 'น้ำมันเบรก DOT', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 12, 'service_name': 'ผ้าเบรกหน้า', 'service_category': 'ระบบเบรก', 'service_description': 'ผ้าเบรกหน้า', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 13, 'service_name': 'ผ้าเบรกหลัง', 'service_category': 'ระบบเบรก', 'service_description': 'ผ้าเบรกหลัง', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 14, 'service_name': 'เจียรจาน', 'service_category': 'ระบบเบรก', 'service_description': 'เจียรจานเบรก', 'option_id': 18, 'option_name': 'หน้า', 'option_price': 0},
                {'service_id': 14, 'service_name': 'เจียรจาน', 'service_category': 'ระบบเบรก', 'service_description': 'เจียรจานเบรก', 'option_id': 19, 'option_name': 'หลัง', 'option_price': 0},
                {'service_id': 15, 'service_name': 'เปลี่ยนจาน', 'service_category': 'ระบบเบรก', 'service_description': 'เปลี่ยนจานเบรก', 'option_id': 20, 'option_name': 'หน้า', 'option_price': 0},
                {'service_id': 15, 'service_name': 'เปลี่ยนจาน', 'service_category': 'ระบบเบรก', 'service_description': 'เปลี่ยนจานเบรก', 'option_id': 21, 'option_name': 'หลัง', 'option_price': 0},
                
                # ไฟฟ้า
                {'service_id': 16, 'service_name': 'น้ำกลั่น', 'service_category': 'ไฟฟ้า', 'service_description': 'น้ำกลั่นแบตเตอรี่', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 17, 'service_name': 'หลอดไฟ', 'service_category': 'ไฟฟ้า', 'service_description': 'หลอดไฟ', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 18, 'service_name': 'แบตเตอรี่', 'service_category': 'ไฟฟ้า', 'service_description': 'แบตเตอรี่', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 19, 'service_name': 'ใบปัดน้ำฝน', 'service_category': 'ไฟฟ้า', 'service_description': 'ใบปัดน้ำฝน', 'option_id': None, 'option_name': None, 'option_price': None},
                
                # บำรุงรักษา
                {'service_id': 20, 'service_name': 'น้ำมันเกียร์', 'service_category': 'บำรุงรักษา', 'service_description': 'น้ำมันเกียร์', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 21, 'service_name': 'น้ำมันเครื่อง', 'service_category': 'บำรุงรักษา', 'service_description': 'น้ำมันเครื่อง', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 22, 'service_name': 'น้ำมันเฟืองท้าย', 'service_category': 'บำรุงรักษา', 'service_description': 'น้ำมันเฟืองท้าย', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 23, 'service_name': 'ไส้กรองน้ำมันเครื่อง', 'service_category': 'บำรุงรักษา', 'service_description': 'ไส้กรองน้ำมันเครื่อง', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 24, 'service_name': 'ไส้กรองอากาศ', 'service_category': 'บำรุงรักษา', 'service_description': 'ไส้กรองอากาศ', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 25, 'service_name': 'ไส้กรองแอร์', 'service_category': 'บำรุงรักษา', 'service_description': 'ไส้กรองแอร์', 'option_id': None, 'option_name': None, 'option_price': None},
                
                # ช่วงล่าง
                {'service_id': 26, 'service_name': 'โช้คอัพหน้า', 'service_category': 'ช่วงล่าง', 'service_description': 'โช้คอัพหน้า', 'option_id': None, 'option_name': None, 'option_price': None},
                {'service_id': 27, 'service_name': 'โช้คอัพหลัง', 'service_category': 'ช่วงล่าง', 'service_description': 'โช้คอัพหลัง', 'option_id': None, 'option_name': None, 'option_price': None}
            ]
            print("Using fallback services data")
        
        # จัดกลุ่มบริการ
        service_groups = {}
        print(f"Services data found: {len(services_data)}")  # Debug print
        print(f"Services data: {services_data}")  # Debug print
        
        for row in services_data:
            category = row['service_category'] or 'บริการทั่วไป'
            if category not in service_groups:
                service_groups[category] = []
            
            # หาบริการที่มีอยู่แล้ว
            existing_service = None
            for service in service_groups[category]:
                if service['service_id'] == row['service_id']:
                    existing_service = service
                    break
            
            if existing_service is None:
                # สร้างบริการใหม่
                service = {
                    'service_id': row['service_id'],
                    'service_name': row['service_name'],
                    'service_description': row['service_description'],
                    'options': []
                }
                service_groups[category].append(service)
                existing_service = service
            
            # เพิ่มตัวเลือกถ้ามี
            if row['option_id']:
                existing_service['options'].append({
                    'option_id': row['option_id'],
                    'option_name': row['option_name'],
                    'option_price': row['option_price']
                })
        
        print(f"Service groups: {service_groups}")  # Debug print
        
        # ดึงข้อมูลลูกค้าที่มีอยู่ (ถ้ามี)
        customer_data = None
        print(f"Session customer_id: {session.get('customer_id')}")
        if session.get('customer_id'):
            try:
                # ดึงข้อมูลลูกค้าและที่อยู่จากตาราง addresses
                cursor.execute('''
                    SELECT c.*, a.*
                    FROM customers c
                    LEFT JOIN addresses a ON c.customer_id = a.customer_id
                    WHERE c.customer_id = %s
                    ORDER BY a.address_id ASC
                    LIMIT 1
                ''', (session.get('customer_id'),))
                customer_data = cursor.fetchone()
                print(f"Customer data with address: {customer_data}")
            except Exception as e:
                print(f"Error fetching customer data with address: {e}")
                # ถ้าไม่มีตาราง addresses ให้ดึงเฉพาะข้อมูลลูกค้า
                try:
                    cursor.execute('''
                        SELECT c.*
                        FROM customers c
                        WHERE c.customer_id = %s
                    ''', (session.get('customer_id'),))
                    customer_data = cursor.fetchone()
                    print(f"Customer data without address: {customer_data}")
                except Exception as e2:
                    print(f"Error fetching customer data: {e2}")
                    customer_data = None
                    print("Using fallback customer_data")
        else:
            print("No customer_id in session")
        
        # ดึงข้อมูลรถทั้งหมดของลูกค้า (ถ้ามี)
        customer_vehicles = []
        vehicle_data = None
        print(f"Fetching vehicle data for customer_id: {session.get('customer_id')}")
        if session.get('customer_id') and customer_data:
            try:
                # ตรวจสอบว่าลูกค้าคนนี้เคยมีประวัติการจองหรือไม่
                cursor.execute('''
                    SELECT COUNT(*) as booking_count
                    FROM bookings
                    WHERE customer_id = %s
                ''', (session.get('customer_id'),))
                booking_count = cursor.fetchone()['booking_count']
                print(f"Booking count for customer {session.get('customer_id')}: {booking_count}")
                
                # ถ้าเคยมีประวัติการจอง ให้ดึงข้อมูลรถที่เคยใช้ในการจอง
                if booking_count > 0:
                    cursor.execute('''
                        SELECT DISTINCT v.*, vt.vehicle_type_name
                        FROM vehicles v
                        LEFT JOIN vehicle_types vt ON v.vehicle_type_id = vt.vehicle_type_id
                        JOIN bookings b ON v.vehicle_id = b.vehicle_id
                        WHERE b.customer_id = %s AND v.customer_id = %s
                        ORDER BY v.vehicle_id DESC
                    ''', (session.get('customer_id'), session.get('customer_id')))
                    customer_vehicles = cursor.fetchall()
                    print(f"Customer vehicles found from booking history: {len(customer_vehicles)} vehicles")
                else:
                    print("No booking history found - customer has never booked before")
                    customer_vehicles = []
                
                # ไม่ใช้รถใดเป็นข้อมูลเริ่มต้น - ให้ฟอร์มเป็นค่าว่าง
                vehicle_data = None
                print(f"Form will start empty - customer needs to select a vehicle")
                
            except Exception as e:
                print(f"Error fetching vehicle data: {e}")
                customer_vehicles = []
                vehicle_data = None
                print("Using fallback vehicle_data")
        else:
            print("No customer_id in session or no customer_data for vehicle data")
            customer_vehicles = []
        

        

        
        print(f"Final service_groups being sent to template: {service_groups}")  # Debug print
        print(f"Vehicle brands being sent to template: {len(vehicle_brands)} brands")  # Debug print
        print(f"Customer data being sent to template: {customer_data}")  # Debug print
        print(f"Vehicle data being sent to template: {vehicle_data}")  # Debug print
        print(f"Customer vehicles being sent to template: {len(customer_vehicles)} vehicles")  # Debug print
        return render_customer_template('customer/booking.html',
                                      vehicle_types=vehicle_types,
                                      provinces=provinces,
                                      vehicle_brands=vehicle_brands,
                                      brands=brands,
                                      service_groups=service_groups,
                                      customer_data=customer_data,
                                      vehicle_data=vehicle_data,
                                      customer_vehicles=customer_vehicles,
                                      user_name=session.get('customer_name', ''))
        
    except Exception as e:
        print(f"Error in booking: {e}")
        # ใช้ข้อมูล fallback เมื่อเกิด error
        vehicle_types = [
            {'vehicle_type_id': 1, 'vehicle_type_name': 'รถเก๋ง'},
            {'vehicle_type_id': 2, 'vehicle_type_name': 'SUV'},
            {'vehicle_type_id': 3, 'vehicle_type_name': 'กระบะ/รถตู้'}
        ]
        provinces = ['กรุงเทพมหานคร', 'กระบี่', 'กาญจนบุรี', 'กาฬสินธุ์', 'กำแพงเพชร', 'ขอนแก่น', 'จันทบุรี', 'ฉะเชิงเทรา', 'ชลบุรี', 'ชัยนาท', 'ชัยภูมิ', 'ชุมพร', 'เชียงราย', 'เชียงใหม่', 'ตรัง', 'ตราด', 'ตาก', 'นครนายก', 'นครปฐม', 'นครพนม', 'นครราชสีมา', 'นครศรีธรรมราช', 'นครสวรรค์', 'นนทบุรี', 'นราธิวาส', 'น่าน', 'บึงกาฬ', 'บุรีรัมย์', 'ปทุมธานี', 'ประจวบคีรีขันธ์', 'ปราจีนบุรี', 'ปัตตานี', 'พระนครศรีอยุธยา', 'พังงา', 'พัทลุง', 'พิจิตร', 'พิษณุโลก', 'เพชรบุรี', 'เพชรบูรณ์', 'แพร่', 'พะเยา', 'ภูเก็ต', 'มหาสารคาม', 'มุกดาหาร', 'แม่ฮ่องสอน', 'ยะลา', 'ยโสธร', 'ร้อยเอ็ด', 'ระนอง', 'ระยอง', 'ราชบุรี', 'ลพบุรี', 'ลำปาง', 'ลำพูน', 'เลย', 'ศรีสะเกษ', 'สกลนคร', 'สงขลา', 'สตูล', 'สมุทรปราการ', 'สมุทรสงคราม', 'สมุทรสาคร', 'สระแก้ว', 'สระบุรี', 'สิงห์บุรี', 'สุโขทัย', 'สุพรรณบุรี', 'สุราษฎร์ธานี', 'สุรินทร์', 'หนองคาย', 'หนองบัวลำภู', 'อ่างทอง', 'อุดรธานี', 'อุทัยธานี', 'อุตรดิตถ์', 'อุบลราชธานี', 'อำนาจเจริญ']
        vehicle_brands = [
            {'brand_id': 1, 'brand_name': 'Toyota'},
            {'brand_id': 2, 'brand_name': 'Honda'},
            {'brand_id': 3, 'brand_name': 'Nissan'},
            {'brand_id': 4, 'brand_name': 'Mazda'},
            {'brand_id': 5, 'brand_name': 'Mitsubishi'},
            {'brand_id': 6, 'brand_name': 'Suzuki'},
            {'brand_id': 7, 'brand_name': 'Isuzu'},
            {'brand_id': 8, 'brand_name': 'Ford'},
            {'brand_id': 9, 'brand_name': 'Chevrolet'},
            {'brand_id': 10, 'brand_name': 'BMW'},
            {'brand_id': 11, 'brand_name': 'Mercedes-Benz'},
            {'brand_id': 12, 'brand_name': 'Audi'},
            {'brand_id': 13, 'brand_name': 'Volkswagen'},
            {'brand_id': 14, 'brand_name': 'Volvo'},
            {'brand_id': 15, 'brand_name': 'Hyundai'},
            {'brand_id': 16, 'brand_name': 'Kia'},
            {'brand_id': 17, 'brand_name': 'MG'},
            {'brand_id': 18, 'brand_name': 'Subaru'},
            {'brand_id': 19, 'brand_name': 'Lexus'},
            {'brand_id': 20, 'brand_name': 'Infiniti'}
        ]
        return render_customer_template('customer/booking.html',
                                      vehicle_types=vehicle_types,
                                      provinces=provinces,
                                      vehicle_brands=vehicle_brands,
                                      brands=[],
                                      service_groups={},
                                      customer_data=None,
                                      vehicle_data=None,
                                      customer_vehicles=[],
                                      user_name=session.get('customer_name', ''))

@customer.route('/recommend', methods=['GET', 'POST'])
def recommend():
    """หน้าแนะนำยาง"""
    try:
        cursor = get_cursor()
        
        # ดึงข้อมูลลักษณะการใช้งาน
        cursor.execute('SELECT usage_type_id, usage_type_name FROM usage_types ORDER BY usage_type_name')
        usage_types = cursor.fetchall()
        
        recommended_tires = None
        
        if request.method == 'POST':
            usage_type_id = request.form.get('usage_type_id')
            car_brand_id = request.form.get('car_brand_id')
            car_model_id = request.form.get('car_model_id')
            
            # สร้าง query สำหรับค้นหายาง
            base_query = """
                SELECT DISTINCT t.tire_id, t.full_size as name, t.width, t.aspect_ratio, t.rim_diameter,
                       t.load_index, t.speed_symbol as speed_rating, t.price_each, t.price_set, 
                       tm.model_name, b.brand_name
                FROM tires t
                JOIN tire_models tm ON t.model_id = tm.model_id
                JOIN brands b ON tm.brand_id = b.brand_id
                JOIN tire_model_vehicle_targets tvt ON tm.model_id = tvt.model_id
                WHERE 1=1
            """
            
            params = []
            
            # เพิ่มเงื่อนไขการค้นหา
            if usage_type_id:
                base_query += " AND tvt.usage_type_id = %s"
                params.append(usage_type_id)
            
            if car_brand_id:
                base_query += " AND tvt.car_model_year_id IN (SELECT car_model_year_id FROM car_model_years WHERE car_model_id IN (SELECT car_model_id FROM car_models WHERE car_brand_id = %s))"
                params.append(car_brand_id)
            
            if car_model_id:
                base_query += " AND tvt.car_model_year_id IN (SELECT car_model_year_id FROM car_model_years WHERE car_model_id = %s)"
                params.append(car_model_id)
            
            base_query += " ORDER BY t.price_each ASC"
            
            cursor.execute(base_query, params)
            recommended_tires = cursor.fetchall()
            
            # ถ้าไม่พบยางที่ตรงกัน ให้แสดงยางทั่วไปตามลักษณะการใช้งาน
            if not recommended_tires and usage_type_id:
                fallback_query = """
                    SELECT DISTINCT t.tire_id, t.full_size as name, t.width, t.aspect_ratio, t.rim_diameter,
                           t.load_index, t.speed_symbol as speed_rating, t.price_each, t.price_set, 
                           tm.model_name, b.brand_name
                    FROM tires t
                    JOIN tire_models tm ON t.model_id = tm.model_id
                    JOIN brands b ON tm.brand_id = b.brand_id
                    JOIN tire_model_vehicle_targets tvt ON tm.model_id = tvt.model_id
                    WHERE tvt.usage_type_id = %s
                    ORDER BY t.price_each ASC
                    LIMIT 10
                """
                cursor.execute(fallback_query, (usage_type_id,))
                recommended_tires = cursor.fetchall()
            
            # ถ้ายังไม่พบ ให้แสดงยางทั่วไปทั้งหมด
            if not recommended_tires:
                general_query = """
                    SELECT DISTINCT t.tire_id, t.full_size as name, t.width, t.aspect_ratio, t.rim_diameter,
                           t.load_index, t.speed_symbol as speed_rating, t.price_each, t.price_set, 
                           tm.model_name, b.brand_name
                    FROM tires t
                    JOIN tire_models tm ON t.model_id = tm.model_id
                    JOIN brands b ON tm.brand_id = b.brand_id
                    ORDER BY t.price_each ASC
                    LIMIT 10
                """
                cursor.execute(general_query)
                recommended_tires = cursor.fetchall()
            
            # Redirect ไปยังหน้า tires.html พร้อมส่งพารามิเตอร์
            if recommended_tires:
                # สร้าง query string สำหรับ redirect
                query_params = []
                if usage_type_id:
                    query_params.append(f"usage_type_id={usage_type_id}")
                if car_brand_id:
                    query_params.append(f"car_brand_id={car_brand_id}")
                if car_model_id:
                    query_params.append(f"car_model_id={car_model_id}")
                
                query_string = "&".join(query_params)
                return redirect(url_for('customer.tires') + "?" + query_string)
            else:
                flash("ไม่พบยางที่ตรงกับเงื่อนไข กรุณาลองเปลี่ยนเงื่อนไขการค้นหา", "error")
                return redirect(url_for('customer.recommend'))
        
        return render_customer_template('customer/recommend.html', 
                                      usage_types=usage_types, 
                                      recommended_tires=recommended_tires)
        
    except Exception as e:
        print(f"Error in recommend: {e}")
        return render_customer_template('customer/recommend.html', 
                                      usage_types=[], 
                                      recommended_tires=[])

@customer.route('/promotions')
def promotions():
    """หน้าโปรโมชั่น"""
    try:
        cursor = get_cursor()
        
        # ดึงข้อมูลโปรโมชันที่ใช้งานได้ (มีวันที่ปัจจุบันอยู่ในช่วงโปรโมชัน)
        cursor.execute("""
            SELECT promotion_id, title, description, image_url,
                   start_date, end_date
            FROM promotions
            WHERE start_date <= CURDATE() AND end_date >= CURDATE()
            ORDER BY start_date DESC
        """)
        promotions = cursor.fetchall()
        print(f"Promotions page - Found {len(promotions)} active promotions: {promotions}")
        
        return render_customer_template('customer/promotions.html', promotions=promotions)
        
    except Exception as e:
        print(f"Error loading promotions: {e}")
        return render_customer_template('customer/promotions.html', promotions=[])

@customer.route('/promotions/<int:promotion_id>')
def promotion_detail(promotion_id):
    """หน้ารายละเอียดโปรโมชั่น"""
    try:
        cursor = get_cursor()
        
        # ดึงข้อมูลโปรโมชันตาม ID
        cursor.execute("""
            SELECT promotion_id, title, description, image_url,
                   start_date, end_date
            FROM promotions
            WHERE promotion_id = %s
        """, (promotion_id,))
        promotion = cursor.fetchone()
        
        if not promotion:
            flash('ไม่พบโปรโมชันที่ต้องการ', 'error')
            return redirect(url_for('customer.promotions'))
        
        return render_customer_template('customer/promotion_detail.html', promotion=promotion)
        
    except Exception as e:
        print(f"Error loading promotion detail: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดข้อมูลโปรโมชัน', 'error')
        return redirect(url_for('customer.promotions'))

@customer.route('/guide')
def guide():
    """หน้าไกด์"""
    return render_customer_template('customer/guide.html')

@customer.route('/contact')
def contact():
    """หน้าติดต่อ"""
    return render_customer_template('customer/contact.html')

@customer.route('/booking-history')
@customer_login_required
def booking_history():
    """หน้ารายการประวัติการจองของลูกค้า"""
    try:
        cursor = get_cursor()
        customer_id = session.get('customer_id')
        
        # รับพารามิเตอร์จาก URL
        page = int(request.args.get('page', 1))
        status_filter = request.args.get('status', '')
        date_filter = request.args.get('date_filter', '')
        per_page = 10
        offset = (page - 1) * per_page
        
        # สร้าง query พื้นฐาน
        base_query = """
            SELECT b.booking_id, b.booking_date, b.service_date, b.service_time, b.status, b.note,
                   v.license_plate, v.brand_name, v.model_name
            FROM bookings b
            JOIN vehicles v ON b.vehicle_id = v.vehicle_id
            WHERE b.customer_id = %s
        """
        params = [customer_id]
        
        # เพิ่มเงื่อนไขการกรอง
        if status_filter:
            base_query += " AND b.status = %s"
            params.append(status_filter)
        
        if date_filter:
            if date_filter == '7':
                base_query += " AND b.booking_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
            elif date_filter == '30':
                base_query += " AND b.booking_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
            elif date_filter == '90':
                base_query += " AND b.booking_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)"
        
        # นับจำนวนทั้งหมด
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor.execute(count_query, params)
        total_bookings = cursor.fetchone()['total']
        total_pages = (total_bookings + per_page - 1) // per_page
        
        # ดึงข้อมูลการจอง
        query = base_query + " ORDER BY b.booking_date DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        cursor.execute(query, params)
        bookings = cursor.fetchall()
        
        # ดึงข้อมูลบริการสำหรับแต่ละการจอง
        for booking in bookings:
            cursor.execute("""
                SELECT s.service_name, s.category
                FROM booking_items bi
                JOIN services s ON bi.service_id = s.service_id
                WHERE bi.booking_id = %s
                ORDER BY s.category, s.service_name
            """, (booking['booking_id'],))
            booking['services'] = cursor.fetchall()
        
        return render_customer_template('customer/booking_history.html',
                             bookings=bookings,
                             page=page,
                             total_pages=total_pages,
                             total_bookings=total_bookings,
                             per_page=per_page,
                             status_filter=status_filter,
                             date_filter=date_filter)
        
    except Exception as e:
        print(f"Error in booking_history: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดประวัติการจอง', 'error')
        # แสดงหน้า error แทนการ redirect ไปหน้า home
        return render_customer_template('customer/booking_history.html',
                             bookings=[],
                             page=1,
                             total_pages=1,
                             total_bookings=0,
                             per_page=10,
                             status_filter='',
                             date_filter='')

@customer.route('/profile', methods=['GET', 'POST'])
@customer_login_required
def profile():
    """หน้าโปรไฟล์ลูกค้า"""
    if not session.get('customer_id'):
        return redirect(url_for('customer.home'))

    if request.method == 'POST':
        try:
            # ดึงข้อมูลจากฟอร์ม
            name = request.form.get('name', '').strip()
            gender = request.form.get('gender', '').strip()
            birthdate = request.form.get('birthdate', '').strip()
            phone = request.form.get('phone', '').strip()
            
            # แยกชื่อและนามสกุล
            name_parts = name.split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            # อัปเดตข้อมูลในฐานข้อมูล
            cursor = get_cursor()
            cursor.execute('''
                UPDATE customers 
                SET first_name = %s, last_name = %s, gender = %s, birthdate = %s, phone = %s 
                WHERE customer_id = %s
            ''', (first_name, last_name, gender, birthdate, phone, session.get('customer_id')))
            
            # อัปเดต name ในตาราง users ด้วย
            cursor.execute('''
                UPDATE users 
                SET name = %s 
                WHERE user_id = (SELECT user_id FROM customers WHERE customer_id = %s)
            ''', (name, session.get('customer_id')))
            
            # อัปเดต session
            session['customer_name'] = name
            
            get_db().commit()
            flash('อัปเดตข้อมูลเรียบร้อยแล้ว', 'success')
            return redirect(url_for('customer.profile'))
            
        except Exception as e:
            flash('เกิดข้อผิดพลาดในการอัปเดตข้อมูล', 'error')
            return redirect(url_for('customer.profile'))

    try:
        cursor = get_cursor()
        cursor.execute('''
            SELECT c.customer_id, c.first_name, c.last_name, c.phone, c.email, c.gender, c.birthdate,
                   u.username, u.avatar_filename, u.created_at, u.name
            FROM customers c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.customer_id = %s
        ''', (session.get('customer_id'),))
        user = cursor.fetchone()
        
        if not user:
            flash('ไม่พบข้อมูลลูกค้า', 'error')
            return redirect(url_for('customer.home'))
        
        return render_customer_template('customer/profile.html', user=user)
        
    except Exception as e:
        flash('เกิดข้อผิดพลาดในการโหลดข้อมูล', 'error')
        return redirect(url_for('customer.home'))

@customer.route('/edit-profile', methods=['GET', 'POST'])
@customer_login_required
def edit_profile():
    """หน้าแก้ไขโปรไฟล์ลูกค้า"""
    if not session.get('customer_id'):
        return redirect(url_for('customer.home'))

    customer_id = session.get('customer_id')

    if request.method == 'POST':
        try:
            # ดึงข้อมูลจากฟอร์ม
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip()
            
            # จัดการไฟล์รูปภาพ
            avatar_filename = None
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and file.filename != '':
                    # ตรวจสอบนามสกุลไฟล์
                    if file and allowed_file(file.filename):
                        # สร้างชื่อไฟล์ใหม่
                        timestamp = int(time.time() * 1000)
                        filename = f"{customer_id}_{timestamp}_{secure_filename(file.filename)}"
                        
                        # บันทึกไฟล์
                        file_path = os.path.join(current_app.config['PROFILE_UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        avatar_filename = filename
                        
                        # ลบไฟล์เก่าถ้ามี
                        cursor = get_cursor()
                        cursor.execute('SELECT avatar_filename FROM users WHERE user_id = (SELECT user_id FROM customers WHERE customer_id = %s)', (customer_id,))
                        user_data = cursor.fetchone()
                        if user_data and user_data.get('avatar_filename'):
                            old_file_path = os.path.join(current_app.config['PROFILE_UPLOAD_FOLDER'], user_data['avatar_filename'])
                            if os.path.exists(old_file_path):
                                os.remove(old_file_path)
                    else:
                        flash('นามสกุลไฟล์ไม่ถูกต้อง กรุณาใช้ไฟล์ JPG, PNG เท่านั้น', 'error')
                        return redirect(url_for('customer.edit_profile'))
            
            # อัปเดตข้อมูลในฐานข้อมูล
            cursor = get_cursor()
            cursor.execute('''
                UPDATE customers 
                SET first_name = %s, last_name = %s, phone = %s, email = %s 
                WHERE customer_id = %s
            ''', (first_name, last_name, phone, email, customer_id))
            
            if avatar_filename:
                cursor.execute('''
                    UPDATE users 
                    SET avatar_filename = %s 
                    WHERE user_id = (SELECT user_id FROM customers WHERE customer_id = %s)
                ''', (avatar_filename, customer_id))
            
            # อัปเดต session
            session['customer_name'] = f"{first_name} {last_name}"
            if avatar_filename:
                session['customer_avatar'] = avatar_filename
            
            flash('อัปเดตข้อมูลเรียบร้อยแล้ว', 'success')
            return redirect(url_for('customer.profile'))
            
        except Exception as e:
            print(f"Error updating customer profile: {e}")
            flash('เกิดข้อผิดพลาดในการอัปเดตข้อมูล', 'error')
            return redirect(url_for('customer.edit_profile'))

    # GET request - แสดงฟอร์ม
    try:
        cursor = get_cursor()
        cursor.execute('''
            SELECT c.customer_id, c.first_name, c.last_name, c.phone, c.email, c.gender, c.birthdate,
                   u.username, u.avatar_filename, u.created_at
            FROM customers c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.customer_id = %s
        ''', (customer_id,))
        customer_data = cursor.fetchone()
        
        if not customer_data:
            flash('ไม่พบข้อมูลลูกค้า', 'error')
            return redirect(url_for('customer.home'))
        
        return render_customer_template('customer/edit_profile.html', customer=customer_data)
        
    except Exception as e:
        print(f"Error loading customer profile: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดข้อมูล', 'error')
        return redirect(url_for('customer.profile'))

@customer.route('/change-password', methods=['GET', 'POST'])
@customer_login_required
def change_password():
    """หน้าเปลี่ยนรหัสผ่านลูกค้า"""
    if not session.get('customer_id'):
        return redirect(url_for('customer.home'))

    if request.method == 'POST':
        try:
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if not current_password or not new_password or not confirm_password:
                flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'error')
                return redirect(url_for('customer.change_password'))
            
            if new_password != confirm_password:
                flash('รหัสผ่านใหม่ไม่ตรงกัน', 'error')
                return redirect(url_for('customer.change_password'))
            
            if len(new_password) < 6:
                flash('รหัสผ่านใหม่ต้องมีอย่างน้อย 6 ตัวอักษร', 'error')
                return redirect(url_for('customer.change_password'))
            
            # ตรวจสอบรหัสผ่านปัจจุบัน
            cursor = get_cursor()
            cursor.execute('''
                SELECT u.password_hash 
                FROM users u 
                JOIN customers c ON u.user_id = c.user_id 
                WHERE c.customer_id = %s
            ''', (session.get('customer_id'),))
            user_data = cursor.fetchone()
            
            if not user_data or not verify_password(current_password, user_data['password_hash']):
                flash('รหัสผ่านปัจจุบันไม่ถูกต้อง', 'error')
                return redirect(url_for('customer.change_password'))
            
            # อัปเดตรหัสผ่านใหม่
            from werkzeug.security import generate_password_hash
            new_password_hash = generate_password_hash(new_password, method='scrypt')
            
            cursor.execute('''
                UPDATE users 
                SET password_hash = %s 
                WHERE user_id = (SELECT user_id FROM customers WHERE customer_id = %s)
            ''', (new_password_hash, session.get('customer_id')))
            
            get_db().commit()
            flash('เปลี่ยนรหัสผ่านเรียบร้อยแล้ว', 'success')
            return redirect(url_for('customer.profile'))
            
        except Exception as e:
            print(f"Error changing customer password: {e}")
            flash('เกิดข้อผิดพลาดในการเปลี่ยนรหัสผ่าน', 'error')
            return redirect(url_for('customer.change_password'))

    return render_customer_template('customer/change_password.html')

@customer.route('/api/car-brands')
def api_car_brands():
    """API สำหรับดึงข้อมูลยี่ห้อรถ"""
    try:
        cursor = get_cursor()
        cursor.execute('SELECT car_brand_id, car_brand_name FROM car_brands ORDER BY car_brand_name')
        brands = cursor.fetchall()
        return jsonify({'success': True, 'data': brands})
    except Exception as e:
        print(f"Error in api_car_brands: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@customer.route('/api/car-models/<int:brand_id>')
def api_car_models(brand_id):
    """API สำหรับดึงข้อมูลรุ่นรถตามยี่ห้อ"""
    try:
        cursor = get_cursor()
        cursor.execute('''
            SELECT car_model_id, car_model_name 
            FROM car_models 
            WHERE car_brand_id = %s
            ORDER BY car_model_name
        ''', (brand_id,))
        models = cursor.fetchall()
        return jsonify({'success': True, 'data': models})
    except Exception as e:
        print(f"Error in api_car_models: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@customer.route('/api/car-years/<int:model_id>')
def api_car_years(model_id):
    """API สำหรับดึงข้อมูลปีที่ผลิตตามรุ่นรถ"""
    try:
        cursor = get_cursor()
        cursor.execute('''
            SELECT car_model_year_id, production_year 
            FROM car_model_years 
            WHERE car_model_id = %s
            ORDER BY production_year DESC
        ''', (model_id,))
        years = cursor.fetchall()
        return jsonify({'success': True, 'data': years})
    except Exception as e:
        print(f"Error in api_car_years: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@customer.route('/logout', methods=['POST'])
def logout():
    """ออกจากระบบลูกค้า"""
    session.clear()
    session.permanent = False
    flash('ออกจากระบบเรียบร้อย', 'success')
    return redirect(url_for('customer.home'))

@customer.route('/update-avatar', methods=['POST'])
@customer_login_required
def update_avatar():
    """อัปเดตรูปโปรไฟล์ลูกค้า"""
    if not session.get('customer_id'):
        return redirect(url_for('customer.home'))
    
    try:

        
        file = request.files.get('avatar')
        if file and file.filename != '':
            # ตรวจสอบนามสกุลไฟล์
            if allowed_file(file.filename):
                # สร้างชื่อไฟล์ใหม่
                customer_id = session.get('customer_id')
                timestamp = int(time.time() * 1000)
                filename = f"{customer_id}_{timestamp}_{secure_filename(file.filename)}"
                
                # บันทึกไฟล์
                file_path = os.path.join(current_app.config['PROFILE_UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # ลบไฟล์เก่าถ้ามี
                cursor = get_cursor()
                cursor.execute('SELECT avatar_filename FROM users WHERE user_id = (SELECT user_id FROM customers WHERE customer_id = %s)', (customer_id,))
                user_data = cursor.fetchone()
                if user_data and user_data.get('avatar_filename'):
                    old_file_path = os.path.join(current_app.config['PROFILE_UPLOAD_FOLDER'], user_data['avatar_filename'])
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                
                # อัปเดตฐานข้อมูล
                cursor.execute('''
                    UPDATE users 
                    SET avatar_filename = %s 
                    WHERE user_id = (SELECT user_id FROM customers WHERE customer_id = %s)
                ''', (filename, customer_id))
                get_db().commit()
                
                # อัปเดต session
                session['customer_avatar'] = filename
                
                flash('อัปเดตรูปโปรไฟล์สำเร็จ', 'success')
            else:
                flash('นามสกุลไฟล์ไม่ถูกต้อง กรุณาใช้ไฟล์ JPG, PNG เท่านั้น', 'error')
        else:
            flash('กรุณาเลือกไฟล์รูปภาพ', 'error')
            
    except Exception as e:
        print(f"Error updating avatar: {e}")
        flash('เกิดข้อผิดพลาดในการอัปเดตรูปโปรไฟล์', 'error')
    
    return redirect(url_for('customer.profile'))



# ฟังก์ชันสำหรับ render template ลูกค้า
def render_customer_template(template_name: str, **context):
    """ฟังก์ชันสำหรับ render template ลูกค้าพร้อมบันทึกการเข้าชม"""
    # ใช้ชื่อไฟล์ template เป็น page_id
    page_id = template_name.replace('.html', '').replace('/', '_')
    
    # บันทึกการเข้าชม
    log_page_view(page_id)
    
    # เพิ่มข้อมูลพื้นฐานสำหรับ template
    context.update({
        'customer_logged_in': bool(session.get('customer_id')),
        'customer_name': session.get('customer_name', ''),
        'customer_username': session.get('customer_username', ''),
        'customer_avatar': session.get('customer_avatar', ''),
        'current_year': datetime.now().year
    })
    
    return render_template(template_name, **context)
# ฟังก์ชันสำหรับบันทึกการเข้าชมหน้าเว็บ
def log_page_view(page_id: str):
    """บันทึกการเข้าชมหน้าเว็บ"""
    try:
        # สร้างตาราง page_views ถ้ายังไม่มี
        ensure_page_views_table()
        
        cursor = get_cursor()
        
        # อัปเดตหรือเพิ่มข้อมูลใน page_views
        cursor.execute("""
            INSERT INTO page_views (page_id, views, last_viewed_at)
            VALUES (%s, 1, %s)
            ON DUPLICATE KEY UPDATE 
            views = views + 1,
            last_viewed_at = %s
        """, (page_id, datetime.now(), datetime.now()))
        
        get_db().commit()
        
    except Exception as e:
        print(f"Error logging page view: {e}")

# ฟังก์ชันสำหรับตรวจสอบรหัสผ่าน
def verify_password(password, hash_string):
    """ตรวจสอบรหัสผ่าน"""
    from werkzeug.security import check_password_hash
    if not hash_string:
        return False
    return check_password_hash(hash_string, password)

# ฟังก์ชันสำหรับตรวจสอบอุปกรณ์
def get_device_type(user_agent):
    """ตรวจสอบประเภทอุปกรณ์"""
    user_agent_lower = user_agent.lower()
    if 'mobile' in user_agent_lower or 'android' in user_agent_lower or 'iphone' in user_agent_lower:
        return 'mobile'
    elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
        return 'tablet'
    else:
        return 'desktop'

# ฟังก์ชันสำหรับสร้างตาราง page_views
def ensure_page_views_table():
    """สร้างตาราง page_views ถ้ายังไม่มี"""
    try:
        cursor = get_cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS page_views (
                page_id VARCHAR(100) NOT NULL PRIMARY KEY,
                views INT DEFAULT 0,
                last_viewed_at DATETIME DEFAULT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        get_db().commit()
    except Exception as e:
        print(f"Error ensuring page_views table: {e}")

