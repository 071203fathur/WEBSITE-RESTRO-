# Website-Monitoring/app.py
# PERUBAHAN: Menambahkan total_points ke data pasien di berbagai endpoint frontend.
# PERUBAHAN: Mengganti dummy data leaderboard dengan panggilan API nyata.
# PERUBAHAN: Menambahkan endpoint untuk manajemen badge (create, update, delete).
# PERBAIKAN: Mengatasi AttributeError: 'NoneType' object has no attribute 'get' pada highest_badge_info.

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import requests
import json
from datetime import date, datetime

# --- Import Firebase Admin SDK ---
import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.auth import UserNotFoundError # Import spesifik untuk menangani error user tidak ditemukan
import os 

app = Flask(__name__)
# GANTI INI DENGAN KUNCI RAHASIA YANG KUAT DAN UNIK UNTUK APLIKASI WEBSITE ANDA!
app.secret_key = 'website_monitoring_super_secret_key_CHANGE_ME_PLEASE_AGAIN' 

# --- Konfigurasi Firebase Admin SDK ---
# Anda harus mengganti 'path/to/your/firebase-adminsdk.json' dengan jalur sebenarnya
# ke file kunci akun layanan Firebase Anda.
# File ini berisi kredensial yang aman untuk Firebase Admin SDK.
# DISARANKAN: Simpan path ini di environment variable (misal: FIREBASE_ADMIN_SDK_PATH)
FIREBASE_ADMIN_SDK_PATH = os.getenv('FIREBASE_ADMIN_SDK_PATH', 'config/restro-62e50-firebase-adminsdk-fbsvc-d9b80ccd3c.json') 

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_ADMIN_SDK_PATH)
        firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")
    # Tangani error inisialisasi Admin SDK sesuai kebutuhan produksi Anda
    pass


# --- Konfigurasi untuk API Backend BE-RESTRO ---
API_BASE_URL = "https://be-restro-api-fnfpghddbka7d4aw.eastasia-01.azurewebsites.net"

# --- Konfigurasi Firebase Client-Side (Client-side Firebase SDK) ---
# Ini adalah konfigurasi yang akan dikirim ke frontend.
# Anda bisa menemukannya di Firebase Console -> Project settings -> General -> Your apps -> Firebase SDK snippet (Config)
FIREBASE_CLIENT_CONFIG = {
    "apiKey": "AIzaSyBpV6OnjPFLzvVT15ByrvaeL9K3NLwyp_8",
    "authDomain": "restro-62e50.firebaseapp.com",
    "projectId": "restro-62e50",
    "storageBucket": "restro-62e50.firebasestorage.app",
    "messagingSenderId": "923846485510",
    "appId": "1:923846485510:web:179847d92b5fbc7438c587",
    "measurementId": "G-14V1KJ7S63"
}


# --- Fungsi Helper untuk Request ke API Backend ---
def api_request(method, endpoint, data=None, params=None, files=None, use_token=True):
    """
    Melakukan permintaan ke API backend BE-RESTRO.
    """
    headers = {}
    if use_token:
        token = session.get('access_token')
        if token:
            headers['Authorization'] = f"Bearer {token}"
    
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if files:
            # requests akan secara otomatis mengatur Content-Type: multipart/form-data untuk files
            response = requests.request(method.upper(), url, headers=headers, data=data, files=files, params=params, timeout=20)
        else:
            if data is not None:
                headers['Content-Type'] = 'application/json'
            response = requests.request(method.upper(), url, headers=headers, json=data, params=params, timeout=20)

        response.raise_for_status()

        if not response.content:
            return {"msg": "Operasi berhasil, tidak ada konten balasan."}, response.status_code, response.headers

        json_response = response.json()
        return json_response, response.status_code, response.headers

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code} for URL: {url}")
        try:
            return e.response.json(), e.response.status_code, e.response.headers
        except json.JSONDecodeError:
            return {"error": "Server memberikan respons error yang bukan JSON.", "raw_text": e.response.text}, e.response.status_code, e.response.headers
    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        return {"error": f"Terjadi kesalahan saat menghubungi API backend: {str(e)}"}, 500, None

# --- Fungsi Helper Autentikasi ---
def is_logged_in():
    """
    Memeriksa apakah pengguna sedang login.
    """
    return 'access_token' in session and 'user_info' in session

def get_current_user_info():
    """
    Mendapatkan informasi pengguna yang sedang login dari sesi.
    """
    return session.get('user_info', {})

def get_current_user_role():
    """
    Mendapatkan peran pengguna yang sedang login.
    """
    return get_current_user_info().get('role')

def get_current_user_name():
    """
    Mendapatkan nama lengkap atau username pengguna yang sedang login.
    """
    user_info = get_current_user_info()
    return user_info.get('nama_lengkap', user_info.get('username', 'Terapis'))

# --- Filter Jinja untuk Format Tanggal ---
@app.template_filter('format_date_id')
def format_date_filter_jinja(value, format='%d %B %Y'):
    """
    Filter Jinja untuk memformat string tanggal ke format Indonesia.
    """
    if not value: return 'N/A'
    try:
        if isinstance(value, str):
            possible_formats = ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%d-%m-%Y')
            dt_object = None
            for fmt in possible_formats:
                try:
                    dt_object = datetime.strptime(value, fmt)
                    break 
                except ValueError: continue
            if dt_object: return dt_object.strftime(format)
            return value 
        elif isinstance(value, (date, datetime)):
            return value.strftime(format)
        return value
    except Exception: return value

