from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import re

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Ukuran file maksimal 16MB

# Buat folder uploads jika belum ada
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def encode_metadata(lines, message_bits, start_bit_index=0):
    """
    Menyisipkan pesan ke dalam bagian metadata PDN dengan menambahkan karakter tidak terlihat
    setelah entri metadata (spasi dan tab).
    
    Parameter:
        lines: List berisi baris-baris teks PDN
        message_bits: List berisi bit-bit pesan biner ('0' dan '1')
        start_bit_index: Indeks awal di message_bits untuk memulai penyandian
    
    Mengembalikan: 
        Tuple (baris yang telah dimodifikasi, jumlah bit yang disandikan, indeks bit terakhir)
    """
    bit_index = start_bit_index
    total_metadata_lines_modified = 0
    
    # Proses setiap baris yang berisi metadata (dimulai dengan '[')
    for i, line in enumerate(lines):
        if bit_index >= len(message_bits):
            break
            
        if line.startswith('[') and line.endswith(']'):
            print(f"Memproses baris metadata {i}: {line}")
            
            # Kita akan menambahkan spasi (bit 0) dan tab (bit 1) setelah baris metadata (setelah tanda kurung tutup)
            invisible_chars = ""
            
            # Menyandi hingga 4 bit per baris metadata (dapat disesuaikan)
            bits_added = 0
            while bit_index < len(message_bits) and bits_added < 4:
                if message_bits[bit_index] == '0':
                    invisible_chars += " "  # Spasi untuk 0
                else:
                    invisible_chars += "\t"  # Tab untuk 1
                bit_index += 1
                bits_added += 1
            
            if bits_added > 0:
                # Tambahkan karakter tidak terlihat SETELAH tanda kurung tutup (bukan di dalamnya)
                modified_line = line + invisible_chars
                lines[i] = modified_line
                total_metadata_lines_modified += 1
                print(f"  Menambahkan {bits_added} bit sebagai karakter tidak terlihat setelah entri metadata")
    
    print(f"Penyandian metadata selesai: {total_metadata_lines_modified} baris metadata dimodifikasi, menggunakan {bit_index - start_bit_index} bit")
    return lines, bit_index - start_bit_index, bit_index

def decode_metadata(lines):
    """
    Mendekode pesan dari bagian metadata dengan memeriksa karakter tidak terlihat (spasi dan tab).
    
    Parameter:
        lines: List berisi baris-baris teks PDN
    
    Mengembalikan: 
        String biner dari bit yang didekode dari metadata
    """
    binary_message = ""
    
    # Proses setiap baris yang berisi metadata
    for line_idx, line in enumerate(lines):
        if line.startswith('[') and ']' in line:  # Periksa apakah ini adalah baris metadata
            # Temukan posisi tanda kurung tutup
            closing_bracket_pos = line.find(']')
            
            # Periksa apakah ada karakter tidak terlihat setelah tanda kurung tutup
            if len(line) > closing_bracket_pos + 1:
                # Ada karakter tidak terlihat setelah tanda kurung tutup
                invisible_part = line[closing_bracket_pos + 1:]
                
                for char in invisible_part:
                    if char == ' ':
                        binary_message += '0'
                        print(f"Baris {line_idx}: Mengekstrak bit '0' dari karakter spasi")
                    elif char == '\t':
                        binary_message += '1'
                        print(f"Baris {line_idx}: Mengekstrak bit '1' dari karakter tab")
    
    return binary_message

