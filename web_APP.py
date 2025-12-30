from dash import Dash, html, dash_table, dcc, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
from dash_bootstrap_templates import load_figure_template
from dashboard_data_parser import parse_http_requests_log
from pathlib import Path
import pandas as pd

# =========================
# PATH CONFIGURATION
# =========================

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "logs" / "http_logs.log"

# =========================
# DASH SETUP
# =========================

load_figure_template(["cyborg"])
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.4/dbc.min.css"

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc_css])
app.title = "HONEYPY"

# =========================
# LAYOUT
# =========================

app.layout = dbc.Container(
    [
        # Interval for live refresh
        dcc.Interval(
            id="refresh",
            interval=3000,
            n_intervals=0,
        ),

        # Logo
        html.Div(
            html.Img(
                src="assets/images/honeypy-logo-white.png",
                style={"height": "25%", "width": "25%"},
            ),
            style={"textAlign": "center"},
        ),

        html.H3(
            "HTTP Honeypot Data",
            style={
                "textAlign": "center",
                "fontFamily": "Consolas",
                "fontWeight": "bold",
            },
        ),

        # Bar chart
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(id="ip-bar"),
                    width=6,
                ),
            ],
            justify="center",
        ),

        # Unified data table
        dash_table.DataTable(
            id="http-table",
            page_size=15,
            style_cell={
                "textAlign": "left",
                "color": "#8dd143",
                "backgroundColor": "#111111",
            },
            style_header={
                "fontWeight": "bold",
                "backgroundColor": "#222222",
            },
        ),
    ],
    fluid=True,
)

# =========================
# CALLBACK
# =========================

@app.callback(
    Output("http-table", "data"),
    Output("http-table", "columns"),
    Output("ip-bar", "figure"),
    Input("refresh", "n_intervals"),
)
def refresh_dashboard(_):
    df = parse_http_requests_log(LOG_FILE)

    # ---------- TABLE ----------
    columns = [{"name": c, "id": c} for c in df.columns]
    data = df.to_dict("records")

    # ---------- BAR CHART ----------
    if not df.empty and "client_ip" in df.columns:
        vc = df["client_ip"].value_counts().head(10)

        top_ips = pd.DataFrame({
            "client_ip": vc.index,
            "count": vc.values,
        })

        fig = px.bar(
            top_ips,
            x="client_ip",
            y="count",
            title="Top Attacker IPs",
            color_discrete_sequence=["#77bb35"],
        )
    else:
        fig = px.bar(
            pd.DataFrame(columns=["client_ip", "count"]),
            x="client_ip",
            y="count",
            title="Top Attacker IPs",
        )

    return data, columns, fig

# =========================
# RUN
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
