# Product Requirements Document (PRD)

## Sistem Middleware Deteksi Serangan *Prompt Injection* untuk Perlindungan Aplikasi *Chatbot*

| Atribut Dokumen | Keterangan |
| :--- | :--- |
| **Institusi** | Program Studi Informatika, Fakultas Teknik, Universitas Siliwangi |
| **Mata Kuliah** | Keamanan Informasi (`KP70065004`) — Semester Ganjil 2026/2027 |
| **Dosen Pengampu** | Muhammad Sidik Asyaky, S.T., M.T. |
| **Topik Proyek** | Topik 1: *Defensive AI* |
| **Versi Dokumen** | 1.1 (Lengkap) |
| **Target Rilis / UAS** | 29 November 2026 |
| **Tim Pengembang** | Kelompok 3 Orang (AI & Data Engineer, Backend & Infrastructure, QA & Document Control) |

---

## 1. Latar Belakang & Tujuan Proyek

### 1.1 Latar Belakang
Pemanfaatan *Large Language Model* (LLM) pada aplikasi *chatbot* membuka celah keamanan baru berupa serangan *Prompt Injection* dan *Jailbreak*. Melalui manipulasi instruksi teks (*adversarial prompts*), penyerang dapat memaksa *chatbot* mengabaikan aturan sistem (*system prompt*), membocorkan instruksi internal, maupun menghasilkan keluaran yang tidak semestinya.

### 1.2 Tujuan
Merancang dan membangun sistem pertahanan berlapis (*Defensive AI*) berupa *middleware guardrail* berbasis model klasifikasi *Multilingual Transformer*. Sistem ini bertugas menyaring setiap masukan (*prompt*) pengguna dalam Bahasa Inggris maupun Bahasa Indonesia secara *real-time* sebelum diteruskan ke layanan LLM lokal (**Ollama**).

---

## 2. Arsitektur Sistem & Lingkungan Pengujian

Untuk memenuhi ketentuan lingkungan pengujian yang terkendali tanpa membebani sistem operasi dengan virtualisasi penuh (VM), seluruh komponen aplikasi diorkestrasi menggunakan **Docker Compose** pada mesin host berkapasitas **RAM 16 GB**.

### 2.1 Diagram Alur Arsitektur

```text
+-------------------------------------------------------------------------+
|                        Host Machine (RAM 16 GB)                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                 Docker Network (guardrail_net)                    |  |
|  |                                                                   |  |
|  |  +-----------------------------+     +-------------------------+  |  |
|  |  | Container 1: Guardrail App  |     | Container 2: Target LLM |  |  |
|  |  | - Web Chat UI (HTML/JS)     |     | - Ollama Engine         |  |  |
|  |  | - FastAPI Gateway           |     | - Model: qwen2.5:1.5b   |  |  |
|  |  | - ONNX Classifier Model     |     |   atau llama3.2:3b      |  |  |
|  |  +--------------+--------------+     +------------+------------+  |  |
|  |                 |                                 ^               |  |
|  |                 | 1. Cek Input Pengguna           |               |  |
|  |                 +---> [Skor Injeksi >= Threshold] |               |  |
|  |                 |     --> Blokir (HTTP 403)       |               |  |
|  |                 |                                 |               |  |
|  |                 | 2. Input Aman (Lolos)           |               |  |
|  |                 +---------------------------------+               |  |
|  |                                                                   |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
```

### 2.2 Spesifikasi Layanan Kontainer
1. **Container 1 (`guardrail-service`):** Berbasis Python (FastAPI) yang menyajikan antarmuka **Web Chat** sekaligus menjalankan model klasifikasi *prompt injection* teroptimasi (format ONNX Runtime) di CPU.
2. **Container 2 (`ollama-service`):** Menjalankan mesin **Ollama** sebagai *chatbot* target dengan model ringan berukuran $\approx 1\text{--}2\text{ GB}$ (seperti `qwen2.5:1.5b` atau `llama3.2:3b`) sehingga sangat aman untuk alokasi RAM 16 GB dan mendukung interaksi dwibahasa (Inggris & Indonesia).

---

## 3. Kebutuhan Fungsional (*Functional Requirements*)

