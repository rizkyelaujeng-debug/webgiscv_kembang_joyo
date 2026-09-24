from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from db_config import get_db_connection

app = Flask(__name__)
# Kunci rahasia ini dibutuhkan agar kita bisa membuat sesi (session) login ke depannya
app.secret_key = 'kunci_rahasia_kembar_joyo' 

# 1. Route untuk Halaman Peta (Tetap sama)
@app.route('/')
def index():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lokasi_fotocopy")
        data_lokasi = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('index.html', lokasi=data_lokasi)
    except Exception as e:
        return f"<h1>Koneksi atau Pengambilan Data Gagal. Error: {e}</h1>"

# 2. Route untuk Fitur Registrasi (Baru)
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Jika tombol "Daftar" ditekan
    if request.method == 'POST':
        nama = request.form['nama_lengkap']
        nohp = request.form['no_hp']
        sandi = request.form['password']
        
        # Enkripsi password sesuai spesifikasi tugas RPL
        sandi_enkripsi = generate_password_hash(sandi)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Simpan ke tabel pelanggan
            cursor.execute("INSERT INTO pelanggan (nama_lengkap, no_hp, password) VALUES (%s, %s, %s)", 
                           (nama, nohp, sandi_enkripsi))
            conn.commit()
            return redirect(url_for('login')) # Setelah sukses, arahkan langsung ke halaman login
        except Exception as e:
            return f"Terjadi kesalahan database: {e}"
        finally:
            cursor.close()
            conn.close()
            
    # Jika hanya membuka halamannya saja
    return render_template('register.html')

# 3. Route untuk Fitur Login (Diperbarui)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nohp = request.form['no_hp']
        sandi_input = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pelanggan WHERE no_hp = %s", (nohp,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        # Cek apakah nomor HP ada dan password input cocok dengan password di database
        if user and check_password_hash(user['password'], sandi_input):
            return f"<h1>Login Berhasil! Selamat datang, {user['nama_lengkap']}! 🎉</h1>"
        else:
            return "<h1>Gagal! Nomor HP atau Kata Sandi salah. Silakan kembali.</h1>"
            
    return render_template('login.html')

# 4. Route untuk Halaman Formulir Pemesanan (DFD 3.1)
@app.route('/pesan')
def pesan():
    return render_template('pesan.html')

