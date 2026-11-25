# CLAUDE.md — Context & Rules for AI Coding Assistants

Dokumen ini adalah sumber kebenaran utama (*single source of truth*) bagi asisten AI (*Claude Code, Antigravity, Cursor, GitHub Copilot*) saat membantu mengembangkan proyek **Prompt Injection Guardrail (Defensive AI)**. Selalu baca dan patuhi seluruh aturan arsitektur, kontrak API, serta batasan teknis di bawah ini sebelum menulis atau memodifikasi kode.

---

## 1. Ringkasan Proyek & Target Utama

* **Nama Sistem:** *Middleware* Deteksi Serangan *Prompt Injection* untuk Perlindungan Aplikasi *Chatbot*
* **Konteks Akademik:** Final Project Keamanan Informasi (Topik 1: *Defensive AI*) — Universitas Siliwangi.
* **Tenggat Rilis:** 29 November 2026.
* **Kriteria Kelulusan Teknis (Wajib):**
  1. Aplikasi *end-to-end* dapat dijalankan penuh menggunakan `docker compose up --build`.
  2. Model klasifikasi mendukung dwibahasa (**Inggris & Indonesia**) dengan **Accuracy $> 85\%$**.
  3. Tersedia skrip evaluasi lengkap yang menghasilkan *Accuracy, Precision, Recall, F1-Score, Confusion Matrix*, serta analisis kasus *False Positive* ($FP$) dan *False Negative* ($FN$).

---

## 2. Peta Direktori Proyek (Jangan Mengubah Struktur Tanpa Izin)

```text
prompt-injection-guardrail/
├── CLAUDE.md                          # File aturan & konteks vibecoding ini
├── PRD_Prompt_Injection_Guardrail.md  # Spesifikasi kebutuhan perangkat lunak
├── planai.md                          # Rencana dataset & preprocessing
├── planmodel.md                       # Rencana training mDeBERTa, ONNX & evaluasi
├── planbe.md                          # Rencana Docker Compose, FastAPI & Ollama
├── planfe.md                          # Rencana Vanilla Web Chat UI
├── planuiux.md                        # Panduan visual SOC Dark Theme & skenario demo
├── todolist.md                        # Daftar tugas & jadwal sprint
├── docker-compose.yml                 # Orkestrasi guardrail-app & ollama-service
├── .env.example                       # Template environment variables
├── notebooks/                         # Dikerjakan di Google Colab (GPU T4)
│   ├── 01_dataset_preparation.ipynb
│   ├── 02_model_training_onnx.ipynb
│   └── 03_model_evaluation.ipynb
├── backend/                           # Dikerjakan di VS Code / Antigravity
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                    # FastAPI routes & StaticFiles mount
│   │   ├── config.py                  # Pydantic Settings / env loader
│   │   ├── detector.py                # Singleton ONNX Runtime classifier
│   │   ├── ollama_client.py           # Async HTTPX client ke Ollama
│   │   └── logger.py                  # Append-only JSONL security logger
│   └── static/                        # Vanilla HTML/CSS/JS (tanpa bundler)
│       ├── index.html
│       ├── style.css
│       └── app.js
├── model_artifacts/
│   └── onnx_guardrail/                # Output ekspor ONNX (model.onnx + tokenizer)
├── evaluation/                        # Output metrik & error analysis untuk laporan
└── logs/                              # Output runtime security_events.jsonl
```

---

## 3. Aturan Ketat Pengembangan (*Coding Guardrails*)

### 3.1 Aturan AI & Dataset (`notebooks/`)
* **JANGAN Hapus Stopwords / Stemming:** Kata seperti *"ignore"*, *"forget"*, *"abaikan"*, *"lupakan"*, *"system"*, dan tanda baca khusus (`###`, `<system>`, `[]`) adalah fitur kunci pendeteksi injeksi. Jangan pernah menghapusnya saat *preprocessing*.
* **Cegah *Data Leakage*:** Pemisahan *train-test split* ($80:20$, *stratified*) **WAJIB** dilakukan sebelum menerjemahkan sampel ke Bahasa Indonesia.
* **Konfigurasi Model:** Gunakan `microsoft/mdeberta-v3-base` (cadangan: `xlm-roberta-base`) dengan `max_length` minimal `384` atau `512` agar injeksi di akhir paragraf panjang tidak terpotong.
* **Ekspor ONNX:** Model akhir wajib diekspor menggunakan `optimum` ke `./onnx_guardrail/` agar berjalan ringan di CPU tanpa PyTorch GPU di dalam *container*.

