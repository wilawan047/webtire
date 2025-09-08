console.log('tire_form.js loaded');

// ฟังก์ชันสำหรับการแสดง preview รูปภาพ
function setupImagePreview() {
    console.log('setupImagePreview called');
    const fileInput = document.querySelector('input[name="tire_image"]');
    console.log('fileInput found:', fileInput);
    
    if (fileInput) {
        // หา upload area ที่มี class border-2 border-dashed
        const uploadArea = fileInput.closest('.border-2.border-dashed');
        console.log('uploadArea found:', uploadArea);
        
        if (uploadArea) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // สร้าง preview รูปภาพ
                const reader = new FileReader();
                reader.onload = function(e) {
                    // ลบ preview เดิม (ถ้ามี)
                    const existingPreview = uploadArea.querySelector('.image-preview');
                    if (existingPreview) {
                        existingPreview.remove();
                    }
                    
                    // สร้าง preview ใหม่
                    const previewDiv = document.createElement('div');
                    previewDiv.className = 'image-preview mt-4';
                    previewDiv.innerHTML = `
                        <img src="${e.target.result}" alt="Preview" class="max-h-40 rounded shadow border mx-auto">
                        <p class="text-sm text-gray-600 mt-2 text-center">${file.name}</p>
                    `;
                    
                    // เพิ่ม preview ลงใน upload area (เฉพาะส่วนอัปโหลด)
                    uploadArea.appendChild(previewDiv);
                };
                reader.readAsDataURL(file);
            }
        });
        
        // เพิ่ม drag and drop functionality
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadArea.classList.add('border-indigo-400', 'bg-indigo-50');
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('border-indigo-400', 'bg-indigo-50');
        });
        
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('border-indigo-400', 'bg-indigo-50');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                fileInput.dispatchEvent(new Event('change'));
            }
        });
        }
    }
}

// Static data for dropdowns (if no data from API)
const WIDTHS = ["135","145","155","165","175","185","195","205","215","225","235","245","255","265","275","285","295","305","315"];
const ASPECTS = ["30","35","40","45","50","55","60","65","70","75","80","85"];
const RIM_DIAMETERS = ["13","14","15","16","17","18","19","20","21","22"];

function setDropdownOptions(select, options, selectedValue) {
    if (!select) {
        console.warn('setDropdownOptions: select element not found');
        return;
    }
    
    select.innerHTML = '';
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'ไม่ระบุ';
    select.appendChild(opt);
    options.forEach(val => {
        const o = document.createElement('option');
        if (typeof val === 'object') {
            o.value = val.value;
            o.textContent = val.label;
            if (selectedValue && selectedValue == val.value) o.selected = true;
        } else {
            o.value = val;
            o.textContent = val;
            if (selectedValue && selectedValue == val) o.selected = true;
        }
        select.appendChild(o);
    });
}

async function loadBrands(selectedBrandId) {
    // ใช้ข้อมูล brands ที่ส่งมาจาก server แทนการเรียก API
    const brands = window.allBrands || [];
    console.log('loadBrands called with selectedBrandId:', selectedBrandId);
    console.log('Available brands:', brands);
    
    const brandSelect = document.getElementById('brandSelect');
    brandSelect.innerHTML = '';
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'ไม่ระบุ';
    brandSelect.appendChild(opt);
    brands.forEach(b => {
        const o = document.createElement('option');
        o.value = b.brand_id;
        o.textContent = b.brand_name;
        if (selectedBrandId && String(selectedBrandId) === String(b.brand_id)) o.selected = true;
        brandSelect.appendChild(o);
    });
}

async function loadModels(brandId, selectedModelId) {
    console.log('=== LOAD MODELS FUNCTION START ===');
    console.log('loadModels called with brandId:', brandId, 'selectedModelId:', selectedModelId);
    
    // ใช้ข้อมูล models ที่ส่งมาจาก server แทนการเรียก API
    const models = window.allModels || [];
    const modelSelect = document.getElementById('modelSelect');
    
    if (!modelSelect) {
        console.error('modelSelect element not found');
        return;
    }
    
    console.log('Total models available:', models.length);
    console.log('Models data:', models);
    
    modelSelect.innerHTML = '';
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'ไม่ระบุ';
    modelSelect.appendChild(opt);
    
    // กรองรุ่นยางตามยี่ห้อที่เลือก
    const filteredModels = models.filter(m => {
        if (!brandId || brandId === '' || brandId === 'null') {
            console.log(`Model ${m.model_name} - no brand filter, showing all`);
            return true; // ถ้าไม่ได้เลือกยี่ห้อ ให้แสดงรุ่นทั้งหมด
        }
        const match = String(m.brand_id) === String(brandId);
        console.log(`Model ${m.model_name} (brand_id: ${m.brand_id}) matches brandId ${brandId}:`, match);
        return match;
    });
    
    console.log('Filtered models count:', filteredModels.length);
    console.log('Filtered models:', filteredModels);
    
    filteredModels.forEach(m => {
        const o = document.createElement('option');
        o.value = m.model_id;
        o.textContent = m.model_name;
        if (selectedModelId && String(selectedModelId) === String(m.model_id)) o.selected = true;
        modelSelect.appendChild(o);
    });
    
    console.log('=== LOAD MODELS FUNCTION END ===');
}

