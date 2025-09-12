from functools import wraps
from flask import session, redirect, url_for, flash, request

def login_required(f):
    """Decorator สำหรับตรวจสอบการเข้าสู่ระบบของผู้ดูแล"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # อนุญาตเฉพาะ session ของผู้ดูแล (admin/staff/owner)
        role = session.get('role')
        if role == 'admin' and session.get('admin_user_id'):
            return f(*args, **kwargs)
        elif role == 'staff' and session.get('staff_user_id'):
            return f(*args, **kwargs)
        elif role == 'owner' and session.get('owner_user_id'):
            return f(*args, **kwargs)
        flash('กรุณาเข้าสู่ระบบผู้ดูแลระบบ', 'error')
        return redirect(url_for('auth.login', next=request.path))
    return decorated_function

def customer_login_required(f):
    """Decorator สำหรับตรวจสอบการเข้าสู่ระบบของลูกค้า"""
    @wraps(f)
    def decorated_function(*args, **kwargs):



        if not session.get('customer_id'):
            flash('กรุณาเข้าสู่ระบบเพื่อจองบริการ', 'error')
            return redirect(url_for('customer.home') + "#login")
        return f(*args, **kwargs)
    return decorated_function

def owner_login_required(f):
    """Decorator สำหรับตรวจสอบการเข้าสู่ระบบของเจ้าของกิจการ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # ตรวจสอบว่ามี session และ role เป็น owner หรือไม่
        if not session.get('owner_user_id') or session.get('role') != 'owner':
            flash('กรุณาเข้าสู่ระบบเจ้าของกิจการ', 'error')
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator สำหรับตรวจสอบการเข้าสู่ระบบของแอดมินเท่านั้น"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_user_id') or session.get('role') != 'admin':
            flash('คุณไม่มีสิทธิ์เข้าถึงส่วนนี้ กรุณาเข้าสู่ระบบแอดมิน', 'error')
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    """Decorator สำหรับตรวจสอบการเข้าสู่ระบบของพนักงานเท่านั้น"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('staff_user_id') or session.get('role') != 'staff':
            flash('คุณไม่มีสิทธิ์เข้าถึงส่วนนี้ กรุณาเข้าสู่ระบบพนักงาน', 'error')
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    """Decorator สำหรับตรวจสอบการเข้าสู่ระบบของลูกค้าเท่านั้น"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('customer_id') or session.get('role') != 'customer':
            flash('คุณไม่มีสิทธิ์เข้าถึงส่วนนี้ กรุณาเข้าสู่ระบบลูกค้า', 'error')
            return redirect(url_for('customer.home') + "#login")
        return f(*args, **kwargs)
    return decorated_function