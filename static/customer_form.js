document.addEventListener('DOMContentLoaded', function() {
    // Global variable to track new vehicle IDs
    let newVehicleCounter = 1;
    let vehicleBrandsData = null;
    
    // Load vehicle data first
    fetch("/static/data/vehicle_brands_models.json")
        .then(response => response.json())
        .then(data => {
            vehicleBrandsData = data;
        })
        .catch(error => {
            console.error('Error loading vehicle data:', error);
        });
    
    // Function to add new vehicle
    window.addVehicle = function() {
        newVehicleCounter++;
        const vehicleId = 'new' + newVehicleCounter;
        const container = document.getElementById('vehicles-container');
        
        const vehicleBlock = document.createElement('div');
        vehicleBlock.className = 'vehicle-block border rounded-lg p-4 mb-4 bg-gray-50';
        vehicleBlock.setAttribute('data-vehicle-id', vehicleId);
        
        // Generate brand options
        let brandOptions = '<option value="">-- เลือกยี่ห้อ --</option>';
        if (vehicleBrandsData && vehicleBrandsData.brands) {
            vehicleBrandsData.brands.forEach(brand => {
                brandOptions += `<option value="${brand.brand_id}">${brand.brand_name}</option>`;
            });
        } else {
            // Fallback options if data not loaded
            brandOptions = `
                <option value="">-- เลือกยี่ห้อ --</option>
                <option value="1">Toyota</option>
                <option value="2">Honda</option>
                <option value="3">Nissan</option>
                <option value="4">Mazda</option>
                <option value="5">Mitsubishi</option>
                <option value="6">Isuzu</option>
                <option value="7">Ford</option>
                <option value="8">Chevrolet</option>
                <option value="9">BMW</option>
                <option value="10">Mercedes-Benz</option>
                <option value="11">Audi</option>
                <option value="12">Volkswagen</option>
                <option value="13">Hyundai</option>
                <option value="14">Kia</option>
                <option value="15">Suzuki</option>
                <option value="16">Subaru</option>
                <option value="17">Lexus</option>
                <option value="18">Infiniti</option>
                <option value="19">Volvo</option>
                <option value="20">Jaguar</option>
                <option value="21">Land Rover</option>
                <option value="22">Mini</option>
                <option value="23">Fiat</option>
                <option value="24">Alfa Romeo</option>
                <option value="25">Peugeot</option>
                <option value="26">Citroen</option>
                <option value="27">Renault</option>
                <option value="28">Opel</option>
                <option value="29">Skoda</option>
                <option value="30">Seat</option>
            `;
        }
        
        vehicleBlock.innerHTML = `
            <div class="flex justify-between items-center mb-3">
                <h4 class="font-medium text-gray-700">รถคันใหม่</h4>
                <button type="button" class="remove-vehicle-btn text-red-600 hover:text-red-800 text-sm" onclick="removeVehicle(this)">
                    <i class="fas fa-trash"></i> ลบรถคันนี้
                </button>
            </div>
            <input type="hidden" name="vehicle_${vehicleId}_id" value="${vehicleId}">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                    <label class="block font-medium mb-1">ประเภทรถ <span class="text-red-500">*</span></label>
                    <select name="vehicle_${vehicleId}_vehicle_type_id" class="w-full border rounded px-3 py-2" required>
                        <option value="">-- เลือกประเภทรถ --</option>
                        <option value="1">รถเก๋ง</option>
                        <option value="2">SUV</option>
                        <option value="3">กระบะ/รถตู้</option>
                    </select>
                </div>
                <div>
                    <label class="block font-medium mb-1">ทะเบียนรถ</label>
                    <input type="text" name="vehicle_${vehicleId}_license_plate" class="w-full border rounded px-3 py-2" value="">
                </div>
                <div>
                    <label class="block font-medium mb-1">จังหวัด</label>
                    <select name="vehicle_${vehicleId}_license_province" class="w-full border rounded px-3 py-2">
                        <option value="">-- เลือกจังหวัด --</option>
                        <option value="กรุงเทพมหานคร">กรุงเทพมหานคร</option>
                        <option value="สมุทรปราการ">สมุทรปราการ</option>
                        <option value="นนทบุรี">นนทบุรี</option>
                        <option value="ปทุมธานี">ปทุมธานี</option>
                        <option value="พระนครศรีอยุธยา">พระนครศรีอยุธยา</option>
                        <option value="อ่างทอง">อ่างทอง</option>
                        <option value="ลพบุรี">ลพบุรี</option>
                        <option value="สิงห์บุรี">สิงห์บุรี</option>
                        <option value="ชัยนาท">ชัยนาท</option>
                        <option value="สระบุรี">สระบุรี</option>
                        <option value="นครนายก">นครนายก</option>
                        <option value="สมุทรสาคร">สมุทรสาคร</option>
                        <option value="สมุทรสงคราม">สมุทรสงคราม</option>
                        <option value="นครปฐม">นครปฐม</option>
                        <option value="สุพรรณบุรี">สุพรรณบุรี</option>
                        <option value="กาญจนบุรี">กาญจนบุรี</option>
                        <option value="ราชบุรี">ราชบุรี</option>
                        <option value="เพชรบุรี">เพชรบุรี</option>
                        <option value="ประจวบคีรีขันธ์">ประจวบคีรีขันธ์</option>
                        <option value="นครศรีธรรมราช">นครศรีธรรมราช</option>
                        <option value="กระบี่">กระบี่</option>
                        <option value="พังงา">พังงา</option>
                        <option value="ภูเก็ต">ภูเก็ต</option>
                        <option value="สุราษฎร์ธานี">สุราษฎร์ธานี</option>
                        <option value="ระนอง">ระนอง</option>
                        <option value="ชุมพร">ชุมพร</option>
                        <option value="สงขลา">สงขลา</option>
                        <option value="สตูล">สตูล</option>
                        <option value="ตรัง">ตรัง</option>
                        <option value="พัทลุง">พัทลุง</option>
                        <option value="ปัตตานี">ปัตตานี</option>
                        <option value="ยะลา">ยะลา</option>
                        <option value="นราธิวาส">นราธิวาส</option>
                        <option value="บึงกาฬ">บึงกาฬ</option>
                        <option value="บุรีรัมย์">บุรีรัมย์</option>
                        <option value="ชัยภูมิ">ชัยภูมิ</option>
                        <option value="นครราชสีมา">นครราชสีมา</option>
                        <option value="นครพนม">นครพนม</option>
                        <option value="มุกดาหาร">มุกดาหาร</option>
                        <option value="ยโสธร">ยโสธร</option>
                        <option value="อำนาจเจริญ">อำนาจเจริญ</option>
                        <option value="หนองบัวลำภู">หนองบัวลำภู</option>
                        <option value="ขอนแก่น">ขอนแก่น</option>
                        <option value="อุดรธานี">อุดรธานี</option>
                        <option value="เลย">เลย</option>
                        <option value="หนองคาย">หนองคาย</option>
                        <option value="มหาสารคาม">มหาสารคาม</option>
                        <option value="ร้อยเอ็ด">ร้อยเอ็ด</option>
                        <option value="กาฬสินธุ์">กาฬสินธุ์</option>
                        <option value="สกลนคร">สกลนคร</option>
                        <option value="นครสวรรค์">นครสวรรค์</option>
                        <option value="อุทัยธานี">อุทัยธานี</option>
                        <option value="กำแพงเพชร">กำแพงเพชร</option>
                        <option value="ตาก">ตาก</option>
                        <option value="สุโขทัย">สุโขทัย</option>
                        <option value="พิษณุโลก">พิษณุโลก</option>
                        <option value="เพชรบูรณ์">เพชรบูรณ์</option>
                        <option value="พิจิตร">พิจิตร</option>
                        <option value="แพร่">แพร่</option>
                        <option value="น่าน">น่าน</option>
                        <option value="พะเยา">พะเยา</option>
                        <option value="เชียงราย">เชียงราย</option>
                        <option value="แม่ฮ่องสอน">แม่ฮ่องสอน</option>
                        <option value="ลำปาง">ลำปาง</option>
                        <option value="ลำพูน">ลำพูน</option>
                        <option value="เชียงใหม่">เชียงใหม่</option>
                        <option value="อุตรดิตถ์">อุตรดิตถ์</option>
                        <option value="ตาก">ตาก</option>
                        <option value="สุโขทัย">สุโขทัย</option>
                        <option value="พิษณุโลก">พิษณุโลก</option>
                        <option value="เพชรบูรณ์">เพชรบูรณ์</option>
                        <option value="พิจิตร">พิจิตร</option>
                        <option value="แพร่">แพร่</option>
                        <option value="น่าน">น่าน</option>
                        <option value="พะเยา">พะเยา</option>
                        <option value="เชียงราย">เชียงราย</option>
                        <option value="แม่ฮ่องสอน">แม่ฮ่องสอน</option>
                        <option value="ลำปาง">ลำปาง</option>
                        <option value="ลำพูน">ลำพูน</option>
                        <option value="เชียงใหม่">เชียงใหม่</option>
                        <option value="อุตรดิตถ์">อุตรดิตถ์</option>
                    </select>
                </div>
                <div>
                    <label class="block font-medium mb-1">ยี่ห้อ</label>
                    <select name="vehicle_${vehicleId}_brand_id" class="vehicle-brand" data-vehicle-id="${vehicleId}" id="brand_${vehicleId}">
                        ${brandOptions}
                    </select>
                </div>
                <div>
                    <label class="block font-medium mb-1">รุ่น</label>
                    <select name="vehicle_${vehicleId}_model_name" class="vehicle-model" data-vehicle-id="${vehicleId}" id="model_${vehicleId}">
                        <option value="">-- เลือกรุ่น --</option>
                    </select>
                </div>
                <div>
                    <label class="block font-medium mb-1">สี</label>
                    <input type="text" name="vehicle_${vehicleId}_color" class="w-full border rounded px-3 py-2" value="">
                </div>
                <div>
                    <label class="block font-medium mb-1">ประเภทเครื่องยนต์</label>
                    <select name="vehicle_${vehicleId}_engine_type_name" class="w-full border rounded px-3 py-2">
                        <option value="">-- เลือกประเภทเครื่องยนต์ --</option>
                        <option value="เบนซิน">เบนซิน</option>
                        <option value="ดีเซล">ดีเซล</option>
                        <option value="ไฮบริด">ไฮบริด</option>
                        <option value="ไฟฟ้า (EV)">ไฟฟ้า (EV)</option>
                    </select>
                </div>
                <div>
                    <label class="block font-medium mb-1">ปี</label>
                    <select name="vehicle_${vehicleId}_year" class="w-full border rounded px-3 py-2" required>
                        <option value="">-- เลือกปี --</option>
                        ${generateYearOptions()}
                    </select>
                </div>
            </div>
        `;
        
        container.appendChild(vehicleBlock);
        
        // Initialize Select2 for brand and model in new vehicle
        const brandSelect = vehicleBlock.querySelector('.vehicle-brand');
        const modelSelect = vehicleBlock.querySelector('.vehicle-model');
        
        if (brandSelect && modelSelect) {
            // Initialize Select2 for brand
            $(brandSelect).select2({
                placeholder: '-- เลือกยี่ห้อ --',
                allowClear: true,
                width: '100%',
                language: {
                    noResults: function() {
                        return "ไม่พบข้อมูล";
                    },
                    searching: function() {
                        return "กำลังค้นหา...";
                    }
                }
            });
            
            // Initialize Select2 for model
            $(modelSelect).select2({
                placeholder: '-- เลือกรุ่น --',
                allowClear: true,
                width: '100%',
                language: {
                    noResults: function() {
                        return "ไม่พบข้อมูล";
                    },
                    searching: function() {
                        return "กำลังค้นหา...";
                    }
                }
            });
            
            // Add brand change event
            $(brandSelect).on('change', function() {
                handleBrandChange(this);
            });
        }
    };
    
    // Function to remove vehicle
    window.removeVehicle = function(button) {
        const vehicleBlock = button.closest('.vehicle-block');
        if (vehicleBlock) {
            // Destroy Select2 instances before removing
            const brandSelect = vehicleBlock.querySelector('.vehicle-brand');
            const modelSelect = vehicleBlock.querySelector('.vehicle-model');
            
            if (brandSelect) {
                $(brandSelect).select2('destroy');
            }
            if (modelSelect) {
                $(modelSelect).select2('destroy');
            }
            
            vehicleBlock.remove();
        }
    };
    
    // Function to generate year options
    function generateYearOptions() {
        const currentYear = new Date().getFullYear();
        let options = '';
        for (let year = currentYear; year >= 1980; year--) {
            options += `<option value="${year}">${year}</option>`;
        }
        return options;
    }
    
    // Function to handle brand change
    function handleBrandChange(brandSelect) {
        const vehicleId = brandSelect.getAttribute('data-vehicle-id');
        const modelSelect = document.getElementById('model_' + vehicleId);
        const brandId = brandSelect.value;
        
        // Clear model options
        modelSelect.innerHTML = '<option value="">-- เลือกรุ่น --</option>';
        
        if (brandId && vehicleBrandsData && vehicleBrandsData.models) {
            // Filter models by brand_id
            const filteredModels = vehicleBrandsData.models.filter(m => m.brand_id == brandId);
            filteredModels.forEach(function(m) {
                const opt = document.createElement('option');
                opt.value = m.model_name;
                opt.text = m.model_name;
                modelSelect.appendChild(opt);
            });
            // Trigger change to update Select2
            $(modelSelect).trigger('change');
        } else if (brandId) {
            // Fallback to API call if local data not available
            fetch('/api/vehicle_models?brand_id=' + encodeURIComponent(brandId))
                .then(res => res.json())
                .then(models => {
                    models.forEach(function(m) {
                        const opt = document.createElement('option');
                        opt.value = m.model_name;
                        opt.text = m.model_name;
                        modelSelect.appendChild(opt);
                    });
                    // Trigger change to update Select2
                    $(modelSelect).trigger('change');
                })
                .catch(error => {
                    console.error('Error loading vehicle models:', error);
                });
        } else {
            // Trigger change to update Select2
            $(modelSelect).trigger('change');
        }
    }
    
    // Add event listener for add vehicle button
    const addVehicleBtn = document.getElementById('add-vehicle-btn');
    if (addVehicleBtn) {
        addVehicleBtn.addEventListener('click', addVehicle);
    }
    
    // Initialize Select2 for existing vehicle brand and model dropdowns
    document.querySelectorAll('.vehicle-brand').forEach(function(brandSelect) {
        brandSelect.addEventListener('change', function() {
            handleBrandChange(this);
        });
        
        // Trigger change event on page load (for edit mode)
        if (brandSelect.value) {
            brandSelect.dispatchEvent(new Event('change'));
        }
    });

    // Address cascading dropdowns
    var provinceSelect = document.getElementById('provinceSelect');
    var districtSelect = document.getElementById('districtSelect');
    var subdistrictSelect = document.getElementById('subdistrictSelect');
    var zipcodeSelect = document.getElementById('zipcodeSelect');
    
    if (provinceSelect && districtSelect) {
        provinceSelect.addEventListener('change', function() {
            var province = this.value;
            districtSelect.innerHTML = '<option value="">-- เลือกอำเภอ/เขต --</option>';
            subdistrictSelect.innerHTML = '<option value="">-- เลือกตำบล/แขวง --</option>';
            zipcodeSelect.innerHTML = '<option value="">-- เลือกรหัสไปรษณีย์ --</option>';
            
            if (province) {
                fetch('/api/districts?province=' + encodeURIComponent(province))
                    .then(res => res.json())
                    .then(districts => {
                        districts.forEach(function(d) {
                            var opt = document.createElement('option');
                            opt.value = d;
                            opt.text = d;
                            districtSelect.appendChild(opt);
                        });
                    })
                    .catch(error => {
                        console.error('Error loading districts:', error);
                    });
                    
                fetch('/api/zipcodes?province=' + encodeURIComponent(province))
                    .then(res => res.json())
                    .then(zipcodes => {
                        zipcodes.forEach(function(z) {
                            var opt = document.createElement('option');
                            opt.value = z;
                            opt.text = z;
                            zipcodeSelect.appendChild(opt);
                        });
                    })
                    .catch(error => {
                        console.error('Error loading zipcodes:', error);
                    });
            }
        });
    }
    
    if (districtSelect && subdistrictSelect && provinceSelect) {
        districtSelect.addEventListener('change', function() {
            var province = provinceSelect.value;
            var district = this.value;
            subdistrictSelect.innerHTML = '<option value="">-- เลือกตำบล/แขวง --</option>';
            
            if (province && district) {
                fetch('/api/subdistricts?province=' + encodeURIComponent(province) + '&district=' + encodeURIComponent(district))
                    .then(res => res.json())
                    .then(subdistricts => {
                        subdistricts.forEach(function(s) {
                            var opt = document.createElement('option');
                            opt.value = s;
                            opt.text = s;
                            subdistrictSelect.appendChild(opt);
                        });
                    })
                    .catch(error => {
                        console.error('Error loading subdistricts:', error);
                    });
            }
        });
    }

    // Form validation before submission
    var form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            // Check if at least one vehicle has required fields
            var vehicleBlocks = document.querySelectorAll('[name*="vehicle_"][name*="_vehicle_type_id"]');
            var hasValidVehicle = false;
            var missingVehicleTypes = [];
            var vehicleCount = 0;
            
            vehicleBlocks.forEach(function(select) {
                vehicleCount++;
                if (select.value && select.value.trim() !== '') {
                    hasValidVehicle = true;
                } else {
                    // Get vehicle number for error message
                    var vehicleId = select.name.match(/vehicle_([^_]+)_vehicle_type_id/);
                    if (vehicleId) {
                        var displayId = vehicleId[1];
                        if (displayId.startsWith('new')) {
                            displayId = 'ใหม่';
                        }
                        missingVehicleTypes.push(displayId);
                    }
                }
            });
            
            if (vehicleCount === 0) {
                e.preventDefault();
                alert('กรุณาเพิ่มรถอย่างน้อย 1 คัน');
                return false;
            }
            
            if (!hasValidVehicle) {
                e.preventDefault();
                alert('กรุณาเลือกประเภทรถอย่างน้อย 1 คัน');
                return false;
            }
            
            if (missingVehicleTypes.length > 0) {
                e.preventDefault();
                alert('กรุณาเลือกประเภทรถสำหรับรถคันที่: ' + missingVehicleTypes.join(', '));
                return false;
            }
            
            // Ensure all Select2 values are properly set
            var select2Elements = document.querySelectorAll('.select2-hidden-accessible');
            select2Elements.forEach(function(element) {
                var select = element.querySelector('select');
                if (select && select.value) {
                    // Force update the hidden input
                    var event = new Event('change', { bubbles: true });
                    select.dispatchEvent(event);
                }
            });
            
            console.log('Form submitted successfully');
        });
    }
    
    // Debug: Log form data on submit
    if (form) {
        form.addEventListener('submit', function(e) {
            console.log('Form submission started');
            var formData = new FormData(this);
            for (var pair of formData.entries()) {
                console.log(pair[0] + ': ' + pair[1]);
            }
        });
    }
}); 

