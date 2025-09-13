#!/usr/bin/env python3
"""
สคริปต์สำหรับสร้างลูกค้าตัวอย่างในระบบ
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from database import get_cursor, get_db
from werkzeug.security import generate_password_hash

def create_sample_customer():
    """สร้างลูกค้าตัวอย่าง"""
    with app.app_context():
        try:
            cursor = get_cursor()
            if not cursor:
                print("❌ ไม่สามารถเชื่อมต่อฐานข้อมูลได้")
                return False
            
            # ตรวจสอบว่ามีลูกค้าตัวอย่างอยู่แล้วหรือไม่
            cursor.execute("""
                SELECT u.username, c.first_name, c.last_name
                FROM users u
                JOIN customers c ON u.user_id = c.user_id
                WHERE u.username = 'customer01' AND u.role_name = 'customer'
            """)
            existing_customer = cursor.fetchone()
            
            if existing_customer:
                print(f"✅ ลูกค้าตัวอย่างมีอยู่แล้ว: {existing_customer['first_name']} {existing_customer['last_name']} ({existing_customer['username']})")
                return True
            
            # สร้าง user ใหม่
            username = 'customer01'
            password = '123456'
            name = 'ลูกค้าตัวอย่าง'
            password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            
            print(f"🔧 กำลังสร้างลูกค้าตัวอย่าง...")
            print(f"   Username: {username}")
            print(f"   Password: {password}")
            print(f"   Name: {name}")
            
            # เพิ่ม user
            cursor.execute('''
                INSERT INTO users (username, password_hash, name, role_name) 
                VALUES (%s, %s, %s, %s)
            ''', (username, password_hash, name, 'customer'))
            
            user_id = cursor.lastrowid
            print(f"✅ สร้าง user สำเร็จ (ID: {user_id})")
            
            # เพิ่ม customer
            cursor.execute('''
                INSERT INTO customers (user_id, first_name, last_name, phone, email) 
                VALUES (%s, %s, %s, %s, %s)
            ''', (user_id, 'ลูกค้า', 'ตัวอย่าง', '0812345678', 'customer@example.com'))
            
            customer_id = cursor.lastrowid
            print(f"✅ สร้าง customer สำเร็จ (ID: {customer_id})")
            
            # Commit transaction
            get_db().commit()
            print("✅ บันทึกข้อมูลสำเร็จ")
            
            print("\n🎉 สร้างลูกค้าตัวอย่างสำเร็จ!")
            print("=" * 50)
            print("ข้อมูลสำหรับทดสอบการล็อกอิน:")
            print(f"Username: {username}")
            print(f"Password: {password}")
            print("=" * 50)
            
            return True
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาด: {e}")
            # Rollback transaction
            try:
                get_db().rollback()
            except:
                pass
            return False

if __name__ == '__main__':
    print("🚀 เริ่มสร้างลูกค้าตัวอย่าง...")
    success = create_sample_customer()
    if success:
        print("\n✅ เสร็จสิ้น!")
    else:
        print("\n❌ ล้มเหลว!")
        sys.exit(1)
