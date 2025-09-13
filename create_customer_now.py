#!/usr/bin/env python3
"""
สร้างลูกค้าตัวอย่างในระบบทันที
รันใน Railway Console
"""

import os
import sys

def create_customer_now():
    """สร้างลูกค้าตัวอย่างทันที"""
    try:
        # ตรวจสอบ environment
        if not os.getenv('DATABASE_URL'):
            print("❌ ไม่พบ DATABASE_URL")
            print("💡 ตรวจสอบว่าอยู่ใน Railway environment หรือไม่")
            return False
        
        # Import modules
        from app import app
        from database import get_cursor, get_db
        from werkzeug.security import generate_password_hash
        
        with app.app_context():
            cursor = get_cursor()
            if not cursor:
                print("❌ ไม่สามารถเชื่อมต่อฐานข้อมูลได้")
                return False
            
            print("🔍 ตรวจสอบลูกค้าในระบบ...")
            
            # ตรวจสอบลูกค้าทั้งหมด
            cursor.execute("""
                SELECT u.username, c.first_name, c.last_name
                FROM users u
                JOIN customers c ON u.user_id = c.user_id
                WHERE u.role_name = 'customer'
                ORDER BY u.username
            """)
            customers = cursor.fetchall()
            
            if customers:
                print(f"✅ พบลูกค้า {len(customers)} คน:")
                for customer in customers:
                    print(f"   - {customer['username']} ({customer['first_name']} {customer['last_name']})")
                print("\n🎉 ลูกค้าสามารถล็อกอินได้แล้ว!")
                print("💡 ใช้ข้อมูลลูกค้าที่มีอยู่แล้วในการล็อกอิน")
                return True
            
            print("❌ ไม่พบลูกค้าในระบบ")
            print("🔧 กำลังสร้างลูกค้าตัวอย่าง...")
            
            # สร้างลูกค้าตัวอย่าง
            username = 'customer01'
            password = '123456'
            name = 'ลูกค้าตัวอย่าง'
            password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            
            # สร้าง user
            cursor.execute('''
                INSERT INTO users (username, password_hash, name, role_name) 
                VALUES (%s, %s, %s, %s)
            ''', (username, password_hash, name, 'customer'))
            
            user_id = cursor.lastrowid
            
            # สร้าง customer
            cursor.execute('''
                INSERT INTO customers (user_id, first_name, last_name, phone, email) 
                VALUES (%s, %s, %s, %s, %s)
            ''', (user_id, 'ลูกค้า', 'ตัวอย่าง', '0812345678', 'customer@example.com'))
            
            # Commit
            get_db().commit()
            
            print("✅ สร้างลูกค้าตัวอย่างสำเร็จ!")
            print("=" * 50)
            print("ข้อมูลสำหรับล็อกอิน:")
            print(f"Username: {username}")
            print(f"Password: {password}")
            print("=" * 50)
            print("🎉 ตอนนี้ลูกค้าสามารถล็อกอินได้แล้ว!")
            
            return True
            
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🚀 เริ่มสร้างลูกค้าตัวอย่าง...")
    success = create_customer_now()
    if success:
        print("\n✅ เสร็จสิ้น! ลูกค้าสามารถล็อกอินได้แล้ว")
        print("💡 ไปที่หน้าเว็บและลองล็อกอินด้วยข้อมูลที่ให้")
    else:
        print("\n❌ ล้มเหลว! กรุณาติดต่อทีมพัฒนา")
        sys.exit(1)
