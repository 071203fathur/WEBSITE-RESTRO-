from flask import Flask, render_template, request, redirect, url_for, session, flash
import json # Import modul json

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' # Ganti dengan kunci rahasia yang kuat!

# Dummy data for demonstration
users = {
    "terapis": "password123"
}

patients_data = [
    {"id": 1, "nama": "Budi Santoso", "foto": "pasien_1.jpg", "tanggal_lahir": "10-01-1990", "jenis_kelamin": "Laki-laki", "diagnosis": "Stroke", "catatan": "Perlu fokus pada kekuatan tangan kiri."},
    {"id": 2, "nama": "Siti Aminah", "foto": "pasien_2.jpg", "tanggal_lahir": "25-03-1985", "jenis_kelamin": "Perempuan", "diagnosis": "Cedera Lutut", "catatan": "Nyeri saat menekuk lutut, fokus pada penguatan otot paha."},
    # Tambahkan pasien lain di sini
]

# Dummy data for movements
# Setiap gerakan punya ID, nama, deskripsi (opsional), dan path gambar
movements_list = [
    {"id": "G001", "name": "Menekuk Siku", "image": "menekuk_siku_1.gif", "description": "Latihan untuk mobilitas sendi siku"},
    {"id": "G002", "name": "Mengangkat Pinggul", "image": "angkat_pinggul.gif", "description": "Latihan peregangan untuk lengan atas, fokus pada rentang gerak penuh."},
    {"id": "G003", "name": "Menekuk Lutut", "image": "lutut_turun.gif", "description": "Latihan penguatan otot paha dan betis, lakukan perlahan dan terkontrol."},
    {"id": "G004", "name": "Naikan Kepalan Ke Depan", "image": "kepalan_tangan.gif", "description": "Latihan stabilisasi tubuh bagian inti, tahan posisi selama 30 detik."},
    {"id": "G005", "name": "Rentangkan Tangan", "image": "rentangkan.gif", "description": "Latihan relaksasi dan peregangan punggung, pastikan punggung rata dengan lantai."},
    # Tambahkan lebih banyak gerakan di sini sesuai kebutuhan
    # {"id": "G006", "name": "Jalan di Tempat", "image": "gerakan_jalan_6.jpg", "description": "Latihan kardio ringan, lakukan selama 5-10 menit."},
    # {"id": "G007", "name": "Latihan Keseimbangan", "image": "gerakan_keseimbangan_7.jpg", "description": "Melatih keseimbangan statis dan dinamis, bisa dengan pegangan jika diperlukan."}
]

# --- Route Utama ---
@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['logged_in'] = True
            session['username'] = username # Simpan username di session
            return redirect(url_for('home'))
        else:
            error = "Username atau password salah."
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/home')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('home.html', username=session.get('username'), active_page='home')

@app.route('/patients')
def patients():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('patients.html', patients=patients_data, username=session.get('username'), active_page='patients')