def encode_pdn(pdn_text, message):
    """
    Menyandikan pesan rahasia ke dalam notasi PDN menggunakan tiga metode:
    1. Menambahkan karakter tidak terlihat (spasi dan tab) setelah entri metadata
    2. Menambahkan angka nol di depan gerakan angka tunggal
    3. Memodifikasi detik pada notasi jam menjadi ganjil (bit 1) atau genap (bit 0)
    
    Pesan harus berupa string biner (mis., '101010')
    
    Parameter:
        pdn_text: String berisi konten PDN
        message: String pesan biner yang akan disandikan
        
    Mengembalikan:
        String PDN yang telah dimodifikasi dengan pesan tersembunyi
    """
    # Pisahkan PDN menjadi baris-baris
    lines = pdn_text.split('\n')
    
    # Konversi pesan biner menjadi daftar bit
    if message:
        message_bits = list(message)
    else:
        message_bits = []
    
    print(f"\n--- Memulai proses penyandian ---")
    
    # Pertama, sandi bit dalam metadata
    lines, metadata_bits_encoded, bit_index = encode_metadata(lines, message_bits)
    
    print(f"Tersandi {metadata_bits_encoded} bit dalam metadata, {len(message_bits) - bit_index} bit tersisa")
    
    # Jika kita sudah menyandikan semua bit, kita selesai
    if bit_index >= len(message_bits):
        encoded_pdn = '\n'.join(lines)
        return encoded_pdn
        
    # Kedua, coba sandi dalam notasi jam jika masih ada bit tersisa
    pdn_text_joined = '\n'.join(lines)
    modified_pdn, clock_bits_encoded, bit_index = encode_time_notation(pdn_text_joined, message_bits, bit_index)
    
    print(f"Tersandi {clock_bits_encoded} bit dalam notasi jam, {len(message_bits) - bit_index} bit tersisa")
    
    # Jika kita sudah menyandikan semua bit dengan notasi jam, kita selesai
    if bit_index >= len(message_bits):
        return modified_pdn
        
    # Terakhir, jika masih ada bit tersisa, gunakan metode notasi gerakan
    # Kita perlu memisahkan teks PDN lagi
    lines = modified_pdn.split('\n')
      # Identifikasi baris yang berisi gerakan (bukan metadata)
    move_lines = []
    for i, line in enumerate(lines):
        if line and not line.startswith('[') and not line.endswith(']') and not line.startswith('{'):
            move_lines.append(i)
    
    print(f"Menemukan {len(move_lines)} baris dengan gerakan potensial")
    
    # Proses setiap baris gerakan untuk menyembunyikan bit pesan yang tersisa
    total_moves_modified = 0
    
    for line_idx in move_lines:
        if bit_index >= len(message_bits):
            break
            
        line = lines[line_idx]
        print(f"\nMemproses baris {line_idx}: {line}")
        
        # Pra-proses baris untuk mengecualikan notasi jam
        parts = re.split(r'(\{[^}]*\})', line)
        move_positions = []  # Simpan posisi dan konten gerakan yang sebenarnya
        
        # Untuk setiap bagian dari baris
        current_pos = 0
        for part in parts:
            if not part.startswith('{'):  # Lewati notasi jam
                # Temukan semua gerakan di bagian ini
                move_pattern = r'(?<!\S)(\d+)([x-])(\d+)(?!\S)'  # Cocokkan gerakan yang berdiri sendiri dengan batas kata
                for match in re.finditer(move_pattern, part):
                    # Simpan posisi absolut dalam baris asli
                    start_pos = current_pos + match.start()
                    end_pos = current_pos + match.end()
                    move_positions.append({
                        'start': start_pos,
                        'end': end_pos,
                        'p1': match.group(1),
                        'separator': match.group(2),
                        'p2': match.group(3),
                        'full_move': match.group(0)
                    })
            current_pos += len(part)
          # Sekarang proses gerakan yang teridentifikasi
        new_line = line
        offset = 0  # Offset untuk menyesuaikan posisi setelah modifikasi
        
        for move_pos in move_positions:
            if bit_index >= len(message_bits):
                break
                
            p1 = move_pos['p1']
            p2 = move_pos['p2']
            separator = move_pos['separator']
            full_move = move_pos['full_move']
            
            # Simpan nilai asli untuk perbandingan
            original_p1 = p1
            original_p2 = p2
            
            # Lacak apakah kita dapat menyandi bit dalam gerakan ini
            can_encode_first = len(p1) == 1 and p1 in '123456789'
            can_encode_second = len(p2) == 1 and p2 in '123456789'
            
            # Lewati gerakan ini jika tidak ada angka yang merupakan digit tunggal
            if not can_encode_first and not can_encode_second:
                print(f"  Melewati gerakan '{full_move}' - tidak ada angka digit tunggal untuk dikodekan")
                continue
                
            # Inisialisasi bit untuk gerakan ini
            bit1 = '0'
            bit2 = '0'
              # Terapkan angka nol di depan berdasarkan bit, tetapi HANYA untuk angka digit tunggal
            if can_encode_first and bit_index < len(message_bits):
                bit1 = message_bits[bit_index]
                if bit1 == '1':
                    p1 = '0' + p1  # Tambahkan angka nol di depan untuk bit 1
                bit_index += 1
            
            if can_encode_second and bit_index < len(message_bits):
                bit2 = message_bits[bit_index]
                if bit2 == '1':
                    p2 = '0' + p2  # Tambahkan angka nol di depan untuk bit 1
                bit_index += 1
                
            # Buat gerakan baru
            new_move = p1 + separator + p2
              # Jika gerakan benar-benar berubah, gantilah dalam baris
            if new_move != full_move:
                # Hitung posisi awal dan akhir gerakan dalam baris
                start_pos = move_pos['start'] + offset
                end_pos = move_pos['end'] + offset
                
                # Ganti hanya instance gerakan tertentu itu
                new_line = new_line[:start_pos] + new_move + new_line[end_pos:]
                
                # Perbarui offset untuk penggantian di masa depan
                offset += len(new_move) - len(full_move)
                
                total_moves_modified += 1
                
                encoded_bits = ""
                if can_encode_first:
                    encoded_bits += bit1
                if can_encode_second:
                    encoded_bits += bit2
                
                print(f"  Gerakan dimodifikasi: '{full_move}' ({original_p1}{separator}{original_p2}) → '{new_move}' (bit: {encoded_bits})")
            else:
                encoded_bits = ""
                if can_encode_first:
                    encoded_bits += bit1
                if can_encode_second:
                    encoded_bits += bit2
                print(f"  Tidak perlu perubahan untuk gerakan: '{full_move}' (bit: {encoded_bits})")
        
        lines[line_idx] = new_line
    
    print(f"\nPenyandian selesai: {total_moves_modified} gerakan dimodifikasi, menggunakan {bit_index} dari {len(message_bits)} bit")
    
    # Gabungkan baris-baris kembali
    encoded_pdn = '\n'.join(lines)
    return encoded_pdn

