/**
 * app.js — Prompt Injection Guardrail Web Chat Logic
 * 
 * ATURAN KEAMANAN UTAMA (CLAUDE.md §3.3):
 * - Anti-XSS: Seluruh teks dinamis (input pengguna, respons bot, alasan blokir)
 *   WAJIB dirender menggunakan `element.textContent`.
 * - DILARANG menggunakan `innerHTML` untuk string dinamis dari user/backend.
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- Elemen DOM ---
    const chatForm = document.getElementById('chat-form');
    const promptInput = document.getElementById('prompt-input');
    const sendBtn = document.getElementById('send-btn');
    const chatMessages = document.getElementById('chat-messages');
    const thresholdSlider = document.getElementById('threshold-slider');
    const thresholdDisplay = document.getElementById('threshold-val-display');

    // Health pill
    const healthBadge = document.getElementById('health-badge');
    const healthStatusText = document.getElementById('health-status-text');

    // Stats counter
    const statTotalEl = document.getElementById('stat-total');
    const statAllowedEl = document.getElementById('stat-allowed');
    const statBlockedEl = document.getElementById('stat-blocked');

    // Sidebar presets & controls
    const presetButtons = document.querySelectorAll('.preset-btn');
    const clearChatBtn = document.getElementById('clear-chat-btn');

    // --- State Lokal ---
    const state = {
        totalRequests: 0,
        allowedCount: 0,
        blockedCount: 0,
        currentThreshold: parseFloat(thresholdSlider.value) || 0.65,
        isProcessing: false,
    };

    // ============================================================
    // 1. Inisialisasi & Health Check
    // ============================================================

    async function checkHealth() {
        try {
            const res = await fetch('/api/health');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            healthBadge.className = 'health-badge';
            if (data.status === 'healthy') {
                healthBadge.classList.add('healthy');
                healthStatusText.textContent = `Sistem Aktif • ${data.model_mode.toUpperCase()} + Ollama`;
            } else {
                healthBadge.classList.add('degraded');
                healthStatusText.textContent = `Degraded • Ollama: ${data.ollama_connected ? 'OK' : 'Offline'}`;
            }
        } catch (err) {
            healthBadge.className = 'health-badge offline';
            healthStatusText.textContent = 'Backend Offline';
        }
    }

    // Cek status saat load & ulangi tiap 30 detik
    checkHealth();
    setInterval(checkHealth, 30000);

    // ============================================================
    // 2. Threshold Slider Event
    // ============================================================

    thresholdSlider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        state.currentThreshold = val;
        thresholdDisplay.textContent = val.toFixed(2);
    });

    // ============================================================
    // 3. Preset Buttons Click Handler
    // ============================================================

    presetButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            const presetPrompt = btn.getAttribute('data-preset');
            if (presetPrompt) {
                promptInput.value = presetPrompt;
                promptInput.focus();
                // Auto scroll textarea ke posisi akhir
                promptInput.scrollTop = promptInput.scrollHeight;
            }
        });
    });

    // Clear Chat
    clearChatBtn.addEventListener('click', () => {
        chatMessages.innerHTML = '';
        appendWelcomeBanner();
    });

    function appendWelcomeBanner() {
        const banner = document.createElement('div');
        banner.className = 'welcome-banner';

        const icon = document.createElement('div');
        icon.className = 'welcome-icon';
        icon.textContent = '🛡️';

        const title = document.createElement('h3');
        title.textContent = 'Sistem Pertahanan AI Aktif';

        const desc = document.createElement('p');
        desc.textContent = 'Setiap prompt diinspeksi oleh middleware Guardrail secara real-time sebelum diteruskan ke mesin LLM lokal (Ollama Qwen 2.5). Ujilah skenario di sebelah kiri atau ketik prompt Anda sendiri.';

        const specs = document.createElement('div');
        specs.className = 'banner-specs';
        specs.innerHTML = '<span>Target LLM: <code>qwen2.5:1.5b</code></span> <span>Host Limit: <code>RAM 16 GB</code></span> <span>Network: <code>guardrail_net</code></span>';

        banner.appendChild(icon);
        banner.appendChild(title);
        banner.appendChild(desc);
        banner.appendChild(specs);
        chatMessages.appendChild(banner);
    }

    // ============================================================
    // 4. Form Submit & API Call
    // ============================================================

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const prompt = promptInput.value.trim();
        if (!prompt || state.isProcessing) return;

        // Bersihkan input & set state processing
        promptInput.value = '';
        state.isProcessing = true;
        setFormLoading(true);

        // Render gelembung pengguna
        renderUserMessage(prompt);

        // Render indikator loading
        const loadingIndicator = renderLoadingIndicator();

        try {
            const startTime = performance.now();
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt: prompt,
                    threshold: state.currentThreshold,
                }),
            });

            const data = await response.json();
            const clientTotalMs = Math.round(performance.now() - startTime);

            // Hapus loading
            if (loadingIndicator && loadingIndicator.parentNode) {
                loadingIndicator.parentNode.removeChild(loadingIndicator);
            }

            // Perbarui statistik sesi
            state.totalRequests += 1;
            statTotalEl.textContent = state.totalRequests;

            if (response.status === 403 || data.status === 'blocked') {
                // === STATUS DIBLOKIR (INJECTION TERDETEKSI) ===
                state.blockedCount += 1;
                statBlockedEl.textContent = state.blockedCount;

                renderInspectionCard(data, 'blocked');
            } else if (response.status === 200 || data.status === 'allowed') {
                // === STATUS AMAN (LOLOS KE OLLAMA) ===
                state.allowedCount += 1;
                statAllowedEl.textContent = state.allowedCount;

                renderInspectionCard(data, 'allowed');

                if (data.bot_reply) {
                    renderBotMessage(data.bot_reply);
                }
            } else {
                renderSystemError(`Error server (${response.status}): ${data.detail || 'Terjadi kesalahan'}`);
            }

        } catch (err) {
            if (loadingIndicator && loadingIndicator.parentNode) {
                loadingIndicator.parentNode.removeChild(loadingIndicator);
            }
            renderSystemError(`Gagal menghubungi server: ${err.message}`);
        } finally {
            state.isProcessing = false;
            setFormLoading(false);
            scrollToBottom();
            promptInput.focus();
        }
    });

    // Enter untuk kirim, Shift+Enter untuk baris baru
    promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // ============================================================
    // 5. Render Functions (STRICT ANTI-XSS: textContent)
    // ============================================================

    function renderUserMessage(text) {
        const entry = document.createElement('div');
        entry.className = 'message-entry user-row';

        const bubble = document.createElement('div');
        bubble.className = 'user-bubble';
        bubble.textContent = text; // ANTI-XSS

        const meta = document.createElement('div');
        meta.className = 'user-meta mono';
        const now = new Date();
        meta.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;

        entry.appendChild(bubble);
        entry.appendChild(meta);
        chatMessages.appendChild(entry);
        scrollToBottom();
    }

    function renderInspectionCard(data, verdict) {
        const isBlocked = verdict === 'blocked';
        const scorePercent = (data.confidence_score * 100).toFixed(1);
        const thresholdPercent = (data.threshold_used * 100).toFixed(0);

        const card = document.createElement('div');
        card.className = `inspection-card ${verdict}`;

        // Header: Verdict + Metrics
        const header = document.createElement('div');
        header.className = 'inspection-header';

        const verdictEl = document.createElement('div');
        verdictEl.className = 'inspection-verdict';
        verdictEl.textContent = isBlocked
            ? '🚫 DIBLOKIR — Terdeteksi Prompt Injection'
            : '✅ AMAN — Lolos Verifikasi Guardrail';

        const metricsEl = document.createElement('div');
        metricsEl.className = 'inspection-metrics';

        const scorePill = document.createElement('span');
        scorePill.className = 'metric-pill';
        scorePill.innerHTML = `Skor Injeksi: <span class="score-highlight">${scorePercent}%</span>`;

        const thresholdPill = document.createElement('span');
        thresholdPill.className = 'metric-pill';
        thresholdPill.textContent = `&tau; = ${data.threshold_used}`;

        const latencyPill = document.createElement('span');
        latencyPill.className = 'metric-pill';
        latencyPill.textContent = `Guardrail: ${data.guardrail_latency_ms} ms`;

        metricsEl.appendChild(scorePill);
        metricsEl.appendChild(thresholdPill);
        metricsEl.appendChild(latencyPill);

        header.appendChild(verdictEl);
        header.appendChild(metricsEl);
        card.appendChild(header);

        // Confidence Gauge Bar
        const gauge = document.createElement('div');
        gauge.className = 'confidence-gauge';

        const gaugeLabel = document.createElement('span');
        gaugeLabel.className = 'mono';
        gaugeLabel.textContent = `0%`;

        const track = document.createElement('div');
        track.className = 'gauge-track';

        const fill = document.createElement('div');
        fill.className = 'gauge-fill';
        fill.style.width = `${Math.min(data.confidence_score * 100, 100)}%`;

        const marker = document.createElement('div');
        marker.className = 'gauge-threshold-marker';
        marker.style.left = `${Math.min(data.threshold_used * 100, 100)}%`;
        marker.title = `Ambang Batas (${thresholdPercent}%)`;

        track.appendChild(fill);
        track.appendChild(marker);

        const gaugeMax = document.createElement('span');
        gaugeMax.className = 'mono';
        gaugeMax.textContent = `100%`;

        gauge.appendChild(gaugeLabel);
        gauge.appendChild(track);
        gauge.appendChild(gaugeMax);
        card.appendChild(gauge);

        // Explanation Reason
        const reason = document.createElement('div');
        reason.className = 'inspection-reason';
        reason.textContent = isBlocked
            ? `Pencegahan aktif: Permintaan tidak diteruskan ke model Ollama demi keamanan sistem. Nilai skor (${scorePercent}%) melampaui ambang batas ${thresholdPercent}%.`
            : `Prompt telah lolos inspeksi keamanan (skor ${scorePercent}% < ${thresholdPercent}%) dan telah dijawab oleh Ollama Qwen 2.5 (Total latensi: ${data.total_latency_ms} ms).`;

        card.appendChild(reason);

        chatMessages.appendChild(card);
        scrollToBottom();
    }

    function renderBotMessage(replyText) {
        const entry = document.createElement('div');
        entry.className = 'message-entry bot-row';

        const bubble = document.createElement('div');
        bubble.className = 'bot-bubble';

        const header = document.createElement('div');
        header.className = 'bot-header';
        header.textContent = '🤖 Chatbot Akademik UNSIL (Qwen 2.5 1.5B)';

        const content = document.createElement('div');
        content.className = 'bot-text';
        content.textContent = replyText; // STRICT ANTI-XSS

        bubble.appendChild(header);
        bubble.appendChild(content);
        entry.appendChild(bubble);
        chatMessages.appendChild(entry);
        scrollToBottom();
    }

    function renderLoadingIndicator() {
        const pill = document.createElement('div');
        pill.className = 'loading-pill';

        const spinner = document.createElement('div');
        spinner.className = 'spinner';

        const text = document.createElement('span');
        text.textContent = 'Inspeksi guardrail & memproses respons LLM...';

        pill.appendChild(spinner);
        pill.appendChild(text);
        chatMessages.appendChild(pill);
        scrollToBottom();
        return pill;
    }

    function renderSystemError(errorMessage) {
        const card = document.createElement('div');
        card.className = 'inspection-card blocked';
        card.style.borderLeftColor = '#F59E0B';

        const title = document.createElement('strong');
        title.textContent = '⚠️ Pemberitahuan Sistem:';

        const desc = document.createElement('p');
        desc.textContent = errorMessage; // STRICT ANTI-XSS

        card.appendChild(title);
        card.appendChild(desc);
        chatMessages.appendChild(card);
        scrollToBottom();
    }

    function setFormLoading(isLoading) {
        sendBtn.disabled = isLoading;
        const iconSpan = document.getElementById('send-icon');
        if (isLoading) {
            iconSpan.textContent = 'Memeriksa...';
        } else {
            iconSpan.textContent = 'Kirim';
        }
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
