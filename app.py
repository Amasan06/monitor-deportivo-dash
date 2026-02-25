import dash
from dash import dcc, html, Input, Output, State, no_update, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import sqlite3
import os


# Importaciones locales
from db import (
    init_db, add_user, user_exists, authenticate_user,
    get_patients_by_user, get_patient_info, save_patient_info,
    guardar_entrenamiento, create_patient,
    save_questionnaire_for_patient, get_nombre_paciente_from_username,
    get_patient_averages, get_training_data_for_patient
)
from questionnaires import questionnaire_layout, get_training_data, get_comparison_figure
from sensors import load_ecg_and_compute_bpm


# Inicialización
init_db()


external_stylesheets = [dbc.themes.DARKLY]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app = dash.Dash(__name__)
server = app.server 
app.title = "BioMonitor Pro"


COLOR_BG = "#121212"
COLOR_CARD = "#1E1E1E"


# -------------------------------------------------------------------------
# GHOSTS (Elementos ocultos OBLIGATORIOS)
# -------------------------------------------------------------------------
def get_runner_ghosts():
    return html.Div(style={"display": "none"}, children=[
        dbc.Button(id="btn-view-register"), dbc.Button(id="btn-view-graphs"), dbc.Button(id="btn-run-save-profile"),
        dbc.Button(id="btn-back-to-register"),
        dbc.Input(id="run-name"), dbc.Input(id="run-nac"), dbc.Input(id="run-age"), dbc.Input(id="run-fcr"), dbc.Input(id="run-vo2"),
        html.Div(id="runner-register-view"), html.Div(id="runner-graphs-view"),
        dcc.Graph(id="runner-graph-load"), dcc.Graph(id="runner-graph-compare"),
        html.Div(id="kpi-fatiga"), html.Div(id="kpi-rpe"), html.Div(id="kpi-suenio"), html.Div(id="kpi-carga"), html.Div(id="kpi-bpm"),
        html.Div(id="data-debug-msg"),
        dcc.Input(id="fatiga"), dcc.Input(id="suenio"), dcc.Input(id="rpe"), dbc.Input(id="tiempo_entrenamiento"),
        dcc.Dropdown(id="sensor-file-dropdown"), html.Div(id="ecg-graph-container"),      
        dbc.Button(id="submit-questionnaire"), html.Div(id="runner-feedback")
    ])


def get_manager_ghosts():
    return html.Div(style={"display": "none"}, children=[
        dbc.Button(id="btn-new-patient"),
        dcc.Dropdown(id="patient-dropdown"),
        html.Div(id="dashboard-content"),
        html.Div(id="patient-list")
    ])


# -------------------------------------------------------------------------
# LOGIN
# -------------------------------------------------------------------------
def login_layout():
    login_form = html.Div(id="login-view", children=[
        dbc.Form([
            dbc.Input(id="log-user", placeholder="Usuario", className="mb-3 bg-dark text-white"),
            dbc.Input(id="log-pass", placeholder="Contraseña", type="password", className="mb-3 bg-dark text-white"),
            dbc.Button("Iniciar Sesión", id="btn-log", color="primary", className="w-100 rounded-pill")
        ])
    ])
    register_form = html.Div(id="register-view", style={"display": "none"}, children=[
        dbc.Form([
            dbc.Input(id="reg-user", placeholder="Nuevo Usuario", className="mb-2 bg-dark text-white"),
            dbc.Input(id="reg-pass", placeholder="Nueva Contraseña", type="password", className="mb-3 bg-dark text-white"),
            dbc.RadioItems(options=[{"label": "Corredor", "value": "paciente"}, {"label": "Entrenador", "value": "entrenador"}],
                value="paciente", id="reg-role", inline=True, className="mb-3 small"),
            dbc.Button("Crear Cuenta", id="btn-reg", color="success", className="w-100 rounded-pill")
        ])
    ])
    return dbc.Container([
        dbc.Card([
            dbc.CardBody([
                html.H2("BioMonitor Pro", className="text-center mb-4 text-white"),
                dbc.Tabs([dbc.Tab(label="Entrar", tab_id="tab-login"), dbc.Tab(label="Registro", tab_id="tab-register")], id="login-tabs", active_tab="tab-login", className="mb-4"),
                login_form, register_form, html.Div(id="auth-feedback", className="mt-3 text-center"),
                get_runner_ghosts(), get_manager_ghosts(), html.Div(dbc.Button(id="btn-logout"), style={"display": "none"})
            ])
        ], style={"backgroundColor": COLOR_CARD, "maxWidth": "450px", "margin": "50px auto"}, className="shadow-lg")
    ], fluid=True)