# 5. Route untuk Logika Kalkulasi Harga (DFD 3.2)
@app.route('/kalkulasi', methods=['POST'])
def kalkulasi():
    if request.method == 'POST':
        kertas = request.form['kertas']
        warna = request.form['warna']
        jilid = request.form['jilid']
        jumlah = int(request.form['jumlah'])
        penerimaan = request.form['penerimaan']
        
        dokumen = request.files['dokumen']
        nama_file = dokumen.filename if dokumen else "Tidak ada file"

        # Tarif Dasar
        harga_kertas = 200 if kertas == 'A4' else (300 if kertas == 'F4' else 500)
        harga_warna = 300 if warna == 'Hitam Putih' else 1000
        
        if jilid == 'Tanpa Jilid':
            harga_jilid = 0
        elif jilid == 'Lakban':
            harga_jilid = 3000
        else:
            harga_jilid = 15000

        # Ongkos kirim jika pilih diantar
        ongkir = 5000 if penerimaan == 'Diantar ke Alamat' else 0

        # Rumus Kalkulasi
        harga_satuan = harga_kertas + harga_warna
        subtotal_cetak = harga_satuan * jumlah
        total_harga = subtotal_cetak + harga_jilid + ongkir
        
        # Gabungkan spesifikasi untuk disimpan ke database
        spesifikasi_lengkap = f"Kertas {kertas}, {warna}, Jilid {jilid} ({jumlah} Rangkap)"

        # Halaman Checkout dengan QRIS
        return f"""
        <div style="font-family: Tahoma, sans-serif; max-width: 500px; margin: 50px auto; padding: 20px; border: 1px solid #ccc; border-radius: 10px; background-color: #f9f9f9;">
            <h2 style="color: #333; text-align: center;">Rincian Pesanan & Pembayaran</h2>
            <p><strong>Nama File:</strong> {nama_file}</p>
            <p><strong>Spesifikasi:</strong> {spesifikasi_lengkap}</p>
            <p><strong>Penerimaan:</strong> {penerimaan}</p>
            <hr>
            <h3 style="color: #28a745; text-align: center;">Total Biaya: Rp {total_harga:,}</h3>
            
            <div style="text-align: center; background-color: #e9ecef; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0 0 10px 0; font-weight: bold; color: #d9534f;">Wajib Bayar via QRIS</p>
                <img src="https://upload.wikimedia.org/wikipedia/commons/d/d0/QR_code_for_mobile_English_Wikipedia.svg" alt="QRIS" style="width: 150px; margin-bottom: 10px;">
                <p style="font-size: 13px; color: #555;">Silakan *scan* menggunakan M-Banking atau E-Wallet sebesar <b>Rp {total_harga:,}</b></p>
            </div>

            <form action="/simpan_pesanan" method="POST" enctype="multipart/form-data">
                <!-- Input tersembunyi (hidden) untuk mengirim data rincian ke route simpan_pesanan -->
                <input type="hidden" name="nama_file" value="{nama_file}">
                <input type="hidden" name="spesifikasi" value="{spesifikasi_lengkap}">
                <input type="hidden" name="penerimaan" value="{penerimaan}">
                <input type="hidden" name="total_harga" value="{total_harga}">
                
                <label style="font-weight: bold; display: block; margin-bottom: 5px;">Unggah Bukti Transfer (JPG/PNG):</label>
                <input type="file" name="bukti_bayar" accept="image/png, image/jpeg" required style="width: 100%; padding: 8px; margin-bottom: 15px; box-sizing: border-box;">
                
                <button type="submit" style="width: 100%; padding: 12px; background-color: #28a745; color: white; border: none; font-weight: bold; border-radius: 5px; cursor: pointer;">Selesaikan Pesanan ➡</button>
            </form>
            
            <br>
            <a href="/pesan" style="display: block; text-align: center; color: #007bff; text-decoration: none;">⬅ Batal / Edit Pesanan</a>
        </div>
        """

# 6. Route untuk Menyimpan Pesanan (DFD 3.3)
@app.route('/simpan_pesanan', methods=['POST'])
def simpan_pesanan():
    if request.method == 'POST':
        nama_file = request.form['nama_file']
        spesifikasi = request.form['spesifikasi']
        penerimaan = request.form['penerimaan']
        total_harga = request.form['total_harga']
        
        # Menangkap file bukti transfer
        bukti_bayar = request.files['bukti_bayar']
        nama_bukti = bukti_bayar.filename if bukti_bayar else "Tidak ada bukti"
        
        # Simulasi ID Pelanggan = 1 (Karena kita belum menyambungkan session login)
        id_pelanggan = 1 
        status = "Menunggu Diproses"
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Memasukkan seluruh data ke dalam database MySQL (Tabel: pesanan)
            query = """
            INSERT INTO pesanan (id_pelanggan, nama_file, spesifikasi, metode_penerimaan, bukti_bayar, total_harga, status_pesanan, tanggal_pesan) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(query, (id_pelanggan, nama_file, spesifikasi, penerimaan, nama_bukti, total_harga, status))
            conn.commit()
            
            # Tampilkan pesan sukses
            return f"""
            <div style="font-family: Tahoma, sans-serif; max-width: 500px; margin: 50px auto; text-align: center; padding: 30px; border: 1px solid #ccc; border-radius: 10px; background-color: #d4edda;">
                <h1 style="color: #155724;">✅ Pesanan Berhasil Dibuat!</h1>
                <p style="color: #155724; font-size: 16px;">Terima kasih. Pesanan dokumen <b>{nama_file}</b> Anda telah masuk ke sistem dan sedang menunggu konfirmasi admin.</p>
                <a href="/" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">⬅ Kembali ke Halaman Utama</a>
            </div>
            """
        except Exception as e:
            return f"<h1>Terjadi kesalahan database: {e}</h1>"
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'conn' in locals(): conn.close()

if __name__ == '__main__':
    app.run(debug=True)