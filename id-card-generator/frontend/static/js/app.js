// Use environment variable or fallback to production URL
const API_BASE_URL = window.ENV?.API_BASE_URL || "https://corporate-id-card.onrender.com";

// ========== STATE ==========
let employeeData = [];
let generatedCards = [];

// ========== NAVIGATION ==========
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const section = item.dataset.section;

        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        item.classList.add('active');

        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.getElementById(`section-${section}`).classList.add('active');

        const titles = {
            'upload': ['Upload Employee Data', 'Upload your Excel file with employee information'],
            'add-employee': ['Add Employee', 'Add or update a single employee and generate their ID card'],
            'photos': ['Employee Photos', 'Upload and manage employee photographs'],
            'generate': ['Generate ID Cards', 'Create high-quality 300 DPI ID cards'],
            'preview': ['Preview Cards', 'Preview all generated ID cards'],
            'download': ['Download Cards', 'Download generated cards individually or as ZIP']
        };

        if (titles[section]) {
            document.getElementById('section-title').textContent = titles[section][0];
            document.getElementById('section-subtitle').textContent = titles[section][1];
        }

        if (section === 'preview') loadPreview();
        if (section === 'download') loadFileList();
    });
});

// ========== EXCEL UPLOAD ==========
const excelDropzone = document.getElementById('excel-dropzone');
const excelInput = document.getElementById('excel-input');

['dragenter', 'dragover'].forEach(event => {
    excelDropzone.addEventListener(event, (e) => {
        e.preventDefault();
        excelDropzone.classList.add('dragover');
    });
});

['dragleave', 'drop'].forEach(event => {
    excelDropzone.addEventListener(event, (e) => {
        e.preventDefault();
        excelDropzone.classList.remove('dragover');
    });
});

excelDropzone.addEventListener('drop', (e) => {
    const file = e.dataTransfer.files[0];
    if (file) uploadExcel(file);
});

excelDropzone.addEventListener('click', () => {
    excelInput.click();
});

excelInput.addEventListener('change', () => {
    if (excelInput.files[0]) uploadExcel(excelInput.files[0]);
});

function uploadExcel(file) {
    showLoading('Uploading Excel file...');

    const formData = new FormData();
    formData.append('file', file);

    fetch(API_BASE_URL + '/upload-excel', { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            hideLoading();
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }

            employeeData = data.employees;
            document.getElementById('stat-employees').textContent = data.count;

            document.getElementById('excel-status').style.display = 'flex';
            document.getElementById('excel-filename').textContent = file.name;
            document.getElementById('excel-count').textContent = `${data.count} employees loaded`;

            renderEmployeeTable();
            showToast(`${data.count} employees loaded successfully!`, 'success');
        })
        .catch(err => {
            hideLoading();
            showToast('Failed to upload file', 'error');
        });
}

function renderEmployeeTable() {
    const container = document.getElementById('employee-table-container');
    const tbody = document.getElementById('employee-tbody');
    const deptFilter = document.getElementById('filter-dept');

    container.style.display = 'block';

    // Populate department filter
    const departments = [...new Set(employeeData.map(e => e.department))].filter(Boolean);
    deptFilter.innerHTML = '<option value="">All Departments</option>';
    departments.forEach(dept => {
        deptFilter.innerHTML += `<option value="${dept}">${dept}</option>`;
    });

    renderTableRows(employeeData);
}