def decode_pdn(pdn_text):
    """
    Mendekode pesan rahasia dari notasi PDN menggunakan tiga metode:
    1. Memeriksa karakter tak terlihat (spasi dan tab) dalam metadata
    2. Memeriksa nilai detik notasi jam (nilai ganjil/genap)
    3. Memeriksa angka nol di depan pada angka digit tunggal dalam gerakan
    
    Parameter:
        pdn_text: String berisi konten PDN yang memiliki pesan tersembunyi
        
    Mengembalikan:
        String biner dari bit yang berhasil didekode dari PDN
    """
    # Pisahkan PDN menjadi baris-baris
    lines = pdn_text.split('\n')
    
    # Ekstrak pesan biner dari metadata terlebih dahulu
    print(f"\n--- Mendekode dari metadata ---")
    metadata_binary_message = decode_metadata(lines)
    print(f"Diekstrak {len(metadata_binary_message)} bit dari metadata")
    
    # Ekstrak pesan biner dari notasi jam kedua
    print(f"\n--- Mendekode dari notasi jam ---")
    clock_binary_message = decode_time_notation(pdn_text)
    print(f"Diekstrak {len(clock_binary_message)} bit dari notasi jam")
    
    # Ekstrak pesan biner dari gerakan ketiga
    print(f"\n--- Mendekode dari gerakan ---")
    move_binary_message = ""
      # Proses setiap baris untuk gerakan
    for line_idx, line in enumerate(lines):
        if line and not line.startswith('[') and not line.endswith(']') and not line.startswith('{'):
            # Pisahkan baris untuk mengecualikan notasi jam
            parts = re.split(r'(\{[^}]*\})', line)
            move_line = ""
            for part in parts:
                if not part.startswith('{'):
                    move_line += part
            
            # Sekarang cari gerakan hanya di bagian yang telah dibersihkan
            move_pattern = r'(?<!\S)(\d+)([x-])(\d+)(?!\S)'  # Cocokkan gerakan yang berdiri sendiri dengan batas kata
            matches = re.finditer(move_pattern, move_line)
            
            # Proses setiap gerakan
            for match in matches:
                full_move = match.group(0)
                p1 = match.group(1)  # Angka pertama
                separator = match.group(2)  # "-" atau "x"
                p2 = match.group(3)  # Angka kedua
                
                # Ekstrak bit berdasarkan angka nol di depan
                # Hanya periksa angka nol di depan pada angka yang secara alami berdigit tunggal (1-9)
                
                # Angka pertama: jika 01-09, memiliki angka nol di depan (ekstrak bit 1)
                # Jika 1-9, tidak memiliki angka nol di depan (ekstrak bit 0)
                # Jika 10+, kita tidak mengekstrak bit apa pun
                if p1.startswith('0') and len(p1) == 2 and p1[1] in '123456789':
                    # Ini adalah angka digit tunggal dengan angka nol di depan (01-09)
                    bit1 = '1'
                    move_binary_message += bit1
                    print(f"Baris {line_idx}, Gerakan '{full_move}': Mengekstrak bit '1' dari angka pertama '{p1}'")
                elif len(p1) == 1 and p1 in '123456789':
                    # Ini adalah angka digit tunggal tanpa angka nol di depan (1-9)
                    bit1 = '0'
                    move_binary_message += bit1
                    print(f"Baris {line_idx}, Gerakan '{full_move}': Mengekstrak bit '0' dari angka pertama '{p1}'")
                
                # Angka kedua: logika yang sama dengan angka pertama
                if p2.startswith('0') and len(p2) == 2 and p2[1] in '123456789':
                    # Ini adalah angka digit tunggal dengan angka nol di depan (01-09)
                    bit2 = '1'
                    move_binary_message += bit2
                    print(f"Baris {line_idx}, Gerakan '{full_move}': Mengekstrak bit '1' dari angka kedua '{p2}'")
                elif len(p2) == 1 and p2 in '123456789':
                    # Ini adalah angka digit tunggal tanpa angka nol di depan (1-9)
                    bit2 = '0'
                    move_binary_message += bit2
                    print(f"Baris {line_idx}, Gerakan '{full_move}': Mengekstrak bit '0' dari angka kedua '{p2}'")
    
    # Gabungkan semua sumber bit
    print(f"Diekstrak {len(move_binary_message)} bit dari gerakan")
    combined_binary_message = metadata_binary_message + clock_binary_message + move_binary_message
    print(f"Total bit yang diekstrak: {len(combined_binary_message)}")
    
    return combined_binary_message