### 3.2 Aturan Backend & Docker (`backend/` & `docker-compose.yml`)
* **Batas Memori Host (16 GB RAM):** Selalu terapkan batas memori di `docker-compose.yml` (`guardrail-app`: maks `2G`, `ollama-service`: maks `6G`).
* **Isolasi Jaringan:** Jaringan internal `guardrail_net` menghubungkan kedua kontainer. **JANGAN** mengekspos port Ollama (`11434`) ke host publik; hanya port `8000` milik `guardrail-app` yang dibuka.
* **Model Ollama:** Gunakan model ringan `qwen2.5:1.5b` (atau `llama3.2:3b`).
* **Singleton Model Loading:** Muat `onnxruntime.InferenceSession` dan `AutoTokenizer` **satu kali** menggunakan FastAPI `lifespan` context manager. Dilarang memuat ulang model di dalam fungsi *endpoint*.
* **Fail-Closed Security:** Jika `confidence_score >= threshold` (default `0.65`), langsung kembalikan `HTTP 403 Forbidden` dan **JANGAN PERNAH** meneruskan permintaan ke Ollama.

### 3.3 Aturan Frontend & Keamanan UI (`backend/static/`)
* **Tanpa Build Step:** Gunakan murni **HTML5, CSS3, dan Vanilla JavaScript (ES6+)**. Jangan menambahkan React, Vue, Vite, atau `node_modules`.
* **Anti-XSS (Wajib):** Karena aplikasi ini menerima input simulasi serangan dari pengguna, selalu gunakan `element.textContent` saat merender pesan pengguna maupun balasan bot. **DILARANG keras menggunakan `innerHTML`** untuk teks dinamis.
* **Tema Visual:** Gunakan palet *Dark Slate SOC* (`#0F172A` background, `#1E293B` surface, `#10B981` untuk status *Allowed*, dan `#EF4444` untuk status *Blocked*).

---

## 4. Kontrak API (*Single Source of Truth*)

### `POST /api/chat`
* **Request Body:**
  ```json
  {
    "prompt": "string (wajib, min 1 karakter)",
    "threshold": 0.65
  }
  ```
* **Response `200 OK` (Lolos / Aman):**
  ```json
  {
    "status": "allowed",
    "is_injection": false,
    "confidence_score": 0.0124,
    "threshold_used": 0.65,
    "guardrail_latency_ms": 38.5,
    "total_latency_ms": 1350.2,
    "message": "Prompt aman dan diteruskan ke asisten AI.",
    "bot_reply": "Jawaban dari model Ollama..."
  }
  ```
* **Response `403 Forbidden` (Terdeteksi Serangan):**
  ```json
  {
    "status": "blocked",
    "is_injection": true,
    "confidence_score": 0.9841,
    "threshold_used": 0.65,
    "guardrail_latency_ms": 41.2,
    "total_latency_ms": 41.8,
    "message": "Permintaan ditolak: Terdeteksi upaya Prompt Injection.",
    "bot_reply": null
  }
  ```

### `GET /api/health`
* Mengembalikan status kesiapan model ONNX (`model_loaded: true`) dan konektivitas kontainer Ollama (`ollama_connected: true`).

---

## 5. Perintah Operasional Penting

* **Menjalankan Seluruh Sistem:**
  ```bash
  docker compose up --build -d
  ```
* **Mengunduh Model LLM Target ke Kontainer Ollama (Jalankan Sekali):**
  ```bash
  docker exec -it ollama-service ollama pull qwen2.5:1.5b
  ```
* **Memantau Log Serangan Secara Real-Time:**
  ```bash
  tail -f logs/security_events.jsonl
  ```
* **Ekspor Model ke ONNX di Google Colab:**
  ```bash
  optimum-cli export onnx --model ./best_checkpoint --task text-classification ./onnx_guardrail/
  ```

---

## 6. Panduan *Vibecoding* untuk Tim

Saat meminta asisten AI menulis kode untuk setiap bagian, gunakan pola *prompt* bertahap berikut agar hasilnya presisi dan tidak merusak modul lain:
1. **Tahap Infra:** *"Baca `CLAUDE.md` dan `planbe.md`, lalu buatkan `docker-compose.yml`, `.env.example`, `backend/Dockerfile`, dan `backend/requirements.txt`."*
2. **Tahap Backend:** *"Baca `CLAUDE.md` dan `planbe.md`, lalu implementasikan modul `config.py`, `detector.py`, `ollama_client.py`, `logger.py`, dan `main.py` di dalam `backend/app/`."*
3. **Tahap Frontend:** *"Baca `CLAUDE.md`, `planfe.md`, dan `planuiux.md`, lalu buatkan `index.html`, `style.css`, dan `app.js` di `backend/static/` sesuai kontrak API."*