function renderTableRows(data) {
    const tbody = document.getElementById('employee-tbody');
    tbody.innerHTML = '';

    data.forEach((emp, i) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${i + 1}</td>
            <td><strong style="color: var(--gold)">${emp.employee_id || ''}</strong></td>
            <td>${emp.name || ''}</td>
            <td>${emp.designation || ''}</td>
            <td>${emp.department || ''}</td>
            <td>${emp.blood_group || ''}</td>
            <td>${emp.mobile || ''}</td>
            <td>${emp.photo || '-'}</td>
        `;
        tbody.appendChild(row);
    });
}

function filterEmployees() {
    const search = document.getElementById('search-employee').value.toLowerCase();
    const dept = document.getElementById('filter-dept').value;

    let filtered = employeeData.filter(emp => {
        const matchesSearch = !search ||
            (emp.name || '').toLowerCase().includes(search) ||
            (emp.employee_id || '').toLowerCase().includes(search) ||
            (emp.designation || '').toLowerCase().includes(search);
        const matchesDept = !dept || emp.department === dept;
        return matchesSearch && matchesDept;
    });

    renderTableRows(filtered);
}

// ========== PHOTO UPLOAD ==========
const photoDropzone = document.getElementById('photo-dropzone');
const photoInput = document.getElementById('photo-input');

['dragenter', 'dragover'].forEach(event => {
    photoDropzone.addEventListener(event, (e) => {
        e.preventDefault();
        photoDropzone.classList.add('dragover');
    });
});

['dragleave', 'drop'].forEach(event => {
    photoDropzone.addEventListener(event, (e) => {
        e.preventDefault();
        photoDropzone.classList.remove('dragover');
    });
});

photoDropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length) uploadPhotos(files);
});

photoDropzone.addEventListener('click', () => {
    photoInput.click();
});

photoInput.addEventListener('change', () => {
    if (photoInput.files.length) uploadPhotos(photoInput.files);
});

function uploadPhotos(files) {
    showLoading('Uploading photos...');

    const formData = new FormData();
    Array.from(files).forEach(file => {
        formData.append('photos', file);
    });

    fetch(API_BASE_URL + '/upload-photos', { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            hideLoading();
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }

            const grid = document.getElementById('photo-grid');
            data.uploaded.forEach(filename => {
                const item = document.createElement('div');
                item.className = 'photo-item';
                item.innerHTML = `
                    <img src="${API_BASE_URL}/preview/${filename}" alt="${filename}" onerror="this.style.display='none'">
                    <div class="photo-name">${filename}</div>
                `;
                grid.appendChild(item);
            });

            showToast(`${data.count} photos uploaded!`, 'success');
        })
        .catch(err => {
            hideLoading();
            showToast('Failed to upload photos', 'error');
        });
}

// ========== GENERATE CARDS ==========
function generateCards() {
    if (employeeData.length === 0) {
        showToast('Please upload Excel data first', 'error');
        return;
    }

    const btn = document.getElementById('btn-generate');
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
    progressContainer.style.display = 'block';

    const total = employeeData.length;
    progressFill.style.width = '10%';
    progressText.textContent = `Generating... 0/${total}`;

    fetch(API_BASE_URL + '/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ employees: employeeData })
    })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error');
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-magic"></i> Generate All ID Cards';
                return;
            }

            generatedCards = data.generated;
            document.getElementById('stat-generated').textContent = data.count;
            document.getElementById('btn-download-all').disabled = false;

            // Animate progress
            let progress = 10;
            const interval = setInterval(() => {
                progress += 5;
                if (progress >= 100) {
                    clearInterval(interval);
                    progress = 100;
                    progressText.textContent = `Complete! ${data.count}/${total} cards generated`;

                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-check"></i> Generation Complete!';
                    setTimeout(() => {
                        btn.innerHTML = '<i class="fas fa-magic"></i> Generate All ID Cards';
                    }, 3000);
                } else {
                    progressText.textContent = `Generating... ${Math.floor(progress / 100 * total)}/${total}`;
                }
                progressFill.style.width = progress + '%';
            }, 50);

            showToast(`${data.count} ID cards generated successfully!`, 'success');
        })
        .catch(err => {
            showToast('Generation failed: ' + err.message, 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-magic"></i> Generate All ID Cards';
        });
}

// ========== PREVIEW ==========
function loadPreview() {
    const grid = document.getElementById('preview-grid');

    fetch(API_BASE_URL + '/get-generated')
        .then(res => res.json())
        .then(data => {
            if (data.files.length === 0) {
                grid.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-eye-slash"></i>
                        <h3>No Cards Generated Yet</h3>
                        <p>Generate ID cards first to preview them here</p>
                    </div>
                `;
                return;
            }

            grid.innerHTML = '';

            // Group front/back pairs
            const pairs = {};
            data.files.forEach(file => {
                const base = file.replace('_front.png', '').replace('_back.png', '');
                if (!pairs[base]) pairs[base] = {};
                if (file.includes('_front')) pairs[base].front = file;
                if (file.includes('_back')) pairs[base].back = file;
            });

            Object.entries(pairs).forEach(([id, files]) => {
                const card = document.createElement('div');
                card.className = 'preview-card';
                const frontFile = files.front || '';
                const backFile = files.back || '';
                card.innerHTML = `
                    <div class="preview-card-header" style="cursor:pointer;" onclick="openCardModal('${id}', '${frontFile}', '${backFile}')">
                        <h4>${id}</h4>
                        <span class="badge">300 DPI</span>
                    </div>
                    <div class="preview-card-images" style="cursor:pointer;" onclick="openCardModal('${id}', '${frontFile}', '${backFile}')">
                        ${files.front ? `<img src="${API_BASE_URL}/preview/${files.front}" alt="Front">` : ''}
                        ${files.back ? `<img src="${API_BASE_URL}/preview/${files.back}" alt="Back">` : ''}
                    </div>
                    <div class="preview-card-actions">
                        <button class="btn btn-gold" onclick="downloadCombined('${frontFile}', '${backFile}')">
                            <i class="fas fa-image"></i> Download Both
                        </button>
                        <a class="btn btn-outline" href="${API_BASE_URL}/download/${frontFile}" download><i class="fas fa-download"></i> Front</a>
                        <a class="btn btn-outline" href="${API_BASE_URL}/download/${backFile}" download><i class="fas fa-download"></i> Back</a>
                    </div>
                `;
                grid.appendChild(card);
            });
        });
}