def count_encodable_moves(pdn_text):
    """
    Menghitung jumlah angka digit tunggal dalam gerakan yang dapat digunakan untuk penyandian.
    Gerakan dengan angka digit tunggal dapat disandikan dengan menambahkan angka nol di depannya.
    
    Parameter:
        pdn_text: String berisi konten PDN
        
    Mengembalikan:
        Integer yang menunjukkan jumlah digit yang dapat disandikan dalam gerakan
    """
    # Pisahkan PDN menjadi baris-baris
    lines = pdn_text.split('\n')
    
    # Hitung digit yang dapat disandikan (angka digit tunggal)
    encodable_digits = 0
    
    # Proses setiap baris
    for line in lines:
        if line and not line.startswith('[') and not line.endswith(']') and not line.startswith('{'):
            # Pisahkan baris untuk mengecualikan notasi jam
            parts = re.split(r'(\{[^}]*\})', line)
            move_line = ""
            for part in parts:
                if not part.startswith('{'):
                    move_line += part
            
            # Sekarang cari gerakan hanya di bagian yang telah dibersihkan
            move_pattern = r'(?<!\S)(\d+)([x-])(\d+)(?!\S)'  # Cocokkan gerakan yang berdiri sendiri dengan batas kata
            matches = re.finditer(move_pattern, move_line)
            
            # Proses setiap gerakan
            for match in matches:
                p1 = match.group(1)  # Angka pertama
                p2 = match.group(3)  # Angka kedua
                
                # Hitung setiap angka digit tunggal
                if len(p1) == 1 and p1 in '123456789':
                    encodable_digits += 1
                
                if len(p2) == 1 and p2 in '123456789':
                    encodable_digits += 1
    
    return encodable_digits

def count_metadata_capacity(pdn_text):
    """
    Menghitung jumlah baris metadata yang dapat digunakan untuk penyandian.
    Setiap baris metadata dapat menyandikan hingga 4 bit (seperti yang didefinisikan dalam fungsi encode_metadata).
    
    Parameter:
        pdn_text: String berisi konten PDN
        
    Mengembalikan:
        Jumlah total bit yang dapat disandikan dalam metadata
    """
    # Pisahkan PDN menjadi baris-baris
    lines = pdn_text.split('\n')
    
    # Hitung baris metadata
    metadata_lines = 0
    for line in lines:
        if line.startswith('[') and line.endswith(']'):
            metadata_lines += 1
    
    # Setiap baris metadata dapat menampung hingga 4 bit
    return metadata_lines * 4

def calculate_max_message_length(pdn_text):
    """
    Menghitung panjang pesan maksimum (dalam karakter) yang dapat disembunyikan dalam PDN
    berdasarkan ketiga metode steganografi:
    1. Karakter tidak terlihat dalam metadata
    2. Angka nol di depan pada gerakan angka digit tunggal
    3. Modifikasi detik notasi jam
    
    Parameter:
        pdn_text: String berisi konten PDN
        
    Mengembalikan:
        Integer yang menunjukkan jumlah maksimum karakter yang dapat disembunyikan dalam PDN
    """
    # Hitung bit dari metadata
    metadata_bit_capacity = count_metadata_capacity(pdn_text)
    
    # Hitung bit dari gerakan yang dapat disandikan
    encodable_digits = count_encodable_moves(pdn_text)
    move_bit_capacity = encodable_digits  # Setiap angka digit tunggal dapat menyandikan 1 bit
    
    # Hitung bit dari notasi jam
    clock_bit_capacity = count_clock_capacity(pdn_text)
    
    # Total kapasitas bit
    total_bit_capacity = metadata_bit_capacity + move_bit_capacity + clock_bit_capacity
    
    # Hitung kapasitas karakter (setiap karakter membutuhkan 8 bit)
    char_capacity = total_bit_capacity // 8
    
    return char_capacity

def get_move_debug_info(pdn_text):
    """
    Mendapatkan informasi debug tentang gerakan dalam PDN.
    Hanya memeriksa angka nol di depan pada angka yang secara alami berdigit tunggal (1-9).
    Fungsi ini berguna untuk debugging dan analisis kapasitas penyandian.
    
    Parameter:
        pdn_text: String berisi konten PDN
        
    Mengembalikan:
        List berisi informasi debug tentang gerakan yang dapat disandikan
    """
    debug_info = []
    
    # Pisahkan PDN menjadi baris-baris
    lines = pdn_text.split('\n')
    
    # Proses setiap baris
    for line_num, line in enumerate(lines):
        if line and not line.startswith('[') and not line.endswith(']') and not line.startswith('{'):
            # Pisahkan baris untuk mengecualikan notasi jam
            parts = re.split(r'(\{[^}]*\})', line)
            move_line = ""
            for part in parts:
                if not part.startswith('{'):
                    move_line += part
            
            # Sekarang cari gerakan hanya di bagian yang telah dibersihkan
            move_pattern = r'(?<!\S)(\d+)([x-])(\d+)(?!\S)'  # Cocokkan gerakan yang berdiri sendiri dengan batas kata
            matches = re.finditer(move_pattern, move_line)
            
            # Proses setiap gerakan
            for match in matches:
                full_move = match.group(0)
                p1 = match.group(1)  # Angka pertama
                separator = match.group(2)  # "-" atau "x"
                p2 = match.group(3)  # Angka kedua
                
                # Inisialisasi nilai default
                bit1 = None
                bit2 = None
                p1_can_have_bit = False
                p2_can_have_bit = False
                  # Angka pertama: jika 01-09, memiliki angka nol di depan (bit 1)
                # Jika 1-9, tidak memiliki angka nol di depan (bit 0)
                # Jika 10+, kita tidak mengekstrak bit apa pun
                if p1.startswith('0') and len(p1) == 2 and p1[1] in '123456789':
                    # Ini adalah angka digit tunggal dengan angka nol di depan (01-09)
                    bit1 = '1'
                    p1_can_have_bit = True
                elif len(p1) == 1 and p1 in '123456789':
                    # Ini adalah angka digit tunggal tanpa angka nol di depan (1-9)
                    bit1 = '0'
                    p1_can_have_bit = True
                
                # Angka kedua: logika yang sama dengan angka pertama
                if p2.startswith('0') and len(p2) == 2 and p2[1] in '123456789':
                    # Ini adalah angka digit tunggal dengan angka nol di depan (01-09)
                    bit2 = '1'
                    p2_can_have_bit = True
                elif len(p2) == 1 and p2 in '123456789':
                    # Ini adalah angka digit tunggal tanpa angka nol di depan (1-9)
                    bit2 = '0'
                    p2_can_have_bit = True
                
                # Buat string bit hanya dengan bit yang bisa kita ekstrak
                bits = ""
                if bit1 is not None:
                    bits += bit1
                if bit2 is not None:
                    bits += bit2
                
                debug_info.append({
                    'line': line_num + 1,
                    'move': full_move,
                    'first_number': p1,
                    'second_number': p2,
                    'first_number_leading_zero': bit1 == '1' if bit1 is not None else None,
                    'second_number_leading_zero': bit2 == '1' if bit2 is not None else None,
                    'first_number_can_encode': p1_can_have_bit,
                    'second_number_can_encode': p2_can_have_bit,
                    'bits': bits
                })
    
    return debug_info

