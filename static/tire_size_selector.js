console.log('Tire Size Selector script file loaded');

// Tire Size Selector - Dynamic Dropdown Management
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing tire size selector...');
    
    // รอสักครู่ให้หน้าเว็บโหลดเสร็จ
    setTimeout(function() {
        initTireSizeSelector();
    }, 1000);
});

function initTireSizeSelector() {
    console.log('Initializing Tire Size Selector...');
    
    const widthSelect = document.getElementById('widthSelect');
    const aspectSelect = document.getElementById('aspectSelect');
    const rimSelect = document.getElementById('rimSelect');
    
    console.log('Found elements:', {
        widthSelect: widthSelect,
        aspectSelect: aspectSelect,
        rimSelect: rimSelect
    });

    // ตรวจสอบว่าเจอ elements หรือไม่
    if (!widthSelect) {
        console.error('Could not find widthSelect element');
        return;
    }
    if (!aspectSelect) {
        console.error('Could not find aspectSelect element');
        return;
    }
    if (!rimSelect) {
        console.error('Could not find rimSelect element');
        return;
    }
    
    console.log('All elements found successfully');

    // โหลดรายการ width เมื่อหน้าเว็บโหลดเสร็จ
    loadWidths();

    // Event listener สำหรับการเปลี่ยนแปลง width
    widthSelect.addEventListener('change', function() {
        const selectedWidth = this.value;
        console.log('Width changed to:', selectedWidth);
        
        // รีเซ็ต aspect และ rim dropdowns
        resetSelect(aspectSelect, 'เลือกแก้มยาง');
        resetSelect(rimSelect, 'เลือกขนาดกระทะล้อ');
        
        if (selectedWidth) {
            loadAspects(selectedWidth);
        }
    });

    // Event listener สำหรับการเปลี่ยนแปลง aspect
    aspectSelect.addEventListener('change', function() {
        const selectedWidth = widthSelect.value;
        const selectedAspect = this.value;
        console.log('Aspect changed to:', selectedAspect);
        
        // รีเซ็ต rim dropdown
        resetSelect(rimSelect, 'เลือกขนาดกระทะล้อ');
        
        if (selectedWidth && selectedAspect) {
            loadRims(selectedWidth, selectedAspect);
        }
    });

    // ฟังก์ชันโหลดรายการ width
    async function loadWidths() {
        try {
            console.log('Loading widths...');
            setLoadingState(widthSelect, 'กำลังโหลด...');
            
            const response = await fetch('/api/tires/widths');
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Widths data:', data);
            
            if (data.success) {
                console.log('Widths loaded successfully:', data.items);
                populateSelect(widthSelect, data.items, 'เลือกความกว้าง');
            } else {
                console.error('API error:', data.error);
                setErrorState(widthSelect, 'เกิดข้อผิดพลาด ลองใหม่');
            }
        } catch (error) {
            console.error('Error loading widths:', error);
            setErrorState(widthSelect, 'เกิดข้อผิดพลาด ลองใหม่');
        }
    }

    // ฟังก์ชันโหลดรายการ aspect_ratio
    async function loadAspects(width) {
        try {
            console.log('Loading aspects for width:', width);
            setLoadingState(aspectSelect, 'กำลังโหลด...');
            aspectSelect.disabled = false;
            
            const response = await fetch(`/api/tires/aspects?width=${width}`);
            const data = await response.json();
            
            if (data.success) {
                console.log('Aspects loaded successfully:', data.items);
                populateSelect(aspectSelect, data.items, 'เลือกแก้มยาง');
                aspectSelect.disabled = false;
            } else {
                console.error('API error:', data.error);
                setErrorState(aspectSelect, 'เกิดข้อผิดพลาด ลองใหม่');
                aspectSelect.disabled = true;
            }
        } catch (error) {
            console.error('Error loading aspects:', error);
            setErrorState(aspectSelect, 'เกิดข้อผิดพลาด ลองใหม่');
            aspectSelect.disabled = true;
        }
    }

    // ฟังก์ชันโหลดรายการ rim_diameter
    async function loadRims(width, aspect) {
        try {
            console.log('Loading rims for width:', width, 'aspect:', aspect);
            setLoadingState(rimSelect, 'กำลังโหลด...');
            rimSelect.disabled = false;
            
            const response = await fetch(`/api/tires/rims?width=${width}&aspect=${aspect}`);
            const data = await response.json();
            
            if (data.success) {
                console.log('Rims loaded successfully:', data.items);
                populateSelect(rimSelect, data.items, 'เลือกขนาดกระทะล้อ');
                rimSelect.disabled = false;
            } else {
                console.error('API error:', data.error);
                setErrorState(rimSelect, 'เกิดข้อผิดพลาด ลองใหม่');
                rimSelect.disabled = true;
            }
        } catch (error) {
            console.error('Error loading rims:', error);
            setErrorState(rimSelect, 'เกิดข้อผิดพลาด ลองใหม่');
            rimSelect.disabled = true;
        }
    }

    // ฟังก์ชันเติมข้อมูลใน select
    function populateSelect(selectElement, items, defaultText) {
        console.log('Populating select with items:', items);
        
        // ล้างข้อมูลเก่า
        selectElement.innerHTML = '';
        
        // เพิ่มตัวเลือกเริ่มต้น
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = defaultText;
        selectElement.appendChild(defaultOption);
        
        // เพิ่มตัวเลือกจากข้อมูล
        items.forEach(item => {
            const option = document.createElement('option');
            option.value = item;
            option.textContent = item;
            selectElement.appendChild(option);
        });
        
        // ลบสถานะ loading
        selectElement.classList.remove('text-gray-500');
        
        console.log('Select populated with', items.length, 'items');
    }

    // ฟังก์ชันรีเซ็ต select
    function resetSelect(selectElement, defaultText) {
        selectElement.innerHTML = '';
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = defaultText;
        selectElement.appendChild(defaultOption);
        selectElement.disabled = true;
        selectElement.classList.remove('text-gray-500');
    }

    // ฟังก์ชันตั้งค่าสถานะ loading
    function setLoadingState(selectElement, loadingText) {
        selectElement.innerHTML = '';
        const loadingOption = document.createElement('option');
        loadingOption.value = '';
        loadingOption.textContent = loadingText;
        selectElement.appendChild(loadingOption);
        selectElement.classList.add('text-gray-500');
    }

    // ฟังก์ชันตั้งค่าสถานะ error
    function setErrorState(selectElement, errorText) {
        selectElement.innerHTML = '';
        const errorOption = document.createElement('option');
        errorOption.value = '';
        errorOption.textContent = errorText;
        selectElement.appendChild(errorOption);
        selectElement.classList.add('text-gray-500');
    }
}