| ID | Fitur Utama | Deskripsi Kebutuhan |
| :--- | :--- | :--- |
| **FR-01** | **Deteksi Injeksi Dwibahasa** | Sistem mampu mengklasifikasikan masukan teks berbahasa Inggris dan Bahasa Indonesia ke dalam dua kelas: `0` (*Benign*/Aman) atau `1` (*Prompt Injection*/Berbahaya). |
| **FR-02** | **Mekanisme Pencegatan (*Blocking*)** | Jika probabilitas serangan melewati ambang batas (*threshold*, misalnya $\tau = 0.65$), sistem memblokir permintaan (`HTTP 403`) dan mengembalikan peringatan keamanan tanpa meneruskannya ke Ollama. |
| **FR-03** | **Penerusan ke *Chatbot* Target** | Jika masukan dinyatakan aman, *middleware* meneruskan *prompt* ke *container* Ollama beserta *system prompt* dasar dan mengembalikan jawaban *chatbot* ke pengguna. |
| **FR-04** | **Antarmuka Web Chat Interaktif** | Menyediakan tampilan web obrolan yang menampilkan riwayat pesan, indikator status keamanan setiap *prompt* (*Aman* / *Diblokir*), skor probabilitas deteksi, serta waktu inferensi. |
| **FR-05** | **Pencatatan Log Keamanan** | Menyimpan setiap transaksi uji ke dalam file log terstruktur (JSON/CSV) berisi *timestamp*, teks *prompt*, bahasa, probabilitas prediksi, dan status keputusan. |
| **FR-06** | **Skrip Evaluasi Kuantitatif** | Menyediakan modul pengujian otomatis terhadap data uji (*test set*) untuk menghasilkan laporan metrik performa dan *confusion matrix*. |

---

## 4. Kebutuhan Non-Fungsional (*Non-Functional Requirements*)

1. **Akurasi Model (`NFR-01`):** Model klasifikasi wajib mencapai tingkat akurasi keseluruhan $> 85\%$ pada data uji gabungan dwibahasa (target optimal $\ge 90\%$).
2. **Efisiensi Memori & Latensi (`NFR-02`):**
   * Total penggunaan RAM seluruh *container* Docker dibatasi maksimal $\le 10\text{ GB}$ agar berjalan stabil pada laptop host berkapasitas 16 GB.
   * Waktu inferensi klasifikasi *guardrail* di CPU ditargetkan $< 150\text{ ms}$ per permintaan.
3. **Isolasi Jaringan & Etika (`NFR-03`):**
   * *Port* internal Ollama (`11434`) tidak diekspos langsung ke jaringan publik host; akses hanya diizinkan melalui jaringan internal Docker (`guardrail_net`).
   * Seluruh *dataset* serangan dan *payload* pengujian hanya digunakan untuk keperluan evaluasi akademik dan tidak disebarluaskan.

---

## 5. Spesifikasi Dataset & Strategi Model AI

### 5.1 Komposisi Dataset (Pendekatan Opsi A — Dwibahasa)
* **Dataset Utama (Fondasi & Baseline):** `xTRam1/safe-guard-prompt-injection` ($\approx 10.200$ baris) dan `deepset/prompt-injections` ($\approx 662$ baris).
* **Dataset Penyerang (*Jailbreak* & *Real-world*):** `jackhhao/jailbreak-classification` ($\approx 650$ sampel serangan) dan `Lakera/gandalf_ignore_instructions` ($\approx 1.000$ sampel acak).
* **Dataset Penyeimbang & *Hard Negatives*:** `databricks/databricks-dolly-15k` ($\approx 1.650$ sampel normal) ditambah $\approx 200$ kalimat *hard negatives* kurasi manual (kalimat aman yang mengandung kata sensitif seperti *"abaikan"* atau *"injection"*).
* **Lokalisasi Bahasa Indonesia:** Translasi sebanyak $1.200$ sampel pada set latih dan $300$ sampel pada set uji setelah pemisahan *train-test split* ($80:20$) untuk mencegah *data leakage*.

### 5.2 Arsitektur Model
* **Base Model:** `microsoft/mdeberta-v3-base` atau `xlm-roberta-base`.
* **Lingkungan Pelatihan:** Google Colab (GPU T4) dengan `max_length = 256` atau `512`, `learning_rate = 2e-5`, dan `epochs = 3` hingga `4`.
* **Optimasi Deployment:** Ekspor model hasil *fine-tuning* ke format **ONNX** agar dapat dijalankan secara ringan dan cepat di dalam *container* Docker berbasis CPU.

---

## 6. Spesifikasi Luaran Proyek (Wajib & Khusus)

### 6.1 Luaran Umum
1. **Video Demonstrasi (YouTube):** Durasi $5\text{--}10$ menit yang menampilkan seluruh anggota kelompok (3 orang) menjelaskan bagian masing-masing serta mendemonstrasikan aplikasi Web Chat secara langsung (pengujian *prompt* normal vs. serangan *prompt injection* dalam Bahasa Inggris dan Indonesia).
2. **Laporan Akhir:** Dokumen tertulis dengan struktur Pendahuluan (latar belakang, rumusan masalah, tujuan), Metode, Pembahasan, dan Kesimpulan.

### 6.2 Luaran Khusus Topik 1 — *Defensive AI* (Wajib)
1. **Model atau Aplikasi yang Bisa Dijalankan:**
   * Aplikasi *end-to-end* yang dapat dijalankan dengan satu perintah `docker compose up --build`, mencakup layanan *Guardrail API*, antarmuka *Web Chat*, dan layanan *Chatbot Ollama*.