def encode_time_notation(pdn_text, message_bits, start_bit_index=0):
    """
    Menyandikan pesan ke dalam notasi jam PDN dengan memodifikasi nilai detik.
    Untuk bit 1: Ubah detik menjadi angka ganjil (jika belum ganjil)
    Untuk bit 0: Ubah detik menjadi angka genap (jika belum genap)
    
    Juga menambahkan urutan terminator (00000000) di akhir pesan
    dan mengisi notasi jam yang tersisa dengan nilai bit acak
    
    Parameter:
        pdn_text: String berisi konten PDN
        message_bits: List berisi bit-bit pesan biner ('0' dan '1')
        start_bit_index: Indeks awal di message_bits untuk memulai penyandian
        
    Mengembalikan: 
        Tuple (pdn_text yang dimodifikasi, jumlah bit yang disandikan, indeks bit terakhir)
    """
    import re
    import random
    
    bit_index = start_bit_index
    total_clocks_modified = 0
    
    # Tambahkan urutan terminator (8 nol) ke bit pesan
    # Tapi jangan memodifikasi daftar message_bits asli, buat yang baru
    message_bits_with_terminator = message_bits.copy()
    if bit_index < len(message_bits_with_terminator):
        message_bits_with_terminator.extend(['0'] * 8)
    
    # Ekspresi reguler untuk notasi jam {[%clock w0:14:00 B0:14:00]}
    # Regex ini menangkap indikator pemain pertama (w/b), jam pertama, dan indikator pemain kedua (w/b) serta jam kedua jika ada
    clock_pattern = r'\{\[%clock\s+([wWbB])(\d{1,2}):(\d{1,2}):(\d{1,2})(?:\s+([wWbB])(\d{1,2}):(\d{1,2}):(\d{1,2}))?\]\}'
    
    # PDN yang dimodifikasi akan dibangun dengan mengganti notasi jam
    modified_pdn = ""
    last_end = 0
    
    # Find all clock notations
    for match in re.finditer(clock_pattern, pdn_text):
        # Add text before this clock notation
        modified_pdn += pdn_text[last_end:match.start()]
        
        # Extract groups for first player
        player1 = match.group(1)
        hours1 = match.group(2)
        minutes1 = match.group(3)
        seconds1 = match.group(4)
        
        # Parse seconds as integer
        seconds1_int = int(seconds1)
        
        # Determine if there's a second player notation
        has_player2 = match.group(5) is not None
        
        # Extract groups for second player if present
        player2 = match.group(5) if has_player2 else ""
        hours2 = match.group(6) if has_player2 else ""
        minutes2 = match.group(7) if has_player2 else ""
        seconds2 = match.group(8) if has_player2 else ""
        
        # Only modify the seconds of first player based on the bit to encode
        modified_seconds1 = seconds1_int
          # Inizialize modified seconds for both players
        modified_seconds1 = seconds1_int
        modified_seconds2 = int(seconds2) if has_player2 else 0
        
        # Flag to track if we encoded any bits in this clock notation
        bits_encoded_in_this_clock = 0
        
        # Encode first bit (player 1) if we still have bits to encode
        if bit_index < len(message_bits_with_terminator):
            current_bit = message_bits_with_terminator[bit_index]
            
            # For bit 1, make seconds odd
            if current_bit == '1':
                if seconds1_int % 2 == 0:  # If even, make it odd
                    modified_seconds1 = seconds1_int + 1
                    if modified_seconds1 > 59:
                        modified_seconds1 = seconds1_int - 1  # Ensure we don't exceed 59
                # If already odd, keep it
            
            # For bit 0, make seconds even
            else:  # current_bit == '0'
                if seconds1_int % 2 == 1:  # If odd, make it even
                    modified_seconds1 = seconds1_int + 1
                    if modified_seconds1 > 59:
                        modified_seconds1 = seconds1_int - 1  # Ensure we don't exceed 59
                # If already even, keep it
                
            bit_index += 1
            bits_encoded_in_this_clock += 1
            total_clocks_modified += 1
            print(f"  Encoded bit {current_bit} in player 1: Modified seconds {seconds1_int} -> {modified_seconds1}")
        else:
            # If we've already encoded all bits, apply random changes to hide message end
            if random.random() < 0.5:  # 50% chance to modify
                # Randomize to odd or even
                if random.random() < 0.5:  # Make even
                    if seconds1_int % 2 == 1:  # If odd, make it even
                        modified_seconds1 = seconds1_int + 1
                        if modified_seconds1 > 59:
                            modified_seconds1 = seconds1_int - 1
                else:  # Make odd
                    if seconds1_int % 2 == 0:  # If even, make it odd
                        modified_seconds1 = seconds1_int + 1
                        if modified_seconds1 > 59:
                            modified_seconds1 = seconds1_int - 1
                
                print(f"  Added noise to player 1: Modified seconds {seconds1_int} -> {modified_seconds1}")
        
        # Encode second bit (player 2) if available and we still have bits to encode
        if has_player2 and bit_index < len(message_bits_with_terminator):
            current_bit = message_bits_with_terminator[bit_index]
            seconds2_int = int(seconds2)
            
            # For bit 1, make seconds odd
            if current_bit == '1':
                if seconds2_int % 2 == 0:  # If even, make it odd
                    modified_seconds2 = seconds2_int + 1
                    if modified_seconds2 > 59:
                        modified_seconds2 = seconds2_int - 1  # Ensure we don't exceed 59
                else:
                    modified_seconds2 = seconds2_int  # Already odd, keep it
            
            # For bit 0, make seconds even
            else:  # current_bit == '0'
                if seconds2_int % 2 == 1:  # If odd, make it even
                    modified_seconds2 = seconds2_int + 1
                    if modified_seconds2 > 59:
                        modified_seconds2 = seconds2_int - 1  # Ensure we don't exceed 59
                else:
                    modified_seconds2 = seconds2_int  # Already even, keep it
                
            bit_index += 1
            bits_encoded_in_this_clock += 1
            total_clocks_modified += 1
            print(f"  Encoded bit {current_bit} in player 2: Modified seconds {seconds2_int} -> {modified_seconds2}")
        elif has_player2:
            # If we've already encoded all bits, apply random changes to hide message end
            seconds2_int = int(seconds2)
            if random.random() < 0.5:  # 50% chance to modify
                # Randomize to odd or even
                if random.random() < 0.5:  # Make even
                    if seconds2_int % 2 == 1:  # If odd, make it even
                        modified_seconds2 = seconds2_int + 1
                        if modified_seconds2 > 59:
                            modified_seconds2 = seconds2_int - 1
                else:  # Make odd
                    if seconds2_int % 2 == 0:  # If even, make it odd
                        modified_seconds2 = seconds2_int + 1
                        if modified_seconds2 > 59:
                            modified_seconds2 = seconds2_int - 1
                
                print(f"  Added noise to player 2: Modified seconds {seconds2_int} -> {modified_seconds2}")
            else:
                modified_seconds2 = seconds2_int
        
        # Format seconds with leading zeros if needed
        formatted_seconds1 = f"{modified_seconds1:02d}"
        formatted_seconds2 = f"{modified_seconds2:02d}" if has_player2 else ""
        
        # Reconstruct the clock notation with proper escaping of curly braces
        if has_player2:
            # Preserve the full format with both players
            modified_clock = f"{{[%clock {player1}{hours1}:{minutes1}:{formatted_seconds1} {player2}{hours2}:{minutes2}:{formatted_seconds2}]}}"
        else:
            # Only one player in the original notation
            modified_clock = f"{{[%clock {player1}{hours1}:{minutes1}:{formatted_seconds1}]}}"
        
        # Add the modified clock notation
        modified_pdn += modified_clock
        last_end = match.end()
    
    # Add remaining text after last clock notation
    modified_pdn += pdn_text[last_end:]
    
    # Calculate how many bits from the original message were encoded (excluding terminator)
    original_bits_encoded = min(bit_index - start_bit_index, len(message_bits) - start_bit_index)
    
    print(f"Time notation encoding completed: {total_clocks_modified} clock notations modified, used {bit_index - start_bit_index} bits")
    return modified_pdn, original_bits_encoded, bit_index

