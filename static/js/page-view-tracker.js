/**
 * Page View Tracker
 * ระบบติดตามการเข้าชมหน้าเว็บ
 */

class PageViewTracker {
    constructor() {
        this.apiUrl = '/api/log-page-view';
        this.pageId = this.getPageId();
        this.init();
    }

    /**
     * รับ page_id จาก URL path
     */
    getPageId() {
        const path = window.location.pathname;
        
        // เก็บสถิติเฉพาะหน้า customer เท่านั้น
        if (path === '/') {
            return 'customer/home.html';
        } else if (path === '/contact') {
            return 'customer/contact.html';
        } else if (path === '/guide') {
            return 'customer/guide.html';
        } else if (path === '/promotions') {
            return 'customer/promotions.html';
        } else if (path === '/recommend') {
            return 'customer/recommend.html';
        } else if (path === '/tires') {
            return 'customer/tires.html';
        } else if (path === '/profile') {
            return 'customer/profile.html';
        } else if (path === '/booking') {
            return 'customer/booking.html';
        } else if (path.startsWith('/tires/')) {
            // สำหรับหน้า tires ตามแบรนด์
            const brand = path.split('/')[2];
            if (brand === 'bfgoodrich') {
                return 'customer/tires_bfgoodrich.html';
            } else if (brand === 'michelin') {
                return 'customer/tires_michelin.html';
            } else if (brand === 'maxxis') {
                return 'customer/tires_maxxis.html';
            }
        } else if (path.startsWith('/promotions/')) {
            return 'customer/promotion_detail.html';
        }
        
        // ไม่เก็บสถิติหน้าอื่นๆ
        return null;
    }

    /**
     * เริ่มต้นการติดตาม
     */
    init() {
        // รอให้หน้าเว็บโหลดเสร็จก่อนส่งข้อมูล
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.trackPageView();
            });
        } else {
            this.trackPageView();
        }
    }

    /**
     * ส่งข้อมูลการเข้าชมหน้าเว็บ
     */
    async trackPageView() {
        // ไม่ส่งข้อมูลถ้าไม่ใช่หน้า customer
        if (!this.pageId) {
            return;
        }
        
        try {
            const response = await fetch(`${this.apiUrl}?page_id=${encodeURIComponent(this.pageId)}`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();
            
            if (data.success) {
                console.log('Page view tracked successfully:', data);
            } else {
                console.error('Failed to track page view:', data.error);
            }
        } catch (error) {
            console.error('Error tracking page view:', error);
        }
    }

    /**
     * ดึงข้อมูลสถิติการเข้าชม (สำหรับใช้ในหน้า admin)
     */
    static async getPageViewsSummary() {
        try {
            const response = await fetch('/page-views-summary');
            const data = await response.json();
            
            if (data.success) {
                return data;
            } else {
                console.error('Failed to get page views summary:', data.error);
                return null;
            }
        } catch (error) {
            console.error('Error getting page views summary:', error);
            return null;
        }
    }
}

// เริ่มต้นการติดตามเมื่อโหลดไฟล์นี้
if (typeof window !== 'undefined') {
    // สร้าง instance ใหม่สำหรับทุกหน้า
    const pageTracker = new PageViewTracker();
    
    // ทำให้สามารถเข้าถึงได้จาก global scope
    window.PageViewTracker = PageViewTracker;
}
