from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
from datetime import date, datetime # Import datetime untuk parsing tanggal

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' # Ganti dengan kunci rahasia yang kuat!

# Dummy data for demonstration
users = {
    "terapis": "password123"
}

patients_data = [
    {"id": 1, "nama": "Budi Santoso", "foto": "pasien_1.jpg", "tanggal_lahir": "10-01-1990", "jenis_kelamin": "Laki-laki", "diagnosis": "Stroke", "catatan": "Perlu fokus pada kekuatan tangan kiri."},
    {"id": 2, "nama": "Siti Aminah", "foto": "pasien_2.jpg", "tanggal_lahir": "25-03-1985", "jenis_kelamin": "Perempuan", "diagnosis": "Cedera Lutut", "catatan": "Nyeri saat menekuk lutut, fokus pada penguatan otot paha."},
    {"id": 3, "nama": "Joko Susilo", "foto": "pasien_1.jpg", "tanggal_lahir": "05-07-1975", "jenis_kelamin": "Laki-laki", "diagnosis": "Nyeri Punggung Bawah", "catatan": "Perlu latihan penguatan inti."},
    {"id": 4, "nama": "Dewi Lestari", "foto": "pasien_2.jpg", "tanggal_lahir": "20-11-1992", "jenis_kelamin": "Perempuan", "diagnosis": "Keseleo Pergelangan Kaki", "catatan": "Fokus pada stabilisasi dan penguatan pergelangan kaki."},
]

# Dummy data for movements
movements_list = [
    {"id": "G001", "name": "Mengangkat Bahu", "image": "gerakan_bahu_1.gif", "description": "Latihan untuk mobilitas sendi bahu, dilakukan 10x repetisi per sisi."},
    {"id": "G002", "name": "Mengangkat Kedua Lengan", "image": "gerakan_lengan_2.gif", "description": "Latihan peregangan untuk lengan atas, fokus pada rentang gerak penuh."},
    {"id": "G003", "name": "Menekuk Kaki", "image": "gerakan_kaki_3.gif", "description": "Latihan penguatan otot paha dan betis, lakukan perlahan dan terkontrol."},
    {"id": "G004", "name": "Posisi Tengkurap", "image": "gerakan_tengkurap_4.gif", "description": "Latihan stabilisasi tubuh bagian inti, tahan posisi selama 30 detik."},
    {"id": "G005", "name": "Posisi Terlentang", "image": "gerakan_terlentang_5.gif", "description": "Latihan relaksasi dan peregangan punggung, pastikan punggung rata dengan lantai."},
]

