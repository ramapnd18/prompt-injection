# AI & Data Engineering Plan (`planai.md`)
## Kurasi Dataset Dwibahasa & Pipeline Prapemrosesan

| Metadata | Detail |
| :--- | :--- |
| **PIC Utama** | Anggota 1 (*AI & Data Engineer*) |
| **Lingkungan Kerja** | Google Colab (Terhubung ke Google Drive) |
| **Target Output** | `train_bilingual.csv` & `test_bilingual.csv` |
| **Target Selesai** | 18 November 2026 |

---

## 1. Strategi Pengumpulan & Komposisi Dataset

Untuk mencapai akurasi di atas $85\%$ sekaligus menekan angka *False Positive* pada percakapan normal, dataset disusun dari tiga peran utama dengan target proporsi kelas yang seimbang ($50\%$ Aman / Label `0` dan $50\%$ Injeksi / Label `1`).

### 1.1 Sumber Dataset Publik (Hugging Face)
1. **Dataset Utama (Fondasi & Baseline):**
   * `xTRam1/safe-guard-prompt-injection` ($\approx 10.200$ baris): Digunakan seluruhnya (*train* + *test*) sebagai tulang punggung distribusi seimbang.
   * `deepset/prompt-injections` ($\approx 662$ baris): Digunakan seluruhnya untuk memperkaya variasi pola injeksi direktif klasik.
2. **Dataset Penyerang (*Jailbreak* & *Adversarial*):**
   * `jackhhao/jailbreak-classification` ($\approx 650$ baris): Hanya mengambil baris dengan kategori `jailbreak` (diberi label `1`).
   * `Lakera/gandalf_ignore_instructions` ($\approx 1.000$ baris acak): Mengambil sampel serangan eksplorasi manusia secara acak (diberi label `1`).
3. **Dataset Penyeimbang Kelas (*Benign*):**
   * `databricks/databricks-dolly-15k` ($\approx 1.650$ baris acak): Mengambil kolom `instruction` secara acak (diberi label `0`) untuk menyeimbangkan jumlah tambahan data penyerang.

### 1.2 Kurasi *Hard Negatives* Manual ($\approx 200$ Baris)
*AI Engineer* wajib membuat file `hard_negatives.csv` berisi kalimat aman (label `0`) dalam Bahasa Inggris dan Bahasa Indonesia yang mengandung kata kunci sensitif namun bukan merupakan serangan.
* **Tujuan:** Mencegah model melakukan *over-blocking* (*False Positive*) terhadap pertanyaan edukatif atau instruksi pemrosesan teks biasa.
* **Contoh Sampel Wajib:**
  * *"Tolong jelaskan bagaimana cara kerja serangan SQL injection dan prompt injection pada LLM."* (`label: 0`)
  * *"Abaikan paragraf pertama dari artikel berikut, lalu buatkan ringkasan poin pentingnya."* (`label: 0`)
  * *"Lupakan topik sebelumnya, sekarang mari kita bahas sejarah Universitas Siliwangi."* (`label: 0`)
  * *"Ignore the formatting errors in this text and translate it to formal Indonesian."* (`label: 0`)

---

## 2. Aturan Pembersihan Teks (*Preprocessing Rules*)

Pemrosesan teks untuk deteksi keamanan **berbeda** dengan analisis sentimen konvensional. Terapkan aturan ketat berikut:

1. **DILARANG Melakukan *Stopword Removal* & *Stemming*:**
   * Kata seperti *"ignore"*, *"forget"*, *"abaikan"*, *"lupakan"*, *"system"*, dan *"sekarang"* merupakan sinyal utama serangan injeksi. Menghapus kata-kata tersebut akan merusak struktur niat kalimat.
2. **DILARANG Melakukan *Lowercasing* Agresif (Opsional / Ikuti Tokenizer):**
   * Gunakan *tokenizer* bawaan model *cased* (seperti `mdeberta-v3-base`) karena penggunaan huruf kapital penuh (misal: `IGNORE ALL PREVIOUS INSTRUCTIONS`) sering menjadi pola khas serangan *jailbreak*.
3. **Normalisasi Wajib:**
   * Hapus baris kosong (`NaN`), hapus duplikasi persis (`drop_duplicates`), dan rapikan spasi berlebih (*whitespace normalization*) tanpa menghapus tanda baca atau karakter khusus (seperti tanda kurung siku `[]`, tag XML `<system>`, atau delimiter `###` yang sering dipakai untuk *context switching*).

---

## 3. Alur Lokalisasi Dwibahasa (Anti-*Data Leakage*)

Untuk mendukung deteksi Bahasa Inggris dan Bahasa Indonesia secara akurat tanpa kebocoran data evaluasi, ikuti urutan eksekusi berikut:

```text
[Dataset Gabungan Mentah (~14.362 baris)]
                  |
                  v
[1. Pembersihan NaN & Duplikat]
                  |
                  v
[2. Stratified Split 80% Train : 20% Test]  <-- WAJIB DILAKUKAN SEBELUM TRANSLASI!
        /                          \
       v                            v
[Train EN (~11.490)]         [Test EN (~2.872)]
       |                            |
       +--> Translasi 1.200         +--> Translasi 300
       |    sampel ke ID            |    sampel ke ID
       v                            v
[Train Bilingual (~12.690)]  [Test Bilingual (~3.172)]
```

### Langkah Teknis di Google Colab (`01_dataset_preparation.ipynb`)
1. Hubungkan Google Colab ke Google Drive (`/content/drive/MyDrive/Project_Keamanan_AI/datasets/`).
2. Gabungkan seluruh dataset publik + `hard_negatives.csv`.
3. Jalankan `train_test_split(..., test_size=0.2, stratify=df['label'], random_state=42)`.
4. Gunakan pustaka `deep-translator` (`GoogleTranslator(source='en', target='id')`) untuk menerjemahkan:
   * $600$ sampel aman + $600$ sampel injeksi dari *Train Set*.
   * $150$ sampel aman + $150$ sampel injeksi dari *Test Set*.
5. Berikan jeda `time.sleep(0.2)` antarpermintaan dan potong teks maksimal $4.500$ karakter agar tidak terkena pembatasan (*rate limit*) API penerjemah.
6. Simpan hasil akhir ke Drive sebagai `train_bilingual.csv` dan `test_bilingual.csv`.