# --- Context Processor untuk Variabel Global di Template ---
@app.context_processor
def inject_now():
    """
    Menginjeksikan objek datetime.utcnow() ke semua template sebagai 'now'.
    """
    return {'now': datetime.utcnow()}

# --- Rute Aplikasi Website ---

@app.route('/')
def index():
    """
    Rute utama, mengarahkan ke halaman home jika sudah login sebagai terapis,
    jika tidak, mengarahkan ke halaman login.
    """
    if is_logged_in() and get_current_user_role() == 'terapis':
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Rute untuk halaman login terapis.
    """
    if is_logged_in() and get_current_user_role() == 'terapis':
        return redirect(url_for('home'))

    if request.method == 'POST':
        identifier = request.form.get('username') 
        password = request.form.get('password')

        if not identifier or not password:
            flash("Username/Email dan password harus diisi.", "danger")
            return render_template('login.html', error="Username/Email dan password harus diisi.")

        payload = {"identifier": identifier, "password": password}
        api_response, status_code, _ = api_request('POST', '/auth/terapis/login', data=payload, use_token=False)

        if status_code == 200 and isinstance(api_response, dict) and 'access_token' in api_response:
            session['access_token'] = api_response['access_token']
            session['user_info'] = api_response.get('user', {}) 
            session['logged_in'] = True
            
            # --- Firebase Custom Token Generation & User Management ---
            terapis_id_from_backend = session['user_info'].get('id') 
            if terapis_id_from_backend:
                uid_str = str(terapis_id_from_backend) 
                try:
                    user = auth.get_user(uid_str)
                    print(f"Firebase user with UID {uid_str} already exists.")
                except UserNotFoundError:
                    try:
                        user = auth.create_user(uid=uid_str, display_name=session['user_info'].get('nama_lengkap'), email=session['user_info'].get('email'))
                        print(f"Successfully created new Firebase user with UID: {user.uid}")
                    except Exception as e:
                        print(f"ERROR: Failed to create Firebase user with UID {uid_str}: {e}")
                        flash("Gagal membuat pengguna Firebase. Fitur chat mungkin tidak berfungsi.", "warning")
                        user = None 
                except Exception as e:
                    print(f"ERROR: Failed to fetch Firebase user {uid_str}: {e}")
                    flash("Gagal memverifikasi pengguna Firebase. Fitur chat mungkin tidak berfungsi.", "warning")
                    user = None

                if user: 
                    try:
                        firebase_custom_token = auth.create_custom_token(user.uid) 
                        session['firebase_custom_token'] = firebase_custom_token.decode('utf-8') 
                        print(f"Firebase Custom Token generated for UID: {user.uid}")
                    except Exception as e:
                        print(f"ERROR: Failed to generate Firebase custom token for UID {user.uid}: {e}")
                        flash("Gagal menghasilkan token chat. Fitur chat mungkin tidak berfungsi.", "warning")
                else: 
                    flash("Tidak dapat menyiapkan Firebase Auth untuk chat. Silakan hubungi admin.", "warning")
            else:
                print("WARNING: Terapis ID not found in session user info. Cannot generate Firebase custom token.")
                flash("ID terapis tidak ditemukan. Fitur chat mungkin tidak berfungsi.", "warning")
            # --- End Firebase Custom Token Generation & User Management ---

            print(f"Login successful for {session['user_info'].get('username')}")
            flash('Login berhasil!', 'success')
            return redirect(url_for('home'))
        else:
            error_msg = "Login gagal. "
            if isinstance(api_response, dict):
                error_msg += str(api_response.get('msg', api_response.get('error', 'Detail error tidak tersedia dari server.')))
            else: 
                error_msg += f"Tidak dapat memproses respons dari server. (Status: {status_code})"
            flash(error_msg, 'danger')
            print(f"Login failed: API Response: {api_response}, Status Code: {status_code}")
            return render_template('login.html', error=error_msg)
            
    return render_template('login.html')


@app.route('/home')
def home():
    """
    Rute untuk halaman dashboard terapis (home).
    Menampilkan ringkasan KPI dan program terbaru.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        flash("Sesi tidak valid atau Anda bukan terapis. Silakan login kembali.", "warning")
        return redirect(url_for('login'))
    
    user_info = get_current_user_info()
    
    dashboard_data_resp, status_code, _ = api_request('GET', '/api/terapis/dashboard-summary')
    
    kpi_data = {
        "pasien_rehabilitasi_hari_ini": 0,
        "pasien_selesai_rehabilitasi_hari_ini": 0,
        "total_pasien_ditangani": 0
    }
    programs_for_display_home = []
    chart_data_patients_per_month = {'labels': [], 'data': []} 
    
    if status_code == 200 and isinstance(dashboard_data_resp, dict):
        kpi_data = dashboard_data_resp.get('kpi', {})
        programs_for_display_home_raw = dashboard_data_resp.get('program_terbaru_terapis', [])
        
        for p_data in programs_for_display_home_raw:
            program_id = p_data.get('id')
            patient_id_for_program = p_data.get('patient_id')
            
            try:
                program_id = int(program_id) if program_id is not None else 0
                patient_id_for_program = int(patient_id_for_program) if patient_id_for_program is not None else 0
            except (ValueError, TypeError):
                program_id = 0
                patient_id_for_program = 0

            programs_for_display_home.append({
                'id': program_id, 
                'program_name': p_data.get('program_name'),
                'patient_name': p_data.get('patient_name'),
                'patient_id': patient_id_for_program,
                'execution_date': p_data.get('execution_date'),
                'status': p_data.get('status'),
                'movements_details': p_data.get('movements_details', [])
            })

        statistik_bulanan = dashboard_data_resp.get('chart_data_patients_per_day', {})
        chart_data_patients_per_month['labels'] = statistik_bulanan.get('labels', [])
        chart_data_patients_per_month['data'] = statistik_bulanan.get('data', [])
    else:
        error_message_from_api = "Detail error tidak diketahui dari server."
        if isinstance(dashboard_data_resp, dict):
            error_message_from_api = dashboard_data_resp.get('msg', dashboard_data_resp.get('error', "Tidak ada pesan error spesifik dari API."))
        elif dashboard_data_resp is None: 
            error_message_from_api = "Tidak dapat terhubung ke server API atau respons timeout."
        else: 
            error_message_from_api = f"Menerima respons tidak terduga dari API (tipe: {type(dashboard_data_resp).__name__})."
        
        flash(f"Gagal mengambil data dashboard terapis: {str(error_message_from_api)}", "warning")

    total_patients_handled = kpi_data.get('total_pasien_ditangani', 0)
    total_patients_rehab_today = kpi_data.get('pasien_rehabilitasi_hari_ini', 0)
    count_patients_completed_rehab = kpi_data.get('pasien_selesai_rehabilitasi_hari_ini', 0)

    # Pass Firebase config and custom token to template
    return render_template(
        'home.html',
        username=user_info.get('nama_lengkap', user_info.get('username')),
        active_page='home',
        total_patients_handled=total_patients_handled,
        total_patients_rehab_today=total_patients_rehab_today,
        count_patients_completed_rehab=count_patients_completed_rehab,
        therapist_programs=programs_for_display_home, 
        chart_data_patients_per_month_json=json.dumps(chart_data_patients_per_month),
        firebase_config_json=json.dumps(FIREBASE_CLIENT_CONFIG),
        firebase_custom_token=session.get('firebase_custom_token'),
        app_id=app.name
    )

