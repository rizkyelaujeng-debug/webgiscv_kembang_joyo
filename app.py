import re

def hitung_halaman_pdf(file_path):
    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        return len(reader.pages)
    except Exception:
        pass
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        counts = re.findall(rb'/Count\s+(\d+)', data)
        if counts:
            return int(counts[0])
        pages = re.findall(rb'/Type\s*/Page[^s]', data)
        if pages:
            return len(pages)
    except Exception:
        pass
    return 1

import os
from urllib.parse import quote
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from db_config import get_db_connection

app = Flask(__name__)
# Kunci rahasia ini sekarang sangat berguna untuk mengamankan Session!
app.secret_key = 'kunci_rahasia_kembar_joyo' 

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    # Jika belum login, arahkan ke halaman login
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_lokasi, nama_tempat, alamat, latitude, longitude, foto_tempat, jam_buka, layanan FROM lokasi_fotocopy")
        data_lokasi = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('index.html', lokasi=data_lokasi)
    except Exception as e:
        return f"<h1>Koneksi gagal: {e}</h1>"

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
            # 1. BUAT SESSION: Simpan ID pelanggan ke dalam memori browser
            session['user_id'] = user['id_pelanggan']
            session['nama_lengkap'] = user['nama_lengkap']
            
            return render_template('login_sukses.html', nama=user['nama_lengkap'])
        else:
            return render_template('login.html', error='Nomor HP atau Kata Sandi salah.')
            
    return render_template('login.html')

# ROUTE BARU: Untuk Logout (Menghapus Session)
@app.route('/logout')
def logout():
    session.clear() # Hapus semua ingatan login
    return redirect(url_for('login'))

@app.route('/pesan')
def pesan():
    # 2. CEK SESSION: Jika belum login, tendang ke halaman login!
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    return render_template('pesan.html')

@app.route('/kalkulasi', methods=['POST'])
def kalkulasi():
    # CEK SESSION JUGA DI SINI
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        kertas = request.form['kertas']
        warna = request.form['warna']
        jilid = request.form['jilid']
        jumlah = int(request.form['jumlah'])
        penerimaan = request.form['penerimaan']
        catatan = request.form.get('catatan', '') 
        warna_jilid = request.form.get('warna_jilid', '').strip()
        alamat_tujuan = request.form.get('alamat_tujuan', '').strip()
        
        dokumen = request.files.get('dokumen')
        if dokumen and dokumen.filename != '':
            nama_file = secure_filename(dokumen.filename)
            dokumen.save(os.path.join(app.config['UPLOAD_FOLDER'], nama_file))
        else:
            nama_file = "Tidak ada file"

        # Harga cetak per halaman: HP=500, Berwarna=1000
        harga_per_halaman = 500 if warna == 'Hitam Putih' else 1000
        harga_jilid = 0 if jilid == 'Tanpa Jilid' else (7000 if jilid == 'Lakban' else 15000)
        ongkir = 10000 if penerimaan == 'Diantar ke Alamat' else 0

        # Ambil input jumlah halaman manual jika diisi
        input_halaman = request.form.get('jumlah_halaman', '').strip()
        jumlah_halaman = 0
        if input_halaman.isdigit():
            jumlah_halaman = int(input_halaman)

        # Jika pengguna tidak isi atau 0, deteksi otomatis dari file PDF
        if jumlah_halaman <= 0 and dokumen and nama_file.lower().endswith('.pdf'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], nama_file)
            jumlah_halaman = hitung_halaman_pdf(file_path)

        if jumlah_halaman <= 0:
            jumlah_halaman = 1

        # Hitung biaya cetak: harga/hal * jumlah halaman * jumlah rangkap
        subtotal_cetak = harga_per_halaman * jumlah_halaman * jumlah
        total_jilid = harga_jilid * jumlah
        total_harga = subtotal_cetak + total_jilid + ongkir
        
        spesifikasi_lengkap = f"Kertas {kertas}, {warna}, {jumlah_halaman} Halaman, Jilid {jilid}"
        if jilid == "Lakban" and warna_jilid:
            spesifikasi_lengkap += f" (Cover {warna_jilid})"
        spesifikasi_lengkap += f" ({jumlah} Rangkap)"
        if catatan.strip() != "":
            spesifikasi_lengkap += f" | Catatan: {catatan}"

        maps_url = ''  # tidak digunakan, dihapus

        return render_template('kalkulasi.html',
            nama_file=nama_file,
            spesifikasi=spesifikasi_lengkap,
            penerimaan=penerimaan,
            total_harga=total_harga,
            alamat_tujuan=alamat_tujuan,
            jumlah_halaman=jumlah_halaman,
            jumlah_rangkap=jumlah,
            subtotal_cetak=subtotal_cetak,
            total_jilid=total_jilid,
            ongkir=ongkir,
            harga_per_halaman=harga_per_halaman
        )

