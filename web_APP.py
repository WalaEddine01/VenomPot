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
app.layout = dbc.Container([
    dcc.Interval(id="refresh", interval=3000, n_intervals=0),

    html.H1("VenomPot Threat Intel", style={"textAlign": "center", "marginTop": "20px", "color": "#8dd143"}),

    dbc.Row([
        dbc.Col(dcc.Graph(id="ip-bar"), width=12),
    ]),

    html.Hr(),
    html.H3("HTTP / WordPress Attack Traffic", style={"color": "#8dd143"}),
    dash_table.DataTable(
        id="http-table",
        page_size=10,
        style_cell={"textAlign": "left", "backgroundColor": "#111", "color": "#8dd143"},
        style_header={"backgroundColor": "#222", "fontWeight": "bold"}
    ),

    html.Br(),
    html.H3("SMB & FTP Connection Logs", style={"color": "#8dd143"}),
    dash_table.DataTable(
        id="smb-ftp-table",
        page_size=10,
        style_cell={"textAlign": "left", "backgroundColor": "#111", "color": "#8dd143"},
        style_header={"backgroundColor": "#222", "fontWeight": "bold"}
    ),
], fluid=True)

# =========================
# CALLBACK
# =========================
@app.callback(
    Output("http-table", "data"),
    Output("http-table", "columns"),
    Output("smb-ftp-table", "data"),
    Output("smb-ftp-table", "columns"),
    Output("ip-bar", "figure"),
    Input("refresh", "n_intervals"),
)
def refresh_dashboard(_):
    # Fetch Data
    df_http = parse_http_requests_log(HTTP_LOGS)
    df_smb = parse_ftp_smb_log(SMB_FTP_LOGS)

    # Tables
    cols_http = [{"name": c, "id": c} for c in df_http.columns]
    cols_smb = [{"name": c, "id": c} for c in df_smb.columns]
    
    # Combined Bar Chart (Top IPs across all services)
    combined_ips = pd.concat([df_http['client_ip'], df_smb['client_ip']]) if not df_http.empty or not df_smb.empty else pd.Series()
    if not combined_ips.empty:
        vc = combined_ips.value_counts().head(10)
        fig = px.bar(x=vc.index, y=vc.values, title="Total Attacks by IP", labels={'x':'IP Address', 'y':'Count'})
        fig.update_layout(template="cyborg")
    else:
        fig = px.bar(title="No Data Yet")

    return df_http.to_dict("records"), cols_http, df_smb.to_dict("records"), cols_smb, fig

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)