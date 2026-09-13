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

if __name__ == '__main__':
    app.run(debug=True)

# 4. Route untuk Halaman Formulir Pemesanan (DFD 3.1)
@app.route('/pesan')
def pesan():
    return render_template('pesan.html')

# 5. Route untuk Logika Kalkulasi Harga (DFD 3.2)
@app.route('/kalkulasi', methods=['POST'])
def kalkulasi():
    if request.method == 'POST':
        # Menangkap data dari formulir HTML
        kertas = request.form['kertas']
        warna = request.form['warna']
        jilid = request.form['jilid']
        jumlah = int(request.form['jumlah'])
        
        # Menangkap nama file yang diunggah
        dokumen = request.files['dokumen']
        nama_file = dokumen.filename if dokumen else "Tidak ada file"

        # Simulasi penarikan harga dari database (D4 Tarif_Layanan)
        harga_kertas = 200 if kertas == 'A4' else (300 if kertas == 'F4' else 500)
        harga_warna = 300 if warna == 'Hitam Putih' else 1000
        
        if jilid == 'Tanpa Jilid':
            harga_jilid = 0
        elif jilid == 'Lakban':
            harga_jilid = 3000
        else: # Spiral
            harga_jilid = 15000

        # Rumus Kalkulasi sesuai Spesifikasi Proses di dokumen laporan
        harga_satuan = harga_kertas + harga_warna
        subtotal_cetak = harga_satuan * jumlah
        total_harga = subtotal_cetak + harga_jilid

        # Menampilkan halaman ringkasan secara langsung
        return f"""
        <div style="font-family: Tahoma, sans-serif; max-width: 500px; margin: 50px auto; padding: 20px; border: 1px solid #ccc; border-radius: 10px; background-color: #f9f9f9;">
            <h2 style="color: #333; text-align: center;">Rincian Pesanan</h2>
            <p><strong>Nama File:</strong> {nama_file}</p>
            <p><strong>Spesifikasi:</strong> Kertas {kertas}, {warna}, Jilid {jilid}</p>
            <p><strong>Jumlah:</strong> {jumlah} Rangkap</p>
            <hr>
            <h3 style="color: #28a745;">Total Biaya: Rp {total_harga}</h3>
            <button style="width: 100%; padding: 10px; background-color: #28a745; color: white; border: none; font-weight: bold; border-radius: 5px; cursor: pointer;">Simpan ke Database (D3)</button>
            <br><br>
            <a href="/pesan" style="display: block; text-align: center; color: #007bff; text-decoration: none;">⬅ Kembali ke Formulir</a>
        </div>
        """