async function loadOptions(modelId, tire) {
    // ใช้ข้อมูลเริ่มต้นแทนการเรียก API ที่ไม่มีอยู่
    console.log('loadOptions called with modelId:', modelId);
    // ไม่ต้องทำอะไรเพราะ HTML ใช้ input text แทน select dropdowns
    // Preselect for construction, speed_symbol, ply_rating, tubeless_type, tire_load_type
    if (tire) {
        document.getElementById('constructionSelect').value = tire.construction || '';
        document.getElementById('speedSymbolSelect').value = tire.speed_symbol || '';
        document.getElementById('plyRatingSelect').value = tire.ply_rating || '';
        document.getElementById('tubelessTypeSelect').value = tire.tubeless_type || '';
        document.getElementById('tireLoadTypeSelect').value = tire.tire_load_type || '';
        // Checkbox for service_description (XL)
        document.querySelector('input[name="service_description"]').checked = tire.service_description === 'XL';
        // Checkbox for high_speed_rating
        document.querySelector('input[name="high_speed_rating"]').checked = !!tire.high_speed_rating;
    }
}

function safeValue(val) {
    return (val === undefined || val === null || val === "None") ? "" : val;
}

// ฟังก์ชันสำหรับ customer_form.html: อัปเดตรุ่นตามยี่ห้อที่เลือก
async function updateVehicleModelDropdown(vehicleId) {
  const brandSelect = document.getElementById('brand_' + vehicleId);
  const modelSelect = document.getElementById('model_' + vehicleId);
  const selectedBrandId = brandSelect.value;
  const selectedModelId = modelSelect.getAttribute('data-selected') || modelSelect.value;
  // ลบ option เดิม
  while (modelSelect.options.length > 1) modelSelect.remove(1);
  if (!selectedBrandId) return;
  // ดึงข้อมูลรุ่นจาก API
  const res = await fetch('/api/vehicle_models?brand_id=' + selectedBrandId);
  const models = await res.json();
  models.forEach(function(m) {
    const opt = document.createElement('option');
    opt.value = m.model_id;
    opt.textContent = m.model_name;
    if (selectedModelId && selectedModelId == m.model_id) opt.selected = true;
    modelSelect.appendChild(opt);
  });
}

// โหลด models ทั้งหมดจาก data attribute หรือ AJAX
window.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.vehicle-brand').forEach(function(brandSelect) {
    brandSelect.addEventListener('change', function() {
      const vehicleId = this.getAttribute('data-vehicle-id');
      updateVehicleModelDropdown(vehicleId);
    });
    // โหลดรุ่นอัตโนมัติเมื่อเปิดฟอร์ม (กรณี edit)
    const vehicleId = brandSelect.getAttribute('data-vehicle-id');
    const modelSelect = document.getElementById('model_' + vehicleId);
    if (brandSelect.value && modelSelect && (modelSelect.getAttribute('data-selected') || modelSelect.value)) {
      updateVehicleModelDropdown(vehicleId);
    }
  });
});

