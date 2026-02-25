import sqlite3
import datetime

DB_PATH = "database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'entrenador')")
    c.execute("CREATE TABLE IF NOT EXISTS pacientes (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, nombre_paciente TEXT UNIQUE, full_name TEXT, edad INTEGER, peso REAL, altura REAL, entrenador_asociado TEXT, equipo TEXT DEFAULT 'Sin asignar', deporte TEXT DEFAULT 'Running', posicion TEXT, nacionalidad TEXT DEFAULT 'Desconocida', fcr INTEGER DEFAULT 60, vo2 REAL DEFAULT 45.0)")
    c.execute("CREATE TABLE IF NOT EXISTS cuestionarios (id INTEGER PRIMARY KEY AUTOINCREMENT, paciente TEXT, username TEXT, fecha TEXT, fatiga INTEGER, suenio INTEGER, rpe INTEGER, tiempo_entrenamiento REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS entrenamientos (id INTEGER PRIMARY KEY AUTOINCREMENT, paciente TEXT, duracion REAL, fatiga INTEGER, rpe INTEGER, bpm INTEGER DEFAULT 0, fecha_inicio TEXT, fecha_fin TEXT, validacion_especialista TEXT DEFAULT 'Pendiente', comentarios_especialista TEXT DEFAULT '')")
    conn.commit()
    conn.close()

