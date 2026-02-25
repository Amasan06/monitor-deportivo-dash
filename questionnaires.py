import dash_bootstrap_components as dbc
from dash import html, dcc
import pandas as pd
import plotly.graph_objs as go
from db import get_training_data_for_patient, get_metrics_for_comparison

CARD_STYLE = {
    "backgroundColor": "#1E1E1E", "border": "1px solid #333",
    "borderRadius": "12px", "marginBottom": "15px", "boxShadow": "0 4px 6px rgba(0,0,0,0.3)"
}

LABEL_STYLE = {"color": "#90CAF9", "fontWeight": "600", "marginBottom": "5px"}

questionnaire_layout = html.Div([
    html.H5("📝 Registro Diario", className="text-white mb-3"),
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Label("⚡ Fatiga (1-10)", style=LABEL_STYLE),
            dcc.Slider(id="fatiga", min=1, max=10, step=1, value=5, marks={i:str(i) for i in range(1,11)}),
        ]), style=CARD_STYLE), width=6),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Label("💤 Sueño (1-10)", style=LABEL_STYLE),
            dcc.Slider(id="suenio", min=1, max=10, step=1, value=7, marks={i:str(i) for i in range(1,11)}),
        ]), style=CARD_STYLE), width=6),
    ]),
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Label("🔥 RPE (1-10)", style=LABEL_STYLE),
            dcc.Slider(id="rpe", min=1, max=10, step=1, value=6, marks={i:str(i) for i in range(1,11)}),
        ]), style=CARD_STYLE), width=6),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Label("⏱️ Minutos", style=LABEL_STYLE),
            dbc.Input(id="tiempo_entrenamiento", type="number", value=60, className="text-center bg-dark text-white"),
        ]), style=CARD_STYLE), width=6),
    ]),
    
    # --- NUEVA SECCIÓN DE SENSOR ECG ---
    dbc.Card(dbc.CardBody([
        html.Label("🫀 Sensor de Frecuencia Cardíaca", style=LABEL_STYLE),
        dcc.Dropdown(
            id="sensor-file-dropdown",
            options=[
                {'label': '❌ Sin Sensor', 'value': 'none'},
                {'label': '📂 Cargar Simulador (ecg_example.csv)', 'value': 'ecg_example.csv'}
            ],
            value='none',
            placeholder="Seleccionar dispositivo...",
            className="mb-2"
        ),
        # Aquí se mostrará la gráfica del ECG cuando se procese
        html.Div(id="ecg-graph-container")
    ]), style=CARD_STYLE),
    
    dbc.Button("✅ Registrar Sesión", id="submit-questionnaire", color="primary", className="w-100 rounded-pill")
])

def get_training_data(paciente):
    data = get_training_data_for_patient(paciente)
    layout_config = dict(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="#B0B0B0"), margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(showgrid=True, gridcolor='#333'), yaxis=dict(showgrid=True, gridcolor='#333')
    )

    if not data:
        fig = go.Figure()
        fig.update_layout(**layout_config, title="Registra una sesión para ver datos")
        return fig

    df = pd.DataFrame(data, columns=["fecha", "carga"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df["carga"], mode="lines+markers", name="Carga",
        line=dict(color="#4285F4", width=3, shape='spline'), fill='tozeroy',
        marker=dict(size=6, color="#1E1E1E", line=dict(width=2, color="#4285F4"))
    ))
    fig.update_layout(**layout_config, title="Evolución de Carga")
    return fig

def get_comparison_figure(target_patients=None):
    data = get_metrics_for_comparison(target_patients)
    
    if not data:
        return go.Figure(layout=dict(title="Sin datos", paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white")))

    names = [p['name'] for p in data]
    vo2_values = [p['vo2'] for p in data]
    fcr_values = [p['fcr'] for p in data]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=names, y=vo2_values, name="VO2 Max", marker_color="#34A853"))
    fig.add_trace(go.Bar(x=names, y=fcr_values, name="Frec. Reposo", marker_color="#EA4335"))

    fig.update_layout(
        title="Comparativa", barmode='group',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="white"), yaxis=dict(showgrid=True, gridcolor='#333'),
        margin=dict(l=40, r=20, t=40, b=40), legend=dict(orientation="h", y=1.1)
    )
    return fig