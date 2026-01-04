from dash import Dash, html, dash_table, dcc, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
from dash_bootstrap_templates import load_figure_template
from dashboard_data_parser import parse_http_requests_log, parse_ftp_smb_log
from pathlib import Path
import pandas as pd

# =========================
# PATH CONFIGURATION
# =========================

BASE_DIR = Path(__file__).resolve().parent
HTTP_LOGS = BASE_DIR / "logs" / "http_logs.log"
SMB_FTP_LOGS = BASE_DIR / "logs" / "ftp_smb_logs.log"

# =========================
# DASH SETUP
# =========================

load_figure_template(["cyborg"])
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.4/dbc.min.css"

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc_css])
app.title = "VENOMPOT DASHBOARD"

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
        # =========================
        # FTP / SMB SECTION
        # =========================

        html.H3(
            "FTP / SMB Honeypot Data",
            style={
                "textAlign": "center",
                "fontFamily": "Consolas",
                "fontWeight": "bold",
                "marginTop": "40px",
            },
        ),

        # FTP / SMB Bar chart
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(id="smb-bar"),
                    width=6,
                ),
            ],
            justify="center",
        ),

        # FTP / SMB Unified data table
        dash_table.DataTable(
            id="smb-table",
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
    Output("smb-table", "data"),
    Output("smb-table", "columns"),
    Output("smb-bar", "figure"),
    Input("refresh", "n_intervals"),
)
def refresh_dashboard(_):
    # =========================
    # HTTP
    # =========================
    df_http = parse_http_requests_log(HTTP_LOGS)

    http_columns = [{"name": c, "id": c} for c in df_http.columns]
    http_data = df_http.to_dict("records")

    if not df_http.empty and "client_ip" in df_http.columns:
        vc_http = df_http["client_ip"].value_counts().head(10)
        http_fig = px.bar(
            pd.DataFrame({
                "client_ip": vc_http.index,
                "count": vc_http.values,
            }),
            x="client_ip",
            y="count",
            title="Top HTTP Attacker IPs",
            color_discrete_sequence=["#77bb35"],
        )
    else:
        http_fig = px.bar(
            pd.DataFrame(columns=["client_ip", "count"]),
            x="client_ip",
            y="count",
            title="Top HTTP Attacker IPs",
        )

    # =========================
    # FTP / SMB
    # =========================
    df_smb = parse_ftp_smb_log(SMB_FTP_LOGS)

    smb_columns = [{"name": c, "id": c} for c in df_smb.columns]
    smb_data = df_smb.to_dict("records")

    if not df_smb.empty and "client_ip" in df_smb.columns:
        vc_smb = df_smb["client_ip"].value_counts().head(10)
        smb_fig = px.bar(
            pd.DataFrame({
                "client_ip": vc_smb.index,
                "count": vc_smb.values,
            }),
            x="client_ip",
            y="count",
            title="Top FTP / SMB Attacker IPs",
            color_discrete_sequence=["#77bb35"],
        )
    else:
        smb_fig = px.bar(
            pd.DataFrame(columns=["client_ip", "count"]),
            x="client_ip",
            y="count",
            title="Top FTP / SMB Attacker IPs",
        )

    return (
        http_data,
        http_columns,
        http_fig,
        smb_data,
        smb_columns,
        smb_fig,
    )
# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