@app.route('/patient/<int:patient_id>')
def patient_detail(patient_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    patient = next((p for p in patients_data if p['id'] == patient_id), None)
    if patient:
        return render_template('patient_detail.html', patient=patient, username=session.get('username'), active_page='patients')
    flash("Pasien tidak ditemukan.", "error")
    return redirect(url_for('patients'))

# --- Perubahan untuk Merumuskan Gerakan: Tambah Kegiatan ---

@app.route('/patient/<int:patient_id>/add_activity', methods=['GET', 'POST'])
def add_activity(patient_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    patient = next((p for p in patients_data if p['id'] == patient_id), None)
    if not patient:
        flash("Pasien tidak ditemukan.", "error")
        return redirect(url_for('patients'))

    # Inisialisasi atau ambil gerakan yang sudah dipilih dari session
    # session['selected_movements_for_activity'] akan menyimpan list of dicts: [{'id': 'G001', 'count': '10', 'unit': 'kali'}]
    # Pastikan ID pasien yang disimpan di session cocok, jika tidak, reset pilihan
    if 'selected_movements_for_activity' not in session or session.get('patient_id_for_activity') != patient_id:
        session['selected_movements_for_activity'] = []
        session['patient_id_for_activity'] = patient_id # Simpan ID pasien agar tidak tercampur

    selected_movements_with_reps = session['selected_movements_for_activity']
    
    # Ambil detail gerakan (nama, deskripsi, gambar) untuk gerakan yang sudah dipilih
    # Ini untuk ditampilkan di 'List Gerakan' pada halaman add_activity
    current_selected_movements_details = []
    for selected_item in selected_movements_with_reps:
        movement_id = selected_item['id']
        count = selected_item.get('count', '') # Ambil count, default kosong
        unit = selected_item.get('unit', '')   # Ambil unit, default kosong
        movement_detail = next((m for m in movements_list if m['id'] == movement_id), None)
        if movement_detail:
            current_selected_movements_details.append({
                'id': movement_detail['id'],
                'name': movement_detail['name'],
                'count': count, # Sertakan informasi count
                'unit': unit    # Sertakan informasi unit
            })

    if request.method == 'POST':
        program_name = request.form['program_name']
        terapist_name = request.form['terapist_name']
        execution_date = request.form['execution_date'] # Tanggal pelaksanaan
        
        # Di sini Anda akan menyimpan data kegiatan ke database Anda
        # Untuk contoh ini, kita hanya akan mencetak ke konsol dan flash pesan
        print(f"--- Program Rehabilitasi Baru untuk {patient['nama']} ---")
        print(f"Nama Program: {program_name}")
        print(f"Nama Terapis: {terapist_name}")
        print(f"Tanggal Pelaksanaan: {execution_date}")
        print("Gerakan yang dipilih:")
        for item in current_selected_movements_details:
            print(f"- {item['name']} ({item['count']} {item['unit']})") # Cetak dengan count dan unit
        
        # Bersihkan session setelah berhasil menyimpan program
        session.pop('selected_movements_for_activity', None)
        session.pop('patient_id_for_activity', None)

        flash("Program rehabilitasi berhasil disimpan!", "success")
        return redirect(url_for('patient_detail', patient_id=patient_id))
    
    return render_template(
        'add_activity.html',
        patient=patient,
        selected_movements=current_selected_movements_details, # Kirim detail gerakan dengan count & unit
        username=session.get('username'),
        active_page='patients'
    )

# --- Perubahan untuk Merumuskan Gerakan: Pilih Gerakan ---

@app.route('/patient/<int:patient_id>/select_movements')
def select_movements(patient_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    patient = next((p for p in patients_data if p['id'] == patient_id), None)
    if not patient:
        flash("Pasien tidak ditemukan.", "error")
        return redirect(url_for('patients'))

    # Ambil gerakan yang sudah dipilih dari session jika ada (berupa list of dicts)
    selected_movements_with_reps = session.get('selected_movements_for_activity', [])
    
    # Konversi list of dictionaries ke string JSON untuk diteruskan ke JavaScript
    selected_movements_json_str = json.dumps(selected_movements_with_reps)

    return render_template(
        'select_movements.html',
        patient=patient,
        movements=movements_list, # Semua daftar gerakan
        # Teruskan string JSON langsung ke template
        selected_movements_json_str=selected_movements_json_str,
        username=session.get('username'),
        active_page='patients'
    )

@app.route('/patient/<int:patient_id>/update_selected_movements', methods=['POST'])
def update_selected_movements(patient_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # Ambil data JSON dari hidden input
    selected_movements_json = request.form.get('selected_movements_json')
    
    if selected_movements_json:
        # Parse JSON string menjadi Python list of dictionaries
        selected_data = json.loads(selected_movements_json)
        # Simpan data yang sudah di-parse ke session
        session['selected_movements_for_activity'] = selected_data
        flash("Gerakan berhasil diperbarui.", "info")
    else:
        # Jika tidak ada data JSON (mungkin tidak ada gerakan yang dipilih)
        session['selected_movements_for_activity'] = []
        flash("Tidak ada gerakan yang dipilih atau diperbarui.", "info")
    
    return redirect(url_for('add_activity', patient_id=patient_id)) # Kembali ke halaman tambah kegiatan

# --- Route Logout ---
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    # Hapus juga data session terkait kegiatan pasien saat logout
    session.pop('selected_movements_for_activity', None)
    session.pop('patient_id_for_activity', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
