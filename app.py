# Website-Monitoring/app.py

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import requests
import json
from datetime import date, datetime

app = Flask(__name__)
# GANTI INI DENGAN KUNCI RAHASIA YANG KUAT DAN UNIK UNTUK APLIKASI WEBSITE ANDA!
app.secret_key = 'website_monitoring_super_secret_key_CHANGE_ME_PLEASE_AGAIN' 

# --- Konfigurasi untuk API Backend BE-RESTRO ---
API_BASE_URL = "http://127.0.0.1:5001"

# --- Fungsi Helper untuk Request ke API Backend ---
def api_request(method, endpoint, data=None, params=None, files=None, use_token=True):
    headers = {}
    if use_token:
        token = session.get('access_token')
        if token:
            headers['Authorization'] = f"Bearer {token}"
    
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if files:
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
    return 'access_token' in session and 'user_info' in session

def get_current_user_info():
    return session.get('user_info', {})

def get_current_user_role():
    return get_current_user_info().get('role')

def get_current_user_name():
    user_info = get_current_user_info()
    return user_info.get('nama_lengkap', user_info.get('username', 'Terapis'))

# --- Filter Jinja untuk Format Tanggal ---
@app.template_filter('format_date_id')
def format_date_filter_jinja(value, format='%d %B %Y'):
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
    return {'now': datetime.utcnow()}

# --- Rute Aplikasi Website ---

@app.route('/')
def index():
    if is_logged_in() and get_current_user_role() == 'terapis':
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
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
            session['logged_in'] = True # Tambahkan baris ini untuk mengatur session.logged_in
            print(f"DEBUG (Login Success): Session content after successful login: {dict(session)}") # Debugging print
            flash('Login berhasil!', 'success')
            return redirect(url_for('home'))
        else:
            error_msg = "Login gagal. "
            if isinstance(api_response, dict):
                error_msg += str(api_response.get('msg', api_response.get('error', 'Detail error tidak tersedia dari server.')))
            else: 
                error_msg += f"Tidak dapat memproses respons dari server. (Status: {status_code})"
            flash(error_msg, 'danger')
            print(f"DEBUG (Login Failed): API Response: {api_response}, Status Code: {status_code}") # Debugging print
            return render_template('login.html', error=error_msg)
            
    return render_template('login.html')


@app.route('/home')
def home():
    # --- DEBUGGING: Cetak status sesi saat mengakses /home ---
    print(f"DEBUG (/home accessed): is_logged_in() = {is_logged_in()}, session.get('logged_in') = {session.get('logged_in')}, session.get('user_info') = {session.get('user_info') is not None}")
    print(f"DEBUG (/home accessed): Full session content: {dict(session)}")
    # --- AKHIR DEBUGGING ---

    if not is_logged_in() or get_current_user_role() != 'terapis':
        flash("Sesi tidak valid atau Anda bukan terapis. Silakan login kembali.", "warning")
        return redirect(url_for('login'))
    
    user_info = get_current_user_info()
    
    dashboard_data_resp, status_code, _ = api_request('GET', '/api/terapis/dashboard-summary')
    
    # Initialize with default values
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
             # Ensure program.id and program.patient_id are integers, with fallback to 0
             program_id = p_data.get('id')
             patient_id_for_program = p_data.get('patient_id')
             
             try:
                 program_id = int(program_id) if program_id is not None else 0
             except (ValueError, TypeError):
                 program_id = 0
             
             try:
                 patient_id_for_program = int(patient_id_for_program) if patient_id_for_program is not None else 0
             except (ValueError, TypeError):
                 patient_id_for_program = 0

             programs_for_display_home.append({
                 'id': program_id, 
                 'program_name': p_data.get('program_name'), # Corrected key
                 'patient_name': p_data.get('patient_name'), # Corrected key
                 'patient_id': patient_id_for_program, # Corrected key
                 'execution_date': p_data.get('execution_date'), # Corrected key
                 'status': p_data.get('status'),
                 'movements_details': p_data.get('movements_details', []) # Pass full movements_details
             })

        statistik_bulanan = dashboard_data_resp.get('chart_data_patients_per_day', {}) # Use chart_data_patients_per_day as per API response
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

    # Map KPI data to more readable names for the template
    total_patients_handled = kpi_data.get('total_pasien_ditangani', 0)
    total_patients_rehab_today = kpi_data.get('pasien_rehabilitasi_hari_ini', 0)
    count_patients_completed_rehab = kpi_data.get('pasien_selesai_rehabilitasi_hari_ini', 0)


    return render_template(
        'home.html',
        username=user_info.get('nama_lengkap', user_info.get('username')),
        active_page='home',
        total_patients_handled=total_patients_handled,
        total_patients_rehab_today=total_patients_rehab_today,
        count_patients_completed_rehab=count_patients_completed_rehab,
        therapist_programs=programs_for_display_home, 
        chart_data_patients_per_month_json=json.dumps(chart_data_patients_per_month)
    )

