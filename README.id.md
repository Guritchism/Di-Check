# Alat Steganografi PDN

Ini adalah aplikasi web untuk menyembunyikan dan mengungkap pesan rahasia dalam notasi PDN (Portable Draughts Notation) menggunakan teknik steganografi.

## Fitur

- **Enkode**: Sembunyikan pesan rahasia dalam notasi PDN menggunakan tiga metode yang saling melengkapi:
  - Karakter tidak terlihat setelah entri metadata
  - Angka nol di depan untuk gerakan angka tunggal
  - Detik ganjil/genap pada notasi jam
- **Dekode**: Ekstrak pesan tersembunyi dari notasi PDN yang telah disandikan.

## Cara Kerja

Aplikasi ini menggunakan tiga metode steganografi:

### Metode 1: Steganografi Metadata
- Setelah setiap baris metadata (seperti `[Event "Game Name"]`), alat ini menambahkan karakter spasi yang tidak terlihat.
- Setiap spasi mewakili biner '0', dan setiap tab mewakili biner '1'.
- Setiap baris metadata dapat menyimpan hingga 4 bit informasi.

### Metode 2: Steganografi Notasi Gerakan
- Untuk gerakan dengan angka digit tunggal (1-9), alat ini dapat menambahkan angka nol di depan untuk menyandikan informasi.
- Gerakan standar: `3-8`
- Gerakan dengan steganografi: `03-08`
- Jika gerakan memiliki angka nol di depan, ini mewakili biner '1'
- Jika gerakan tidak memiliki angka nol di depan, ini mewakili biner '0'

### Metode 3: Steganografi Notasi Jam
- File PDN sering berisi notasi jam dalam format `{[%clock w0:14:00 B0:14:00]}`
- Metode ini memodifikasi nilai detik untuk menyandikan bit:
  - Detik ganjil (misalnya, 01, 03, 59) mewakili biner '1'
  - Detik genap (misalnya, 00, 02, 58) mewakili biner '0'
- Akhir pesan ditandai dengan urutan terminator (8 nol berturut-turut)
- Setelah pesan dan terminator, notasi jam yang tersisa dimodifikasi secara acak untuk menyembunyikan di mana pesan berakhir

Aplikasi menggunakan metode-metode ini secara berurutan, pertama mencoba menyandikan dalam metadata, kemudian dalam notasi jam, dan terakhir dalam notasi gerakan. Dengan cara ini, aplikasi memaksimalkan kapasitas penyandian sambil mempertahankan kevalidan PDN.

Urutan nilai biner ini dapat diterjemahkan menjadi teks menggunakan pengkodean ASCII.

## Pengaturan

1. Instal paket yang diperlukan:
```
pip install flask
```

2. Jalankan aplikasi:
```
python app.py
```

3. Buka browser Anda dan navigasikan ke:
```
http://127.0.0.1:5000/
```

## Penggunaan

### Menyandikan Pesan
1. Navigasikan ke tab "Encode Message"
2. Tempelkan notasi permainan PDN Anda di area teks yang disediakan
3. Masukkan pesan rahasia Anda di kolom input
4. Klik tombol "Encode Message"
5. Salin PDN yang telah disandikan dari area hasil

### Mendekode Pesan

1. Navigasikan ke tab "Decode Message"
2. Tempelkan notasi permainan PDN yang telah disandikan
3. Klik tombol "Decode Message"
4. Lihat pesan biner dan pesan yang didekodekan di area hasil

## Panjang Maksimum Pesan

Alat ini menghitung panjang pesan maksimum berdasarkan:
- Jumlah baris metadata × 4 bit per baris (kapasitas metadata)
- Jumlah notasi jam × 1 bit per notasi (kapasitas notasi jam)
- Jumlah angka digit tunggal dalam gerakan (kapasitas notasi gerakan)
- Total bit ÷ 8 = Jumlah maksimum karakter

Sebagai contoh, jika file PDN memiliki:
- 10 baris metadata: 10 × 4 = 40 bit
- 15 notasi jam: 15 bit
- 20 angka digit tunggal dalam gerakan: 20 bit
- Kapasitas total: 75 bit ÷ 8 = 9,375 karakter (9 karakter penuh)

## Teknologi yang Digunakan

- Backend: Flask (Python)
- Frontend: HTML, CSS, JavaScript