def decode_time_notation(pdn_text):
    """
    Mendekode pesan dari notasi jam dalam PDN dengan memeriksa paritas detik.
    Detik ganjil = bit 1, Detik genap = bit 0
    Berhenti mendekode ketika menemukan sekuens terminator (8 nol berturut-turut)
    
    Mengembalikan: string biner dari bit yang didekode
    """
    import re
    
    binary_message = ""
    # Regular expression for clock notations {[%clock w0:14:00 B0:14:00]}
    # This regex matches the PDN clock notation format
    clock_pattern = r'\{\[%clock\s+([wWbB])(\d{1,2}):(\d{1,2}):(\d{1,2})(?:\s+([wWbB])(\d{1,2}):(\d{1,2}):(\d{1,2}))?\]\}'
    
    # Counter for terminator sequence
    zero_count = 0
    terminator_found = False
    
    # Find all clock notations
    for match_idx, match in enumerate(re.finditer(clock_pattern, pdn_text)):
        # Stop if we've found the terminator sequence
        if terminator_found:
            break
            
        # Extract seconds for player 1
        seconds1 = match.group(4)
        seconds1_int = int(seconds1)
        
        # Check parity of seconds for player 1
        if seconds1_int % 2 == 1:  # Odd = bit 1
            binary_message += '1'
            zero_count = 0  # Reset zero counter
            print(f"Clock {match_idx} Player 1: Extracted bit '1' from seconds {seconds1_int} (odd)")
        else:  # Even = bit 0
            binary_message += '0'
            zero_count += 1  # Increment zero counter
            print(f"Clock {match_idx} Player 1: Extracted bit '0' from seconds {seconds1_int} (even)")
            
            # Check if this completes the terminator sequence
            if zero_count >= 8:
                terminator_found = True
                # Remove the terminator from the message
                binary_message = binary_message[:-8]
                print(f"Found terminator sequence after {match_idx - 7} clocks")
                break
        
        # Extract seconds for player 2 if available
        if match.group(5) is not None:  # Check if player 2 exists in this notation
            seconds2 = match.group(8)
            seconds2_int = int(seconds2)
            
            # Don't extract more bits if we already found the terminator
            if terminator_found:
                break
                
            # Check parity of seconds for player 2
            if seconds2_int % 2 == 1:  # Odd = bit 1
                binary_message += '1'
                zero_count = 0  # Reset zero counter
                print(f"Clock {match_idx} Player 2: Extracted bit '1' from seconds {seconds2_int} (odd)")
            else:  # Even = bit 0
                binary_message += '0'
                zero_count += 1  # Increment zero counter
                print(f"Clock {match_idx} Player 2: Extracted bit '0' from seconds {seconds2_int} (even)")
                
                # Check if this completes the terminator sequence
                if zero_count >= 8:
                    terminator_found = True
                    # Remove the terminator from the message
                    binary_message = binary_message[:-8]
                    print(f"Found terminator sequence after player 2 of clock {match_idx}")
    
    # If no terminator was found, return all bits (useful for testing)
    if not terminator_found and binary_message:
        print(f"Warning: No terminator sequence found. Returning all {len(binary_message)} extracted bits.")
    
    return binary_message

