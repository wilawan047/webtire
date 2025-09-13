#!/usr/bin/env python3
"""
สคริปต์ทดสอบการล็อกอินของลูกค้า
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from database import get_cursor
from werkzeug.security import check_password_hash

def test_customer_login():
    """ทดสอบการล็อกอินของลูกค้า"""
    with app.app_context():
        try:
            cursor = get_cursor()
            if not cursor:
                print("❌ ไม่สามารถเชื่อมต่อฐานข้อมูลได้")
                return False
            
            print("🔍 ตรวจสอบลูกค้าในระบบ...")
            
            # ตรวจสอบลูกค้าทั้งหมด
            cursor.execute("""
                SELECT u.username, u.name, u.password_hash, c.customer_id, c.first_name, c.last_name, c.phone
                FROM users u
                JOIN customers c ON u.user_id = c.user_id
                WHERE u.role_name = 'customer'
                ORDER BY u.username
            """)
            customers = cursor.fetchall()
            
            if not customers:
                print("❌ ไม่พบลูกค้าในระบบ")
                print("💡 ต้องสร้างลูกค้าตัวอย่างก่อน")
                return False
            
            print(f"✅ พบลูกค้า {len(customers)} คน:")
            print("=" * 60)
            
            for customer in customers:
                print(f"Username: {customer['username']}")
                print(f"Name: {customer['first_name']} {customer['last_name']}")
                print(f"Phone: {customer['phone']}")
                print(f"Customer ID: {customer['customer_id']}")
                print(f"Password Hash: {'มี' if customer['password_hash'] else 'ไม่มี'}")
                print("-" * 40)
            
            # ทดสอบการล็อกอินด้วย username แรก
            test_username = customers[0]['username']
            test_passwords = ['123456', 'password', '1234', 'admin']
            
            print(f"\n🧪 ทดสอบการล็อกอินด้วย username: {test_username}")
            print("=" * 60)
            
            for test_password in test_passwords:
                print(f"ทดสอบรหัสผ่าน: {test_password}")
                if customer['password_hash'] and check_password_hash(customer['password_hash'], test_password):
                    print(f"✅ รหัสผ่านถูกต้อง: {test_password}")
                    break
                else:
                    print(f"❌ รหัสผ่านไม่ถูกต้อง: {test_password}")
            
            return True
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาด: {e}")
            return False

if __name__ == '__main__':
    print("🚀 เริ่มทดสอบการล็อกอินของลูกค้า...")
    success = test_customer_login()
    if success:
        print("\n✅ เสร็จสิ้น!")
    else:
        print("\n❌ ล้มเหลว!")
        sys.exit(1)
