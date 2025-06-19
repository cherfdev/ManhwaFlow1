// web/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const convertCbzBtn = document.getElementById('convertCbzBtn');
    const combinePdfsBtn = document.getElementById('combinePdfsBtn');
    const suffixInput = document.getElementById('suffixInput');
    const qualitySelect = document.getElementById('qualitySelect');
    const deleteOriginalsCheckbox = document.getElementById('deleteOriginalsCheckbox');
    const globalProgress = document.getElementById('globalProgress');
    const globalProgressText = document.getElementById('globalProgressText');
    const globalProgressCount = document.getElementById('globalProgressCount');
    const globalProgressFill = document.getElementById('globalProgressFill');
    const activityLog = document.getElementById('activityLog');
    const logContent = document.getElementById('logContent');
    const clearLogBtn = document.getElementById('clearLogBtn');
    const logEntryTemplate = document.getElementById('log-entry-template');
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    const toastContainer = document.getElementById('toastContainer');

    let totalTasks = 0;
    let completedTasks = 0;

    const loadSettings = () => {
        const savedSuffix = localStorage.getItem('manhwaflow_suffix');
        if (savedSuffix === null) {
            suffixInput.value = '@KaydopKingmanhwa';
        } else {
            suffixInput.value = savedSuffix;
        }

        qualitySelect.value = localStorage.getItem('manhwaflow_quality') || '85';
        
        const deletePref = localStorage.getItem('manhwaflow_delete');
        deleteOriginalsCheckbox.checked = deletePref === null ? true : JSON.parse(deletePref);
    };

    const getSettings = () => {
        const settings = {
            suffix: suffixInput.value,
            quality: parseInt(qualitySelect.value, 10),
            deleteOriginals: deleteOriginalsCheckbox.checked
        };
        localStorage.setItem('manhwaflow_suffix', settings.suffix);
        localStorage.setItem('manhwaflow_quality', settings.quality);
        localStorage.setItem('manhwaflow_delete', settings.deleteOriginals);
        return settings;
    };

    const updateGlobalProgress = () => {
        completedTasks++;
        const percentage = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;
        globalProgressFill.style.width = `${percentage}%`;
        globalProgressCount.textContent = `${completedTasks}/${totalTasks}`;
        if (completedTasks >= totalTasks) {
            globalProgressText.textContent = "Opérations terminées !";
        }
    };

    const setAppStatus = (status, text) => {
        statusIndicator.className = 'status-indicator';
        statusText.textContent = text;
        const dot = statusIndicator.querySelector('.status-dot');
        let colorVar = status === 'processing' ? '--warning-color' : status === 'error' ? '--error-color' : '--success-color';
        dot.style.background = `var(${colorVar})`;
    };

    const setUiLock = (locked) => {
        convertCbzBtn.disabled = locked;
        combinePdfsBtn.disabled = locked;
        setAppStatus(locked ? 'processing' : 'success', locked ? 'Occupé...' : 'Prêt');
    };
    
    eel.expose(show_toast, 'show_toast');
    function show_toast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.5s ease forwards';
            setTimeout(() => toast.remove(), 500);
        }, 4000);
    };

    convertCbzBtn.addEventListener('click', () => {
        setUiLock(true);
        eel.start_cbz_conversion(getSettings())();
    });

    combinePdfsBtn.addEventListener('click', () => {
        setUiLock(true);
        eel.start_pdf_combination(getSettings())();
    });

    clearLogBtn.addEventListener('click', () => {
        logContent.innerHTML = '';
        activityLog.style.display = 'none';
        globalProgress.style.display = 'none';
    });

    eel.expose(prepare_ui_for_tasks, 'prepare_ui_for_tasks');
    function prepare_ui_for_tasks(tasks, taskNames = {}) {
        logContent.innerHTML = '';
        totalTasks = tasks.length;
        completedTasks = 0;
        tasks.forEach(task => {
            const entry = logEntryTemplate.content.cloneNode(true).firstElementChild;
            const filename = taskNames[task] || task.split(/[\\/]/).pop();
            entry.querySelector('.log-file-name').textContent = filename;
            entry.id = `log-${task.replace(/[^a-zA-Z0-9]/g, '-')}`;
            logContent.appendChild(entry);
        });
        globalProgress.style.display = 'block';
        activityLog.style.display = 'flex';
        globalProgressText.textContent = "Traitement en cours...";
        globalProgressCount.textContent = `0/${totalTasks}`;
        globalProgressFill.style.width = '0%';
    }

    eel.expose(update_ui, 'update_ui');
    function update_ui(taskId, data) {
        const entryId = `log-${taskId.replace(/[^a-zA-Z0-9]/g, '-')}`;
        const entry = document.getElementById(entryId);
        if (!entry) return;

        const statusBadge = entry.querySelector('.log-status');
        const detailsText = entry.querySelector('.log-details');
        const progressFill = entry.querySelector('.log-progress-fill');
        
        statusBadge.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
        statusBadge.className = `log-status ${data.status}`;
        detailsText.textContent = data.details;
        progressFill.style.width = `${data.progress}%`;
        
        if (data.status === 'success' && data.outputPath) {
            const logActions = entry.querySelector('.log-actions');
            logActions.innerHTML = ''; // Vider les actions précédentes
            
            const filePath = data.outputPath;
            const dirPath = filePath.substring(0, filePath.lastIndexOf('\\') + 1) || filePath.substring(0, filePath.lastIndexOf('/') + 1);

            const openFileBtn = document.createElement('button');
            openFileBtn.className = 'action-btn';
            openFileBtn.innerHTML = `<span class="icon">👁️</span> Ouvrir`;
            openFileBtn.onclick = () => eel.open_path(filePath)();
            
            const openDirBtn = document.createElement('button');
            openDirBtn.className = 'action-btn';
            openDirBtn.innerHTML = `<span class="icon">📁</span> Dossier`;
            openDirBtn.onclick = () => eel.open_path(dirPath)();
            
            logActions.appendChild(openFileBtn);
            logActions.appendChild(openDirBtn);
            logActions.style.display = 'flex';
        }

        if (data.progress === 100 && !entry.classList.contains('completed')) {
            entry.classList.add('completed');
            updateGlobalProgress();
        }
    }

    eel.expose(all_tasks_complete, 'all_tasks_complete');
    function all_tasks_complete() {
        setUiLock(false);
        if (totalTasks > 0) {
           show_toast('Toutes les tâches sont terminées !', 'success');
        }
        totalTasks = 0;
        completedTasks = 0;
    }
    
    loadSettings();
});