function downloadCombined(frontFile, backFile) {
    if (!frontFile || !backFile) {
        showToast('Both front and back are needed', 'error');
        return;
    }
    fetch(API_BASE_URL + '/download-combined', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ front: frontFile, back: backFile })
    })
        .then(res => {
            if (!res.ok) throw new Error('Download failed');
            return res.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = frontFile.replace('_front.png', '') + '_id_card.png';
            a.click();
            window.URL.revokeObjectURL(url);
            showToast('Downloaded!', 'success');
        })
        .catch(() => showToast('Download failed', 'error'));
}

// ========== DOWNLOAD ==========
function loadFileList() {
    fetch(API_BASE_URL + '/get-generated')
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById('file-list');
            const count = document.getElementById('dl-count');
            count.textContent = `${data.files.length} cards`;

            list.innerHTML = '';
            data.files.forEach(file => {
                const item = document.createElement('div');
                item.className = 'file-item';
                item.innerHTML = `
                    <span class="file-item-name">
                        <i class="fas fa-image"></i>
                        ${file}
                    </span>
                    <a class="btn btn-outline" href="${API_BASE_URL}/download/${file}">
                        <i class="fas fa-download"></i>
                    </a>
                `;
                list.appendChild(item);
            });
        });
}

function downloadZip() {
    showLoading('Creating ZIP archive...');

    fetch(API_BASE_URL + '/download-zip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files: [] })
    })
        .then(res => {
            if (!res.ok) throw new Error('Download failed');
            return res.blob();
        })
        .then(blob => {
            hideLoading();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'id_cards.zip';
            a.click();
            window.URL.revokeObjectURL(url);
            showToast('ZIP downloaded successfully!', 'success');
        })
        .catch(err => {
            hideLoading();
            showToast('Download failed: ' + err.message, 'error');
        });
}

function clearOutput() {
    if (!confirm('Are you sure you want to clear all generated cards?')) return;

    fetch(API_BASE_URL + '/clear-output', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                generatedCards = [];
                document.getElementById('stat-generated').textContent = '0';
                document.getElementById('btn-download-all').disabled = true;
                showToast('All output cleared', 'info');
                loadPreview();
            }
        });
}

// ========== UTILITIES ==========
function showLoading(text) {
    document.getElementById('loading-text').textContent = text || 'Processing...';
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle'
    };

    toast.innerHTML = `<i class="fas ${icons[type] || icons.info}"></i> ${message}`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ========== IMAGE MODAL ==========
let currentModalFiles = { front: '', back: '' };

function openCardModal(id, frontFile, backFile) {
    const modal = document.getElementById('image-modal');
    document.getElementById('modal-title').textContent = id;
    document.getElementById('modal-front').src = API_BASE_URL + '/preview/' + frontFile;
    document.getElementById('modal-back').src = API_BASE_URL + '/preview/' + backFile;
    document.getElementById('modal-dl-front').href = API_BASE_URL + '/download/' + frontFile;
    document.getElementById('modal-dl-back').href = API_BASE_URL + '/download/' + backFile;
    currentModalFiles = { front: frontFile, back: backFile };
    modal.style.display = 'flex';
}

function closeModal(event) {
    if (event.target === event.currentTarget) {
        document.getElementById('image-modal').style.display = 'none';
    }
}

