#!/usr/bin/env python3
"""
สคริปต์สำหรับสร้างฐานข้อมูลและนำเข้าข้อมูลจากไฟล์ SQL
"""

import mysql.connector
from mysql.connector import Error
import os
import sys

def create_database():
    """สร้างฐานข้อมูล tire_shop"""
    try:
        # เชื่อมต่อ MySQL server (ไม่ระบุ database)
        connection = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password=''
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # สร้างฐานข้อมูล
            cursor.execute("CREATE DATABASE IF NOT EXISTS tire_shop CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print("✅ สร้างฐานข้อมูล tire_shop สำเร็จ")
            
            # ใช้ฐานข้อมูล
            cursor.execute("USE tire_shop")
            
            # อ่านไฟล์ SQL และรันคำสั่ง
            with open('tire_shop.sql', 'r', encoding='utf-8') as file:
                sql_content = file.read()
            
            # แยกคำสั่ง SQL
            sql_commands = sql_content.split(';')
            
            print("🔄 กำลังนำเข้าข้อมูล...")
            for i, command in enumerate(sql_commands):
                command = command.strip()
                if command and not command.startswith('--') and not command.startswith('/*'):
                    try:
                        cursor.execute(command)
                        if i % 50 == 0:  # แสดงความคืบหน้าทุก 50 คำสั่ง
                            print(f"   ประมวลผลคำสั่งที่ {i+1}...")
                    except Error as e:
                        if "already exists" not in str(e).lower():
                            print(f"⚠️  คำเตือน: {e}")
            
            connection.commit()
            print("✅ นำเข้าข้อมูลสำเร็จ")
            
            # ตรวจสอบจำนวนยาง
            cursor.execute("SELECT COUNT(*) FROM tires")
            tire_count = cursor.fetchone()[0]
            print(f"📊 จำนวนยางในฐานข้อมูล: {tire_count} รายการ")
            
    except Error as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("🔌 ปิดการเชื่อมต่อฐานข้อมูล")
    
    return True

def test_connection():
    """ทดสอบการเชื่อมต่อฐานข้อมูล"""
    try:
        from database import get_cursor
        
        cursor = get_cursor()
        if cursor:
            cursor.execute("SELECT COUNT(*) as count FROM tires")
            result = cursor.fetchone()
            print(f"✅ การเชื่อมต่อสำเร็จ - จำนวนยาง: {result['count']}")
            return True
        else:
            print("❌ ไม่สามารถสร้าง cursor ได้")
            return False
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการทดสอบ: {e}")
        return False

if __name__ == "__main__":
    print("🚀 เริ่มต้นการตั้งค่าฐานข้อมูล...")
    
    # ตรวจสอบว่ามีไฟล์ SQL หรือไม่
    if not os.path.exists('tire_shop.sql'):
        print("❌ ไม่พบไฟล์ tire_shop.sql")
        sys.exit(1)
    
    # สร้างฐานข้อมูลและนำเข้าข้อมูล
    if create_database():
        print("\n🧪 ทดสอบการเชื่อมต่อ...")
        if test_connection():
            print("\n🎉 การตั้งค่าฐานข้อมูลเสร็จสิ้น!")
        else:
            print("\n⚠️  การตั้งค่าฐานข้อมูลเสร็จสิ้น แต่การเชื่อมต่อมีปัญหา")
    else:
        print("\n❌ การตั้งค่าฐานข้อมูลล้มเหลว")
        sys.exit(1)