# --- NEW ROUTE: API Endpoint for Frontend to Get Patient List for Chat ---
@app.route('/api/patients_for_chat', methods=['GET'])
def get_patients_for_chat_api():
    """
    Rute API untuk frontend mengambil daftar pasien untuk fitur chat.
    Memanggil API backend untuk mendapatkan data pasien.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        return jsonify({"error": "Unauthorized"}), 401
    
    # Memanggil API backend eksternal menggunakan helper api_request yang sudah ada
    response_data, status_code, headers = api_request('GET', '/api/program/pasien-list')

    if status_code == 200 and isinstance(response_data, list):
        # Memformat data pasien sesuai kebutuhan UI chat frontend
        formatted_patients = []
        for p in response_data:
            patient_id = p.get('id') or p.get('user_id') # Ambil ID pasien
            patient_name = p.get('nama') or p.get('nama_lengkap') or 'Nama Tidak Dikenal'
            foto_display_src = p.get('foto_url') or p.get('foto_filename') 
            if not (foto_display_src and (foto_display_src.startswith('http://') or foto_display_src.startswith('https://'))):
                foto_display_src = url_for('static', filename='img/default_avatar.png')

            formatted_patients.append({
                'id': patient_id,
                'name': patient_name,
                'photo_url': foto_display_src, # Menggunakan photo_url agar konsisten dengan frontend
                'total_points': p.get('total_points', 0) # Menambahkan total_points
            })
        return jsonify(formatted_patients), 200
    else:
        # Menangani kasus di mana API eksternal mengembalikan error atau data non-list
        error_msg = response_data.get('msg', response_data.get('error', 'Gagal mengambil daftar pasien dari API eksternal.'))
        return jsonify({"error": error_msg, "status_code": status_code}), status_code


@app.route('/patients')
def patients(): 
    """
    Rute untuk halaman daftar pasien.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        return redirect(url_for('login'))

    response_data, status_code, _ = api_request('GET', '/api/program/pasien-list')
    
    patient_list_from_api = []

    if status_code == 200 and isinstance(response_data, list):
        patient_list_from_api = response_data
        
        for p in patient_list_from_api:
            if 'nama' not in p and 'nama_lengkap' in p:
                p['nama'] = p['nama_lengkap']
            
            foto_value = p.get('foto_url', p.get('foto_filename')) 
            if foto_value:
                if foto_value.startswith('http://') or foto_value.startswith('https://'):
                    p['foto_display_src'] = foto_value
                else: 
                    p['foto_display_src'] = url_for('static', filename=f"img/{foto_value}") 
            else:
                p['foto_display_src'] = url_for('static', filename='img/default_avatar.png')
            
            if 'diagnosis' not in p or not p['diagnosis']:
                p['diagnosis'] = 'Belum ada diagnosis'
    
    elif isinstance(response_data, dict) and 'msg' in response_data:
        flash(f"Gagal mengambil daftar pasien: {str(response_data['msg'])}", 'danger')
    else:
        error_detail = response_data.get('error', 'Tidak diketahui') if isinstance(response_data, dict) else "Respons API tidak valid"
        flash(f"Gagal mengambil daftar pasien. Status: {status_code}, Detail: {str(error_detail)}", 'danger')

    # Pass Firebase config and custom token to template
    return render_template(
        'patients.html', 
        patients=patient_list_from_api, 
        username=get_current_user_name(), 
        active_page='patients',
        firebase_config_json=json.dumps(FIREBASE_CLIENT_CONFIG),
        firebase_custom_token=session.get('firebase_custom_token'),
        app_id=app.name
    )