function downloadBothCards() {
    if (!currentModalFiles.front || !currentModalFiles.back) return;

    fetch(API_BASE_URL + '/download-combined', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ front: currentModalFiles.front, back: currentModalFiles.back })
    })
        .then(res => res.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = currentModalFiles.front.replace('_front.png', '') + '_id_card.png';
            a.click();
            window.URL.revokeObjectURL(url);
            showToast('Downloaded!', 'success');
        })
        .catch(() => showToast('Download failed', 'error'));
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.getElementById('image-modal').style.display = 'none';
    }
});

// ========== ADD SINGLE EMPLOYEE ==========
let singleCardFiles = { front: '', back: '' };

function loadEmployee() {
    const empId = document.getElementById('add-empid').value.trim();
    if (!empId) {
        showToast('Enter an Employee ID first', 'error');
        return;
    }

    fetch(`${API_BASE_URL}/api/employee/${empId}`)
        .then(res => {
            if (!res.ok) throw new Error('Not found');
            return res.json();
        })
        .then(emp => {
            if (emp.error) {
                showToast(emp.error, 'error');
                return;
            }
            document.getElementById('add-name').value = emp.name || '';
            document.getElementById('add-designation').value = emp.designation || '';
            document.getElementById('add-department').value = emp.department || '';
            document.getElementById('add-valid').value = emp.valid_till || 'Dec 2027';
            document.getElementById('add-mobile').value = emp.mobile || '';
            document.getElementById('add-email').value = emp.email || '';
            document.getElementById('add-company').value = emp.company || 'Acme Corp International';
            document.getElementById('add-website').value = emp.website || 'www.acmecorp.com';
            document.getElementById('add-address').value = emp.address || '';

            // Set blood group dropdown
            const bloodSel = document.getElementById('add-blood');
            const bg = emp.blood_group || 'O +ve';
            for (let opt of bloodSel.options) {
                if (opt.value === bg) { bloodSel.value = bg; break; }
            }

            // Load existing card preview if available
            const empIdSafe = empId.replace(/ /g, '_');
            const frontFile = empIdSafe + '_front.png';
            const backFile = empIdSafe + '_back.png';
            singleCardFiles = { front: frontFile, back: backFile };

            const preview = document.getElementById('single-card-preview');
            preview.innerHTML = `
                <img src="${API_BASE_URL}/preview/${frontFile}?t=${Date.now()}" alt="Front" onerror="this.style.display='none'">
                <img src="${API_BASE_URL}/preview/${backFile}?t=${Date.now()}" alt="Back" onerror="this.style.display='none'">
            `;
            const actions = document.getElementById('single-card-actions');
            actions.style.display = 'flex';
            document.getElementById('single-dl-front').href = '/download/' + frontFile;
            document.getElementById('single-dl-back').href = '/download/' + backFile;

            showToast(`Loaded: ${emp.name}`, 'success');
        })
        .catch(() => showToast('Employee not found in database', 'error'));
}

function clearAddForm() {
    document.getElementById('add-name').value = '';
    document.getElementById('add-empid').value = '';
    document.getElementById('add-designation').value = '';
    document.getElementById('add-department').value = '';
    document.getElementById('add-valid').value = 'Dec 2027';
    document.getElementById('add-blood').value = 'O +ve';
    document.getElementById('add-mobile').value = '';
    document.getElementById('add-email').value = '';
    document.getElementById('add-company').value = 'Acme Corp International';
    document.getElementById('add-website').value = 'www.acmecorp.com';
    document.getElementById('add-address').value = '';

    // Reset photo
    document.getElementById('add-photo-preview').style.display = 'none';
    document.getElementById('add-photo-preview').src = '';
    document.getElementById('add-photo-placeholder').style.display = 'flex';
    document.getElementById('add-photo-input').value = '';

    // Reset preview
    document.getElementById('single-card-preview').innerHTML = `
        <div class="empty-preview">
            <i class="fas fa-id-card"></i>
            <p>Fill the form and click<br>"Generate ID Card" to preview</p>
        </div>
    `;
    document.getElementById('single-card-actions').style.display = 'none';
    singleCardFiles = { front: '', back: '' };
}

function previewAddPhoto(input) {
    const file = input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function (e) {
        const img = document.getElementById('add-photo-preview');
        img.src = e.target.result;
        img.style.display = 'block';
        document.getElementById('add-photo-placeholder').style.display = 'none';
    };
    reader.readAsDataURL(file);
}