# -------------------------------------------------------------------------
# DASHBOARD CORREDOR (ATLETA)
# -------------------------------------------------------------------------
def runner_dashboard_layout(username):
    pac_name = get_nombre_paciente_from_username(username)
    info = get_patient_info(pac_name) if pac_name else {}
   
    register_view = html.Div(id="runner-register-view", children=[
        html.H3("📝 Mis Datos", className="text-white mb-4 text-center"),
        dbc.Card([dbc.CardHeader("Perfil Físico"), dbc.CardBody([
                dbc.Row([dbc.Col([html.Label("Nombre"), dbc.Input(id="run-name", value=info.get("full_name",""), className="bg-dark text-white mb-2")]),
                         dbc.Col([html.Label("Nacionalidad"), dbc.Input(id="run-nac", value=info.get("nacionalidad",""), className="bg-dark text-white mb-2")])]),
                dbc.Row([dbc.Col([html.Label("FCR (Reposo)"), dbc.Input(id="run-fcr", type="number", value=info.get("fcr",60), className="bg-dark text-white")]),
                         dbc.Col([html.Label("VO2 Max"), dbc.Input(id="run-vo2", type="number", value=info.get("vo2",45), className="bg-dark text-white")])], className="mb-3"),
                dbc.Button("💾 Actualizar Perfil", id="btn-run-save-profile", color="success", size="sm", className="w-100")
        ])], style={"backgroundColor": COLOR_CARD}, className="mb-4"),


        dbc.Card([dbc.CardHeader("Sesión de Hoy"), dbc.CardBody(questionnaire_layout)], style={"backgroundColor": COLOR_CARD}),
        html.Div(id="runner-feedback", className="mt-3 text-center")
    ])


    graphs_view = html.Div(id="runner-graphs-view", style={"display": "none"}, children=[
        dbc.Row([dbc.Col(html.H3("📊 Tu Rendimiento", className="text-white"), width=8), dbc.Col(dbc.Button("🔙 Volver", id="btn-back-to-register", color="light", outline=True, className="float-end"), width=4)], className="mb-4"),
       
        html.Div(id="data-debug-msg", className="text-center mb-3 text-info small"),


        dbc.Row([
            dbc.Col(dbc.Card([dbc.CardBody([html.H6("Media Fatiga", className="text-muted"), html.H2(id="kpi-fatiga", className="text-warning")])], style={"backgroundColor": COLOR_CARD}, className="mb-3"), width=6, lg=3),
            dbc.Col(dbc.Card([dbc.CardBody([html.H6("Media RPE", className="text-muted"), html.H2(id="kpi-rpe", className="text-danger")])], style={"backgroundColor": COLOR_CARD}, className="mb-3"), width=6, lg=3),
            dbc.Col(dbc.Card([dbc.CardBody([html.H6("Media Sueño", className="text-muted"), html.H2(id="kpi-suenio", className="text-info")])], style={"backgroundColor": COLOR_CARD}, className="mb-3"), width=6, lg=3),
            dbc.Col(dbc.Card([dbc.CardBody([html.H6("BPM Medio", className="text-muted"), html.H2(id="kpi-bpm", className="text-success")])], style={"backgroundColor": COLOR_CARD}, className="mb-3"), width=6, lg=3),
        ]),
        dbc.Row([
            dbc.Col(dbc.Card([dbc.CardHeader("Evolución de Carga"), dbc.CardBody(dcc.Graph(id="runner-graph-load", style={"height": "350px"}))], style={"backgroundColor": COLOR_CARD}), md=12, className="mb-4"),
            dbc.Col(dbc.Card([dbc.CardHeader("Comparativa con Equipo"), dbc.CardBody(dcc.Graph(id="runner-graph-compare", style={"height": "350px"}))], style={"backgroundColor": COLOR_CARD}), md=12),
        ])
    ])


    return dbc.Container([
        html.Div([html.H2(f"Hola, {username}", className="text-white"), html.P("Panel Atleta", className="text-muted")], className="py-4"),
        dbc.Row([dbc.Col(dbc.Button("📝 REGISTRO", id="btn-view-register", color="primary", className="w-100"), width=6), dbc.Col(dbc.Button("📈 GRÁFICAS", id="btn-view-graphs", color="info", className="w-100"), width=6)], className="mb-4"),
        register_view, graphs_view,
        html.Div(dbc.Button("Salir", id="btn-logout", color="danger", outline=True, size="sm"), className="mt-5"),
        get_manager_ghosts()
    ], fluid=True)


