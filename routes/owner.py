from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, current_app, jsonify, send_file
from flask_wtf.csrf import CSRFError
from database import get_cursor, get_db
from decorators import owner_login_required
import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

owner = Blueprint('owner', __name__, url_prefix='/owner')

# CSRF Error Handler
@owner.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash('CSRF token หมดอายุ กรุณาลองใหม่อีกครั้ง', 'error')
    return redirect(request.url)

@owner.route('/')
@owner.route('/dashboard')
@owner_login_required
def dashboard():
    """หน้าแดชบอร์ดเจ้าของกิจการ"""
    try:
        cursor = get_cursor()
        
        # สถิติสรุป
        cursor.execute('SELECT COUNT(*) as total FROM customers')
        total_customers = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as total FROM bookings')
        total_bookings = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as total FROM tires')
        total_tires = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as total FROM page_views')
        total_page_views = cursor.fetchone()['total']
        
        # ดึงข้อมูลสถานะการจองสำหรับ chart
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM bookings
            GROUP BY status
            ORDER BY count DESC
        ''')
        booking_status = cursor.fetchall()
        
        return render_template('owner/dashboard.html',
                             total_customers=total_customers,
                             total_bookings=total_bookings,
                             total_tires=total_tires,
                             total_revenue=0,  # ไม่มีข้อมูล revenue ในขณะนี้
                             total_page_views=total_page_views,
                             booking_status=booking_status)
    except Exception as e:
        print(f"Error in owner_dashboard: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดข้อมูล', 'error')
        return redirect(url_for('auth.login'))

@owner.route('/bookings_report')
@owner_login_required
def bookings_report():
    """หน้ารายงานการจองสำหรับเจ้าของกิจการ"""
    try:
        cursor = get_cursor()
        
        # สถิติสรุป
        cursor.execute('SELECT COUNT(*) as total FROM bookings')
        total_bookings = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as pending FROM bookings WHERE status = "รอดำเนินการ"')
        pending_bookings = cursor.fetchone()['pending']
        
        cursor.execute('SELECT COUNT(*) as completed FROM bookings WHERE status = "สำเร็จ"')
        completed_bookings = cursor.fetchone()['completed']
        
        cursor.execute('SELECT COUNT(*) as cancelled FROM bookings WHERE status = "ยกเลิก"')
        cancelled_bookings = cursor.fetchone()['cancelled']
        
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
            ORDER BY b.booking_date DESC, b.booking_id DESC
            LIMIT 10
        ''')
        bookings = cursor.fetchall()
        
        return render_template('owner/bookings_report.html', 
                             bookings=bookings,
                             total_bookings=total_bookings,
                             pending_bookings=pending_bookings,
                             completed_bookings=completed_bookings,
                             cancelled_bookings=cancelled_bookings,
                             monthly_bookings=monthly_bookings)
        
    except Exception as e:
        print(f"Error in bookings_report: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดรายงาน', 'error')
        return redirect(url_for('owner.dashboard'))


@owner.route('/bookings_report_pdf')
@owner_login_required
def bookings_report_pdf():
    """หน้ารายงานการจอง PDF สำหรับเจ้าของกิจการ"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        cursor = get_cursor()
        
        # ดึงข้อมูลการจองตามช่วงวันที่ - ใช้ query เดียวกับ admin
        query = '''
            SELECT DISTINCT b.booking_id, b.booking_date, b.service_date, b.service_time, b.status, b.note,
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
        
        query += ' GROUP BY b.booking_id ORDER BY v.license_province ASC, b.booking_date DESC'
        cursor.execute(query, params)
        bookings = cursor.fetchall()
        
        # แปลงข้อมูลให้เป็น JSON serializable และดึงข้อมูลยาง
        bookings_data = []
        processed_booking_ids = set()  # เก็บ booking_id ที่ประมวลผลแล้ว
        
        for booking in bookings:
            booking_id = booking['booking_id']
            
            # ตรวจสอบว่า booking_id นี้ประมวลผลแล้วหรือยัง
            if booking_id in processed_booking_ids:
                continue
            processed_booking_ids.add(booking_id)
            
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
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io
        import os
        from datetime import datetime
        
        # สร้าง buffer สำหรับ PDF
        buffer = io.BytesIO()
        
        # ฟังก์ชันสำหรับเพิ่มเส้นขีดและเลขหน้า
        def add_page_number(canvas, doc):
            canvas.saveState()
            # วาดเส้นขีดสีเขียว green-700
            canvas.setStrokeColor(colors.HexColor('#15803d'))  # green-700
            canvas.setLineWidth(1.2)
            
            # เส้นวาดเหนือ margin (เช่น y=doc.bottomMargin-10)
            y_line = doc.bottomMargin - 10
            canvas.line(doc.leftMargin, y_line, A4[0] - doc.rightMargin, y_line)
            
            # วันที่และเวลาปัจจุบัน - ย้ายไปมุมล่างซ้าย
            canvas.setFont('Helvetica', 9)
            current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            canvas.drawString(doc.leftMargin, y_line - 12, f"This report was created: {current_time}")
            
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
        
        # ลงทะเบียนฟอนต์ตัวหนา
        try:
            bold_font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'Noto_Sans_Thai', 'static', 'NotoSansThai-Bold.ttf')
            pdfmetrics.registerFont(TTFont('NotoSansThai-Bold', bold_font_path))
        except:
            # ถ้าไม่มีฟอนต์ตัวหนา ให้ใช้ฟอนต์ปกติ
            pdfmetrics.registerFont(TTFont('NotoSansThai-Bold', font_path))
        
        # สร้างสไตล์
        styles = getSampleStyleSheet()
        
        # สร้างสไตล์สำหรับชื่อร้าน (กลางหน้ากระดาษ, สีเขียว, ตัวหนา)
        shop_name_style = ParagraphStyle(
            'ShopName',
            parent=styles['Heading1'],
            fontName='NotoSansThai-Bold',
            fontSize=20,
            textColor=colors.HexColor('#14532d'),  # green-900
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
            textColor=colors.black,  # สีดำ
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
            textColor=colors.black,  # สีดำ
            spaceAfter=8,  # ลดระยะห่าง
            alignment=1,  # center
            leading=14
        )
        
        # สไตล์สำหรับหัวข้อส่วน
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName='NotoSansThai-Bold',
            fontSize=14,
            textColor=colors.black,
            spaceAfter=5
        )
        
        # สไตล์สำหรับข้อความปกติ
        normal_style = ParagraphStyle(
            'ThaiNormal',
            parent=styles['Normal'],
            fontName='NotoSansThai',
            fontSize=10,
            leading=12
        )
        
        # สไตล์สำหรับข้อความตัวหนา
        bold_style = ParagraphStyle(
            'ThaiBold',
            parent=styles['Normal'],
            fontName='NotoSansThai-Bold',
            fontSize=10,
            leading=12
        )
        
        # สร้างสไตล์สำหรับลำดับ (จัดกึ่งกลาง)
        center_style = ParagraphStyle(
            'ThaiCenter',
            parent=styles['Normal'],
            fontName='NotoSansThai',
            fontSize=10,
            alignment=1,  # center
            leading=12
        )
        
        # สไตล์สำหรับหัวตาราง
        header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='NotoSansThai-Bold',
            fontSize=11,
            textColor=colors.white,
            alignment=1,  # center
            leading=13
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
        title = Paragraph("Booking Service Report", title_style)
        elements.append(title)
        elements.append(Spacer(1, 3))  # ลดระยะห่างหลังหัวเรื่อง
        
        # สร้างตารางข้อมูล
        if bookings_data:
            # หัวตาราง
            table_data = [
                [Paragraph("ลำดับ", header_style), 
                 Paragraph("ลูกค้า", header_style), 
                 Paragraph("รถยนต์", header_style), 
                 Paragraph("บริการที่จอง", header_style), 
                 Paragraph("หมายเหตุ", header_style), 
                 Paragraph("วันที่จอง", header_style), 
                 Paragraph("สถานะ", header_style)]
            ]
            
            # ข้อมูลในตาราง
            row_number = 1
            for booking in bookings_data:
                # จัดรูปแบบชื่อลูกค้า
                first_name = booking['first_name'] or ''
                last_name = booking['last_name'] or ''
                full_name = f"{first_name} {last_name}".strip()
                
                # ถ้าชื่อยาวเกิน 15 ตัวอักษร ให้แยกบรรทัด
                if len(full_name) > 15:
                    customer_name = Paragraph(f"{first_name}<br/>{last_name}", normal_style)
                else:
                    customer_name = Paragraph(full_name, normal_style)
                
                # จัดรูปแบบข้อมูลรถยนต์ - แยกยี่ห้อและรุ่น
                brand_name = booking['brand_name'] or ''
                model_name = booking['model_name'] or ''
                
                if brand_name and model_name:
                    vehicle_info = Paragraph(f"ยี่ห้อ : {brand_name}<br/>รุ่น : {model_name}", normal_style)
                elif brand_name:
                    vehicle_info = Paragraph(f"ยี่ห้อ : {brand_name}", normal_style)
                elif model_name:
                    vehicle_info = Paragraph(f"รุ่น : {model_name}", normal_style)
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
                            all_content.append(f"๐ {main_service}")
                            all_content.append(f"  - {sub_service}")
                        else:
                            # ไม่มีบริการย่อย
                            all_content.append(f"๐ {service}")
                
                # เพิ่มข้อมูลยาง
                tire_info = booking.get('tire_info', {})
                has_tire_data = any(tire_info.get(pos) for pos in ['front_left', 'front_right', 'rear_left', 'rear_right'])
                
                if has_tire_data:
                    # ยางด้านหน้า
                    front_tires = []
                    if tire_info.get('front_left'): front_tires.append(tire_info['front_left'])
                    if tire_info.get('front_right'): front_tires.append(tire_info['front_right'])
                    if front_tires:
                        all_content.append("๐ ยางด้านหน้า")
                        for tire in front_tires:
                            if tire.get('size'): all_content.append(f"  - ขนาด: {tire['size']}")
                            if tire.get('brand'): all_content.append(f"  - ยี่ห้อ: {tire['brand']}")
                            if tire.get('model'): all_content.append(f"  - รุ่น: {tire['model']}")
                    
                    # ยางด้านหลัง
                    rear_tires = []
                    if tire_info.get('rear_left'): rear_tires.append(tire_info['rear_left'])
                    if tire_info.get('rear_right'): rear_tires.append(tire_info['rear_right'])
                    if rear_tires:
                        all_content.append("๐ ยางด้านหลัง")
                        for tire in rear_tires:
                            if tire.get('size'): all_content.append(f"  - ขนาด: {tire['size']}")
                            if tire.get('brand'): all_content.append(f"  - ยี่ห้อ: {tire['brand']}")
                            if tire.get('model'): all_content.append(f"  - รุ่น: {tire['model']}")
                    
                    # DOT ของยาง
                    dot_data = []
                    for pos, tire in tire_info.items():
                        if tire and tire.get('dot'):
                            pos_name = {'front_left': 'หน้าซ้าย', 'front_right': 'หน้าขวา', 'rear_left': 'หลังซ้าย', 'rear_right': 'หลังขวา'}.get(pos, pos)
                            dot_data.append(f"  - {pos_name}: {tire['dot']}")
                    if dot_data:
                        all_content.append("๐ DOT ของยาง")
                        all_content.extend(dot_data)
                
                # สร้าง Paragraph objects สำหรับบริการ
                if all_content:
                    services_list = []
                    for content in all_content:
                        if content.startswith('๐ '):
                            services_list.append(Paragraph(content, bold_style))
                        else:
                            services_list.append(Paragraph(content, normal_style))
                    services = services_list
                else:
                    services = Paragraph('-', normal_style)
                
                # หมายเหตุ
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
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#166534')),  # green-800
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'NotoSansThai-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # จัดกึ่งกลางหัวตารางทั้งหมด
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),  # จัดกึ่งกลางแนวตั้งหัวตาราง

                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fefce8')),  # yellow-50
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#166534')),  # green-800
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
        
        # สร้าง PDF
        doc.build(elements)
        buffer.seek(0)
        
        # ส่งกลับไฟล์ PDF
        from flask import send_file
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'booking_report_{start_date}_to_{end_date}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error in bookings_report_pdf: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@owner.route('/page_views_report_pdf')
@owner_login_required
def page_views_report_pdf():
    """หน้ารายงานสถิติการเข้าชม PDF สำหรับเจ้าของกิจการ"""
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
        
        # ฟังก์ชันสำหรับเพิ่มเส้นขีดและเลขหน้า
        def add_page_number(canvas, doc):
            canvas.saveState()
            # วาดเส้นขีดสีเขียว green-700
            canvas.setStrokeColor(colors.HexColor('#15803d'))  # green-700
            canvas.setLineWidth(1.2)
            
            # เส้นวาดเหนือ margin (เช่น y=doc.bottomMargin-10)
            y_line = doc.bottomMargin - 10
            canvas.line(doc.leftMargin, y_line, A4[0] - doc.rightMargin, y_line)
            
            # วันที่และเวลาปัจจุบัน - ย้ายไปมุมล่างซ้าย
            canvas.setFont('Helvetica', 9)
            current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            canvas.drawString(doc.leftMargin, y_line - 12, f"This report was created: {current_time}")
            
            #เลขหน้า
            page_num = canvas.getPageNumber()
            canvas.drawRightString(A4[0] - doc.rightMargin, y_line - 12, f"หน้าที่ {page_num}")
            
            canvas.restoreState()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
            onFirstPage=add_page_number,
            onLaterPages=add_page_number
        )
        elements = []
        
        # ลงทะเบียน font ภาษาไทย
        font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'Noto_Sans_Thai', 'NotoSansThai-VariableFont_wdth,wght.ttf')
        pdfmetrics.registerFont(TTFont('NotoSansThai', font_path))
        
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
            textColor=colors.HexColor('#14532d'),  # green-900
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
            textColor=colors.black,  # สีดำ
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
            textColor=colors.black,  # สีดำ
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
            textColor=colors.HexColor('#166534'),  # green-800
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
            textColor=colors.HexColor('#374151'),  # gray-700
            leading=16,
            spaceAfter=6
        )
        
        # สไตล์สำหรับข้อความตัวหนา
        bold_style = ParagraphStyle(
            'CustomBold',
            parent=styles['Normal'],
            fontName='NotoSansThai-Bold',
            fontSize=11,
            textColor=colors.HexColor('#374151'),  # gray-700
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
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#166534')),  # green-800
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'NotoSansThai-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fdf4')),  # green-50
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#166534')),  # green-800
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
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#166534')),  # green-800
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'NotoSansThai-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fefce8')),  # yellow-50
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#166534')),  # green-800
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
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#166534')),  # green-800
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # หัวตารางอยู่กึ่งกลาง
                ('FONTNAME', (0, 0), (-1, 0), 'NotoSansThai-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fdf4')),  # green-50
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#166534')),  # green-800
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
        
        # สร้าง PDF
        doc.build(elements)
        buffer.seek(0)
        
        # ส่งไฟล์ PDF กลับไป
        filename = f"page_views_report_{start_date}_to_{end_date}.pdf" if start_date and end_date else "page_views_report.pdf"
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error in page_views_report_pdf: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@owner.route('/page_views_report')
@owner_login_required
def page_views_report():
    """หน้ารายงานสถิติการเข้าชมสำหรับเจ้าของกิจการ"""
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
            WHERE viewed_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(viewed_at)
            ORDER BY date DESC
        ''')
        daily_visits = cursor.fetchall()
        
        return render_template('owner/page_views_report.html', 
                             total_page_views=total_page_views,
                             total_visits=total_visits,
                             top_pages=top_pages,
                             device_stats=device_stats,
                             daily_visits=daily_visits)
        
    except Exception as e:
        print(f"Error in page_views_report: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดรายงาน', 'error')
        return redirect(url_for('owner.dashboard'))


@owner.route('/profile', methods=['GET', 'POST'])
@owner_login_required
def profile():
    """หน้าแก้ไขข้อมูลผู้ใช้เจ้าของกิจการ"""
    try:
        cursor = get_cursor()
        
        # ดึงข้อมูลผู้ใช้ปัจจุบัน
        owner_user_id = session.get('owner_user_id')
        cursor.execute('''
            SELECT u.user_id, u.username, u.name, u.avatar_filename, u.role_name
            FROM users u
            WHERE u.user_id = %s
        ''', (owner_user_id,))
        user = cursor.fetchone()
        
        if request.method == 'POST':
            # อัปเดตข้อมูลผู้ใช้
            name = request.form.get('name')
            
            # อัปเดตชื่อ
            cursor.execute('''
                UPDATE users 
                SET name = %s
                WHERE user_id = %s
            ''', (name, owner_user_id))
            
            flash('อัปเดตข้อมูลเรียบร้อยแล้ว', 'success')
            return redirect(url_for('owner.profile'))
        
        return render_template('owner/profile.html', user=user)
        
    except Exception as e:
        print(f"Error in owner profile: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดข้อมูล', 'error')
        return redirect(url_for('owner.dashboard'))


@owner.route('/logout', methods=['POST', 'GET'])
@owner_login_required
def logout():
    """ออกจากระบบเจ้าของกิจการ"""
    session.clear()
    session.permanent = False
    flash('ออกจากระบบเจ้าของกิจการเรียบร้อย', 'success')
    return redirect(url_for('auth.login'))