@app.route('/patients')
def patients(): 
    # --- DEBUGGING: Cetak status sesi saat mengakses /patients ---
    print(f"DEBUG (/patients accessed): is_logged_in() = {is_logged_in()}, session.get('logged_in') = {session.get('logged_in')}, session.get('user_info') = {session.get('user_info') is not None}")
    print(f"DEBUG (/patients accessed): Full session content: {dict(session)}")
    # --- AKHIR DEBUGGING ---

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

    return render_template('patients.html', patients=patient_list_from_api, username=get_current_user_name(), active_page='patients')

@app.route('/patient/<int:patient_id>')
def patient_detail(patient_id):
    # --- DEBUGGING: Cetak status sesi saat mengakses /patient/<id> ---
    print(f"DEBUG (/patient/<id> accessed): is_logged_in() = {is_logged_in()}, session.get('logged_in') = {session.get('logged_in')}, session.get('user_info') = {session.get('user_info') is not None}")
    print(f"DEBUG (/patient/<id> accessed): Full session content: {dict(session)}")
    # --- AKHIR DEBUGGING ---

    if not is_logged_in() or get_current_user_role() != 'terapis':
        return redirect(url_for('login'))

    monitoring_data_api, monitoring_status, _ = api_request('GET', f'/api/monitoring/summary/pasien/{patient_id}')
    
    patient_info_for_header = {} 
    if monitoring_status == 200 and isinstance(monitoring_data_api, dict):
        patient_info_for_header = monitoring_data_api.get('pasien_info', {})
        
        # Ensure 'id' key exists in patient_info_for_header, using 'user_id' from API if available
        # Otherwise, fall back to the patient_id from the URL
        patient_info_for_header['id'] = patient_info_for_header.get('user_id', patient_id)

        if 'nama' not in patient_info_for_header and 'nama_lengkap' in patient_info_for_header:
            patient_info_for_header['nama'] = patient_info_for_header['nama_lengkap']
        foto_profil_val = patient_info_for_header.get('url_foto_profil', patient_info_for_header.get('foto_filename'))
        if foto_profil_val and (foto_profil_val.startswith('http://') or foto_profil_val.startswith('https://')):
             patient_info_for_header['foto_src_display'] = foto_profil_val
        else:
             patient_info_for_header['foto_src_display'] = url_for('static', filename='img/default_avatar.png')

        # Add flash messages for missing sections from monitoring_data_api
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

    # REVERTED: Fetch patient_rehab_history from its dedicated API endpoint
    rehab_history_resp, rehab_history_status, _ = api_request('GET', f'/api/program/terapis/assigned-to-patient/{patient_id}', params={'per_page': 100})
    
    patient_rehab_history_for_tab = []
    if rehab_history_status == 200 and isinstance(rehab_history_resp, dict) and 'programs' in rehab_history_resp:
        patient_rehab_history_for_tab = rehab_history_resp['programs']
    elif isinstance(rehab_history_resp, dict) and 'msg' in rehab_history_resp:
          flash(f"Info: Gagal mengambil riwayat program rehabilitasi: {str(rehab_history_resp['msg'])}", "info")
    else:
          flash("Info: Riwayat program rehabilitasi tidak tersedia atau gagal diambil.", "info")

    # Patient meal plans (currently stored in session)
    # Since there's no API to fetch existing meal plans, we'll continue to rely on the session
    # for displaying previously added meal plans within the current session.
    patient_meal_plans = session.get(f'meal_plans_patient_{patient_id}', [])

    return render_template('patient_detail.html', 
                           patient=patient_info_for_header, 
                           monitoring_data_js=json.dumps(monitoring_data_api if isinstance(monitoring_data_api,dict) else {}),
                           patient_rehab_history=patient_rehab_history_for_tab, 
                           patient_meal_plans_json=json.dumps(patient_meal_plans), 
                           username=get_current_user_name(),
                           active_page='patients')


