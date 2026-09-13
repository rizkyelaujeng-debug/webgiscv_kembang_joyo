import pymysql

def get_db_connection():
    # Fungsi ini akan dipanggil setiap kali kita butuh mengambil/menyimpan data
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='db_kembar_joyo',
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection