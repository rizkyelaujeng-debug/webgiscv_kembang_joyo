import os
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from db_config import get_db_connection

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_kembar_joyo' 

# Konfigurasi Folder untuk menyimpan file fisik
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Otomatis membuat folder jika belum ada

# 1. Route untuk Halaman Peta
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

# 2. Route untuk Fitur Registrasi
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nama = request.form['nama_lengkap']
        nohp = request.form['no_hp']
        sandi = request.form['password']
        sandi_enkripsi = generate_password_hash(sandi)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO pelanggan (nama_lengkap, no_hp, password) VALUES (%s, %s, %s)", 
                           (nama, nohp, sandi_enkripsi))
            conn.commit()
            return redirect(url_for('login'))
        except Exception as e:
            return f"Terjadi kesalahan database: {e}"
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')

# 3. Route untuk Fitur Login
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
        
        if user and check_password_hash(user['password'], sandi_input):
            # Memunculkan Pop-Up sukses ala Windows XP
            return f"""
            <!DOCTYPE html>
            <html lang="id">
            <head>
                <link rel="stylesheet" href="https://unpkg.com/xp.css">
                <style>body {{ background-color: #004e98; background-image: url('https://archive.org/download/bliss-600dpi/bliss-600dpi.jpg'); background-size: cover; font-family: Tahoma; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}</style>
            </head>
            <body>
                <div class="window" style="width: 320px;">
                    <div class="title-bar">
                        <div class="title-bar-text">Informasi Sistem</div>
                        <div class="title-bar-controls"><button aria-label="Close"></button></div>
                    </div>
                    <div class="window-body" style="text-align: center; padding: 15px;">
                        <span style="font-size: 32px; display: block; margin-bottom: 10px;">🎉</span>
                        <p>Login Berhasil!<br>Selamat datang, <b>{user['nama_lengkap']}</b>.</p>
                        <br>
                        <a href="/pesan"><button style="width: 80px;">OK</button></a>
                    </div>
                </div>
            </body>
            </html>
            """
        else:
            return "<script>alert('Gagal! Nomor HP atau Kata Sandi salah.'); window.history.back();</script>"
    return render_template('login.html')

# 4. Route untuk Halaman Formulir Pemesanan
@app.route('/pesan')
def pesan():
    return render_template('pesan.html')

# 5. Route untuk Logika Kalkulasi Harga & Simpan Dokumen Sementara
@app.route('/kalkulasi', methods=['POST'])
def kalkulasi():
    if request.method == 'POST':
        kertas = request.form['kertas']
        warna = request.form['warna']
        jilid = request.form['jilid']
        jumlah = int(request.form['jumlah'])
        penerimaan = request.form['penerimaan']
        
        # Menangkap input catatan dari pelanggan
        catatan = request.form.get('catatan', '') 
        
        # PROSES PENYIMPANAN FISIK FILE DOKUMEN
        dokumen = request.files.get('dokumen')
        if dokumen and dokumen.filename != '':
            nama_file = secure_filename(dokumen.filename)
            dokumen.save(os.path.join(app.config['UPLOAD_FOLDER'], nama_file))
        else:
            nama_file = "Tidak ada file"

        # Tarif Dasar
        harga_kertas = 200 if kertas == 'A4' else (300 if kertas == 'F4' else 500)
        harga_warna = 300 if warna == 'Hitam Putih' else 1000
        harga_jilid = 0 if jilid == 'Tanpa Jilid' else (3000 if jilid == 'Lakban' else 15000)
        ongkir = 5000 if penerimaan == 'Diantar ke Alamat' else 0

        # Rumus Kalkulasi
        harga_satuan = harga_kertas + harga_warna
        subtotal_cetak = harga_satuan * jumlah
        total_harga = subtotal_cetak + harga_jilid + ongkir
        
        # Menggabungkan spesifikasi utama dengan catatan (jika ada)
        spesifikasi_lengkap = f"Kertas {kertas}, {warna}, Jilid {jilid} ({jumlah} Rangkap)"
        if catatan.strip() != "":
            spesifikasi_lengkap += f" | Catatan: {catatan}"

        # Halaman Checkout
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

# 6. Route untuk Simpan Bukti Bayar & Database
@app.route('/simpan_pesanan', methods=['POST'])
def simpan_pesanan():
    if request.method == 'POST':
        nama_file = request.form['nama_file']
        spesifikasi = request.form['spesifikasi']
        penerimaan = request.form['penerimaan']
        total_harga = request.form['total_harga']
        
        # PROSES PENYIMPANAN FISIK GAMBAR BUKTI TRANSFER
        bukti_bayar = request.files.get('bukti_bayar')
        if bukti_bayar and bukti_bayar.filename != '':
            nama_bukti = secure_filename(bukti_bayar.filename)
            bukti_bayar.save(os.path.join(app.config['UPLOAD_FOLDER'], nama_bukti))
        else:
            nama_bukti = "Tidak ada bukti"
        
        id_pelanggan = 1 
        status = "Menunggu Diproses"
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            query = """
            INSERT INTO pesanan (id_pelanggan, nama_file, spesifikasi, metode_penerimaan, bukti_bayar, total_harga, status_pesanan, tanggal_pesan) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(query, (id_pelanggan, nama_file, spesifikasi, penerimaan, nama_bukti, total_harga, status))
            conn.commit()
            
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

# 7. Route Dashboard Admin (Tema Windows XP)
@app.route('/admin')
def admin():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pesanan ORDER BY id_pesanan DESC")
        data_pesanan = cursor.fetchall()
        return render_template('admin.html', pesanan=data_pesanan)
    except Exception as e:
        return f"Error: {e}"
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

# 8. Route Update Status Pesanan
@app.route('/update_status/<int:id_pesanan>', methods=['POST'])
def update_status(id_pesanan):
    status_baru = request.form['status_baru']
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE pesanan SET status_pesanan = %s WHERE id_pesanan = %s", (status_baru, id_pesanan))
        conn.commit()
        return redirect(url_for('admin'))
    except Exception as e:
        return f"Gagal update status: {e}"
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

if __name__ == '__main__':
    app.run(debug=True)