@app.route('/patient/<int:patient_id>')
def patient_detail(patient_id):
    """
    Rute untuk halaman detail pasien.
    Menampilkan data monitoring, riwayat program, dan pola makan.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        return redirect(url_for('login'))

    monitoring_data_api, monitoring_status, _ = api_request('GET', f'/api/monitoring/summary/pasien/{patient_id}')
    
    patient_info_for_header = {} 
    if monitoring_status == 200 and isinstance(monitoring_data_api, dict):
        patient_info_for_header = monitoring_data_api.get('pasien_info', {})
        
        patient_info_for_header['id'] = patient_info_for_header.get('user_id', patient_id)

        if 'nama' not in patient_info_for_header and 'nama_lengkap' in patient_info_for_header:
            patient_info_for_header['nama'] = patient_info_for_header['nama_lengkap']
        foto_profil_val = patient_info_for_header.get('url_foto_profil', patient_info_for_header.get('foto_filename'))
        if foto_profil_val and (foto_profil_val.startswith('http://') or foto_profil_val.startswith('https://')):
            patient_info_for_header['foto_src_display'] = foto_profil_val
        else:
            patient_info_for_header['foto_src_display'] = url_for('static', filename='img/default_avatar.png')

        # HAPUS MOCK DATA: 'total_points' seharusnya datang dari backend di 'pasien_info'
        # if 'total_points' not in monitoring_data_api['summary_kpi']:
        #     monitoring_data_api['summary_kpi']['total_points'] = 1200 
            
        if not monitoring_data_api.get('summary_kpi'):
            flash("Informasi KPI pasien tidak tersedia dari API ringkasan.", "info")
        if not monitoring_data_api.get('trends_chart'):
            flash("Data tren grafik pasien tidak tersedia dari API ringkasan.", "info")
        if not monitoring_data_api.get('distribusi_hasil_gerakan_total'):
            flash("Data distribusi gerakan tidak tersedia dari API ringkasan.", "info")
        if not monitoring_data_api.get('catatan_observasi_terbaru'):
            flash("Catatan observasi terbaru tidak tersedia dari API ringkasan.", "info")
            
    else:
        error_detail = "Error tidak diketahui dari server."
        if isinstance(monitoring_data_api, dict):
            error_detail = monitoring_data_api.get('error', monitoring_data_api.get('msg', 'Error tidak diketahui dari server.'))
        flash(f"Gagal mengambil data monitoring untuk pasien ID {patient_id}. Pesan: {str(error_detail)}", 'danger')
        return redirect(url_for('patients'))

    rehab_history_resp, rehab_history_status, _ = api_request('GET', f'/api/program/terapis/assigned-to-patient/{patient_id}', params={'per_page': 100})
    
    patient_rehab_history_for_tab = []
    if rehab_history_status == 200 and isinstance(rehab_history_resp, dict) and 'programs' in rehab_history_resp:
        patient_rehab_history_for_tab = rehab_history_resp['programs']
    elif isinstance(rehab_history_resp, dict) and 'msg' in rehab_history_resp:
            flash(f"Info: Gagal mengambil riwayat program rehabilitasi: {str(rehab_history_resp['msg'])}", "info")
    else:
            flash("Info: Riwayat program rehabilitasi tidak tersedia atau gagal diambil.", "info")

    patient_meal_plans = session.get(f'meal_plans_patient_{patient_id}', [])

    # Pass Firebase config and custom token to template
    return render_template(
        'patient_detail.html', 
        patient=patient_info_for_header, 
        monitoring_data_js=json.dumps(monitoring_data_api if isinstance(monitoring_data_api,dict) else {}),
        patient_rehab_history=patient_rehab_history_for_tab, 
        patient_meal_plans_json=json.dumps(patient_meal_plans), 
        username=get_current_user_name(),
        active_page='patients',
        firebase_config_json=json.dumps(FIREBASE_CLIENT_CONFIG),
        firebase_custom_token=session.get('firebase_custom_token'),
        app_id=app.name
    )


@app.route('/save_add_activity_form_temp', methods=['POST'])
def save_add_activity_form_temp():
    """
    Menyimpan data form 'add activity' sementara di sesi.
    """
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    session['add_activity_form_data'] = {
        'program_name': data.get('program_name', ''),
        'execution_date': data.get('execution_date', ''),
        'catatan_terapis': data.get('catatan_terapis', '')
    }
    return jsonify({"msg": "Form data saved temporarily."}), 200

@app.route('/patient/<int:patient_id>/add_activity', methods=['GET', 'POST'])
def add_activity(patient_id):
    """
    Rute untuk menambah program rehabilitasi baru untuk pasien.
    """
    if not is_logged_in():
        return redirect(url_for('login'))
    
    patient_info_resp, pi_status, _ = api_request('GET', f'/api/monitoring/summary/pasien/{patient_id}')
    patient_info_for_form = {}
    if pi_status == 200 and isinstance(patient_info_resp, dict) and 'pasien_info' in patient_info_resp:
        patient_info_for_form = patient_info_resp['pasien_info']
        patient_info_for_form['id'] = patient_info_for_form.get('user_id', patient_id)
    else:
        flash(f"Gagal mengambil info pasien (ID: {patient_id}).", "danger")
        return redirect(url_for('patient_detail', patient_id=patient_id))

    saved_form_data = session.pop('add_activity_form_data', {}) 
    if 'execution_date' in saved_form_data and saved_form_data['execution_date']:
        try:
            saved_form_data['execution_date'] = datetime.strptime(saved_form_data['execution_date'], '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            pass


    if request.method == 'POST':
        try:
            gerakan_data_str = request.form.get('selected_movements_data_json', '[]')
            selected_movements = json.loads(gerakan_data_str)

            if not selected_movements:
                flash("Harap pilih minimal satu gerakan untuk program ini.", "warning")
                session['add_activity_form_data'] = { 
                    'program_name': request.form.get('program_name', ''),
                    'execution_date': request.form.get('execution_date', ''),
                    'catatan_terapis': request.form.get('catatan_terapis', '')
                }
                return redirect(url_for('add_activity', patient_id=patient_id))

            list_gerakan_direncanakan = []
            for i, item in enumerate(selected_movements):
                list_gerakan_direncanakan.append({
                    "gerakan_id": int(item["id"]),
                    "jumlah_repetisi_direncanakan": int(item["count"]),
                    "urutan_dalam_program": int(item.get("urutan") or i + 1)
                })

            api_payload = {
                "nama_program": request.form.get('program_name'),
                "pasien_id": patient_id,
                "tanggal_program": request.form.get('execution_date'),
                "catatan_terapis": request.form.get('catatan_terapis', ''),
                "list_gerakan_direncanakan": list_gerakan_direncanakan
            }
            
            response_data, status_code, _ = api_request('POST', '/api/program/', data=api_payload)
            
            if status_code == 201:
                flash('Program rehabilitasi berhasil dibuat!', 'success')
                session.pop('selected_movements_for_activity', None)
                session.pop('patient_id_for_activity', None)
                session.pop('add_activity_form_data', None)
                return redirect(url_for('patient_detail', patient_id=patient_id))
            else:
                error_msg = response_data.get('msg', response_data.get('error', 'Terjadi kesalahan saat membuat program.'))
                flash(f"Gagal membuat program: {error_msg}", 'danger')
                session['add_activity_form_data'] = {
                    'program_name': request.form.get('program_name', ''),
                    'execution_date': request.form.get('execution_date', ''),
                    'catatan_terapis': request.form.get('catatan_terapis', '')
                }
        
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            flash(f"Terjadi kesalahan dalam memproses data gerakan: {str(e)}", "danger")
            session['add_activity_form_data'] = { 
                'program_name': request.form.get('program_name', ''),
                'execution_date': request.form.get('execution_date', ''),
                'catatan_terapis': request.form.get('catatan_terapis', '')
            }

    selected_movements_from_session = []
    if session.get('patient_id_for_activity') == patient_id:
        selected_in_session = session.get('selected_movements_for_activity', [])

    # Pass Firebase config and custom token to template
    return render_template(
        'add_activity.html', 
        patient=patient_info_for_form,
        username=get_current_user_name(),
        selected_movements_from_session_json=json.dumps(selected_in_session),
        form_data=saved_form_data,
        now=datetime.utcnow(),
        firebase_config_json=json.dumps(FIREBASE_CLIENT_CONFIG),
        firebase_custom_token=session.get('firebase_custom_token'),
        app_id=app.name
    )

@app.route('/patient/<int:patient_id>/select_movements')
def select_movements_view(patient_id):
    """
    Rute untuk memilih gerakan rehabilitasi dari perpustakaan.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        return redirect(url_for('login'))
        
    patient_info_resp, _, _ = api_request('GET', f'/api/monitoring/summary/pasien/{patient_id}')
    gerakan_resp, _, _ = api_request('GET', '/api/gerakan', params={'per_page': 1000}) 
    
    patient_info = patient_info_resp.get('pasien_info', {}) if isinstance(patient_info_resp, dict) else {}
    patient_info['id'] = patient_info.get('user_id', patient_id)

    all_movements = gerakan_resp.get('gerakan', []) if isinstance(gerakan_resp, dict) else []

    selected_in_session = []
    if session.get('patient_id_for_activity') == patient_id:
        selected_in_session = session.get('selected_movements_for_activity', [])

    # Pass Firebase config and custom token to template
    return render_template(
        'select_movements.html',
        patient=patient_info,
        movements=all_movements,
        selected_movements_json_str=json.dumps(selected_in_session),
        username=get_current_user_name(),
        firebase_config_json=json.dumps(FIREBASE_CLIENT_CONFIG),
        firebase_custom_token=session.get('firebase_custom_token'),
        app_id=app.name
    )