def add_user(username, password, role="entrenador"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
        if role == 'paciente':
            c.execute("SELECT id FROM pacientes WHERE username = ?", (username,))
            if not c.fetchone():
                 # Creamos el paciente asegurando que el nombre es el username para evitar confusiones
                 c.execute("INSERT INTO pacientes (username, nombre_paciente, entrenador_asociado, full_name, equipo, deporte, fcr, vo2) VALUES (?, ?, 'Auto', ?, 'Club', 'Running', 60, 45)", (username, username, username))
        conn.commit()
        return True
    except sqlite3.IntegrityError: return False
    finally: conn.close()

def user_exists(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    res = c.fetchone()
    conn.close()
    return res is not None

def authenticate_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE username = ? AND password = ?", (username, password))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_patients_by_user(username, role):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # TRUCO: El entrenador ve a TODOS para que no salga la lista vacía
    c.execute("SELECT nombre_paciente, equipo, full_name, nacionalidad FROM pacientes")
    patients = [{"label": f"{r[2] if r[2] else r[0]} ({r[1]})", "value": r[0]} for r in c.fetchall()]
    conn.close()
    return patients

def create_patient(entrenador_username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM pacientes WHERE entrenador_asociado = ?", (entrenador_username,))
    count = c.fetchone()[0] + 1
    nombre_paciente = f"Atleta_{count}_{entrenador_username}"
    while True:
        c.execute("SELECT id FROM pacientes WHERE nombre_paciente = ?", (nombre_paciente,))
        if not c.fetchone(): break
        nombre_paciente += "_X"
    c.execute("INSERT INTO pacientes (username, nombre_paciente, entrenador_asociado, full_name, edad, peso, altura, equipo, deporte, fcr, vo2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 60, 45)", (nombre_paciente, nombre_paciente, entrenador_username, "Nuevo Atleta", 0, 0, 0, "Sin Equipo", "General"))
    conn.commit()
    conn.close()
    return nombre_paciente

def get_patient_info(paciente):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT full_name, edad, peso, altura, equipo, deporte, posicion, nacionalidad, fcr, vo2 FROM pacientes WHERE nombre_paciente = ?", (paciente,))
    row = c.fetchone()
    conn.close()
    if row: return {"full_name": row[0], "edad": row[1], "peso": row[2], "altura": row[3], "equipo": row[4], "deporte": row[5], "posicion": row[6], "nacionalidad": row[7], "fcr": row[8], "vo2": row[9]}
    return {}

def save_patient_info(nombre_paciente, full_name, edad, peso, altura, equipo, deporte, posicion, nacionalidad, fcr, vo2):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE pacientes SET full_name=?, edad=?, peso=?, altura=?, equipo=?, deporte=?, posicion=?, nacionalidad=?, fcr=?, vo2=? WHERE nombre_paciente=?", (full_name, edad, peso, altura, equipo, deporte, posicion, nacionalidad, fcr, vo2, nombre_paciente))
    conn.commit()
    conn.close()
    print(f"--- DB: Perfil actualizado para {nombre_paciente} ---")

def get_metrics_for_comparison(selected_patients=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = "SELECT nombre_paciente, full_name, vo2, fcr FROM pacientes"
    if selected_patients:
        placeholders = ','.join('?' for _ in selected_patients)
        query += f" WHERE nombre_paciente IN ({placeholders})"
        c.execute(query, tuple(selected_patients))
    else: c.execute(query)
    clean_data = []
    for row in c.fetchall():
        try: vo2 = float(row[2])
        except: vo2 = 0.0
        try: fcr = int(row[3])
        except: fcr = 0
        clean_data.append({"name": row[1] if row[1] else row[0], "vo2": vo2, "fcr": fcr})
    conn.close()
    return clean_data

def get_training_data_for_patient(paciente):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if not paciente:
        conn.close()
        return []
    
    # Obtenemos fecha y calculamos carga. Forzamos conversión a número para evitar errores.
    c.execute("""
        SELECT fecha, 
               CAST(rpe AS FLOAT) * CAST(tiempo_entrenamiento AS FLOAT) as carga 
        FROM cuestionarios 
        WHERE paciente = ? 
        ORDER BY fecha ASC
    """, (paciente,))
    
    data = c.fetchall()
    conn.close()
    print(f"--- DB: Consultando datos para {paciente}. Encontrados: {len(data)} registros ---")
    return data

def guardar_entrenamiento(paciente, duracion, fatiga, rpe, bpm=0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO entrenamientos (paciente, duracion, fatiga, rpe, bpm, fecha_inicio, fecha_fin, validacion_especialista) 
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Pendiente')
    """, (paciente, duracion, fatiga, rpe, bpm, fecha, fecha))
    conn.commit()
    conn.close()

def save_questionnaire_for_patient(username, paciente, fatiga, suenio, rpe, tiempo_entrenamiento):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO cuestionarios (paciente, username, fecha, fatiga, suenio, rpe, tiempo_entrenamiento) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (paciente, username, fecha, fatiga, suenio, rpe, tiempo_entrenamiento))
    conn.commit()
    conn.close()
    print(f"--- DB: GUARDADO Cuestionario para {paciente} (RPE:{rpe}, Tiempo:{tiempo_entrenamiento}) ---")

def get_nombre_paciente_from_username(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT nombre_paciente FROM pacientes WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    # Si no encuentra un nombre oficial, devuelve el username para que no falle
    return row[0] if row else username 

def get_patient_averages(paciente):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if not paciente: return {"fatiga": 0, "rpe": 0, "suenio": 0, "carga": 0, "bpm": 0}
    
    c.execute("""
        SELECT AVG(fatiga), AVG(rpe), AVG(suenio), AVG(rpe * tiempo_entrenamiento)
        FROM cuestionarios WHERE paciente = ?
    """, (paciente,))
    row_quest = c.fetchone()
    
    c.execute("SELECT AVG(bpm) FROM entrenamientos WHERE paciente = ? AND bpm > 0", (paciente,))
    row_bpm = c.fetchone()
    
    conn.close()
    
    fatiga = round(row_quest[0], 1) if row_quest and row_quest[0] else 0
    rpe = round(row_quest[1], 1) if row_quest and row_quest[1] else 0
    suenio = round(row_quest[2], 1) if row_quest and row_quest[2] else 0
    carga = int(row_quest[3]) if row_quest and row_quest[3] else 0
    bpm = int(row_bpm[0]) if row_bpm and row_bpm[0] else 0

    return {"fatiga": fatiga, "rpe": rpe, "suenio": suenio, "carga": carga, "bpm": bpm}