@app.route('/simpan_pesanan', methods=['POST'])
def simpan_pesanan():
    # CEK SESSION JUGA
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        nama_file = request.form['nama_file']
        spesifikasi = request.form['spesifikasi']
        penerimaan = request.form['penerimaan']
        total_harga = request.form['total_harga']
        alamat_tujuan = request.form.get('alamat_tujuan', '')
        
        bukti_bayar = request.files.get('bukti_bayar')
        if bukti_bayar and bukti_bayar.filename != '':
            nama_bukti = secure_filename(bukti_bayar.filename)
            bukti_bayar.save(os.path.join(app.config['UPLOAD_FOLDER'], nama_bukti))
        else:
            nama_bukti = "Tidak ada bukti"
        
        # 3. AMBIL ID DARI SESSION!
        id_pelanggan = session['user_id'] 
        status = "Menunggu Diproses"
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            query = """
            INSERT INTO pesanan (id_pelanggan, nama_file, spesifikasi, metode_penerimaan, alamat_tujuan, bukti_bayar, total_harga, status_pesanan, tanggal_pesan) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(query, (id_pelanggan, nama_file, spesifikasi, penerimaan, alamat_tujuan, nama_bukti, total_harga, status))
            conn.commit()
            
            wa_pesan = (
                "Halo kak! Saya ingin mengkonfirmasi pesanan saya di CV. Kembar Joyo " + "\n\n" +
                " Detail Pesanan:\n" +
                " Nama File: " + nama_file + "\n" +
                " Spesifikasi: " + spesifikasi + "\n" +
                " Penerimaan: " + penerimaan + "\n" +
                " Total: Rp {:,}".format(int(float(total_harga))) + "\n\n" +
                "Bukti transfer sudah saya kirimkan. Mohon segera diproses ya kak " + "\n" +
                "Terima kasih! "
            )
            wa_url = "https://wa.me/6282321065677?text=" + quote(wa_pesan)
            return render_template('sukses_pesanan.html',
                nama_pelanggan=session['nama_lengkap'],
                nama_file=nama_file,
                spesifikasi=spesifikasi,
                penerimaan=penerimaan,
                alamat_tujuan=alamat_tujuan,
                total_harga=int(float(total_harga)),
                wa_url=wa_url
            )
        except Exception as e:
            return f"<h1>Terjadi kesalahan database: {e}</h1>"
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'conn' in locals(): conn.close()

@app.route('/riwayat')
def riwayat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM pesanan WHERE id_pelanggan = %s ORDER BY id_pesanan DESC",
            (session['user_id'],)
        )
        pesanan_list = cursor.fetchall()
        return render_template('riwayat.html', pesanan=pesanan_list)
    except Exception as e:
        return f"<h1>Error: {e}</h1>"
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/profil', methods=['GET', 'POST'])
def profil():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    pesan_sukses = None
    pesan_error  = None
    if request.method == 'POST':
        nama_baru     = request.form.get('nama_lengkap', '').strip()
        nohp_baru     = request.form.get('no_hp', '').strip()
        sandi_baru    = request.form.get('password_baru', '').strip()
        sandi_konfirm = request.form.get('password_konfirmasi', '').strip()
        if not nama_baru or not nohp_baru:
            pesan_error = 'Nama dan Nomor HP tidak boleh kosong.'
        elif sandi_baru and sandi_baru != sandi_konfirm:
            pesan_error = 'Konfirmasi kata sandi tidak cocok.'
        elif sandi_baru and len(sandi_baru) < 6:
            pesan_error = 'Kata sandi minimal 6 karakter.'
        else:
            try:
                conn2 = get_db_connection()
                cur2  = conn2.cursor()
                if sandi_baru:
                    sandi_hash = generate_password_hash(sandi_baru)
                    cur2.execute(
                        "UPDATE pelanggan SET nama_lengkap=%s, no_hp=%s, password=%s WHERE id_pelanggan=%s",
                        (nama_baru, nohp_baru, sandi_hash, session['user_id'])
                    )
                else:
                    cur2.execute(
                        "UPDATE pelanggan SET nama_lengkap=%s, no_hp=%s WHERE id_pelanggan=%s",
                        (nama_baru, nohp_baru, session['user_id'])
                    )
                conn2.commit()
                session['nama_lengkap'] = nama_baru
                pesan_sukses = 'Profil berhasil diperbarui!'
            except Exception as e:
                pesan_error = f'Terjadi kesalahan: {e}'
            finally:
                if 'cur2' in locals(): cur2.close()
                if 'conn2' in locals(): conn2.close()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pelanggan WHERE id_pelanggan = %s", (session['user_id'],))
        data_profil = cursor.fetchone()
        return render_template('profil.html',
            profil=data_profil,
            pesan_sukses=pesan_sukses,
            pesan_error=pesan_error
        )
    except Exception as e:
        return f"<h1>Error: {e}</h1>"
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

# ==========================================
# AREA KHUSUS ADMIN (DILINDUNGI SESSION)
# ==========================================

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Cek kredensial statis sesuai permintaanmu
        if username == 'admin' and password == '1234':
            session['admin_logged_in'] = True # Beri "Kartu Akses" Admin
            return redirect(url_for('admin'))
        else:
            return "<script>alert('Akses Ditolak! Username atau Password Admin salah.'); window.history.back();</script>"
            
    return render_template('admin_login.html')

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_logged_in', None) # Tarik kembali "Kartu Akses" Admin
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin():
    # KUNCI KEAMANAN: Jika tidak ada kartu akses admin, tendang ke login admin!
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, pl.nama_lengkap, pl.no_hp
            FROM pesanan p
            LEFT JOIN pelanggan pl ON p.id_pelanggan = pl.id_pelanggan
            ORDER BY p.id_pesanan DESC
        """)
        data_pesanan = cursor.fetchall()
        return render_template('admin.html', pesanan=data_pesanan)
    except Exception as e:
        return f"Error: {e}"
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/update_status/<int:id_pesanan>', methods=['POST'])
def update_status(id_pesanan):
    # KUNCI KEAMANAN: Aksi mengubah status juga harus dilindungi
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
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


@app.route('/hapus_pesanan/<int:id_pesanan>', methods=['POST'])
def hapus_pesanan(id_pesanan):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Ambil nama file dulu sebelum dihapus
        cursor.execute(
            "SELECT nama_file, bukti_bayar FROM pesanan WHERE id_pesanan = %s",
            (id_pesanan,)
        )
        row = cursor.fetchone()
        if row:
            # Hapus file dokumen
            for col in ['nama_file', 'bukti_bayar']:
                fname = row[col]
                if fname and fname not in ('Tidak ada file', 'Tidak ada bukti'):
                    fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                    if os.path.exists(fpath):
                        os.remove(fpath)
            # Hapus record dari database
            cursor.execute("DELETE FROM pesanan WHERE id_pesanan = %s", (id_pesanan,))
            conn.commit()
        return redirect(url_for('admin'))
    except Exception as e:
        return f"Gagal menghapus pesanan: {e}"
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

if __name__ == '__main__':
    app.run(debug=True)