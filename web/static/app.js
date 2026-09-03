document.addEventListener('DOMContentLoaded', () => {
    const patchForm = document.getElementById('patchForm');
    const apkUrlInput = document.getElementById('apkUrl');
    const btnSample = document.getElementById('btnSample');
    const btnStart = document.getElementById('btnStart');

    const progressSection = document.getElementById('progressSection');
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const statusText = document.getElementById('statusText');
    const terminalLogs = document.getElementById('terminalLogs');

    const resultSection = document.getElementById('resultSection');
    const patchesList = document.getElementById('patchesList');
    const summaryText = document.getElementById('summaryText');
    const btnDownloadApk = document.getElementById('btnDownloadApk');
    const btnDownloadMagisk = document.getElementById('btnDownloadMagisk');
    const btnDownloadReport = document.getElementById('btnDownloadReport');

    let pollInterval = null;
    let lastLogCount = 0;

    // Quick test URL button
    btnSample.addEventListener('click', () => {
        apkUrlInput.value = 'https://raw.githubusercontent.com/mertcqnkld/HyperOS-GlobalConvert/main/PowerKeeper.apk';
    });

    // Form submission
    patchForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const url = apkUrlInput.value.trim();
        if (!url) {
            alert('Lütfen geçerli bir APK URL\'si veya dosya yolu girin.');
            return;
        }

        // Reset UI
        btnStart.disabled = true;
        progressSection.classList.remove('hidden');
        resultSection.classList.add('hidden');
        terminalLogs.textContent = '';
        progressBar.style.width = '0%';
        progressBar.style.background = 'linear-gradient(90deg, var(--primary), var(--accent))';
        progressPercent.textContent = '0%';
        statusText.textContent = 'İşlem sıraya alınıyor...';
        lastLogCount = 0;

        try {
            const response = await fetch('/api/patch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });

            const data = await response.json();
            if (data.error) {
                alert('Hata: ' + data.error);
                btnStart.disabled = false;
                return;
            }

            const jobId = data.job_id;
            startPolling(jobId);

        } catch (err) {
            alert('Sunucu bağlantı hatası: ' + err.message);
            btnStart.disabled = false;
        }
    });

    function startPolling(jobId) {
        if (pollInterval) clearInterval(pollInterval);

        pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/status?job_id=${jobId}`);
                if (!res.ok) return;
                const job = await res.json();

                // Update progress
                const progress = job.progress || 0;
                progressBar.style.width = `${progress}%`;
                progressPercent.textContent = `${progress}%`;
                statusText.textContent = job.message || 'İşleniyor...';

                // Update logs
                if (job.logs && job.logs.length > lastLogCount) {
                    const newLogs = job.logs.slice(lastLogCount);
                    terminalLogs.textContent += newLogs.join('\n') + '\n';
                    terminalLogs.scrollTop = terminalLogs.scrollHeight;
                    lastLogCount = job.logs.length;
                }

                // Check completion
                if (job.status === 'completed') {
                    clearInterval(pollInterval);
                    btnStart.disabled = false;
                    showResults(job);
                } else if (job.status === 'failed') {
                    clearInterval(pollInterval);
                    btnStart.disabled = false;
                    statusText.textContent = 'Hata: ' + job.message;
                    progressBar.style.background = '#ef4444';
                    terminalLogs.textContent += `\n[ERROR] ${job.message}\n`;
                    terminalLogs.scrollTop = terminalLogs.scrollHeight;
                }

            } catch (e) {
                console.error('Polling error:', e);
            }
        }, 800);
    }

    function showResults(job) {
        resultSection.classList.remove('hidden');

        // Populate patches list
        patchesList.innerHTML = '';
        if (job.patches && job.patches.length > 0) {
            job.patches.forEach((p, idx) => {
                const item = document.createElement('div');
                item.className = 'patch-item';
                item.innerHTML = `
                    <div class="patch-item-title">
                        <span>#${idx + 1} ${escapeHtml(p.class_name)} &bull; ${escapeHtml(p.method_name)}</span>
                        <span style="font-family:'JetBrains Mono';font-size:0.75rem;color:#f59e0b;">Satır ${p.line_number}</span>
                    </div>
                    <div class="patch-item-desc">
                        <span style="color:#f87171;">- ${escapeHtml(p.original_line.trim())}</span><br>
                        <span style="color:#34d399;">+ const/4 ${escapeHtml(p.register)}, 0x1</span>
                    </div>
                `;
                patchesList.appendChild(item);
            });
            summaryText.textContent = `${job.output_filename} (${(job.file_size_bytes / (1024 * 1024)).toFixed(2)} MB) &bull; Toplam ${job.patches.length} cerrahi yama uygulandı ve doğrulandı.`;
        } else {
            patchesList.innerHTML = '<div style="padding:0.75rem;color:#9ca3af;font-size:0.85rem;">Method gövdesinde çalıştırılabilir IS_INTERNATIONAL_BUILD okuması bulunamadı.</div>';
        }

        // Setup download URLs
        btnDownloadApk.href = `/api/download/apk?job_id=${job.id}`;
        if (job.magisk_zip_path) {
            btnDownloadMagisk.href = `/api/download/magisk?job_id=${job.id}`;
            btnDownloadMagisk.parentElement.parentElement.style.display = 'flex';
        } else {
            btnDownloadMagisk.parentElement.parentElement.style.display = 'none';
        }
        btnDownloadReport.href = `/api/download/report?job_id=${job.id}`;

        // Scroll smoothly to results
        resultSection.scrollIntoView({ behavior: 'smooth' });
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/[&<>'"]/g,
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag)
        );
    }
});