@app.route('/patient/<int:patient_id>/update_selected_movements', methods=['POST'])
def update_selected_movements_view(patient_id): 
    """
    API endpoint untuk mengupdate gerakan yang dipilih di sesi.
    """
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401 
    
    data = request.get_json()
    if not data or 'selected_movements' not in data:
        return jsonify({"error": "Data 'selected_movements' tidak ditemukan"}), 400
        
    session['selected_movements_for_activity'] = data.get('selected_movements', [])
    session['patient_id_for_activity'] = patient_id 
    return jsonify({"msg": "Pilihan gerakan berhasil disimpan di sesi."}), 200

@app.route('/api/terapis/diet-plan', methods=['POST'])
def create_diet_plan():
    """
    API endpoint untuk membuat rencana pola makan baru oleh terapis.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        return jsonify({"error": "Unauthorized"}), 401
    
    request_data = request.get_json()
    if not request_data:
        return jsonify({"error": "No data provided"}), 400

    pasien_id = request_data.get('pasien_id')
    tanggal_makan = request_data.get('tanggal_makan')
    menu_pagi = request_data.get('menu_pagi', '')
    menu_siang = request_data.get('menu_siang', '')
    menu_malam = request_data.get('menu_malam', '')
    cemilan = request_data.get('cemilan', '')

    if not pasien_id or not tanggal_makan:
        return jsonify({"error": "Data tidak lengkap: pasien_id dan tanggal_makan wajib diisi."}), 400

    api_payload = {
        "pasien_id": pasien_id,
        "tanggal_makan": tanggal_makan,
        "menu_pagi": menu_pagi,
        "menu_siang": menu_siang,
        "menu_malam": menu_malam,
        "cemilan": cemilan
    }

    api_response, status_code, _ = api_request('POST', '/api/terapis/diet-plan', data=api_payload)

    if status_code == 201:
        flash('Pola makan berhasil dibuat!', 'success')
        patient_meal_plans = session.get(f'meal_plans_patient_{pasien_id}', [])
        patient_meal_plans.append(api_response.get('pola_makan', api_payload))
        session[f'meal_plans_patient_{pasien_id}'] = patient_meal_plans

        return jsonify(api_response), 201
    else:
        error_msg = api_response.get('msg', api_response.get('error', 'Terjadi kesalahan saat membuat pola makan.'))
        flash(f"Gagal membuat pola makan: {error_msg}", 'danger')
        return jsonify(api_response), status_code


@app.route('/program-report/<int:patient_id>/<int:program_id>')
def program_report_detail(patient_id, program_id):
    """
    Rute untuk melihat detail laporan program rehabilitasi.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        return redirect(url_for('login'))
    
    report_data_for_template = None
    program_info_for_header = None
    patient_data_for_template = {} 

    program_resp, prog_status, _ = api_request('GET', f'/api/program/{program_id}')

    if prog_status == 200 and isinstance(program_resp, dict) and 'program' in program_resp:
        program_data_from_api = program_resp['program']
        
        program_info_for_header = {
            "id": program_data_from_api.get("id"),
            "nama_program": program_data_from_api.get("nama_program"),
            "tanggal_program": program_data_from_api.get("tanggal_program"),
            "nama_terapis_program": program_data_from_api.get("terapis", {}).get("nama_lengkap", "N/A"),
            "list_gerakan_direncanakan": program_data_from_api.get("list_gerakan_direncanakan", [])
        }
        patient_data_for_template = program_data_from_api.get('pasien', {})
        patient_data_for_template['id'] = patient_data_for_template.get('id', patient_id)


        if 'laporan_terkait' in program_data_from_api and isinstance(program_data_from_api['laporan_terkait'], dict):
            report_data_for_template = program_data_from_api['laporan_terkait']
        else:
            program_name_for_flash = program_info_for_header.get('nama_program', 'N/A')
            flash(f"Laporan untuk program '{str(program_name_for_flash)}' belum disubmit oleh pasien.", "info")

    else:
        error_detail = program_resp.get('error', program_resp.get('msg', 'Error tidak diketahui dari server (Program API).')) if isinstance(program_resp, dict) else "Respons API program tidak valid."
        flash(f"Gagal mengambil detail program. Pesan: {str(error_detail)}", "danger")
        return redirect(url_for('patient_detail', patient_id=patient_id))

    if 'nama_lengkap' not in patient_data_for_template and 'nama' in patient_data_for_template:
        patient_data_for_template['nama_lengkap'] = patient_data_for_template['nama']

    # Pass Firebase config and custom token to template
    return render_template('program_report_detail.html', 
                            report_data_json=json.dumps(report_data_for_template if report_data_for_template else {}), 
                            program_info_header_json=json.dumps(program_info_for_header if program_info_for_header else {}), 
                            patient_info_json=json.dumps(patient_data_for_template if patient_data_for_template else {}),
                            patient=patient_data_for_template, 
                            username=get_current_user_name(),
                            active_page='patients',
                            firebase_config_json=json.dumps(FIREBASE_CLIENT_CONFIG),
                            firebase_custom_token=session.get('firebase_custom_token'),
                            app_id=app.name
    )