2. **Evaluasi Model & Analisis Kesalahan:**
   * Pengukuran metrik kuantitatif pada $20\%$ data uji (*test set*) berdasarkan komponen *True Positive* ($TP$), *True Negative* ($TN$), *False Positive* ($FP$), dan *False Negative* ($FN$):
     $$\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN} > 85\%$$
     $$\text{Precision} = \frac{TP}{TP + FP}$$
     $$\text{Recall} = \frac{TP}{TP + FN}$$
     $$\text{F1-Score} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$
   * **Analisis *False Positive* ($FP$):** Mengidentifikasi contoh pertanyaan pengguna yang sebenarnya aman namun keliru diblokir oleh sistem, menganalisis pemicu katanya, serta mendokumentasikan efek penyesuaian nilai *threshold* ($\tau$).
   * **Analisis *False Negative* ($FN$):** Mengidentifikasi contoh serangan *prompt injection* yang berhasil lolos dari penyaringan, menganalisis pola serangan yang belum terwakili di data latih, serta merumuskan rekomendasi perbaikannya.

---

## 7. Struktur Direktori Proyek

Berikut adalah rancangan struktur folder repositori yang memisahkan alur kerja pelatihan model di Google Colab dengan alur kerja *deployment* Docker di VS Code / Antigravity:

```text
prompt-injection-guardrail/
├── README.md                          # Panduan instalasi, cara menjalankan Docker, dan penggunaan API
├── docker-compose.yml                 # Orkestrasi container guardrail-app dan ollama-service
├── .env.example                       # Konfigurasi environment (threshold deteksi, URL Ollama, nama model)
│
├── notebooks/                         # Dikerjakan di Google Colab (AI & Data Engineer)
│   ├── 01_dataset_preparation.ipynb   # Unduh dataset Hugging Face, penggabungan, split 80:20, & translasi ID
│   ├── 02_model_training_onnx.ipynb   # Fine-tuning mDeBERTa/XLM-RoBERTa & ekspor model ke format ONNX
│   └── 03_model_evaluation.ipynb      # Pengujian test set: Precision, Recall, F1, Confusion Matrix, & analisis FP/FN
│
├── backend/                           # Dikerjakan di VS Code / Antigravity (Backend & Infrastructure)
│   ├── Dockerfile                     # Image build untuk layanan FastAPI + ONNX Runtime
│   ├── requirements.txt               # Dependensi Python (fastapi, uvicorn, onnxruntime, transformers, httpx)
│   ├── app/
│   │   ├── main.py                    # Entry point FastAPI, routing endpoint /api/chat & penyaji Web UI
│   │   ├── config.py                  # Pembacaan variabel lingkungan (.env) dan parameter threshold
│   │   ├── detector.py                # Modul pemuat model ONNX & logika klasifikasi prompt injection
│   │   ├── ollama_client.py           # Klien HTTP asinkron untuk komunikasi ke container Ollama
│   │   └── logger.py                  # Pencatatan log kejadian keamanan ke folder logs/
│   └── static/                        # Antarmuka Web Chat Demo
│       ├── index.html                 # Halaman utama antarmuka obrolan chatbot
│       ├── style.css                  # Styling tampilan chat & indikator status keamanan (Aman/Diblokir)
│       └── app.js                     # Logika pengiriman prompt, penampilan skor probabilitas, & respons chat
│
├── model_artifacts/                   # Folder penyimpanan aset model hasil training dari Google Drive
│   └── onnx_guardrail/                # Berisi model.onnx, tokenizer.json, dan config.json
│
├── evaluation/                        # Aset hasil pengujian untuk Bab Pembahasan Laporan (QA & Document Control)
│   ├── metrics_summary.json           # Hasil akhir Accuracy, Precision, Recall, dan F1-Score
│   ├── confusion_matrix.png           # Visualisasi grafik Confusion Matrix
│   └── error_analysis_fp_fn.csv       # Daftar sampel kasus False Positive dan False Negative beserta analisisnya
│
└── logs/                              # Penyimpanan log runtime otomatis saat aplikasi dijalankan
    └── security_events.jsonl          # Catatan riwayat deteksi selama sesi pengujian & demo
```

---

## 8. Pembagian Tugas & Target Penyelesaian

| Peran Anggota | Fokus Tanggung Jawab Utama | Target Selesai |
| :--- | :--- | :--- |
| **Anggota 1: AI & Data Engineer** | Menjalankan *notebook* `01` dan `02` di Google Colab, memastikan akurasi model $> 85\%$, serta mengekspor folder `onnx_guardrail/` ke tim. | 21 November 2026 |
| **Anggota 2: Backend & Infrastructure** | Menyusun `docker-compose.yml`, membangun API FastAPI (`detector.py`, `ollama_client.py`), menyiapkan model Ollama di RAM 16 GB, dan membuat antarmuka Web Chat (`static/`). | 24 November 2026 |
| **Anggota 3: QA & Document Control** | Menjalankan *notebook* `03` untuk evaluasi metrik & analisis *False Positive* / *False Negative*, menyusun laporan akhir, serta mengoordinasikan rekaman video demo YouTube ($5\text{--}10$ menit). | 28 November 2026 |