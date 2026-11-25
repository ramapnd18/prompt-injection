# Master To-Do List & Sprint Schedule (`todolist.md`)
## Jadwal Eksekusi Proyek Akhir Keamanan Informasi (16 – 29 November 2026)

| Informasi Proyek | Keterangan |
| :--- | :--- |
| **Rentang Waktu** | 16 November 2026 – 29 November 2026 (14 Hari Kalender) |
| **Batas Akhir Pengumpulan** | **Sabtu, 29 November 2026** (Via Google Form Mata Kuliah) |
| **Status Target** | Aplikasi Docker Berjalan, Akurasi $> 85\%$, Laporan Akhir & Video YouTube |

---

## Sprint 1: Data & Fondasi Infrastruktur (16 – 19 November 2026)

### Anggota 1 — AI & Data Engineer
- [ ] Membuat folder kerja proyek di Google Drive (`/Project_Keamanan_AI/`).
- [ ] Menulis dan menjalankan `01_dataset_preparation.ipynb` di Google Colab untuk mengunduh 5 dataset Hugging Face (`safe-guard`, `deepset`, `jailbreak-classification`, `gandalf`, `dolly-15k`).
- [ ] Menyusun manual $\approx 200$ kalimat *Hard Negatives* (Inggris & Indonesia) dalam `hard_negatives.csv`.
- [ ] Melakukan *stratified train-test split* ($80:20$) **sebelum** proses translasi untuk mencegah *data leakage*.
- [ ] Menerjemahkan $1.200$ sampel *train* dan $300$ sampel *test* ke Bahasa Indonesia, lalu menyimpan `train_bilingual.csv` dan `test_bilingual.csv`.

### Anggota 2 — Backend & Infrastructure
- [x] Membuat struktur direktori repositori `prompt-injection-guardrail/` di laptop lokal sesuai PRD.
- [x] Menyusun `docker-compose.yml` dengan jaringan tertutup `guardrail_net` dan pembatasan RAM (`2 GB` untuk FastAPI, `6 GB` untuk Ollama).
- [x] Menguji kontainer `ollama-service` dan menarik model ringan `qwen2.5:1.5b` (atau `llama3.2:3b`).
- [x] Membuat kerangka API FastAPI (`main.py`, `config.py`, `ollama_client.py`, `logger.py`) dengan *mock detector* sementara.

### Anggota 3 — QA & Document Control
- [ ] Menyiapkan dokumen draf **Laporan Akhir** (Bab 1 Pendahuluan: Latar Belakang, Rumusan Masalah, Tujuan; serta kerangka Bab 2 Metode dan Daftar Pustaka sumber dataset).
- [ ] Menyusun daftar $30$ skenario *prompt* pengujian manual (campuran normal, *hard negative*, dan *jailbreak* EN/ID) untuk uji coba sistem.

---

## Sprint 2: Training Model, Integrasi ONNX & Web UI (20 – 24 November 2026)

### Anggota 1 — AI & Data Engineer
- [ ] Menjalankan `02_model_training_onnx.ipynb` di Google Colab (GPU T4) menggunakan `microsoft/mdeberta-v3-base` (`max_length=384`, `epochs=3`).
- [ ] Memastikan skor validasi sementara sudah melampaui ambang batas minimal $> 85\%$.
- [ ] Mengekspor model terbaik ke format **ONNX** (`model.onnx` + file *tokenizer*) dan membagikannya ke tim melalui Google Drive.

### Anggota 2 — Backend & Infrastructure
- [x] Mengunduh folder `onnx_guardrail/` ke direktori lokal `model_artifacts/onnx_guardrail/` (Telah tersedia model.onnx 1.11 GB & tokenizer).
- [x] Mengimplementasikan inferensi nyata menggunakan `onnxruntime` di `backend/app/detector.py` (Mode ONNX riil aktif dan tervalidasi).
- [x] Membangun antarmuka Web Chat (`index.html`, `style.css`, `app.js`) lengkap dengan *slider threshold* dan tombol *preset* uji cepat.
- [x] Melakukan uji integrasi penuh (`docker compose up --build`) dan memastikan alur *blocking* (`HTTP 403`) dan *forwarding* ke Ollama (`HTTP 200`) berjalan mulus.

### Anggota 3 — QA & Document Control
- [ ] Menulis `03_model_evaluation.ipynb` di Google Colab menggunakan `test_bilingual.csv` ($\approx 3.172$ baris).
- [ ] Menghitung nilai akhir **Accuracy, Precision, Recall, dan F1-Score**, serta membuat grafik `confusion_matrix.png`.
- [ ] Menguji variasi *threshold* ($\tau \in \{0.50, 0.60, 0.65, 0.70\}$) untuk menentukan nilai *default* terbaik.

---

## Sprint 3: Analisis Error, Laporan & Video Demo (25 – 29 November 2026)

### Anggota 3 — QA & Document Control (Lead Dokumentasi)
- [ ] Mengekstrak daftar sampel kesalahan prediksi ke `evaluation/error_analysis_fp_fn.csv`.
- [ ] Menuliskan **Analisis *False Positive* ($FP$)** dan **Analisis *False Negative* ($FN$)** secara mendalam pada Bab 3 Pembahasan laporan akhir.
- [ ] Menyusun naskah pembagian bicara untuk video demonstrasi berdurasi $5\text{--}10$ menit.

### Seluruh Tim (Anggota 1, 2, dan 3)
- [ ] **26 Nov:** Melakukan *end-to-end stress test* pada Web Chat menggunakan $30$ skenario uji manual dan memeriksa `logs/security_events.jsonl`.
- [ ] **27 Nov:** Merekam video demonstrasi proyek (seluruh 3 anggota tampil menjelaskan bagian masing-masing + demo langsung aplikasi Web Chat).
- [ ] **28 Nov:** Melakukan *editing* ringan, mengunggah video ke **YouTube** (pastikan visibilitas *Unlisted* atau *Public*), serta melakukan *final proofreading* Laporan Akhir (PDF).
- [ ] **29 Nov (HARI H):** Mengumpulkan tautan video YouTube, file Laporan Akhir, dan repositori/arsip kode ke **Google Form** sebelum batas waktu berakhir.

---

## Definition of Done (Checklist Kelulusan Proyek)

- [ ] **Luaran Khusus 1:** Aplikasi berjalan utuh dengan satu perintah `docker compose up --build` tanpa *error* memori pada laptop RAM 16 GB.
- [ ] **Luaran Khusus 2:** Akurasi model uji $> 85\%$, dilengkapi nilai *Precision*, *Recall*, *F1-Score*, *Confusion Matrix*, serta pembahasan tertulis mengenai kasus *False Positive* dan *False Negative*.
- [ ] **Luaran Umum 1:** Video demo YouTube berdurasi $5\text{--}10$ menit dengan seluruh anggota kelompok (3 orang) tampil aktif.
- [ ] **Luaran Umum 2:** Laporan akhir lengkap (Pendahuluan, Metode, Pembahasan, Kesimpulan) dan mematuhi aturan etika akademik.