@app.route('/logout') 
def logout(): 
    """
    Rute untuk logout pengguna.
    """
    session.clear() 
    flash('Anda telah berhasil logout.', 'success')
    return redirect(url_for('login'))

@app.route('/create_movement', methods=['GET'])
def create_movement():
    """
    Rute untuk halaman membuat gerakan baru.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        flash("Sesi tidak valid atau Anda bukan terapis. Silakan login kembali.", "warning")
        return redirect(url_for('login'))
    # Pass Firebase config and custom token to template
    return render_template(
        'create_movement.html', 
        username=get_current_user_name(),
        firebase_config_json=json.dumps(FIREBASE_CLIENT_CONFIG),
        firebase_custom_token=session.get('firebase_custom_token'),
        app_id=app.name
    )


@app.route('/api/create_movement', methods=['POST'])
def create_new_movement():
    """
    API endpoint untuk membuat gerakan baru.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        flash("Sesi tidak valid atau Anda bukan terapis.", "warning")
        return redirect(url_for('login'))

    nama_gerakan = request.form.get('nama_gerakan')
    deskripsi = request.form.get('deskripsi', '')

    if not nama_gerakan:
        flash("Nama gerakan wajib diisi.", "danger")
        return redirect(url_for('create_movement'))

    payload_data = {
        "nama_gerakan": nama_gerakan,
        "deskripsi": deskripsi
    }

    files = {}
    if 'foto' in request.files:
        files['foto'] = (request.files['foto'].filename, request.files['foto'].read(), request.files['foto'].content_type)
    if 'video' in request.files:
        files['video'] = (request.files['video'].filename, request.files['video'].read(), request.files['video'].content_type)
    if 'model_tflite' in request.files:
        files['model_tflite'] = (request.files['model_tflite'].filename, request.files['model_tflite'].read(), request.files['model_tflite'].content_type)

    api_response, status_code, _ = api_request('POST', '/api/gerakan/', data=payload_data, files=files)

    if status_code == 201:
        flash('Gerakan baru berhasil dibuat!', 'success')
        return redirect(url_for('select_movements_view', patient_id=session.get('patient_id_for_activity', 0)))
    else:
        error_msg = api_response.get('msg', api_response.get('error', 'Terjadi kesalahan saat membuat gerakan baru.'))
        flash(f"Gagal membuat gerakan baru: {error_msg}", 'danger')
        return redirect(url_for('create_movement'))