def count_clock_capacity(pdn_text):
    """
    Menghitung jumlah notasi jam yang dapat digunakan untuk penyandian.
    Setiap notasi jam dapat menyandikan hingga 2 bit - satu untuk nilai detik masing-masing pemain.
    
    Parameter:
        pdn_text: String berisi konten PDN
        
    Mengembalikan:
        Integer yang menunjukkan jumlah total bit yang dapat disandikan dalam notasi jam
    """
    import re
    
    # Regular expression for clock notations - matches {[%clock w0:14:00 B0:14:00]}
    clock_pattern = r'\{\[%clock\s+([wWbB])(\d{1,2}):(\d{1,2}):(\d{1,2})(?:\s+([wWbB])(\d{1,2}):(\d{1,2}):(\d{1,2}))?\]\}'
    
    # Count clock notations and how many players in each
    total_bits = 0
    
    for match in re.finditer(clock_pattern, pdn_text):
        # Each notation always has player 1
        total_bits += 1
        
        # Check if player 2 exists in this notation
        if match.group(5) is not None:
            total_bits += 1
    
    return total_bits

@app.route('/')
def index():
    """
    Endpoint untuk halaman utama aplikasi.
    Menampilkan antarmuka pengguna utama untuk steganografi PDN.
    
    Mengembalikan:
        Halaman HTML index.html yang telah dirender
    """
    return render_template('index.html')

@app.route('/upload_pdn', methods=['POST'])
def upload_pdn():
    """
    Endpoint untuk mengunggah file PDN.
    Menerima file PDN dari pengguna, menyimpannya sementara, dan menghitung kapasitas penyandian maksimum.
    
    Mengembalikan:
        JSON berisi informasi kapasitas penyandian dan hasil analisis PDN
    """
    if 'pdn_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['pdn_file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and file.filename and isinstance(file.filename, str) and file.filename.lower().endswith('.pdn'):
        try:
            # Save the file temporarily
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                pdn_content = f.read()
            
            # Calculate max message length
            max_chars = calculate_max_message_length(pdn_content)
            
            # Clean up
            os.remove(file_path)
            
            return jsonify({
                'pdn_content': pdn_content,
                'max_message_length': max_chars
            })
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    return jsonify({'error': 'File must be a PDN file'}), 400

@app.route('/get_max_length', methods=['POST'])
def get_max_length():
    """
    Endpoint untuk mendapatkan panjang maksimum pesan yang dapat disandikan dalam PDN.
    Menerima teks PDN melalui permintaan JSON dan menghitung kapasitas maksimum.
    
    Mengembalikan:
        JSON berisi panjang maksimum pesan (dalam karakter) yang dapat disandikan
    """
    data = request.get_json()
    pdn_text = data.get('pdn', '')
    
    # Calculate max message length
    max_chars = calculate_max_message_length(pdn_text)
    
    return jsonify({
        'max_message_length': max_chars
    })