function generateSingleCard() {
    const name = document.getElementById('add-name').value.trim();
    const empId = document.getElementById('add-empid').value.trim();
    const designation = document.getElementById('add-designation').value.trim();

    if (!name || !empId || !designation) {
        showToast('Please fill Name, Employee ID, and Designation', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('employee_id', empId);
    formData.append('designation', designation);
    formData.append('department', document.getElementById('add-department').value.trim());
    formData.append('valid_till', document.getElementById('add-valid').value.trim());
    formData.append('blood_group', document.getElementById('add-blood').value);
    formData.append('mobile', document.getElementById('add-mobile').value.trim());
    formData.append('email', document.getElementById('add-email').value.trim());
    formData.append('company', document.getElementById('add-company').value.trim());
    formData.append('website', document.getElementById('add-website').value.trim());
    formData.append('address', document.getElementById('add-address').value.trim());

    const photoInput = document.getElementById('add-photo-input');
    if (photoInput.files[0]) {
        formData.append('photo', photoInput.files[0]);
    }

    showLoading('Generating ID Card...');

    fetch(API_BASE_URL + '/generate-single', {
        method: 'POST',
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            hideLoading();
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }
            showToast('ID Card generated!', 'success');

            singleCardFiles = { front: data.front, back: data.back };

            // Show preview
            const preview = document.getElementById('single-card-preview');
            preview.innerHTML = `
                <img src="${API_BASE_URL}/preview/${data.front}?t=${Date.now()}" alt="Front">
                <img src="${API_BASE_URL}/preview/${data.back}?t=${Date.now()}" alt="Back">
            `;

            // Show actions
            const actions = document.getElementById('single-card-actions');
            actions.style.display = 'flex';
            document.getElementById('single-dl-front').href = '/download/' + data.front;
            document.getElementById('single-dl-back').href = '/download/' + data.back;
        })
        .catch(err => {
            hideLoading();
            showToast('Generation failed: ' + err.message, 'error');
        });
}

function downloadSingleBoth() {
    if (!singleCardFiles.front) return;
    fetch(API_BASE_URL + '/download-combined', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ front: singleCardFiles.front, back: singleCardFiles.back })
    })
        .then(res => res.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = singleCardFiles.front.replace('_front.png', '') + '_id_card.png';
            a.click();
            window.URL.revokeObjectURL(url);
            showToast('Downloaded!', 'success');
        })
        .catch(() => showToast('Download failed', 'error'));
}

// ========== MONGODB ==========
function checkDBStatus() {
    fetch(API_BASE_URL + '/db-status')
        .then(res => res.json())
        .then(data => {
            const indicator = document.getElementById('db-indicator');
            const statusText = document.getElementById('db-status-text');
            const loadBtn = document.getElementById('btn-load-db');

            if (data.connected) {
                indicator.classList.add('connected');
                indicator.classList.remove('disconnected');
                statusText.textContent = `MongoDB Connected • ${data.employees} employees • ${data.generated_cards} cards`;
                loadBtn.style.display = 'inline-flex';
            } else {
                indicator.classList.add('disconnected');
                indicator.classList.remove('connected');
                statusText.textContent = `MongoDB: ${data.message || 'Not connected'}`;
                loadBtn.style.display = 'none';
            }
        })
        .catch(() => {
            const indicator = document.getElementById('db-indicator');
            const statusText = document.getElementById('db-status-text');
            indicator.classList.add('disconnected');
            statusText.textContent = 'MongoDB: Connection check failed';
        });
}

function loadFromDB() {
    showLoading('Loading employees from MongoDB...');

    fetch(API_BASE_URL + '/api/load-from-db')
        .then(res => res.json())
        .then(data => {
            hideLoading();
            if (data.error) {
                showToast(data.error, 'error');
                return;
            }

            employeeData = data.employees;
            document.getElementById('stat-employees').textContent = data.count;

            document.getElementById('excel-status').style.display = 'flex';
            document.getElementById('excel-filename').textContent = 'Loaded from MongoDB';
            document.getElementById('excel-count').textContent = `${data.count} employees loaded from database`;

            renderEmployeeTable();
            showToast(`${data.count} employees loaded from MongoDB!`, 'success');
        })
        .catch(err => {
            hideLoading();
            showToast('Failed to load from database', 'error');
        });
}

// Check DB status on page load
checkDBStatus();