// Responsive design management for customer home page
document.addEventListener('DOMContentLoaded', function() {
    // Handle window resize events
    function handleResize() {
        const container = document.querySelector('.container');
        const grid = document.querySelector('.grid');
        
        if (window.innerWidth < 1024) {
            // Mobile/tablet layout adjustments
            if (container) {
                container.classList.add('px-2');
                container.classList.remove('px-4');
            }
        } else {
            // Desktop layout
            if (container) {
                container.classList.remove('px-2');
                container.classList.add('px-4');
            }
        }
    }
    
    // Initial call
    handleResize();
    
    // Listen for resize events
    window.addEventListener('resize', handleResize);
    
    // Handle image slider responsive behavior
    const sliderContainer = document.querySelector('.aspect-square');
    if (sliderContainer) {
        const images = sliderContainer.querySelectorAll('img');
        images.forEach(img => {
            img.addEventListener('load', function() {
                // Ensure proper aspect ratio on mobile
                if (window.innerWidth < 768) {
                    this.style.objectFit = 'cover';
                    this.style.objectPosition = 'center';
                }
            });
        });
    }
    
    // Handle form responsive behavior
    const form = document.querySelector('form');
    if (form) {
        const inputs = form.querySelectorAll('select, input');
        inputs.forEach(input => {
            input.addEventListener('focus', function() {
                // Add responsive focus styles
                this.classList.add('ring-2', 'ring-yellow-400');
            });
            
            input.addEventListener('blur', function() {
                // Remove focus styles
                this.classList.remove('ring-2', 'ring-yellow-400');
            });
        });
    }
});

// Enhanced slider functionality
function initSlider() {
    let current = 0;
    const images = document.querySelectorAll('[id^="slider-img-"]');
    
    function showSlide(index) {
        images.forEach((img, i) => {
            if (i === index) {
                img.classList.remove('opacity-0');
                img.style.zIndex = '1';
            } else {
                img.classList.add('opacity-0');
                img.style.zIndex = '0';
            }
        });
    }
    
    window.changeSlide = function(direction) {
        current = (current + direction + images.length) % images.length;
        showSlide(current);
    };
    
    if (images.length > 1) {
        // Auto-slide with responsive timing
        const slideInterval = window.innerWidth < 768 ? 4000 : 3000;
        setInterval(() => {
            current = (current + 1) % images.length;
            showSlide(current);
        }, slideInterval);
    }
}

// Initialize slider when DOM is loaded
document.addEventListener('DOMContentLoaded', initSlider); 