@app.route('/encode', methods=['POST'])
def encode():
    """
    Endpoint untuk menyandikan pesan dalam file PDN.
    Menerima teks PDN dan pesan melalui permintaan JSON, kemudian menyandikan pesan
    ke dalam PDN menggunakan tiga metode steganografi yang berbeda.
    
    Mengembalikan:
        JSON berisi PDN yang telah dimodifikasi dengan pesan tersembunyi
    """
    data = request.get_json()
    pdn_text = data.get('pdn', '')
    message = data.get('message', '')
    
    print(f"\n--- ENCODE REQUEST ---")
    print(f"Message: {message}")
      # Convert message to binary
    binary_message = ''.join(format(ord(char), '08b') for char in message)
    print(f"Binary message: {binary_message}")
      # Calculate total bit capacity
    metadata_bit_capacity = count_metadata_capacity(pdn_text)
    move_bit_capacity = count_encodable_moves(pdn_text)
    clock_bit_capacity = count_clock_capacity(pdn_text)
    total_bit_capacity = metadata_bit_capacity + move_bit_capacity + clock_bit_capacity
    max_chars = total_bit_capacity // 8  # Each character requires 8 bits
    
    print(f"Metadata capacity: {metadata_bit_capacity} bits, Move capacity: {move_bit_capacity} bits, Clock capacity: {clock_bit_capacity} bits")
    print(f"Total bit capacity: {total_bit_capacity} bits, Char capacity: {max_chars}")
    
    # Check if PDN has enough capacity to encode the message
    if len(binary_message) > total_bit_capacity:
        print(f"ERROR: Message too long. Requires {len(binary_message)} bits, but only have {total_bit_capacity} bits capacity.")
        return jsonify({
            'error': f'Message too long. The PDN has only {total_bit_capacity} bits capacity, but your message requires {len(binary_message)} bits to encode.',
            'binary_message': binary_message,
            'max_message_length': max_chars
        }), 400
    
    # Encode the message into the PDN
    encoded_pdn = encode_pdn(pdn_text, binary_message)
    
    # Print a sample of the original and encoded PDN for comparison
    print("\n--- COMPARING ORIGINAL vs ENCODED ---")
    orig_lines = pdn_text.split('\n')
    encoded_lines = encoded_pdn.split('\n')
    
    # Find a few lines with actual moves (not headers/metadata)
    shown_samples = 0
    for i in range(min(len(orig_lines), len(encoded_lines))):
        if (i < len(orig_lines) and i < len(encoded_lines) and 
            orig_lines[i] and not orig_lines[i].startswith('[') and 
            not orig_lines[i].startswith('{')):
            print(f"Original line {i}: {orig_lines[i]}")
            print(f"Encoded line {i}: {encoded_lines[i]}")
            print("---")
            shown_samples += 1
            if shown_samples >= 5:  # Show only first 5 examples
                break
    
    print(f"Encoding complete. Message bits: {len(binary_message)}, Original PDN length: {len(pdn_text)}, Encoded PDN length: {len(encoded_pdn)}")
    
    # Check if any moves were modified
    if pdn_text == encoded_pdn:
        print("WARNING: Original and encoded PDN are identical. No changes were made!")
    
    return jsonify({
        'encoded_pdn': encoded_pdn,
        'binary_message': binary_message,
        'max_message_length': max_chars
    })

@app.route('/decode', methods=['POST'])
def decode():
    """
    Endpoint untuk mendekode pesan tersembunyi dari file PDN.
    Menerima teks PDN melalui permintaan JSON, kemudian mendekode pesan tersembunyi
    menggunakan tiga metode deteksi steganografi yang berbeda.
    
    Mengembalikan:
        JSON berisi pesan yang berhasil didekode dan informasi debug
    """
    data = request.get_json()
    pdn_text = data.get('pdn', '')
    
    print(f"\n--- DECODE REQUEST ---")
    
    # Decode the message from the PDN
    binary_message = decode_pdn(pdn_text)
    print(f"Extracted binary message: {binary_message}")
    
    # Get debug info to see what moves were detected
    debug_info = get_move_debug_info(pdn_text)
    
    # Print some debug info samples
    print("\n--- MOVE ANALYSIS ---")
    for i, move_debug in enumerate(debug_info[:10]):  # Show first 10 moves
        print(f"Move: {move_debug['move']}, Bits: {move_debug['bits']}")
    
    # Convert binary back to text
    decoded_message = ''
    for i in range(0, len(binary_message), 8):
        if i + 8 <= len(binary_message):
            byte = binary_message[i:i+8]
            try:
                # Skip null bytes (all zeros)
                if byte != '00000000':
                    char = chr(int(byte, 2))
                    decoded_message += char
                    print(f"Byte: {byte}, Char: {char}")
            except ValueError as e:
                print(f"Error decoding byte {byte}: {str(e)}")
                # Skip invalid binary sequences
                pass
    
    return jsonify({
        'binary_message': binary_message,
        'decoded_message': decoded_message,
        'debug_info': debug_info
    })

if __name__ == '__main__':
    app.run(debug=True)