# Rute baru untuk menyimpan data form sementara di sesi
@app.route('/save_add_activity_form_temp', methods=['POST'])
def save_add_activity_form_temp():
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
    if not is_logged_in():
        return redirect(url_for('login'))
    
    patient_info_resp, pi_status, _ = api_request('GET', f'/api/monitoring/summary/pasien/{patient_id}')
    patient_info_for_form = {}
    if pi_status == 200 and isinstance(patient_info_resp, dict) and 'pasien_info' in patient_info_resp:
        patient_info_for_form = patient_info_resp['pasien_info']
        # Ensure 'id' key exists for form, using 'user_id' from API if available
        patient_info_for_form['id'] = patient_info_for_form.get('user_id', patient_id)
    else:
        flash(f"Gagal mengambil info pasien (ID: {patient_id}).", "danger")
        return redirect(url_for('patient_detail', patient_id=patient_id))

    # Ambil data form yang disimpan dari sesi untuk request GET
    # Gunakan .pop() untuk menghapus data dari sesi setelah diambil
    saved_form_data = session.pop('add_activity_form_data', {}) 
    if 'execution_date' in saved_form_data and saved_form_data['execution_date']:
        try:
            # Reformat the date to YYYY-MM-DD for the input type="date"
            saved_form_data['execution_date'] = datetime.strptime(saved_form_data['execution_date'], '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            # If the format is already different or invalid, keep it as is or handle error
            pass


    if request.method == 'POST':
        try:
            gerakan_data_str = request.form.get('selected_movements_data_json', '[]')
            selected_movements = json.loads(gerakan_data_str)

            if not selected_movements:
                flash("Harap pilih minimal satu gerakan untuk program ini.", "warning")
                # Simpan kembali data form ke sesi jika validasi gagal
                session['add_activity_form_data'] = { 
                    'program_name': request.form.get('program_name', ''),
                    'execution_date': request.form.get('execution_date', ''),
                    'catatan_terapis': request.form.get('catatan_terapis', '')
                }
                return redirect(url_for('add_activity', patient_id=patient_id))

            # --- PERBAIKAN 1: Mengubah struktur data agar sesuai dengan API Backend ---
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
                session.pop('add_activity_form_data', None) # Hapus data form setelah sukses submit
                return redirect(url_for('patient_detail', patient_id=patient_id))
            else:
                error_msg = response_data.get('msg', response_data.get('error', 'Error tidak diketahui dari server.'))
                flash(f"Gagal membuat program: {error_msg}", 'danger')
                # Jika POST gagal, simpan kembali data form di sesi untuk ditampilkan ulang
                session['add_activity_form_data'] = {
                    'program_name': request.form.get('program_name', ''),
                    'execution_date': request.form.get('execution_date', ''),
                    'catatan_terapis': request.form.get('catatan_terapis', '')
                }
        
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            flash(f"Terjadi kesalahan dalam memproses data gerakan: {str(e)}", "danger")
            # Simpan kembali data form di sesi jika terjadi error
            session['add_activity_form_data'] = { 
                'program_name': request.form.get('program_name', ''),
                'execution_date': request.form.get('execution_date', ''),
                'catatan_terapis': request.form.get('catatan_terapis', '')
            }

    selected_movements_from_session = []
    if session.get('patient_id_for_activity') == patient_id:
        selected_movements_from_session = session.get('selected_movements_for_activity', [])

    return render_template(
        'add_activity.html', 
        patient=patient_info_for_form,
        username=get_current_user_name(),
        selected_movements_from_session_json=json.dumps(selected_movements_from_session),
        form_data=saved_form_data, # Teruskan data form yang diambil dari sesi ke template
        now=datetime.utcnow()
    )

@app.route('/patient/<int:patient_id>/select_movements')
def select_movements_view(patient_id):
    if not is_logged_in():
        return redirect(url_for('login'))
        
    patient_info_resp, _, _ = api_request('GET', f'/api/monitoring/summary/pasien/{patient_id}')
    gerakan_resp, _, _ = api_request('GET', '/api/gerakan', params={'per_page': 1000}) 
    
    patient_info = patient_info_resp.get('pasien_info', {}) if isinstance(patient_info_resp, dict) else {}
    # Ensure 'id' key exists for patient_info, using 'user_id' from API if available
    patient_info['id'] = patient_info.get('user_id', patient_id)

    all_movements = gerakan_resp.get('gerakan', []) if isinstance(gerakan_resp, dict) else []

    selected_in_session = []
    if session.get('patient_id_for_activity') == patient_id:
        selected_in_session = session.get('selected_movements_for_activity', [])

    return render_template(
        'select_movements.html',
        patient=patient_info,
        movements=all_movements,
        selected_movements_json_str=json.dumps(selected_in_session),
        username=get_current_user_name()
    )


@app.route('/patient/<int:patient_id>/update_selected_movements', methods=['POST'])
def update_selected_movements_view(patient_id): 
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401 
    
    data = request.get_json()
    if not data or 'selected_movements' not in data:
        return jsonify({"error": "Data 'selected_movements' tidak ditemukan"}), 400
        
    session['selected_movements_for_activity'] = data.get('selected_movements', [])
    session['patient_id_for_activity'] = patient_id 
    return jsonify({"msg": "Pilihan gerakan berhasil disimpan di sesi."}), 200

# MODIFIED: Route for saving meal plan, now integrates with /api/terapis/diet-plan
@app.route('/api/terapis/diet-plan', methods=['POST'])
def create_diet_plan():
    if not is_logged_in() or get_current_user_role() != 'terapis':
        return jsonify({"error": "Unauthorized"}), 401
    
    request_data = request.get_json()
    if not request_data:
        return jsonify({"error": "No data provided"}), 400

    # Extract data according to the API spec
    pasien_id = request_data.get('pasien_id')
    tanggal_makan = request_data.get('tanggal_makan')
    menu_pagi = request_data.get('menu_pagi', '')
    menu_siang = request_data.get('menu_siang', '')
    menu_malam = request_data.get('menu_malam', '')
    cemilan = request_data.get('cemilan', '')

    # Basic validation (add more as needed)
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

    # Call the backend API
    api_response, status_code, _ = api_request('POST', '/api/terapis/diet-plan', data=api_payload)

    if status_code == 201:
        flash('Pola makan berhasil dibuat!', 'success')
        # Optionally, you might want to refresh the local session's meal plans
        # by fetching from a (hypothetical) API that retrieves all meal plans for a patient.
        # Since that API isn't provided, we'll mimic by updating the session here
        # to include the newly created plan (for display purposes).
        # In a real app, you'd fetch the updated list from the backend.
        
        # Add the new meal plan to the session data for immediate display
        patient_meal_plans = session.get(f'meal_plans_patient_{pasien_id}', [])
        patient_meal_plans.append(api_response.get('pola_makan', api_payload)) # Use returned data if available, else request payload
        session[f'meal_plans_patient_{pasien_id}'] = patient_meal_plans

        return jsonify(api_response), 201
    else:
        error_msg = api_response.get('msg', api_response.get('error', 'Terjadi kesalahan saat membuat pola makan.'))
        flash(f"Gagal membuat pola makan: {error_msg}", 'danger')
        return jsonify(api_response), status_code


@app.route('/program-report/<int:patient_id>/<int:program_id>')
def program_report_detail(patient_id, program_id):
    if not is_logged_in() or get_current_user_role() != 'terapis':
        return redirect(url_for('login'))
    
    report_data_for_template = None
    program_info_for_header = None
    patient_data_for_template = {} 

    # Attempt to fetch program details first, as it might contain 'laporan_terkait'
    program_resp, prog_status, _ = api_request('GET', f'/api/program/{program_id}')

    if prog_status == 200 and isinstance(program_resp, dict) and 'program' in program_resp:
        program_data_from_api = program_resp['program']
        
        # Populate program_info_for_header from the program data
        program_info_for_header = {
            "id": program_data_from_api.get("id"),
            "nama_program": program_data_from_api.get("nama_program"),
            "tanggal_program": program_data_from_api.get("tanggal_program"),
            "nama_terapis_program": program_data_from_api.get("terapis", {}).get("nama_lengkap", "N/A"),
            "list_gerakan_direncanakan": program_data_from_api.get("list_gerakan_direncanakan", []) # Include planned movements
        }
        patient_data_for_template = program_data_from_api.get('pasien', {})
        # Ensure 'id' for patient_data_for_template, using 'id' from program_data_from_api['pasien'] or fallback
        patient_data_for_template['id'] = patient_data_for_template.get('id', patient_id)


        # Check if 'laporan_terkait' exists within the program data
        if 'laporan_terkait' in program_data_from_api and isinstance(program_data_from_api['laporan_terkait'], dict):
            report_data_for_template = program_data_from_api['laporan_terkait']
            # If report is found here, it's considered successfully loaded. No flash message needed.
        else:
            # No 'laporan_terkait' found in program details, means report not submitted yet.
            program_name_for_flash = program_info_for_header.get('nama_program', 'N/A')
            flash(f"Laporan untuk program '{str(program_name_for_flash)}' belum disubmit oleh pasien.", "info")

    else:
        # Failed to get program details at all
        error_detail = program_resp.get('error', program_resp.get('msg', 'Error tidak diketahui dari server (Program API).')) if isinstance(program_resp, dict) else "Respons API program tidak valid."
        flash(f"Gagal mengambil detail program. Pesan: {str(error_detail)}", "danger")
        return redirect(url_for('patient_detail', patient_id=patient_id))

    # Ensure patient_data_for_template is consistent with patient_id if it wasn't properly set by program/report data
    # This block can be simplified as the patient_data_for_template is already populated from program_resp['program']['pasien']
    # And its 'id' is already ensured above.
    if 'nama_lengkap' not in patient_data_for_template and 'nama' in patient_data_for_template:
        patient_data_for_template['nama_lengkap'] = patient_data_for_template['nama']

    return render_template('program_report_detail.html', 
                           report_data_json=json.dumps(report_data_for_template if report_data_for_template else {}), 
                           program_info_header_json=json.dumps(program_info_for_header if program_info_for_header else {}), 
                           patient_info_json=json.dumps(patient_data_for_template if patient_data_for_template else {}),
                           patient=patient_data_for_template, 
                           username=get_current_user_name(),
                           active_page='patients')


@app.route('/logout') 
def logout(): 
    # Menghapus semua data dari sesi pengguna
    session.clear() 
    # Menampilkan pesan sukses kepada pengguna
    flash('Anda telah berhasil logout.', 'success')
    # Mengarahkan pengguna kembali ke halaman login
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