document.addEventListener('DOMContentLoaded', async function() {
    console.log('DOMContentLoaded - Starting tire form initialization');
    let tire = window.tireData || null;
    let brandId = tire?.brand_id;
    
    console.log('Initial tire data:', tire);
    console.log('Initial brandId:', brandId);
    
    // Setup image preview functionality
    setupImagePreview();
    
    // If brand_id is missing but model_id exists, lookup brand_id from model_id
    if (!brandId && tire?.model_id) {
        const res = await fetch('/api/tire_models');
        const models = await res.json();
        const found = models.find(m => String(m.model_id) === String(tire.model_id));
        if (found) brandId = found.brand_id;
    }
    
    console.log('About to load brands and models');
    await loadBrands(safeValue(brandId));
    // สำหรับหน้า add tire ให้โหลด models ทั้งหมดก่อน
    await loadModels(null, safeValue(tire?.model_id));
    await loadOptions(null, tire);

    // Preselect all dropdowns and checkboxes after all loads
    if (tire) {
        const brandSelect = document.getElementById('brandSelect');
        const modelSelect = document.getElementById('modelSelect');
        const widthSelect = document.getElementById('widthSelect');
        const aspectRatioSelect = document.getElementById('aspectRatioSelect');
        const constructionSelect = document.getElementById('constructionSelect');
        const rimDiameterSelect = document.getElementById('rimDiameterSelect');
        const speedSymbolSelect = document.getElementById('speedSymbolSelect');
        const plyRatingSelect = document.getElementById('plyRatingSelect');
        const tubelessTypeSelect = document.getElementById('tubelessTypeSelect');
        const tireLoadTypeSelect = document.getElementById('tireLoadTypeSelect');
        
        if (brandSelect) brandSelect.value = safeValue(brandId);
        if (modelSelect) modelSelect.value = safeValue(tire.model_id);
        if (widthSelect) widthSelect.value = safeValue(tire.width);
        if (aspectRatioSelect) aspectRatioSelect.value = safeValue(tire.aspect_ratio);
        if (constructionSelect) constructionSelect.value = safeValue(tire.construction);
        if (rimDiameterSelect) rimDiameterSelect.value = safeValue(tire.rim_diameter);
        if (speedSymbolSelect) speedSymbolSelect.value = safeValue(tire.speed_symbol);
        if (plyRatingSelect) plyRatingSelect.value = safeValue(tire.ply_rating);
        if (tubelessTypeSelect) tubelessTypeSelect.value = safeValue(tire.tubeless_type);
        if (tireLoadTypeSelect) tireLoadTypeSelect.value = safeValue(tire.tire_load_type);
        
        const serviceDescInput = document.querySelector('input[name="service_description"]');
        const highSpeedInput = document.querySelector('input[name="high_speed_rating"]');
        const loadIndexInput = document.querySelector('input[name="load_index"]');
        const priceEachInput = document.querySelector('input[name="price_each"]');
        const priceSetInput = document.querySelector('input[name="price_set"]');
        const productDateInput = document.querySelector('input[name="product_date"]');
        
        if (serviceDescInput) serviceDescInput.checked = tire.service_description === 'XL';
        if (highSpeedInput) highSpeedInput.checked = !!tire.high_speed_rating;
        if (loadIndexInput) loadIndexInput.value = safeValue(tire.load_index);
        if (priceEachInput) priceEachInput.value = safeValue(tire.price_each);
        if (priceSetInput) priceSetInput.value = safeValue(tire.price_set);
        if (productDateInput) productDateInput.value = safeValue(tire.product_date);
    }

    document.getElementById('brandSelect').addEventListener('change', async function() {
        const selectedBrandId = this.value;
        console.log('=== BRAND CHANGE EVENT ===');
        console.log('Brand changed to:', selectedBrandId);
        console.log('Available brands data:', window.allBrands);
        console.log('Available models data:', window.allModels);
        
        // Load models for the selected brand
        console.log('Calling loadModels with brandId:', selectedBrandId);
        await loadModels(selectedBrandId, null);
        
        // Reset model selection when brand changes
        document.getElementById('modelSelect').value = '';
        
        // Clear any existing options loading
        console.log('Models loaded for brand:', selectedBrandId);
        console.log('=== END BRAND CHANGE EVENT ===');
    });
    document.getElementById('modelSelect').addEventListener('change', async function() {
        // Store current values
        const widthSelect = document.getElementById('widthSelect');
        const aspectRatioSelect = document.getElementById('aspectRatioSelect');
        const rimDiameterSelect = document.getElementById('rimDiameterSelect');
        const constructionSelect = document.getElementById('constructionSelect');
        const speedSymbolSelect = document.getElementById('speedSymbolSelect');
        const plyRatingSelect = document.getElementById('plyRatingSelect');
        const tubelessTypeSelect = document.getElementById('tubelessTypeSelect');
        const tireLoadTypeSelect = document.getElementById('tireLoadTypeSelect');
        
        const prevWidth = widthSelect ? widthSelect.value : '';
        const prevAspect = aspectRatioSelect ? aspectRatioSelect.value : '';
        const prevRim = rimDiameterSelect ? rimDiameterSelect.value : '';
        const prevConstruction = constructionSelect ? constructionSelect.value : '';
        const prevSpeed = speedSymbolSelect ? speedSymbolSelect.value : '';
        const prevPly = plyRatingSelect ? plyRatingSelect.value : '';
        const prevTubeless = tubelessTypeSelect ? tubelessTypeSelect.value : '';
        const prevLoadType = tireLoadTypeSelect ? tireLoadTypeSelect.value : '';

        await loadOptions(null, {
            width: prevWidth,
            aspect_ratio: prevAspect,
            rim_diameter: prevRim,
            construction: prevConstruction,
            speed_symbol: prevSpeed,
            ply_rating: prevPly,
            tubeless_type: prevTubeless,
            tire_load_type: prevLoadType
        });
    });

    var modelSelect = document.getElementById('modelSelect');
    if (modelSelect) {
        modelSelect.addEventListener('change', function() {
            var modelId = this.value;
            var yearSelect = document.getElementById('yearSelect');
            if (!yearSelect) return;
            yearSelect.innerHTML = '<option value="">ไม่ระบุ</option>';
            if (modelId) {
                fetch('/api/vehicle_model_years?model_id=' + encodeURIComponent(modelId))
                    .then(res => res.json())
                    .then(years => {
                        years.forEach(function(year) {
                            var opt = document.createElement('option');
                            opt.value = year;
                            opt.text = year;
                            yearSelect.appendChild(opt);
                        });
                    });
            }
        });
    }
}); 