# --- NEW ROUTE: Scoreboard ---
@app.route('/scoreboard')
def scoreboard():
    """
    Rute untuk menampilkan halaman leaderboard (papan peringkat) pasien.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        flash("Sesi tidak valid atau Anda bukan terapis. Silakan login kembali.", "warning")
        return redirect(url_for('login'))

    user_info = get_current_user_info()

    # Pass Firebase config and custom token to template
    return render_template(
        'scoreboard.html',
        username=user_info.get('nama_lengkap', user_info.get('username')),
        active_page='scoreboard',
        firebase_config_json=json.dumps(FIREBASE_CLIENT_CONFIG),
        firebase_custom_token=session.get('firebase_custom_token'),
        app_id=app.name
    )

# --- NEW API ENDPOINT: Leaderboard Data for Frontend ---
@app.route('/api/gamification/leaderboard', methods=['GET'])
def get_leaderboard_data_api(): # Ubah nama fungsi untuk menghindari konflik dengan rute FE /api/gamification/leaderboard di BE
    """
    API endpoint untuk frontend yang menyediakan data leaderboard pasien.
    Mendapatkan total poin untuk setiap pasien dari backend nyata.
    """
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401

    leaderboard_resp, status_code, _ = api_request('GET', '/api/gamification/leaderboard')

    if status_code == 200 and isinstance(leaderboard_resp, dict) and 'leaderboard' in leaderboard_resp:
        # Format data agar konsisten dengan ekspektasi frontend (misal: 'name' alih-alih 'nama_lengkap')
        formatted_leaderboard = []
        for entry in leaderboard_resp['leaderboard']:
            # PERBAIKAN: Tangani kasus None untuk 'highest_badge_info' dengan lebih aman
            highest_badge_info = entry.get('highest_badge_info')
            photo_url = (highest_badge_info or {}).get('image_url') 
            
            if not photo_url:
                # Jika tidak ada badge tertinggi atau image_url-nya kosong, gunakan default_avatar
                photo_url = url_for('static', filename='img/default_avatar.png')

            formatted_leaderboard.append({
                "id": entry.get('user_id'),
                "name": entry.get('nama_lengkap', entry.get('username')),
                "total_points": entry.get('total_points'),
                "photo_url": photo_url,
                "highest_badge_info": highest_badge_info # Tetap sertakan objek lengkap jika ada
            })
        
        # Backend sudah mengurutkan, tapi kita bisa pastikan lagi di FE
        sorted_leaderboard = sorted(formatted_leaderboard, key=lambda x: x["total_points"], reverse=True)
        
        return jsonify({"leaderboard": sorted_leaderboard}), 200
    else:
        error_msg = leaderboard_resp.get('msg', leaderboard_resp.get('error', 'Gagal mengambil data leaderboard dari API backend.'))
        return jsonify({"error": error_msg, "status_code": status_code}), status_code

# --- NEW ROUTE: Badges Management Page (Terapis) ---
@app.route('/badges', methods=['GET'])
def badges_management():
    """
    Rute untuk halaman manajemen badge (tampilan daftar semua badge dan opsi CRUD).
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        flash("Sesi tidak valid atau Anda bukan terapis. Silakan login kembali.", "warning")
        return redirect(url_for('login'))
    
    badges_resp, status_code, _ = api_request('GET', '/api/gamification/badges')
    
    all_badges = []
    if status_code == 200 and isinstance(badges_resp, dict) and 'badges' in badges_resp:
        for badge in badges_resp['badges']:
            # Pastikan ada URL gambar, jika tidak gunakan default
            if not badge.get('image_url'):
                badge['image_url'] = url_for('static', filename='img/default_badge.png')
            all_badges.append(badge)
    else:
        error_msg = badges_resp.get('msg', badges_resp.get('error', 'Gagal mengambil daftar badge.'))
        flash(f"Error mengambil badge: {error_msg}", "danger")

    return render_template(
        'badges_management.html',
        username=get_current_user_name(),
        active_page='badges',
        badges=all_badges,
        firebase_config_json=json.dumps(FIREBASE_CLIENT_CONFIG),
        firebase_custom_token=session.get('firebase_custom_token'),
        app_id=app.name
    )