# Dummy data for rehabilitation programs
rehab_programs = [
    {
        'id': 'PROG001',
        'terapist_name': 'terapis',
        'patient_id': 1,
        'program_name': 'Rehabilitasi Lengan Budi',
        'execution_date': '2025-05-26', # Hari ini
        'status': 'ongoing', # ongoing, completed
        'movements': [
            {'id': 'G001', 'count': '10', 'unit': 'kali'},
            {'id': 'G002', 'count': '3', 'unit': 'set'}
        ]
    },
    {
        'id': 'PROG002',
        'terapist_name': 'terapis',
        'patient_id': 2,
        'program_name': 'Penguatan Lutut Siti',
        'execution_date': '2025-05-25', # Kemarin
        'status': 'completed',
        'movements': [
            {'id': 'G003', 'count': '15', 'unit': 'kali'}
        ]
    },
    {
        'id': 'PROG003',
        'terapist_name': 'terapis',
        'patient_id': 1,
        'program_name': 'Latihan Keseimbangan Budi',
        'execution_date': '2025-05-27', # Besok
        'status': 'ongoing',
        'movements': [
            {'id': 'G005', 'count': '5', 'unit': 'menit'}
        ]
    },
    {
        'id': 'PROG004',
        'terapist_name': 'terapis',
        'patient_id': 3,
        'program_name': 'Terapi Punggung Joko',
        'execution_date': '2025-05-26', # Hari ini
        'status': 'ongoing',
        'movements': [
            {'id': 'G004', 'count': '2', 'unit': 'set'}
        ]
    },
    {
        'id': 'PROG005',
        'terapist_name': 'terapis',
        'patient_id': 4,
        'program_name': 'Pemulihan Kaki Dewi',
        'execution_date': '2025-05-26', # Hari ini
        'status': 'ongoing',
        'movements': [
            {'id': 'G003', 'count': '20', 'unit': 'kali'}
        ]
    },
    {
        'id': 'PROG006',
        'terapist_name': 'terapis',
        'patient_id': 2,
        'program_name': 'Peregangan Lengan Siti',
        'execution_date': '2025-05-26', # Hari ini
        'status': 'ongoing',
        'movements': [
            {'id': 'G002', 'count': '10', 'unit': 'menit'}
        ]
    },
    {
        'id': 'PROG007',
        'terapist_name': 'terapis',
        'patient_id': 1,
        'program_name': 'Program Lanjutan Budi',
        'execution_date': '2025-05-24', # Sudah selesai
        'status': 'completed',
        'movements': [
            {'id': 'G001', 'count': '15', 'unit': 'kali'},
            {'id': 'G002', 'count': '5', 'unit': 'set'}
        ]
    },
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
            session['username'] = username
            return redirect(url_for('home'))
        else:
            error = "Username atau password salah."
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/home')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    current_username = session.get('username')
    
    # Filter program berdasarkan terapis yang login
    therapist_programs = [p for p in rehab_programs if p['terapist_name'] == current_username]

    # Urutkan program berdasarkan tanggal pelaksanaan terbaru (descending)
    # Gunakan datetime.strptime untuk mengonversi string tanggal menjadi objek tanggal untuk perbandingan yang benar
    sorted_therapist_programs = sorted(
        therapist_programs,
        key=lambda x: datetime.strptime(x['execution_date'], '%Y-%m-%d'),
        reverse=True
    )
    
    # Ambil hanya 2 program teratas
    top_2_recent_programs = sorted_therapist_programs[:2]

    # Hitung metrik KPI baru
    today_date_str = date.today().isoformat() # Format YYYY-MM-DD
    
    patients_rehab_today_set = set() # Menggunakan set untuk menghindari duplikasi pasien
    for program in therapist_programs:
        if program['execution_date'] == today_date_str and program['status'] == 'ongoing': # Hanya hitung yang ongoing hari ini
            patients_rehab_today_set.add(program['patient_id'])
    total_patients_rehab_today = len(patients_rehab_today_set)

    patients_completed_rehab_set = set()
    for program in therapist_programs:
        if program['status'] == 'completed':
            patients_completed_rehab_set.add(program['patient_id'])
    count_patients_completed_rehab = len(patients_completed_rehab_set)

    total_patients_handled = len(patients_data) # Total pasien yang terdaftar di sistem

    # Siapkan data program untuk ditampilkan di agenda/program list (hanya top 2)
    programs_for_display = []
    for program in top_2_recent_programs: # Gunakan top_2_recent_programs
        patient = next((p for p in patients_data if p['id'] == program['patient_id']), None)
        patient_name = patient['nama'] if patient else 'Pasien Tidak Dikenal'
        
        # Ambil detail gerakan (nama, count, unit)
        program_movements_details = []
        for mvmt_item in program['movements']:
            mvmt_detail = next((m for m in movements_list if m['id'] == mvmt_item['id']), None)
            if mvmt_detail:
                program_movements_details.append({
                    'name': mvmt_detail['name'],
                    'count': mvmt_item.get('count', ''),
                    'unit': mvmt_item.get('unit', '')
                })
        
        programs_for_display.append({
            'id': program['id'],
            'program_name': program['program_name'],
            'patient_name': patient_name,
            'execution_date': program['execution_date'],
            'status': program['status'],
            'movements_details': program_movements_details
        })
    
    # Data dummy untuk grafik (contoh sederhana)
    chart_data_patients_per_month = {
        'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun'],
        'data': [5, 8, 12, 10, 15, 13] # Contoh jumlah pasien baru per bulan
    }
    chart_data_overall_patients = total_patients_handled # Jumlah pasien keseluruhan

    return render_template(
        'home.html',
        username=current_username,
        active_page='home',
        total_patients_handled=total_patients_handled,
        total_patients_rehab_today=total_patients_rehab_today,
        count_patients_completed_rehab=count_patients_completed_rehab,
        therapist_programs=programs_for_display, # Ini sekarang hanya berisi 2 program teratas
        chart_data_patients_per_month=chart_data_patients_per_month,
        chart_data_overall_patients=chart_data_overall_patients
    )

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