# -------------------------------------------------------------------------
# MANAGER DASHBOARD (SIN PESTAÑAS, DIRECTO AL GRANO)
# -------------------------------------------------------------------------
def manager_dashboard_layout(session):
    role = session["role"]
    username = session["user"]
    patients = get_patients_by_user(username, role)
    btn_new_style = {"display": "block"} if role == "entrenador" else {"display": "none"}
   
    sidebar = dbc.Col([
        html.H4("BioMonitor", className="text-white mb-4"),
        html.Label("Seleccionar Atleta:", className="text-muted small"),
        dcc.Dropdown(id="patient-dropdown", options=patients, placeholder="Elige un corredor...", className="mb-4"),
       
        dbc.Button("➕ Nuevo Atleta", id="btn-new-patient", color="success", className="w-100 mb-3", size="sm", style=btn_new_style),
        dbc.Button("Salir", id="btn-logout", color="danger", outline=True, className="w-100 mt-auto", size="sm")
    ], width=12, lg=3, className="bg-dark p-3 vh-100")
   
    # ZONA PRINCIPAL: MUESTRA DATOS DIRECTAMENTE
    content = dbc.Col([
        html.H3("Panel de Entrenador", className="text-white mt-4 mb-4"),
        html.Div(id="dashboard-content"), # AQUÍ SE PINTARÁN LAS GRÁFICAS
        get_runner_ghosts()
    ], width=12, lg=9)
   
    return dbc.Row([sidebar, content], className="g-0")


app.layout = html.Div(style={"backgroundColor": COLOR_BG, "color": "#E0E0E0", "minHeight": "100vh"}, children=[
    dcc.Location(id="url", refresh=False), dcc.Store(id="session", storage_type="session"), dcc.Store(id="selected-patient", storage_type="session"),
    html.Div(id="page-content", children=login_layout())
])


# -------------------------------------------------------------------------
# CALLBACKS GENERALES
# -------------------------------------------------------------------------
@app.callback([Output("login-view", "style"), Output("register-view", "style")], Input("login-tabs", "active_tab"))
def switch_forms(tab): return ({"display": "none"}, {"display": "block"}) if tab == "tab-register" else ({"display": "block"}, {"display": "none"})


@app.callback([Output("auth-feedback", "children"), Output("url", "pathname"), Output("session", "data")], [Input("btn-log", "n_clicks"), Input("btn-reg", "n_clicks")], [State("log-user", "value"), State("log-pass", "value"), State("reg-user", "value"), State("reg-pass", "value"), State("reg-role", "value")], prevent_initial_call=True)
def auth_handler(n_log, n_reg, l_u, l_p, r_u, r_p, r_role):
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == "btn-reg":
        if not r_u or not r_p: return "⚠️ Faltan datos", no_update, no_update
        if user_exists(r_u): return "❌ Usuario ya existe", no_update, no_update
        if add_user(r_u, r_p, r_role): return "✅ Cuenta creada. Entra.", no_update, no_update
        return "❌ Error BD", no_update, no_update
    if trigger == "btn-log":
        role = authenticate_user(l_u, l_p)
        if role: return "", "/dashboard", {"user": l_u, "role": role}
        return "❌ Credenciales incorrectas", no_update, no_update
    return no_update, no_update, no_update


# --- CALLBACK DE CORREDOR ---
@app.callback(
    [Output("runner-register-view", "style"), Output("runner-graphs-view", "style"),
     Output("runner-graph-load", "figure"), Output("runner-graph-compare", "figure"),
     Output("kpi-fatiga", "children"), Output("kpi-rpe", "children"),
     Output("kpi-suenio", "children"), Output("kpi-bpm", "children"),
     Output("data-debug-msg", "children")],
    [Input("btn-view-register", "n_clicks"), Input("btn-view-graphs", "n_clicks"), Input("btn-back-to-register", "n_clicks")],
    [State("session", "data"), State("run-name", "value")], prevent_initial_call=True
)
def runner_view_toggle(n_reg, n_graph, n_back, session, run_name_input):
    if not session and not run_name_input: return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    user = session["user"] if session else run_name_input
   
    if trigger == "btn-view-register" or trigger == "btn-back-to-register":
        return {"display": "block"}, {"display": "none"}, no_update, no_update, no_update, no_update, no_update, no_update, ""
   
    if trigger == "btn-view-graphs":
        pac = get_nombre_paciente_from_username(user)
        target = pac if pac else user
       
        try:
            fig_load = get_training_data(target)
            fig_comp = get_comparison_figure([target])
            avgs = get_patient_averages(target)
            raw_data = get_training_data_for_patient(target)
            msg = f"⚠️ NO HAY DATOS para '{target}'. Registra una sesión primero." if len(raw_data) == 0 else f"✅ Mostrando {len(raw_data)} registros para '{target}'."
            return {"display": "none"}, {"display": "block"}, fig_load, fig_comp, str(avgs["fatiga"]), str(avgs["rpe"]), str(avgs["suenio"]), f"{avgs['bpm']} bpm", msg
        except Exception as e:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, f"Error: {str(e)}"
       
    return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update