# --- NEW ROUTE: Create Badge Page (Terapis) ---
@app.route('/badges/create', methods=['GET'])
def create_badge_page():
    """
    Rute untuk halaman form membuat badge baru.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        flash("Sesi tidak valid atau Anda bukan terapis. Silakan login kembali.", "warning")
        return redirect(url_for('login'))
    
    return render_template(
        'create_badge.html',
        username=get_current_user_name(),
        active_page='badges',
        firebase_config_json=json.dumps(FIREBASE_CLIENT_CONFIG),
        firebase_custom_token=session.get('firebase_custom_token'),
        app_id=app.name
    )

# --- NEW API ENDPOINT: Create Badge (Terapis) ---
@app.route('/api/badges', methods=['POST'])
def api_create_badge():
    """
    API endpoint untuk membuat badge baru melalui backend.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        return jsonify({"msg": "Unauthorized"}), 401

    # Data dari form-data (karena ada file upload)
    name = request.form.get('name')
    description = request.form.get('description')
    point_threshold = request.form.get('point_threshold')
    image_file = request.files.get('image')

    payload_data = {
        "name": name,
        "description": description,
        "point_threshold": point_threshold
    }
    
    files = {}
    if image_file:
        files['image'] = (image_file.filename, image_file.read(), image_file.content_type)

    api_response, status_code, _ = api_request('POST', '/api/gamification/badges', data=payload_data, files=files)

    if status_code == 201:
        flash('Badge berhasil dibuat!', 'success')
        return jsonify(api_response), 201
    else:
        error_msg = api_response.get('msg', api_response.get('error', 'Terjadi kesalahan saat membuat badge.'))
        return jsonify({"msg": f"Gagal membuat badge: {error_msg}"}), status_code

# --- NEW ROUTE: Edit Badge Page (Terapis) ---
@app.route('/badges/<int:badge_id>/edit', methods=['GET'])
def edit_badge_page(badge_id):
    """
    Rute untuk halaman form edit badge. Mengambil data badge yang sudah ada.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        flash("Sesi tidak valid atau Anda bukan terapis. Silakan login kembali.", "warning")
        return redirect(url_for('login'))
    
    badge_resp, status_code, _ = api_request('GET', f'/api/gamification/badges/{badge_id}')
    
    badge_data = {}
    if status_code == 200 and isinstance(badge_resp, dict):
        badge_data = badge_resp
        if not badge_data.get('image_url'):
            badge_data['image_url'] = url_for('static', filename='img/default_badge.png')
    else:
        error_msg = badge_resp.get('msg', badge_resp.get('error', 'Badge tidak ditemukan atau error mengambil data.'))
        flash(f"Error: {error_msg}", "danger")
        return redirect(url_for('badges_management'))

    return render_template(
        'edit_badge.html',
        username=get_current_user_name(),
        active_page='badges',
        badge=badge_data,
        firebase_config_json=json.dumps(FIREBASE_CLIENT_CONFIG),
        firebase_custom_token=session.get('firebase_custom_token'),
        app_id=app.name
    )

# --- NEW API ENDPOINT: Update Badge (Terapis) ---
@app.route('/api/badges/<int:badge_id>', methods=['POST']) # Menggunakan POST karena multipart/form-data tidak mendukung PUT
def api_update_badge(badge_id):
    """
    API endpoint untuk memperbarui badge melalui backend.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        return jsonify({"msg": "Unauthorized"}), 401

    # Data dari form-data
    name = request.form.get('name')
    description = request.form.get('description')
    point_threshold = request.form.get('point_threshold')
    image_file = request.files.get('image') # Bisa None jika tidak ada file baru

    # Buat payload data. Kirim hanya field yang ada di form
    payload_data = {}
    if name is not None: payload_data['name'] = name
    if description is not None: payload_data['description'] = description
    if point_threshold is not None: payload_data['point_threshold'] = point_threshold

    files = {}
    if image_file:
        files['image'] = (image_file.filename, image_file.read(), image_file.content_type)
    # Jika ada checkbox "hapus gambar" atau ingin mengganti dengan null, bisa ditambahkan logika
    # if request.form.get('remove_image') == 'true':
    #     files['image'] = ('', b'', 'application/octet-stream') # Mengirim file kosong untuk menghapus

    api_response, status_code, _ = api_request('PUT', f'/api/gamification/badges/{badge_id}', data=payload_data, files=files)

    if status_code == 200:
        flash('Badge berhasil diperbarui!', 'success')
        return jsonify(api_response), 200
    else:
        error_msg = api_response.get('msg', api_response.get('error', 'Terjadi kesalahan saat memperbarui badge.'))
        return jsonify({"msg": f"Gagal memperbarui badge: {error_msg}"}), status_code

# --- NEW API ENDPOINT: Delete Badge (Terapis) ---
@app.route('/api/badges/<int:badge_id>/delete', methods=['POST'])
def api_delete_badge(badge_id):
    """
    API endpoint untuk menghapus badge melalui backend.
    """
    if not is_logged_in() or get_current_user_role() != 'terapis':
        return jsonify({"msg": "Unauthorized"}), 401

    api_response, status_code, _ = api_request('DELETE', f'/api/gamification/badges/{badge_id}')

    if status_code == 200:
        flash('Badge berhasil dihapus!', 'success')
        return jsonify(api_response), 200
    else:
        error_msg = api_response.get('msg', api_response.get('error', 'Terjadi kesalahan saat menghapus badge.'))
        return jsonify({"msg": f"Gagal menghapus badge: {error_msg}"}), status_code


if __name__ == '__main__':
    app.run(debug=True, port=5000)
