# Import modules ที่จำเป็นสำหรับ API routes
from flask import Blueprint, request, jsonify, session
from database import get_cursor, get_db
from utils import validate_pagination_params, validate_sort_params
from datetime import datetime
from utils import get_device_type
import json
from functools import wraps

# สร้าง Blueprint สำหรับ API routes
api = Blueprint('api', __name__)

@api.route('/log-page-view', methods=['POST'])
def log_page_view():
    """บันทึกการเข้าชมหน้าเว็บ"""
    try:
        # Debug: แสดงข้อมูลที่ได้รับจาก request
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"Request data: {request.get_data()}")
        
        # แปลง JSON data ที่ได้รับ
        data = request.get_json()
        print(f"Parsed JSON data: {data}")
        
        # ดึง page_id จากข้อมูลที่ส่งมา
        page_id = data.get('page_id') if data else None
        
        # ตรวจสอบว่ามี page_id หรือไม่
        if not page_id:
            return jsonify({'success': False, 'error': 'page_id is required'}), 400
        
        # เชื่อมต่อฐานข้อมูล
        cursor = get_cursor()
        
        # ตรวจสอบ device_type จาก User-Agent header
        user_agent = request.headers.get('User-Agent', '')
        device_type = get_device_type(user_agent)
        
        print(f"Page ID: {page_id}")
        print(f"Device Type: {device_type}")
        
        # บันทึกข้อมูลการเข้าชมลงในตาราง page_view_logs
        cursor.execute('''
            INSERT INTO page_view_logs (page_id, device_type, viewed_at)
            VALUES (%s, %s, %s)
        ''', (page_id, device_type, datetime.now()))
        
        # อัปเดตหรือเพิ่มข้อมูลสถิติการเข้าชมในตาราง page_views
        cursor.execute('''
            INSERT INTO page_views (page_id, views, last_viewed_at)
            VALUES (%s, 1, %s)
            ON DUPLICATE KEY UPDATE
            views = views + 1,
            last_viewed_at = %s
        ''', (page_id, datetime.now(), datetime.now()))
        
        # บันทึกการเปลี่ยนแปลงลงฐานข้อมูล
        cursor.connection.commit()
        
        print(f"Successfully logged page view for: {page_id}")
        
        return jsonify({
            'success': True,
            'message': 'Page view logged successfully',
            'page_id': page_id,
            'device_type': device_type
        })
        
    except Exception as e:
        # จัดการ error และแสดงข้อมูล debug
        print(f"Error in log_page_view: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/log-page-view', methods=['GET', 'POST'])
def api_log_page_view():
    """API สำหรับบันทึกการเข้าชมหน้าเว็บ (ไม่มี CSRF protection)"""
    try:
        # รับ page_id จาก GET parameter หรือ JSON body ตาม HTTP method
        if request.method == 'GET':
            page_id = request.args.get('page_id')
        else:
            data = request.get_json()
            page_id = data.get('page_id') if data else None
        
        # ตรวจสอบว่ามี page_id หรือไม่
        if not page_id:
            return jsonify({'success': False, 'error': 'page_id is required'}), 400
        
        # เชื่อมต่อฐานข้อมูล
        cursor = get_cursor()
        
        # ตรวจสอบ device_type จาก User-Agent header
        user_agent = request.headers.get('User-Agent', '')
        device_type = get_device_type(user_agent)
        
        # บันทึกข้อมูลการเข้าชมลงในตาราง page_view_logs
        cursor.execute('''
            INSERT INTO page_view_logs (page_id, device_type, viewed_at)
            VALUES (%s, %s, %s)
        ''', (page_id, device_type, datetime.now()))
        
        # อัปเดตหรือเพิ่มข้อมูลสถิติการเข้าชมในตาราง page_views
        cursor.execute('''
            INSERT INTO page_views (page_id, views, last_viewed_at)
            VALUES (%s, 1, %s)
            ON DUPLICATE KEY UPDATE
            views = views + 1,
            last_viewed_at = %s
        ''', (page_id, datetime.now(), datetime.now()))
        
        # บันทึกการเปลี่ยนแปลงลงฐานข้อมูล
        from database import get_db
        get_db().commit()
        
        return jsonify({
            'success': True,
            'message': 'Page view logged successfully',
            'page_id': page_id,
            'device_type': device_type
        })
        
    except Exception as e:
        # จัดการ error และแสดงข้อมูล debug
        print(f"Error in api_log_page_view: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/page-views-summary')
def page_views_summary():
    """ดึงข้อมูลสรุปการเข้าชมหน้าเว็บ"""
    try:
        # เชื่อมต่อฐานข้อมูล
        cursor = get_cursor()
        
        # ดึงข้อมูลสถิติการเข้าชมหน้าเว็บ 10 อันดับแรก
        cursor.execute('''
            SELECT page_id, views, last_viewed_at
            FROM page_views
            ORDER BY views DESC
            LIMIT 10
        ''')
        top_pages = cursor.fetchall()
        
        # ดึงข้อมูลสถิติการเข้าชมแยกตามประเภทอุปกรณ์
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN device_type IS NULL OR device_type = '' THEN 'unknown'
                    ELSE device_type 
                END as device_type, 
                COUNT(*) as count
            FROM page_view_logs
            GROUP BY 
                CASE 
                    WHEN device_type IS NULL OR device_type = '' THEN 'unknown'
                    ELSE device_type 
                END
            ORDER BY count DESC
        ''')
        device_stats = cursor.fetchall()
        
        # ดึงข้อมูลการเข้าชมรายวันในช่วง 7 วันล่าสุด
        cursor.execute('''
            SELECT DATE(viewed_at) as date, COUNT(*) as count
            FROM page_view_logs
            WHERE viewed_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(viewed_at)
            ORDER BY date ASC
        ''')
        daily_visits = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'top_pages': top_pages,
            'device_stats': device_stats,
            'daily_visits': daily_visits
        })
        
    except Exception as e:
        # จัดการ error และแสดงข้อมูล debug
        print(f"Error in page_views_summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/tires')
def api_tires():
    """API สำหรับดึงข้อมูลยาง"""
    try:
        # รับพารามิเตอร์ pagination และ filter
        page, per_page = validate_pagination_params(
            request.args.get('page'), 
            request.args.get('per_page')
        )
        
        # รับพารามิเตอร์สำหรับการกรองข้อมูลยาง
        brand_id = request.args.get('brand_id')
        width = request.args.get('width')
        aspect_ratio = request.args.get('aspect_ratio')
        rim_diameter = request.args.get('rim_diameter')
        
        # สร้าง SQL query หลักสำหรับดึงข้อมูลยาง
        base_query = """
            SELECT t.tire_id, t.name, t.width, t.aspect_ratio, t.rim_diameter, 
                   t.load_index, t.speed_rating, t.price, t.stock_quantity,
                   t.image_filename, t.description, t.created_at,
                   b.brand_name, b.brand_id
            FROM tires t
            JOIN brands b ON t.brand_id = b.brand_id
            WHERE 1=1
        """
        
        params = []
        
        # เพิ่มเงื่อนไขการกรองตามพารามิเตอร์ที่ส่งมา
        if brand_id:
            base_query += " AND t.brand_id = %s"
            params.append(brand_id)
        
        if width:
            base_query += " AND t.width = %s"
            params.append(width)
        
        if aspect_ratio:
            base_query += " AND t.aspect_ratio = %s"
            params.append(aspect_ratio)
        
        if rim_diameter:
            base_query += " AND t.rim_diameter = %s"
            params.append(rim_diameter)
        
        # นับจำนวนรายการทั้งหมดสำหรับ pagination
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor = get_cursor()
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # คำนวณค่า offset และจำนวนหน้าทั้งหมด
        offset = (page - 1) * per_page
        total_pages = (total + per_page - 1) // per_page
        
        # เพิ่ม ORDER BY และ LIMIT สำหรับ pagination
        base_query += " ORDER BY t.created_at DESC"
        base_query += " LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        # ดึงข้อมูลยางตามเงื่อนไขที่กำหนด
        cursor.execute(base_query, params)
        tires = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'data': tires,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages
            }
        })
        
    except Exception as e:
        # จัดการ error และแสดงข้อมูล debug
        print(f"Error in api_tires: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/tires/widths')
def api_tire_widths():
    """API สำหรับดึงรายการ width ทั้งหมดที่มีในตาราง tires"""
    try:
        # เชื่อมต่อฐานข้อมูล
        cursor = get_cursor()
        
        # ดึง width ที่ไม่ซ้ำและเรียงลำดับแบบตัวเลข
        cursor.execute("""
            SELECT DISTINCT width
            FROM tires 
            WHERE width IS NOT NULL
            ORDER BY width ASC
        """)
        
        # แปลงผลลัพธ์เป็น list ของ width
        widths = [row['width'] for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'items': widths
        })
        
    except Exception as e:
        # จัดการ error และแสดงข้อมูล debug
        print(f"Error in api_tire_widths: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/tires/aspects')
def api_tire_aspects():
    """API สำหรับดึงรายการ aspect_ratio ตาม width ที่เลือก"""
    try:
        # รับพารามิเตอร์ width
        width = request.args.get('width')
        if not width:
            return jsonify({
                'success': False,
                'error': 'Width parameter is required'
            }), 400
        
        # เชื่อมต่อฐานข้อมูล
        cursor = get_cursor()
        
        # ดึง aspect_ratio ที่ไม่ซ้ำสำหรับ width ที่เลือก
        cursor.execute("""
            SELECT DISTINCT aspect_ratio
            FROM tires 
            WHERE width = %s AND aspect_ratio IS NOT NULL
            ORDER BY aspect_ratio ASC
        """, (width,))
        
        # แปลงผลลัพธ์เป็น list ของ aspect_ratio
        aspects = [row['aspect_ratio'] for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'items': aspects
        })
        
    except Exception as e:
        # จัดการ error และแสดงข้อมูล debug
        print(f"Error in api_tire_aspects: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/tires/rims')
def api_tire_rims():
    """API สำหรับดึงรายการ rim_diameter ตาม width และ aspect_ratio ที่เลือก"""
    try:
        # รับพารามิเตอร์ width และ aspect
        width = request.args.get('width')
        aspect = request.args.get('aspect')
        
        # ตรวจสอบว่ามีพารามิเตอร์ครบถ้วนหรือไม่
        if not width or not aspect:
            return jsonify({
                'success': False,
                'error': 'Width and aspect parameters are required'
            }), 400
        
        # เชื่อมต่อฐานข้อมูล
        cursor = get_cursor()
        
        # ดึง rim_diameter ที่ไม่ซ้ำสำหรับ width และ aspect_ratio ที่เลือก
        cursor.execute("""
            SELECT DISTINCT rim_diameter
            FROM tires 
            WHERE width = %s AND aspect_ratio = %s AND rim_diameter IS NOT NULL
            ORDER BY rim_diameter ASC
        """, (width, aspect))
        
        # แปลงผลลัพธ์เป็น list ของ rim_diameter
        rims = [row['rim_diameter'] for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'items': rims
        })
        
    except Exception as e:
        # จัดการ error และแสดงข้อมูล debug
        print(f"Error in api_tire_rims: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/customers/<int:customer_id>')
def api_customer_detail(customer_id):
    """API สำหรับดึงข้อมูลลูกค้า"""
    try:
        # เชื่อมต่อฐานข้อมูล
        cursor = get_cursor()
        
        # ดึงข้อมูลลูกค้าจากตาราง customers และ users
        cursor.execute("""
            SELECT c.customer_id, c.first_name, c.last_name, c.phone, c.email,
                   u.username, u.avatar_filename, u.created_at
            FROM customers c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.customer_id = %s
        """, (customer_id,))
        customer = cursor.fetchone()
        
        # ตรวจสอบว่าพบลูกค้าหรือไม่
        if not customer:
            return jsonify({
                'success': False,
                'error': 'Customer not found'
            }), 404
        
        # ดึงข้อมูลรถของลูกค้าจากตาราง vehicles
        cursor.execute("""
            SELECT v.vehicle_id, v.license_plate, v.license_province,
                   v.brand_name, v.model_name, v.production_year, v.color,
                   vt.vehicle_type_name as vehicle_type
            FROM vehicles v
            LEFT JOIN vehicle_types vt ON v.vehicle_type_id = vt.vehicle_type_id
            WHERE v.customer_id = %s
            ORDER BY v.vehicle_id ASC
        """, (customer_id,))
        vehicles = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'data': {
                'customer': customer,
                'vehicles': vehicles
            }
        })
        
    except Exception as e:
        # จัดการ error และแสดงข้อมูล debug
        print(f"Error in api_customer_detail: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/bookings')
def api_bookings():
    """API สำหรับดึงข้อมูลการจอง"""
    try:
        # รับพารามิเตอร์ pagination และ filter
        page, per_page = validate_pagination_params(
            request.args.get('page'), 
            request.args.get('per_page')
        )
        
        # รับพารามิเตอร์สำหรับการกรองข้อมูลการจอง
        status_filter = request.args.get('status')
        customer_id = request.args.get('customer_id')
        
        # สร้าง SQL query หลักสำหรับดึงข้อมูลการจอง
        base_query = """
            SELECT b.booking_id, b.booking_date, b.status,
                   c.customer_id, c.first_name, c.last_name, c.phone,
                   v.license_plate, v.license_province, v.brand_name, v.model_name
            FROM bookings b
            JOIN customers c ON b.customer_id = c.customer_id
            JOIN vehicles v ON b.vehicle_id = v.vehicle_id
            WHERE 1=1
        """
        
        params = []
        
        # เพิ่มเงื่อนไขการกรองตามพารามิเตอร์ที่ส่งมา
        if status_filter:
            base_query += " AND b.status = %s"
            params.append(status_filter)
        
        if customer_id:
            base_query += " AND b.customer_id = %s"
            params.append(customer_id)
        
        # นับจำนวนรายการทั้งหมดสำหรับ pagination
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor = get_cursor()
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # คำนวณค่า offset และจำนวนหน้าทั้งหมด
        offset = (page - 1) * per_page
        total_pages = (total + per_page - 1) // per_page
        
        # เพิ่ม ORDER BY และ LIMIT สำหรับ pagination
        base_query += " ORDER BY b.booking_date DESC"
        base_query += " LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        # ดึงข้อมูลการจองตามเงื่อนไขที่กำหนด
        cursor.execute(base_query, params)
        bookings = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'data': bookings,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages
            }
        })
        
    except Exception as e:
        print(f"Error in api_bookings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/bookings/<int:booking_id>/detail')
def api_booking_detail(booking_id):
    """API สำหรับดึงรายละเอียดการจอง"""
    try:
        cursor = get_cursor()
        
        # ดึงข้อมูลการจองหลัก
        cursor.execute("""
            SELECT b.booking_id, b.booking_date, b.service_date, b.service_time, b.status, b.note,
                   c.customer_id, c.first_name, c.last_name, c.phone, c.email,
                   v.vehicle_id, v.license_plate, v.license_province, 
                   v.brand_name, v.model_name, v.production_year, v.color
            FROM bookings b
            JOIN customers c ON b.customer_id = c.customer_id
            JOIN vehicles v ON b.vehicle_id = v.vehicle_id
            WHERE b.booking_id = %s
        """, (booking_id,))
        booking = cursor.fetchone()
        
        # แปลง timedelta เป็น string
        if booking and booking.get('service_time'):
            if hasattr(booking['service_time'], 'total_seconds'):
                # แปลง timedelta เป็น string format HH:MM:SS
                total_seconds = int(booking['service_time'].total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                booking['service_time'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                # ถ้าเป็น string อยู่แล้ว ให้ใช้ตามเดิม
                booking['service_time'] = str(booking['service_time'])
        
        if not booking:
            return jsonify({
                'success': False,
                'error': 'Booking not found'
            }), 404
        
        # ดึงรายการบริการ
        cursor.execute("""
            SELECT bi.item_id, bi.service_id, bi.quantity,
                   s.service_name, s.category,
                   bi.created_at, bi.updated_at
            FROM booking_items bi
            LEFT JOIN services s ON bi.service_id = s.service_id
            WHERE bi.booking_id = %s
            ORDER BY bi.item_id ASC
        """, (booking_id,))
        services = cursor.fetchall()
        
        # ดึงตัวเลือกของบริการ
        for service in services:
            cursor.execute("""
                SELECT bio.option_id, so.option_name, so.note
                FROM booking_item_options bio
                LEFT JOIN service_options so ON bio.option_id = so.option_id
                WHERE bio.item_id = %s
            """, (service['item_id'],))
            service['options'] = cursor.fetchall()
        
        # ดึงข้อมูลยาง
        cursor.execute("""
            SELECT position, brand, model, size, dot
            FROM service_tires
            WHERE booking_id = %s
            ORDER BY 
                CASE position
                    WHEN 'front_left' THEN 1
                    WHEN 'front_right' THEN 2
                    WHEN 'rear_left' THEN 3
                    WHEN 'rear_right' THEN 4
                END
        """, (booking_id,))
        tires = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'data': {
                'booking': booking,
                'services': services,
                'tires': tires
            }
        })
        
    except Exception as e:
        print(f"Error in api_booking_detail: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/promotions/active')
def api_promotions_active():
    """API สำหรับดึงโปรโมชั่นที่ใช้งานได้"""
    try:
        cursor = get_cursor()
        
        cursor.execute("""
            SELECT promotion_id, title, description, image_url,
                   start_date, end_date
            FROM promotions
            WHERE start_date <= CURDATE() AND end_date >= CURDATE()
            ORDER BY promotion_id DESC
        """)
        promotions = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'data': promotions
        })
        
    except Exception as e:
        print(f"Error in api_promotions_active: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/staff')
def api_staff():
    """API สำหรับดึงข้อมูลพนักงาน"""
    try:
        # รับพารามิเตอร์
        page, per_page = validate_pagination_params(
            request.args.get('page'), 
            request.args.get('per_page')
        )
        
        # สร้าง query
        base_query = """
            SELECT 
                sp.staff_id, sp.first_name, sp.last_name,
                sp.phone, sp.email, sp.created_at,
                u.user_id, u.username, u.name, u.avatar_filename,
                u.role_name
            FROM staff_profiles sp
            JOIN users u ON sp.user_id = u.user_id
            WHERE 1=1
        """
        
        params = []
        
        # นับจำนวนทั้งหมด
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor = get_cursor()
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # คำนวณ pagination
        offset = (page - 1) * per_page
        total_pages = (total + per_page - 1) // per_page
        
        # เพิ่ม ORDER BY และ LIMIT
        base_query += " ORDER BY sp.first_name, sp.last_name"
        base_query += " LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        # ดึงข้อมูล
        cursor.execute(base_query, params)
        staff = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'data': staff,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages
            }
        })
        
    except Exception as e:
        print(f"Error in api_staff: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/tire-models/<int:brand_id>')
def get_tire_models(brand_id):
    """API สำหรับดึงข้อมูลรุ่นยางตามยี่ห้อที่เลือก"""
    try:
        print(f"API called: /api/tire-models/{brand_id}")
        cursor = get_cursor()
        
        cursor.execute('''
            SELECT model_id, model_name 
            FROM tire_models 
            WHERE brand_id = %s 
            ORDER BY model_name
        ''', (brand_id,))
        
        models = cursor.fetchall()
        print(f"Found {len(models)} models for brand_id {brand_id}")
        print(f"Models: {models}")
        
        return jsonify(models)
        
    except Exception as e:
        print(f"Error in get_tire_models: {e}")
        return jsonify([]), 500

@api.route('/api/vehicle_models')
def get_vehicle_models():
    """API สำหรับดึงข้อมูลรุ่นรถตามยี่ห้อที่เลือก"""
    try:
        brand_id = request.args.get('brand_id')
        if not brand_id:
            return jsonify([])
        
        print(f"API called: /api/vehicle_models?brand_id={brand_id}")
        cursor = get_cursor()
        
        # ใช้ชื่อยี่ห้อรถแทน ID
        cursor.execute('''
            SELECT cm.car_model_id, cm.car_model_name 
            FROM car_models cm
            JOIN car_brands cb ON cm.car_brand_id = cb.car_brand_id
            WHERE cb.car_brand_name = %s 
            ORDER BY cm.car_model_name
        ''', (brand_id,))
        
        models = cursor.fetchall()
        print(f"Found {len(models)} vehicle models for brand_name {brand_id}")
        print(f"Models: {models}")
        
        return jsonify(models)
        
    except Exception as e:
        print(f"Error in get_vehicle_models: {e}")
        return jsonify([]), 500

@api.route('/api/districts')
def get_districts():
    """ดึงรายการอำเภอ/เขตตามจังหวัด"""
    try:
        province = request.args.get('province', '').strip()
        if not province:
            return jsonify([])
        
        # อ่านข้อมูลจาก JSON file
        with open('static/data/api_province_with_amphure_tambon.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # กรองข้อมูลตามจังหวัด
        districts = []
        for province_data in data:
            if province_data.get('name_th') == province:
                amphures = province_data.get('amphure', [])
                for amphure in amphures:
                    amphure_name = amphure.get('name_th')
                    if amphure_name and amphure_name not in districts:
                        districts.append(amphure_name)
                break
        
        # เรียงลำดับ
        districts.sort()
        return jsonify(districts)
        
    except Exception as e:
        print(f"Error in get_districts: {e}")
        return jsonify([]), 500

@api.route('/api/subdistricts')
def get_subdistricts():
    """ดึงรายการตำบล/แขวงตามจังหวัดและอำเภอ"""
    try:
        province = request.args.get('province', '').strip()
        district = request.args.get('district', '').strip()
        
        if not province or not district:
            return jsonify([])
        
        # อ่านข้อมูลจาก JSON file
        with open('static/data/api_province_with_amphure_tambon.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # กรองข้อมูลตามจังหวัดและอำเภอ
        subdistricts = []
        for province_data in data:
            if province_data.get('name_th') == province:
                amphures = province_data.get('amphure', [])
                for amphure in amphures:
                    if amphure.get('name_th') == district:
                        tambons = amphure.get('tambon', [])
                        for tambon in tambons:
                            tambon_name = tambon.get('name_th')
                            if tambon_name and tambon_name not in subdistricts:
                                subdistricts.append(tambon_name)
                        break
                break
        
        # เรียงลำดับ
        subdistricts.sort()
        return jsonify(subdistricts)
        
    except Exception as e:
        print(f"Error in get_subdistricts: {e}")
        return jsonify([]), 500

@api.route('/api/zipcodes')
def get_zipcodes():
    """ดึงรายการรหัสไปรษณีย์ตามจังหวัด อำเภอ และตำบล"""
    try:
        province = request.args.get('province', '').strip()
        district = request.args.get('district', '').strip()
        subdistrict = request.args.get('subdistrict', '').strip()
        
        if not province or not district or not subdistrict:
            return jsonify([])
        
        # อ่านข้อมูลจาก JSON file
        with open('static/data/api_province_with_amphure_tambon.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # กรองข้อมูลตามจังหวัด อำเภอ และตำบล
        zipcodes = []
        for province_data in data:
            if province_data.get('name_th') == province:
                amphures = province_data.get('amphure', [])
                for amphure in amphures:
                    if amphure.get('name_th') == district:
                        tambons = amphure.get('tambon', [])
                        for tambon in tambons:
                            if tambon.get('name_th') == subdistrict:
                                zipcode = tambon.get('zip_code')
                                if zipcode and str(zipcode) not in zipcodes:
                                    zipcodes.append(str(zipcode))
                        break
                break
        
        # เรียงลำดับ
        zipcodes.sort()
        return jsonify(zipcodes)
        
    except Exception as e:
        print(f"Error in get_zipcodes: {e}")
        return jsonify([]), 500

@api.route('/api/booking-availability')
def get_booking_availability():
    """ตรวจสอบความพร้อมของแต่ละชั่วโมง (จำกัด 3 คิวต่อชั่วโมง)"""
    try:
        service_date = request.args.get('service_date', '').strip()
        
        if not service_date:
            return jsonify({'success': False, 'error': 'service_date is required'}), 400
        
        # ดึงข้อมูลจากฐานข้อมูลจริง
        try:
            cursor = get_cursor()
            
            # ตรวจสอบจำนวนการจองในแต่ละชั่วโมง
            cursor.execute('''
                SELECT service_time, COUNT(*) as booking_count
                FROM bookings 
                WHERE service_date = %s AND status != 'ยกเลิก'
                GROUP BY service_time
            ''', (service_date,))
            
            booking_counts = {}
            for row in cursor.fetchall():
                # แปลง service_time เป็น string format
                service_time = row['service_time']
                if hasattr(service_time, 'total_seconds'):
                    # ถ้าเป็น timedelta object
                    total_seconds = int(service_time.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    time_str = f"{hours:02d}:{minutes:02d}"
                elif hasattr(service_time, 'strftime'):
                    # ถ้าเป็น time object
                    time_str = service_time.strftime('%H:%M')
                else:
                    # ถ้าเป็น string หรือ format อื่น
                    time_str = str(service_time)
                    if ':' in time_str:
                        # แปลง format ให้เป็น HH:MM
                        parts = time_str.split(':')
                        if len(parts) >= 2:
                            time_str = f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
                
                booking_counts[time_str] = row['booking_count']
                
        except Exception as db_error:
            print(f"Database error: {db_error}")
            # ถ้าฐานข้อมูลมีปัญหา ให้ใช้ข้อมูลว่าง
            booking_counts = {}
        
        # สร้างรายการเวลาที่มีให้เลือก
        available_times = ['09:00', '10:00', '11:00', '13:00', '14:00', '15:00']
        availability = {}
        
        for time_slot in available_times:
            current_count = booking_counts.get(time_slot, 0)
            availability[time_slot] = {
                'available': current_count < 3,
                'current_bookings': current_count,
                'max_bookings': 3,
                'remaining': max(0, 3 - current_count)
            }
        
        return jsonify({
            'success': True,
            'availability': availability
        })
        
    except Exception as e:
        print(f"Error in get_booking_availability: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/booking-customers')
def get_booking_customers():
    """ดึงข้อมูลลูกค้าที่จองในแต่ละชั่วโมง"""
    try:
        service_date = request.args.get('service_date', '').strip()
        
        if not service_date:
            return jsonify({'success': False, 'error': 'service_date is required'}), 400
        
        try:
            cursor = get_cursor()
            
            # ดึงข้อมูลการจองพร้อมข้อมูลลูกค้าและรถ
            cursor.execute('''
                SELECT 
                    b.service_time,
                    v.license_plate,
                    v.license_province,
                    c.phone
                FROM bookings b
                JOIN customers c ON b.customer_id = c.customer_id
                JOIN vehicles v ON b.vehicle_id = v.vehicle_id
                WHERE b.service_date = %s AND b.status != 'ยกเลิก'
                ORDER BY b.service_time, b.booking_id
            ''', (service_date,))
            
            bookings = cursor.fetchall()
            
            # จัดกลุ่มข้อมูลตามเวลา
            time_slots = ['09:00', '10:00', '11:00', '13:00', '14:00', '15:00']
            customers_by_time = {}
            
            for time_slot in time_slots:
                customers_by_time[time_slot] = []
            
            for booking in bookings:
                # แปลง service_time เป็น string format
                if hasattr(booking['service_time'], 'total_seconds'):
                    total_seconds = int(booking['service_time'].total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    time_str = f"{hours:02d}:{minutes:02d}"
                else:
                    time_str = str(booking['service_time'])
                
                if time_str in customers_by_time:
                    customers_by_time[time_str].append({
                        'license_plate': booking['license_plate'],
                        'license_province': booking['license_province'],
                        'phone': booking['phone']
                    })
            
            return jsonify({
                'success': True,
                'customers_by_time': customers_by_time
            })
            
        except Exception as db_error:
            print(f"Database error: {db_error}")
            return jsonify({
                'success': False,
                'error': 'Database error'
            }), 500
        
    except Exception as e:
        print(f"Error in get_booking_customers: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/cancel-booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    """API สำหรับยกเลิกการจองโดยลูกค้า"""
    try:
        # ตรวจสอบว่าลูกค้าเข้าสู่ระบบหรือไม่
        if 'customer_id' not in session:
            return jsonify({'success': False, 'message': 'กรุณาเข้าสู่ระบบก่อน'}), 401
        
        customer_id = session['customer_id']
        cursor = get_cursor()
        
        # ตรวจสอบว่าการจองนี้เป็นของลูกค้าที่เข้าสู่ระบบหรือไม่
        cursor.execute('''
            SELECT booking_id, status 
            FROM bookings 
            WHERE booking_id = %s AND customer_id = %s
        ''', (booking_id, customer_id))
        
        booking = cursor.fetchone()
        
        if not booking:
            return jsonify({'success': False, 'message': 'ไม่พบการจองหรือไม่มีสิทธิ์ยกเลิก'}), 404
        
        # ตรวจสอบสถานะการจอง
        if booking['status'] != 'รอดำเนินการ':
            return jsonify({'success': False, 'message': 'ไม่สามารถยกเลิกการจองที่สถานะ: ' + booking['status']}), 400
        
        # อัปเดตสถานะการจองเป็น 'ยกเลิก'
        cursor.execute('''
            UPDATE bookings 
            SET status = 'ยกเลิก' 
            WHERE booking_id = %s
        ''', (booking_id,))
        
        get_db().commit()
        
        return jsonify({'success': True, 'message': 'ยกเลิกการจองเรียบร้อยแล้ว'})
        
    except Exception as e:
        print(f"Error in cancel_booking: {e}")
        return jsonify({'success': False, 'message': 'เกิดข้อผิดพลาดในการยกเลิกการจอง'}), 500