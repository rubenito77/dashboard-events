from flask import Flask, render_template, request
import pandas as pd
import os
import glob
import re
from datetime import datetime

app = Flask(__name__)

REPORTES_DIR = "/app/reportes"
COLUMNAS_PRINCIPALES = ['Fall', 'Flapping', 'NetworkElement', 'Event', 'Notification']

timestamp_pattern = re.compile(r'Hora: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
data_pattern = re.compile(r'ar\.com\.cablevision\.model\.(\w+):(\d+)')

CACHE = {"mtime": 0, "df_totales": pd.DataFrame()}

def procesar_reportes():
    global CACHE
    archivos = glob.glob(os.path.join(REPORTES_DIR, "reporte_kie*.txt"))
    if not archivos:
        return pd.DataFrame()

    max_mtime = max(os.path.getmtime(f) for f in archivos)
    if max_mtime <= CACHE["mtime"]:
        return CACHE["df_totales"]

    all_data = []
    for archivo_path in archivos:
        try:
            with open(archivo_path, 'r', encoding='utf-8') as f:
                raw_data = f.read()
        except:
            continue

        parsed_data = []
        current_entry = None
        for line in raw_data.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            ts = timestamp_pattern.search(line)
            if ts:
                if current_entry:
                    parsed_data.append(current_entry)
                current_entry = {'Fecha y Hora': ts.group(1)}
            dm = data_pattern.search(line)
            if dm and current_entry:
                current_entry[dm.group(1)] = int(dm.group(2))
        if current_entry:
            parsed_data.append(current_entry)

        df = pd.DataFrame(parsed_data)
        if df.empty:
            continue

        # Normalizar columnas principales (si faltan, poner 0)
        for col in COLUMNAS_PRINCIPALES:
            if col not in df.columns:
                df[col] = 0

        df['Fecha y Hora'] = pd.to_datetime(df['Fecha y Hora'])
        df['Fecha'] = df['Fecha y Hora'].dt.date
        df['Fecha_str'] = df['Fecha'].astype(str)
        df['Hora_str'] = df['Fecha y Hora'].dt.strftime("%H:%M:%S")

        basename = os.path.basename(archivo_path)
        fuente = re.sub(r'reporte_|\.txt', '', basename)
        df['Fuente'] = fuente

        all_data.append(df)

    if not all_data:
        return pd.DataFrame()

    df_totales = pd.concat(all_data, ignore_index=True)
    CACHE["df_totales"] = df_totales
    CACHE["mtime"] = max_mtime
    return df_totales

@app.route("/")
def index():
    df = procesar_reportes()
    if df.empty:
        return render_template(
            "index.html", data=[], labels=[], numeric_cols=[], 
            fechas_disponibles=[], fecha_seleccionada=None,
            kieservers_disponibles=[], kieserver_seleccionado=None,
            show_totals=False, totales=None
        )

    fechas_disponibles = sorted(df['Fecha_str'].unique())
    kieservers_disponibles = sorted(df['Fuente'].unique())

    fecha_seleccionada = request.args.get('fecha')
    kieserver_seleccionado = request.args.get('kieserver')

    df_graph = df.copy()

    # Filtrado por fecha
    if fecha_seleccionada and fecha_seleccionada != "todos":
        df_graph = df_graph[df_graph['Fecha_str'] == fecha_seleccionada]

    # Filtrado por KieServer
    if kieserver_seleccionado and kieserver_seleccionado != "todos":
        df_graph = df_graph[df_graph['Fuente'] == kieserver_seleccionado]

    numeric_cols = [col for col in df_graph.columns if col in COLUMNAS_PRINCIPALES]

    labels = df_graph['Hora_str'].tolist()
    show_totals = False
    totales = None

    # Caso: Día específico + todos los KieServers → mostrar última fila por KieServer + fila TOTAL
    if fecha_seleccionada and fecha_seleccionada != "todos" and (not kieserver_seleccionado or kieserver_seleccionado == "todos"):
        last_rows = df_graph.groupby('Fuente').tail(1)
        total_row = last_rows[numeric_cols].sum()
        total_row_dict = {'Fecha_str': fecha_seleccionada, 'Fuente': 'TOTAL', 'Hora_str': ''}
        total_row_dict.update(total_row.to_dict())
        df_graph = pd.concat([last_rows, pd.DataFrame([total_row_dict])], ignore_index=True)
        labels = df_graph['Hora_str'].tolist()
        show_totals = True
        totales = df_graph

    # Caso: Todos los días + todos los KieServers → mostrar fila TOTAL por día
    elif (not fecha_seleccionada or fecha_seleccionada == "todos") and (not kieserver_seleccionado or kieserver_seleccionado == "todos"):
        df_graph_sorted = df_graph.sort_values(['Fecha_str', 'Fuente', 'Hora_str'])
        total_rows = []
        for fecha in df_graph_sorted['Fecha_str'].unique():
            df_fecha = df_graph_sorted[df_graph_sorted['Fecha_str'] == fecha]
            last_rows = df_fecha.groupby('Fuente').tail(1)
            total = last_rows[numeric_cols].sum()
            total_row = {'Fecha_str': fecha, 'Fuente': 'TOTAL', 'Hora_str': ''}
            total_row.update(total.to_dict())
            total_rows.append(total_row)
        df_graph = pd.DataFrame(total_rows)
        labels = df_graph['Hora_str'].tolist()
        show_totals = True
        totales = df_graph

    return render_template(
        "index.html", data=df_graph.to_dict(orient='records'), labels=labels, numeric_cols=numeric_cols,
        fechas_disponibles=fechas_disponibles, fecha_seleccionada=fecha_seleccionada,
        kieservers_disponibles=kieservers_disponibles, kieserver_seleccionado=kieserver_seleccionado,
        show_totals=show_totals, totales=totales
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