# --- CALLBACK DE GUARDADO ---
@app.callback(
    [Output("runner-feedback", "children"), Output("ecg-graph-container", "children")],
    Input("submit-questionnaire", "n_clicks"),
    [State("session", "data"), State("run-name", "value"),
     State("fatiga", "value"), State("suenio", "value"),
     State("rpe", "value"), State("tiempo_entrenamiento", "value"),
     State("sensor-file-dropdown", "value")], prevent_initial_call=True
)
def runner_submit_data(n, session, run_name_input, f, s, r, t, sensor_file):
    if session: user = session["user"]
    elif run_name_input: user = run_name_input
    else: return html.Div("❌ Error: Escribe tu nombre arriba.", className="text-danger"), None


    try:
        val_fatiga, val_suenio, val_rpe, val_tiempo = int(f), int(s), int(r), float(t)
        pac = get_nombre_paciente_from_username(user)
        if not pac: pac = user
        save_questionnaire_for_patient(user, pac, val_fatiga, val_suenio, val_rpe, val_tiempo)
       
        calculated_bpm = 0
        ecg_graph = None
        if sensor_file and sensor_file != 'none':
            file_path = os.path.join("data", sensor_file)
            if os.path.exists(file_path):
                time_ax, ecg_signal, bpm_val = load_ecg_and_compute_bpm(file_path)
                calculated_bpm = int(bpm_val)
                fig_ecg = go.Figure()
                fig_ecg.add_trace(go.Scatter(x=time_ax[:1000], y=ecg_signal[:1000], mode='lines', name='ECG', line=dict(color="#FF0000")))
                fig_ecg.update_layout(title=f"ECG Detectado - BPM: {calculated_bpm}", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), height=250, margin=dict(l=20,r=20,t=40,b=20))
                ecg_graph = dcc.Graph(figure=fig_ecg)
            else:
                ecg_graph = html.Div(f"⚠️ Archivo no encontrado: {file_path}", className="text-warning")


        guardar_entrenamiento(pac, val_tiempo, val_fatiga, val_rpe, bpm=calculated_bpm)
        feedback = html.Div([
            html.Div(f"✅ Guardado para: {pac}", className="text-success fw-bold"),
            html.Div(f"BPM: {calculated_bpm}" if calculated_bpm > 0 else "", className="text-info small")
        ])
        return feedback, ecg_graph
    except Exception as e: return html.Div(f"❌ Error: {str(e)}", className="text-danger"), None


@app.callback(Output("btn-run-save-profile", "children"), Input("btn-run-save-profile", "n_clicks"), [State("session", "data"), State("run-name", "value"), State("run-nac", "value"), State("run-fcr", "value"), State("run-vo2", "value")], prevent_initial_call=True)
def runner_save_profile(n, session, name, nac, fcr, vo2):
    if session: username = session["user"]
    elif name: username = name
    else: return "❌ Escribe Nombre"
   
    pac = get_nombre_paciente_from_username(username)
    if not pac:
        try:
            conn = sqlite3.connect("database.db")
            c = conn.cursor()
            c.execute("INSERT INTO pacientes (username, nombre_paciente, entrenador_asociado, full_name, equipo, deporte, fcr, vo2) VALUES (?, ?, 'Auto', ?, 'Club', 'Running', 60, 45)", (username, username, username))
            conn.commit()
            conn.close()
            pac = username
        except: return "❌ Error DB"
    try: val_fcr = int(fcr)
    except: val_fcr = 60
    try: val_vo2 = float(vo2)
    except: val_vo2 = 45.0
    save_patient_info(pac, name if name else pac, 0, 0, 0, "Personal", "Running", "Runner", nac, val_fcr, val_vo2)
    return "✅ Actualizado"


