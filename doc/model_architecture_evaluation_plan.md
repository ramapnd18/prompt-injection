# Model Architecture, Training & Evaluation Plan (`planmodel.md`)
## Spesifikasi Fine-Tuning Transformer, Optimasi ONNX & Analisis Metrik

| Metadata | Detail |
| :--- | :--- |
| **PIC Utama** | Anggota 1 (*Training* & ONNX) & Anggota 3 (*Evaluation* & *Error Analysis*) |
| **Lingkungan Kerja** | Google Colab (Runtime GPU T4 — 16 GB VRAM) |
| **Target Akurasi** | $> 85\%$ (Target Optimal: $92\% \text{--} 96\%$) |
| **Target Selesai** | 21 November 2026 (Model ONNX) & 26 November 2026 (Evaluasi) |

---

## 1. Pemilihan Arsitektur Model

Model harus memahami konteks semantik lintas bahasa (*cross-lingual semantic intent*), bukan sekadar mencocokkan kata kunci.

* **Arsitektur Utama:** `microsoft/mdeberta-v3-base` (Multilingual DeBERTa-v3).
  * *Alasan:* Menggunakan mekanisme *disentangled attention* yang sangat akurat mendeteksi manipulasi instruksi tersembunyi di tengah paragraf panjang dalam 100 bahasa (termasuk Inggris dan Indonesia).
* **Arsitektur Cadangan:** `xlm-roberta-base` (digunakan jika terjadi kendala kompatibilitas *opset* saat ekspor ONNX).

---

## 2. Konfigurasi *Hyperparameter Training* (`02_model_training_onnx.ipynb`)

Gunakan konfigurasi berikut pada pustaka Hugging Face `Trainer` untuk mencegah *overfitting* sekaligus menangkap serangan panjang:

| Parameter | Nilai Konfigurasi | Justifikasi Teknis |
| :--- | :--- | :--- |
| `max_length` | `384` atau `512` | Serangan *jailbreak* sering menyembunyikan perintah berbahaya di bagian akhir teks panjang. |
| `learning_rate` | `2e-5` | Standar stabil untuk *fine-tuning* model Transformer berbasis DeBERTa/RoBERTa. |
| `batch_size` | `16` (`fp16=True`) | Memaksimalkan kapasitas VRAM GPU T4 (16 GB) di Google Colab tanpa *Out of Memory*. |
| `num_train_epochs` | `3` (maksimal `4`) | Cukup untuk konvergensi tanpa membuat model menghafal data latih (*overfitting*). |
| `weight_decay` | `0.01` | Regularisasi L2 untuk menjaga kemampuan generalisasi pada pola serangan baru. |
| `evaluation_strategy` | `epoch` | Menyimpan *checkpoint* terbaik berdasarkan nilai `eval_f1` tertinggi. |

---

## 3. Optimasi *Deployment* ke Format ONNX

Karena *container* Docker akan berjalan di CPU laptop (tanpa ketergantungan GPU saat demo), model PyTorch wajib dikonversi ke format **ONNX Runtime** menggunakan pustaka `optimum`:

1. Jalankan ekspor melalui CLI/Notebook:
   ```bash
   optimum-cli export onnx --model ./best_checkpoint --task text-classification ./onnx_guardrail/
   ```
2. Terapkan *dynamic quantization* (`INT8`) jika ukuran file `model.onnx` melebihi $500\text{ MB}$ agar penggunaan RAM di dalam Docker tetap di bawah $1\text{ GB}$ dan latensi inferensi turun menjadi $< 100\text{ ms}$.
3. Verifikasi bahwa folder `onnx_guardrail/` berisi: `model.onnx`, `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`, dan `config.json`.

---

## 4. Protokol Evaluasi & Kalibrasi *Threshold* (`03_model_evaluation.ipynb`)

Untuk memenuhi **Luaran Khusus Topik 1**, Anggota 3 (QA) menjalankan pengujian menyeluruh pada `test_bilingual.csv` ($\approx 3.172$ baris) dan menghasilkan artefak berikut:

### 4.1 Metrik Kuantitatif Wajib
Hitung skor keseluruhan maupun terpisah berdasarkan bahasa (`lang == 'en'` dan `lang == 'id'`):
* **Accuracy:** $\frac{TP + TN}{TP + TN + FP + FN} > 0.85$
* **Precision:** $\frac{TP}{TP + FP}$ (Mengukur seberapa akurat sistem saat memblokir *prompt*)
* **Recall:** $\frac{TP}{TP + FN}$ (Mengukur seberapa banyak serangan nyata yang berhasil dicegah)
* **F1-Score:** $2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$

### 4.2 Kalibrasi *Threshold* Probabilitas ($\tau$)
Lakukan simulasi pengujian pada nilai $\tau \in \{0.50, 0.60, 0.65, 0.70, 0.80\}$:
* Jika $P(\text{injection}) \ge \tau$, klasifikasikan sebagai **Blokir (`1`)**.
* Pilih nilai $\tau$ yang memberikan keseimbangan terbaik antara keamanan tinggi (*Recall* tinggi) dan kenyamanan pengguna (*False Positive Rate* rendah), lalu dokumentasikan grafik *Precision-Recall Trade-off* tersebut di Bab Pembahasan laporan.

### 4.3 Rubrik Analisis *False Positive* ($FP$) & *False Negative* ($FN$)
Ekspor seluruh baris yang salah diprediksi ke file `error_analysis_fp_fn.csv`, lalu kategorikan minimal $10$ sampel teratas untuk laporan akhir:
1. **Analisis *False Positive* ($FP$ — Aman tapi Diblokir):**
   * Identifikasi kata pemicu (misal: pertanyaan akademik tentang keamanan siber atau kata perintah biasa seperti *"abaikan"*).
   * Jelaskan solusi mitigasinya (penambahan *hard negatives* atau penyesuaian nilai $\tau$).
2. **Analisis *False Negative* ($FN$ — Serangan Lolos):**
   * Identifikasi teknik penyamaran yang berhasil menembus model (misal: penggunaan bahasa gaul/singkatan, *encoding* Base64, atau skenario cerita fiksi yang sangat halus).
   * Rumuskan rekomendasi pengembangan lanjutan (misal: *preprocessing* dekode Base64 atau penambahan data latih *adversarial*).