@app.route('/patient/<int:patient_id>/add_activity', methods=['GET', 'POST'])
def add_activity(patient_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    patient = next((p for p in patients_data if p['id'] == patient_id), None)
    if not patient:
        flash("Pasien tidak ditemukan.", "error")
        return redirect(url_for('patients'))

    if 'selected_movements_for_activity' not in session or session.get('patient_id_for_activity') != patient_id:
        session['selected_movements_for_activity'] = []
        session['patient_id_for_activity'] = patient_id

    selected_movements_with_reps = session['selected_movements_for_activity']
    
    current_selected_movements_details = []
    for selected_item in selected_movements_with_reps:
        movement_id = selected_item['id']
        count = selected_item.get('count', '')
        unit = selected_item.get('unit', '')
        movement_detail = next((m for m in movements_list if m['id'] == movement_id), None)
        if movement_detail:
            current_selected_movements_details.append({
                'id': movement_detail['id'],
                'name': movement_detail['name'],
                'count': count,
                'unit': unit
            })

    if request.method == 'POST':
        program_name = request.form['program_name']
        terapist_name = request.form['terapist_name']
        execution_date = request.form['execution_date']
        
        new_program_id = f"PROG{len(rehab_programs) + 1:03d}"
        rehab_programs.append({
            'id': new_program_id,
            'terapist_name': terapist_name,
            'patient_id': patient_id,
            'program_name': program_name,
            'execution_date': execution_date,
            'status': 'ongoing',
            'movements': selected_movements_with_reps
        })

        print(f"--- Program Rehabilitasi Baru untuk {patient['nama']} ---")
        print(f"Nama Program: {program_name}")
        print(f"Nama Terapis: {terapist_name}")
        print(f"Tanggal Pelaksanaan: {execution_date}")
        print("Gerakan yang dipilih:")
        for item in current_selected_movements_details:
            print(f"- {item['name']} ({item['count']} {item['unit']})")
        
        session.pop('selected_movements_for_activity', None)
        session.pop('patient_id_for_activity', None)

        flash("Program rehabilitasi berhasil disimpan!", "success")
        return redirect(url_for('patient_detail', patient_id=patient_id))
    
    return render_template(
        'add_activity.html',
        patient=patient,
        selected_movements=current_selected_movements_details,
        username=session.get('username'),
        active_page='patients'
    )

@app.route('/patient/<int:patient_id>/select_movements')
def select_movements(patient_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    patient = next((p for p in patients_data if p['id'] == patient_id), None)
    if not patient:
        flash("Pasien tidak ditemukan.", "error")
        return redirect(url_for('patients'))

    selected_movements_with_reps = session.get('selected_movements_for_activity', [])
    selected_movements_json_str = json.dumps(selected_movements_with_reps)

    return render_template(
        'select_movements.html',
        patient=patient,
        movements=movements_list,
        selected_movements_json_str=selected_movements_json_str,
        username=session.get('username'),
        active_page='patients'
    )

@app.route('/patient/<int:patient_id>/update_selected_movements', methods=['POST'])
def update_selected_movements(patient_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    selected_movements_json = request.form.get('selected_movements_json')
    
    if selected_movements_json:
        selected_data = json.loads(selected_movements_json)
        session['selected_movements_for_activity'] = selected_data
        flash("Gerakan berhasil diperbarui.", "info")
    else:
        session['selected_movements_for_activity'] = []
        flash("Tidak ada gerakan yang dipilih atau diperbarui.", "info")
    
    return redirect(url_for('add_activity', patient_id=patient_id))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('selected_movements_for_activity', None)
    session.pop('patient_id_for_activity', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
