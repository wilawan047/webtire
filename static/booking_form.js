// booking_form.js - จัดการดรอปดาวน์ยี่ห้อและรุ่นยาง
console.log('booking_form.js loaded');

// ตรวจสอบว่าไฟล์ถูกโหลดหรือไม่
if (typeof window !== 'undefined') {
    window.tireDropdownLoaded = true;
    console.log('Tire dropdown script loaded successfully');
}

// ฟังก์ชันโหลดรุ่นยางตามยี่ห้อที่เลือก
async function loadTireModels(brandId, modelSelectElement, selectedModelId = null) {
    try {
        console.log('Loading tire models for brand_id:', brandId);
        console.log('Model select element:', modelSelectElement);
        
        // ล้าง options เดิม
        modelSelectElement.innerHTML = '<option value="">-- เลือกรุ่น --</option>';
        
        if (!brandId) {
            console.log('No brand selected, skipping model load');
            return;
        }
        
        // ใช้โค้ดนี้แทนส่วน fetch เดิม
        const url = `/api/tire_models?brand_id=${brandId}`;
        console.log('Fetching from URL:', url);

        const response = await fetch(url);
        const models = await response.json();

        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.model_id;
            option.textContent = model.model_name;
            if (selectedModelId && String(selectedModelId) === String(model.model_id)) {
                option.selected = true;
            }
            modelSelectElement.appendChild(option);
        });

        console.log('Model dropdown populated with', models.length, 'options');
    } catch (error) {
        console.error('Error loading tire models:', error);
        
        // Fallback: เพิ่มข้อมูลทดสอบถ้า API ไม่ทำงาน
        console.log('Adding fallback models...');
        const fallbackModels = {
            1: [ // Michelin
                { model_id: 1, model_name: 'EXM2+' },
                { model_id: 2, model_name: 'ENERGY XM2+' },
                { model_id: 3, model_name: 'AGILIS3' }
            ],
            2: [ // BFgoodrich
                { model_id: 4, model_name: 'g-Force Sport' },
                { model_id: 5, model_name: 'Advantage T/A' }
            ],
            3: [ // Maxxis
                { model_id: 6, model_name: 'Victra Sport' },
                { model_id: 7, model_name: 'Premitra HP' }
            ]
        };
        
        const models = fallbackModels[brandId] || [];
        console.log('Using fallback models for brand', brandId, ':', models);
        
        modelSelectElement.innerHTML = '<option value="">-- เลือกรุ่น --</option>';
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.model_id;
            option.textContent = model.model_name;
            if (selectedModelId && String(selectedModelId) === String(model.model_id)) {
                option.selected = true;
            }
            modelSelectElement.appendChild(option);
            console.log('Added fallback option:', model.model_name);
        });
    }
}

// ฟังก์ชันจัดการการเปลี่ยนแปลงยี่ห้อ
function handleBrandChange(brandSelectElement, modelSelectElement) {
    console.log('Setting up brand change handler for:', brandSelectElement.id);
    
    brandSelectElement.addEventListener('change', async function() {
        console.log('Brand changed to:', this.value);
        console.log('Brand element:', this);
        console.log('Model element:', modelSelectElement);
        
        // ล้างรุ่นยางเมื่อเปลี่ยนยี่ห้อ
        modelSelectElement.innerHTML = '<option value="">-- เลือกรุ่น --</option>';
        
        if (this.value) {
            await loadTireModels(this.value, modelSelectElement);
        }
    });
}

// ฟังก์ชันเริ่มต้นสำหรับแต่ละคู่ยาง (หน้า/หลัง)
async function initializeTireDropdowns() {
    console.log('Initializing tire dropdowns...');
    
    // ยางด้านหน้า
    const frontBrandSelect = document.getElementById('tire_front_brand');
    const frontModelSelect = document.getElementById('tire_front_model');
    
    console.log('Front brand select found:', !!frontBrandSelect);
    console.log('Front model select found:', !!frontModelSelect);
    console.log('Front brand select element:', frontBrandSelect);
    console.log('Front model select element:', frontModelSelect);
    
    if (frontBrandSelect && frontModelSelect) {
        console.log('Setting up front tire dropdowns...');
        handleBrandChange(frontBrandSelect, frontModelSelect);
        
        // โหลดรุ่นยางเริ่มต้นถ้ามียี่ห้อที่เลือกไว้
        const selectedBrandId = frontBrandSelect.value;
        const selectedModelId = frontModelSelect.getAttribute('data-selected');
        
        console.log('Front selected brand ID:', selectedBrandId);
        console.log('Front selected model ID:', selectedModelId);
        
        if (selectedBrandId) {
            await loadTireModels(selectedBrandId, frontModelSelect, selectedModelId);
        }
    }
    
    // ยางด้านหลัง
    const rearBrandSelect = document.getElementById('tire_rear_brand');
    const rearModelSelect = document.getElementById('tire_rear_model');
    
    console.log('Rear brand select found:', !!rearBrandSelect);
    console.log('Rear model select found:', !!rearModelSelect);
    console.log('Rear brand select element:', rearBrandSelect);
    console.log('Rear model select element:', rearModelSelect);
    
    if (rearBrandSelect && rearModelSelect) {
        console.log('Setting up rear tire dropdowns...');
        handleBrandChange(rearBrandSelect, rearModelSelect);
        
        // โหลดรุ่นยางเริ่มต้นถ้ามียี่ห้อที่เลือกไว้
        const selectedBrandId = rearBrandSelect.value;
        const selectedModelId = rearModelSelect.getAttribute('data-selected');
        
        console.log('Rear selected brand ID:', selectedBrandId);
        console.log('Rear selected model ID:', selectedModelId);
        
        if (selectedBrandId) {
            await loadTireModels(selectedBrandId, rearModelSelect, selectedModelId);
        }
    }
}

// เริ่มต้นเมื่อหน้าโหลดเสร็จ
document.addEventListener('DOMContentLoaded', async function() {
    console.log('DOM Content Loaded - Starting tire dropdown initialization');
    
    // ตรวจสอบว่า elements ถูกพบหรือไม่
    const frontBrandSelect = document.getElementById('tire_front_brand');
    const frontModelSelect = document.getElementById('tire_front_model');
    const rearBrandSelect = document.getElementById('tire_rear_brand');
    const rearModelSelect = document.getElementById('tire_rear_model');
    
    console.log('Elements found:', {
        frontBrandSelect: !!frontBrandSelect,
        frontModelSelect: !!frontModelSelect,
        rearBrandSelect: !!rearBrandSelect,
        rearModelSelect: !!rearModelSelect
    });
    
    console.log('All elements:', {
        frontBrandSelect: frontBrandSelect,
        frontModelSelect: frontModelSelect,
        rearBrandSelect: rearBrandSelect,
        rearModelSelect: rearModelSelect
    });
    
    if (!frontBrandSelect || !frontModelSelect || !rearBrandSelect || !rearModelSelect) {
        console.log('ERROR: Some tire dropdown elements are missing!');
        console.log('Available elements with "tire" in ID:');
        document.querySelectorAll('[id*="tire"]').forEach(el => {
            console.log('-', el.id, el.tagName);
        });
        return;
    }
    
    // เรียกใช้ฟังก์ชันเริ่มต้น
    await initializeTireDropdowns();
    
    console.log('Tire dropdown initialization completed');
});