@app.callback(Output("page-content", "children"), [Input("url", "pathname"), State("session", "data")])
def router(path, session):
    if path == "/dashboard" and session: return runner_dashboard_layout(session["user"]) if session["role"] == "paciente" else manager_dashboard_layout(session)
    return login_layout()


# --- CALLBACK DEL ENTRENADOR (CLON EXACTO DEL CORREDOR) ---
# He eliminado el chequeo de "if not session: return Error" que causaba tu problema
@app.callback(Output("dashboard-content", "children"),
              [Input("patient-dropdown", "value")],
              [State("session", "data")])
def render_manager_view(patient_selected, session):
    # Si no hay selección, mostramos mensaje de bienvenida
    if not patient_selected:
        return html.Div([
            html.H1("👈", className="display-1"),
            html.H4("Selecciona un atleta en el menú lateral"),
            html.P("Verás sus datos inmediatamente.")
        ], className="text-center mt-5 text-muted")
   
    # Calculamos datos del seleccionado
    try:
        patient = patient_selected
        fig_load = get_training_data(patient)
        fig_comp = get_comparison_figure([patient])
        avgs = get_patient_averages(patient)
       
        # INTERFAZ IDÉNTICA A LA DEL CORREDOR
        return dbc.Container([
            html.H3(f"Analizando a: {patient}", className="text-white mb-4"),
            # Tarjetas de Medias
            dbc.Row([
                dbc.Col(dbc.Card([dbc.CardBody([html.H6("Media Fatiga", className="text-muted"), html.H2(avgs["fatiga"], className="text-warning")])], style={"backgroundColor": COLOR_CARD}, className="mb-3"), width=6, lg=3),
                dbc.Col(dbc.Card([dbc.CardBody([html.H6("Media RPE", className="text-muted"), html.H2(avgs["rpe"], className="text-danger")])], style={"backgroundColor": COLOR_CARD}, className="mb-3"), width=6, lg=3),
                dbc.Col(dbc.Card([dbc.CardBody([html.H6("Media Sueño", className="text-muted"), html.H2(avgs["suenio"], className="text-info")])], style={"backgroundColor": COLOR_CARD}, className="mb-3"), width=6, lg=3),
                dbc.Col(dbc.Card([dbc.CardBody([html.H6("BPM Medio", className="text-muted"), html.H2(f"{avgs['bpm']} bpm", className="text-success")])], style={"backgroundColor": COLOR_CARD}, className="mb-3"), width=6, lg=3),
            ]),
            # Gráficas
            dbc.Row([
                dbc.Col(dbc.Card([dbc.CardHeader("Evolución Carga"), dbc.CardBody(dcc.Graph(figure=fig_load, style={"height": "350px"}))], style={"backgroundColor": COLOR_CARD}), md=6),
                dbc.Col(dbc.Card([dbc.CardHeader("Métricas Físicas"), dbc.CardBody(dcc.Graph(figure=fig_comp, style={"height": "350px"}))], style={"backgroundColor": COLOR_CARD}), md=6)
            ])
        ])
    except Exception as e:
        return html.Div(f"Error cargando datos: {str(e)}", className="text-danger")


@app.callback([Output("url", "pathname", allow_duplicate=True), Output("session", "data", allow_duplicate=True)], Input("btn-logout", "n_clicks"), prevent_initial_call=True)
def logout(n): return "/", None


@app.callback([Output("patient-dropdown", "options"), Output("selected-patient", "data", allow_duplicate=True)], [Input("session", "data"), Input("btn-new-patient", "n_clicks")], prevent_initial_call=True)
def update_patients_dropdown(session, n_new):
    if not session or session["role"] == "paciente": return no_update, no_update
    new_p = create_patient(session["user"]) if callback_context.triggered[0]['prop_id'] == "btn-new-patient.n_clicks" else None
    opts = get_patients_by_user(session["user"], session["role"])
    return opts, ({"patient": new_p} if new_p else no_update)


@app.callback(Output("selected-patient", "data", allow_duplicate=True), Input("patient-dropdown", "value"), prevent_initial_call=True)
def select_patient(value): return {"patient": value} if value else no_update


@app.callback(Output("patient-list", "children"), Input("session", "data"))
def dummy(x): return no_update


if __name__ == "__main__":
    app.run_server(debug=True, port=8050)


