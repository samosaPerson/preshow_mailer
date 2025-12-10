import json
from datetime import datetime, timezone
from pathlib import Path
import base64
import io
import os

import dash
from dash import Dash, ALL, Input, Output, State, dcc, html
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from dotenv import load_dotenv
import yaml

from src.generator import generate_email
from src import sender


load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT_DIR / "data" / "examples" / "theatre_config.yaml"
DEFAULT_SHOW_PATH = ROOT_DIR / "data" / "examples" / "show_info.json"
MAILCHIMP_READY = all([
    os.environ.get("MAILCHIMP_API_KEY"),
    os.environ.get("MAILCHIMP_SERVER_PREFIX"),
    os.environ.get("MAILCHIMP_LIST_ID")
])


def load_config(path: Path = DEFAULT_CONFIG_PATH):
    with path.open("r") as stream:
        return yaml.safe_load(stream)


def load_show_info(path: Path = DEFAULT_SHOW_PATH):
    with path.open("r") as stream:
        return json.load(stream)


def normalize_datetime(value: str):
    if not value:
        return ""
    # HTML datetime-local omits seconds; generator expects them
    if len(value) == 16:
        return f"{value}:00"
    return value


def build_show_data_from_inputs(show_title, start_time, end_time, doors_open_time,
                                intermission_description, timezone_abbreviation,
                                audience_rating, content_warnings):
    return {
        "show_title": show_title,
        "start_time": normalize_datetime(start_time),
        "end_time": normalize_datetime(end_time),
        "doors_open_time": normalize_datetime(doors_open_time),
        "intermission_description": intermission_description,
        "timezone_abbreviation": timezone_abbreviation,
        "audience_rating": audience_rating,
        "content_warnings": content_warnings
    }


def build_config_from_inputs(config_base, theatre_name, theatre_address, phone, email,
                             accessibility_note, logo_url, primary_color, secondary_color,
                             headline_color, latitude, longitude, radius, whitelist_radius,
                             concessions_description, sponsor_name, sponsor_url,
                             whitelist_csv, blacklist_csv,
                             primary_hex=None, secondary_hex=None, headline_hex=None):
    config = dict(config_base or config_defaults)
    theatre = config.setdefault("theatre", {})
    theatre["name"] = theatre_name
    theatre["address"] = theatre_address
    theatre.setdefault("location", {})
    theatre["location"]["latitude"] = float(latitude) if latitude else None
    theatre["location"]["longitude"] = float(longitude) if longitude else None
    theatre["radius_meters"] = int(radius) if radius else theatre.get("radius_meters")
    theatre["whitelist_radius_meters"] = int(whitelist_radius) if whitelist_radius else theatre.get("whitelist_radius_meters")

    branding = config.setdefault("branding", {})
    branding["primary_color"] = primary_hex or primary_color
    branding["secondary_color"] = secondary_hex or secondary_color
    branding["headline_color"] = headline_hex or headline_color
    branding["logo_url"] = logo_url

    details = config.setdefault("details", {})
    details["contact_phone"] = phone
    details["contact_email"] = email
    details["accessibility_note"] = accessibility_note

    concessions = config.setdefault("concessions", {})
    concessions["description"] = concessions_description
    concessions.setdefault("sponsor", {})
    concessions["sponsor"]["name"] = sponsor_name
    concessions["sponsor"]["url"] = sponsor_url

    def csv_to_list(value):
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    lists_cfg = config.setdefault("lists", {})
    lists_cfg["whitelist"] = csv_to_list(whitelist_csv)
    lists_cfg["blacklist"] = csv_to_list(blacklist_csv)
    return config


def normalize_hex(val):
    if not val:
        return ""
    val = val.strip()
    if not val.startswith("#"):
        val = "#" + val
    if len(val) in (4, 7):
        return val
    return val


def generate_email_html(show_data, config):
    html_body, _ = generate_email(config, show_data)
    return html_body


def apply_preview_overrides(html_body, theme_mode):
    if not html_body:
        return html_body
    styles = []
    if theme_mode == "dark":
        # Force dark color-scheme so preview shows dark email colors regardless of OS preference.
        styles.append(":root { color-scheme: dark !important; }")
        styles.append("""
            body, .body-bg, .container-bg {
                background-color: #121212 !important; /* Dark preview canvas */
                color: #f1f1f1 !important;             /* Light text on dark canvas */
            }
            h1,h2,h3,h4,p,li,div { color: #f1f1f1 !important; }
        """)
    elif theme_mode == "light":
        # Force light color-scheme so preview stays light even if user prefers dark.
        styles.append(":root { color-scheme: light !important; }")
        styles.append("""
            body, .body-bg, .container-bg {
                background-color: #ffffff !important; /* Light preview canvas */
                color: #1a1a1a !important;             /* Dark text on light canvas */
            }
            h1,h2,h3,h4,p,li,div { color: #1a1a1a !important; }
            @media (prefers-color-scheme: dark) {
                * { color-scheme: light !important; }
            }
        """)
    if styles:
        override = "<style id='preview-theme-override'>" + " ".join(styles) + "</style>"
        if "</head>" in html_body:
            return html_body.replace("</head>", f"{override}</head>", 1)
        return override + html_body
    return html_body


def decode_upload(contents):
    if not contents:
        return None
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    return decoded


def to_utc_iso(local_str: str):
    if not local_str:
        raise ValueError("No schedule time provided")
    local_dt = datetime.fromisoformat(local_str)
    local_tz = datetime.now().astimezone().tzinfo
    return local_dt.replace(tzinfo=local_tz).astimezone(timezone.utc).isoformat()


def campaign_cards(campaigns, empty_message, action_type="scheduled"):
    if not campaigns:
        return dbc.Alert(empty_message, color="secondary", className="mb-0")

    cards = []
    for item in campaigns:
        header = html.Div([
            html.Span(item.get("subject") or "Untitled Campaign", className="fw-semibold"),
            html.Span(f" • {item.get('status', '').title()}", className="ms-2 text-muted")
        ])

        meta = html.Small([
            f"Send/Schedule: {item.get('send_time') or 'TBD'}",
            html.Br(),
            f"ID: {item.get('id')}"
        ])

        actions = []
        if action_type == "scheduled":
            actions.append(
                dbc.Button("Cancel", id={"type": "cancel-campaign", "index": item["id"]},
                           color="danger", size="sm", className="me-2", n_clicks=0)
            )
        if item.get("web_link"):
            actions.append(
                dbc.Button("Open in Mailchimp", href=item["web_link"], target="_blank",
                           color="secondary", size="sm")
            )

        body = dbc.CardBody([
            header,
            meta,
            dbc.ButtonGroup(actions, className="mt-2") if actions else None
        ])
        cards.append(dbc.Card(body, className="mb-2"))
    return cards


def sent_list(campaigns):
    if not campaigns:
        return dbc.Alert("No sent campaigns in this range.", color="secondary", className="mb-0")
    items = []
    for item in campaigns:
        label = f"{item.get('send_time') or 'Sent'} — {item.get('subject') or 'Untitled'}"
        items.append(
            dbc.ListGroupItem(
                label,
                action=True,
                id={"type": "sent-campaign", "index": item["id"]},
                n_clicks=0,
                className="mb-1"
            )
        )
    return dbc.ListGroup(items, flush=True)


show_defaults = load_show_info()
config_defaults = load_config()

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.MORPH, dbc.icons.BOOTSTRAP],
    title="Theatre Pre-Show Emailer",
    suppress_callback_exceptions=True
)


hero = dbc.Row([
    dbc.Col([
        html.H2("Theatre Pre-Show Emailer", className="fw-bold text-white"),
        html.P("Craft, review, and schedule patron emails without leaving the theatre office.",
               className="text-white-50 mb-0")
    ])
], className="p-4 rounded-3", style={
    "background": "linear-gradient(120deg, #144550 0%, #165264 50%, #103b49 100%)",  # Header banner gradient
    "boxShadow": "0 14px 40px rgba(6,12,26,0.35)",                                   # Depth under banner
    "border": "1px solid #1e2e4d"                                                    # Edge line around hero
})


def editor_tab():
    theatre_form = dbc.Card(
        dbc.CardBody([
            html.H5("Theatre Details", className="fw-semibold mb-3"),
            dbc.Button("Load Theatre YAML", id="upload-config-btn", color="secondary", className="mb-2 secondary-btn", n_clicks=0),
            dcc.Upload(id="upload-config", children=html.Div(["Drag & drop or click to upload"]), className="upload-box rounded p-2 mb-2"),
            html.Div(id="config-load-status", className="mb-2"),
            dbc.Label("Name", html_for="theatre-name"),
            dcc.Input(id="theatre-name", type="text", value=config_defaults["theatre"].get("name", ""), className="form-control mb-2"),
            dbc.Label("Address", html_for="theatre-address"),
            dcc.Input(id="theatre-address", type="text", value=config_defaults["theatre"].get("address", ""), className="form-control mb-2"),
            dbc.Label("Contact Phone", html_for="theatre-phone"),
            dcc.Input(id="theatre-phone", type="text", value=config_defaults["details"].get("contact_phone", ""), className="form-control mb-2"),
            dbc.Label("Contact Email", html_for="theatre-email"),
            dcc.Input(id="theatre-email", type="email", value=config_defaults["details"].get("contact_email", ""), className="form-control mb-2"),
            dbc.Label("Accessibility Note", html_for="theatre-accessibility"),
            dcc.Textarea(id="theatre-accessibility", value=config_defaults["details"].get("accessibility_note", ""), className="form-control mb-2"),
            dbc.Label("Logo URL", html_for="logo-url"),
            dcc.Input(id="logo-url", type="text", value=config_defaults["branding"].get("logo_url", ""), className="form-control mb-2"),
            dbc.Label("Primary Color", html_for="primary-color"),
            dbc.InputGroup([
                dbc.InputGroupText("Pick"),
                dcc.Input(id="primary-color", type="color", value=config_defaults["branding"].get("primary_color", "#e86a4f"), className="form-control form-control-color"),
                dbc.InputGroupText("Hex"),
                dcc.Input(id="primary-color-hex", type="text", value=config_defaults["branding"].get("primary_color", "#e86a4f"), className="form-control hex-input")
            ], className="mb-2"),
            dbc.Label("Secondary Color", html_for="secondary-color"),
            dbc.InputGroup([
                dbc.InputGroupText("Pick"),
                dcc.Input(id="secondary-color", type="color", value=config_defaults["branding"].get("secondary_color", "#17162a"), className="form-control form-control-color"),
                dbc.InputGroupText("Hex"),
                dcc.Input(id="secondary-color-hex", type="text", value=config_defaults["branding"].get("secondary_color", "#17162a"), className="form-control hex-input")
            ], className="mb-2"),
    dbc.Label("Headline Color", html_for="headline-color"),
    dbc.InputGroup([
        dbc.InputGroupText("Pick"),
        dcc.Input(id="headline-color", type="color", value=config_defaults["branding"].get("headline_color", "#ffffff"), className="form-control form-control-color"),
        dbc.InputGroupText("Hex"),
        dcc.Input(id="headline-color-hex", type="text", value=config_defaults["branding"].get("headline_color", "#ffffff"), className="form-control hex-input")
    ], className="mb-2"),
    dbc.Label("Concessions Description", html_for="concession-description"),
    dcc.Textarea(id="concession-description", value=config_defaults.get("concessions", {}).get("description", ""), className="form-control mb-2"),
    dbc.Label("Concession Sponsor Name", html_for="sponsor-name"),
    dcc.Input(id="sponsor-name", type="text", value=config_defaults.get("concessions", {}).get("sponsor", {}).get("name", ""), className="form-control mb-2"),
    dbc.Label("Concession Sponsor URL", html_for="sponsor-url"),
    dcc.Input(id="sponsor-url", type="text", value=config_defaults.get("concessions", {}).get("sponsor", {}).get("url", ""), className="form-control mb-2"),
    dbc.Label("Whitelist (comma separated)", html_for="whitelist"),
    dcc.Input(id="whitelist", type="text", value=",".join(config_defaults.get("lists", {}).get("whitelist", []) or []), className="form-control mb-2"),
    dbc.Label("Blacklist (comma separated)", html_for="blacklist"),
    dcc.Input(id="blacklist", type="text", value=",".join(config_defaults.get("lists", {}).get("blacklist", []) or []), className="form-control mb-2"),
    dbc.Label("Latitude", html_for="latitude"),
    dcc.Input(id="latitude", type="number", value=config_defaults["theatre"]["location"].get("latitude", ""), className="form-control mb-2"),
    dbc.Label("Longitude", html_for="longitude"),
            dcc.Input(id="longitude", type="number", value=config_defaults["theatre"]["location"].get("longitude", ""), className="form-control mb-2"),
            dbc.Label("Radius (meters)", html_for="radius"),
            dcc.Input(id="radius", type="number", value=config_defaults["theatre"].get("radius_meters", ""), className="form-control mb-2"),
            dbc.Label("Whitelist Radius (meters)", html_for="whitelist-radius"),
            dcc.Input(id="whitelist-radius", type="number", value=config_defaults["theatre"].get("whitelist_radius_meters", ""), className="form-control")
        ]),
        className="mb-3"
    )

    show_form = dbc.Card(
        dbc.CardBody([
            html.H5("Show Details", className="fw-semibold mb-3"),
            dbc.Button("Load Show JSON", id="upload-show-btn", color="secondary", className="mb-2 secondary-btn", n_clicks=0),
            dcc.Upload(id="upload-show", children=html.Div(["Drag & drop or click to upload"]), className="upload-box rounded p-2 mb-2"),
            html.Div(id="show-load-status", className="mb-2"),
            dbc.Label("Show Title", html_for="show-title"),
            dcc.Input(id="show-title", type="text", value=show_defaults.get("show_title", ""), className="form-control mb-2"),
            dbc.Label("Timezone (e.g., EST)", html_for="timezone-abbrev"),
            dcc.Input(id="timezone-abbrev", type="text", value=show_defaults.get("timezone_abbreviation", ""), className="form-control mb-2"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Audience Rating", html_for="audience-rating"),
                    dcc.Input(id="audience-rating", type="text", value=show_defaults.get("audience_rating", ""), className="form-control mb-2")
                ], md=6),
                dbc.Col([
                    dbc.Label("Content Advisory", html_for="content-warnings"),
                    dcc.Textarea(id="content-warnings", className="form-control mb-2", value=show_defaults.get("content_warnings", ""))
                ], md=6)
            ], className="g-2"),
            dbc.Label("Doors Open", html_for="doors-open"),
            dcc.Input(id="doors-open", type="datetime-local", value=show_defaults.get("doors_open_time", ""), className="form-control mb-2"),
            dbc.Label("Show Start", html_for="show-start"),
            dcc.Input(id="show-start", type="datetime-local", value=show_defaults.get("start_time", ""), className="form-control mb-2"),
            dbc.Label("Show End", html_for="show-end"),
            dcc.Input(id="show-end", type="datetime-local", value=show_defaults.get("end_time", ""), className="form-control mb-2"),
            dbc.Label("Intermission Notes", html_for="intermission"),
            dcc.Textarea(id="intermission", className="form-control mb-2", value=show_defaults.get("intermission_description", ""))
        ]),
        className="mb-3"
    )

    actions = dbc.Row([
        dbc.Col(dbc.Button("Generate Preview", id="preview-btn", color="primary", className="w-100 action-btn")),
        dbc.Col(dbc.Button("Export HTML", id="export-btn", color="light", className="w-100 action-btn")),
        dbc.Col(dbc.Button("Send Now", id="send-btn", color="success", className="w-100 action-btn", disabled=not MAILCHIMP_READY)),
        dbc.Col(dbc.Button("Schedule", id="schedule-btn", color="warning", className="w-100 text-dark action-btn", disabled=not MAILCHIMP_READY))
    ], className="g-2 mb-2")

    preview_controls = dbc.Row([
        dbc.Col([
            dbc.Label("Preview Theme"),
            dcc.RadioItems(
                id="theme-toggle",
                options=[{"label": "Light", "value": "light"}, {"label": "Dark", "value": "dark"}],
                value="light",
                inline=True,
                className="toggle-group"
            )
        ], md=6),
        dbc.Col([
            dbc.Label("Viewport"),
            dcc.RadioItems(
                id="viewport-toggle",
                options=[{"label": "Desktop", "value": "desktop"}, {"label": "Mobile", "value": "mobile"}],
                value="desktop",
                inline=True,
                className="toggle-group"
            )
        ], md=6)
    ], className="g-2 mb-2")

    preview = dbc.Card(
        dbc.CardBody([
            html.Div(id="send-status"),
            html.Div(id="schedule-status"),
            html.Div(id="preview-status"),
            preview_controls,
            dcc.Loading(html.Iframe(id="preview-frame", style={
                "width": "100%",                   # Default desktop width
                "height": "92vh",                  # Tall enough to see full email
                "border": "1px solid #1f1f1f",     # Dark frame around email preview
                "borderRadius": "8px",             # Rounded iframe corners
                "background": "#102532"            # Fallback backdrop while loading
            }, className="bg-white"), type="default")
        ]),
        className="bg-dark text-light"
    )

    show_section = dbc.Card([
        dbc.CardHeader(
            html.Div([
                html.Span("▸", id="show-chevron", className="me-2 chevron-icon rotate-90"),
                html.Span("Show Details", className="fw-semibold")
            ], id="toggle-show", n_clicks=0, className="d-flex align-items-center text-white text-decoration-none toggle-row"),
            className="bg-transparent border-0"
        ),
        dbc.Collapse(show_form, id="show-collapse", is_open=True)
    ], className="mb-3 border-0")

    theatre_section = dbc.Card([
        dbc.CardHeader(
            html.Div([
                html.Span("▸", id="theatre-chevron", className="me-2 chevron-icon rotate-90"),
                html.Span("Theatre Details", className="fw-semibold")
            ], id="toggle-theatre", n_clicks=0, className="d-flex align-items-center text-white text-decoration-none toggle-row"),
            className="bg-transparent border-0"
        ),
        dbc.Collapse(theatre_form, id="theatre-collapse", is_open=True)
    ], className="mb-3 border-0")

    mailchimp_note = None
    if not MAILCHIMP_READY:
        mailchimp_note = dbc.Alert("Mailchimp keys missing; Send and Schedule are disabled.", color="secondary", className="py-2 my-1")

    return dbc.Row([
        dbc.Col([show_section, theatre_section], lg=5),
        dbc.Col([actions, mailchimp_note, html.Div(id="export-status"), preview], lg=7)
    ], className="mt-3")


def scheduled_tab():
    return dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col(html.H5("Scheduled Campaigns", className="fw-semibold"), sm=8),
                dbc.Col(dbc.Button("Refresh", id="scheduled-refresh", color="secondary",
                                   className="float-end secondary-btn"), sm=4)
            ]),
            html.Div(id="management-status", className="mt-2"),
            dcc.Loading(html.Div(id="scheduled-table"), type="dot")
        ])
    )


def archive_tab():
    today = datetime.now().date()
    month_ago = today.replace(day=1)
    return dbc.Card(
        dbc.CardBody([
            html.H5("Sent Campaign Archive", className="fw-semibold"),
            dbc.Alert("Archive relies on Mailchimp history; results are accurate only for campaigns sent through this dashboard/Mailchimp account.", color="warning", className="text-dark"),
            dbc.Row([
                dbc.Col(dcc.DatePickerRange(
                    id="date-range",
                    start_date=month_ago,
                end_date=today
            ), md=8),
            dbc.Col(dbc.Button("Load Sent", id="sent-refresh", color="secondary", className="mt-2 mt-md-0 secondary-btn"))
        ], className="g-2 mb-3"),
            dbc.Row([
                dbc.Col(dcc.Loading(html.Div(id="sent-list"), type="dot"), md=5),
                dbc.Col(dcc.Loading(html.Iframe(id="sent-preview", style={
                    "width": "100%", "height": "60vh", "border": "1px solid #1f1f1f", "borderRadius": "8px"
                }, className="bg-white"), type="default"), md=7)
            ], className="g-3")
        ])
    )


app.layout = dbc.Container([
    dcc.Store(id="config-store", data=config_defaults),
    dcc.Store(id="show-store", data=show_defaults),
    dcc.Store(id="generated-html"),
    hero,
    dbc.Tabs([
        dbc.Tab(editor_tab(), label="Editor & Actions", tab_id="tab-editor", tabClassName="fw-semibold"),
        dbc.Tab(scheduled_tab(), label="Scheduled Campaigns", tab_id="tab-scheduled", tabClassName="fw-semibold"),
        dbc.Tab(archive_tab(), label="Archive", tab_id="tab-archive", tabClassName="fw-semibold")
    ], id="main-tabs", active_tab="tab-editor", className="mt-4"),
    dbc.Modal([
        dbc.ModalHeader("Schedule Campaign"),
        dbc.ModalBody([
            dbc.Label("Send time (local)", html_for="schedule-datetime"),
            dcc.Input(id="schedule-datetime", type="datetime-local", className="form-control")
        ]),
        dbc.ModalFooter([
            dbc.Button("Close", id="schedule-close", color="secondary"),
            dbc.Button("Confirm Schedule", id="schedule-confirm", color="warning", className="text-dark")
        ])
    ], id="schedule-modal", is_open=False),
    dcc.Download(id="download-html"),
], fluid=True, className="pb-4", style={
    "background": "#0f0f10",   # App shell background behind cards
    "minHeight": "100vh",      # Ensure full-height backdrop
    "color": "#f8f9fa"         # Default text color on shell
})


@app.callback(
    Output("schedule-modal", "is_open"),
    [Input("schedule-btn", "n_clicks"), Input("schedule-close", "n_clicks")],
    [State("schedule-modal", "is_open")]
)
def toggle_schedule_modal(open_clicks, close_clicks, is_open):
    if not open_clicks and not close_clicks:
        raise PreventUpdate
    return not is_open


@app.callback(
    Output("show-collapse", "is_open"),
    Output("show-chevron", "className"),
    Input("toggle-show", "n_clicks"),
    State("show-collapse", "is_open"),
    prevent_initial_call=True
)
def toggle_show_section(n, is_open):
    if not n:
        raise PreventUpdate
    new_state = not is_open
    chevron_class = "me-2 chevron-icon rotate-90" if new_state else "me-2 chevron-icon"
    return new_state, chevron_class


@app.callback(
    Output("theatre-collapse", "is_open"),
    Output("theatre-chevron", "className"),
    Input("toggle-theatre", "n_clicks"),
    State("theatre-collapse", "is_open"),
    prevent_initial_call=True
)
def toggle_theatre_section(n, is_open):
    if not n:
        raise PreventUpdate
    new_state = not is_open
    chevron_class = "me-2 chevron-icon rotate-90" if new_state else "me-2 chevron-icon"
    return new_state, chevron_class


@app.callback(
    Output("primary-color-hex", "value", allow_duplicate=True),
    Input("primary-color", "value"),
    prevent_initial_call=True
)
def sync_primary_color_to_hex(val):
    return val


@app.callback(
    Output("primary-color", "value", allow_duplicate=True),
    Input("primary-color-hex", "value"),
    prevent_initial_call=True
)
def sync_primary_hex_to_color(val):
    return normalize_hex(val)


@app.callback(
    Output("secondary-color-hex", "value", allow_duplicate=True),
    Input("secondary-color", "value"),
    prevent_initial_call=True
)
def sync_secondary_color_to_hex(val):
    return val


@app.callback(
    Output("secondary-color", "value", allow_duplicate=True),
    Input("secondary-color-hex", "value"),
    prevent_initial_call=True
)
def sync_secondary_hex_to_color(val):
    return normalize_hex(val)


@app.callback(
    Output("headline-color-hex", "value", allow_duplicate=True),
    Input("headline-color", "value"),
    prevent_initial_call=True
)
def sync_headline_color_to_hex(val):
    return val


@app.callback(
    Output("headline-color", "value", allow_duplicate=True),
    Input("headline-color-hex", "value"),
    prevent_initial_call=True
)
def sync_headline_hex_to_color(val):
    return normalize_hex(val)


@app.callback(
    Output("theatre-name", "value"),
    Output("theatre-address", "value"),
    Output("theatre-phone", "value"),
    Output("theatre-email", "value"),
    Output("theatre-accessibility", "value"),
    Output("logo-url", "value"),
    Output("primary-color", "value"),
    Output("primary-color-hex", "value"),
    Output("secondary-color", "value"),
    Output("secondary-color-hex", "value"),
    Output("headline-color", "value"),
    Output("headline-color-hex", "value"),
    Output("concession-description", "value"),
    Output("sponsor-name", "value"),
    Output("sponsor-url", "value"),
    Output("whitelist", "value"),
    Output("blacklist", "value"),
    Output("latitude", "value"),
    Output("longitude", "value"),
    Output("radius", "value"),
    Output("whitelist-radius", "value"),
    Output("config-store", "data"),
    Output("config-load-status", "children"),
    Input("upload-config", "contents"),
    State("upload-config", "filename"),
    prevent_initial_call=True
)
def load_config_upload(contents, filename):
    if not contents:
        raise PreventUpdate
    try:
        decoded = decode_upload(contents)
        data = yaml.safe_load(decoded)
        theatre = data.get("theatre", {})
        branding = data.get("branding", {})
        details = data.get("details", {})
        concessions = data.get("concessions", {})
        sponsor = concessions.get("sponsor", {})
        lists_cfg = data.get("lists", {})
        status = dbc.Alert(f"Loaded config from {filename}.", color="success", dismissable=True)
        return (
            theatre.get("name", ""),
            theatre.get("address", ""),
            details.get("contact_phone", ""),
            details.get("contact_email", ""),
            details.get("accessibility_note", ""),
            branding.get("logo_url", ""),
            branding.get("primary_color", ""),
            branding.get("primary_color", ""),
            branding.get("secondary_color", ""),
            branding.get("secondary_color", ""),
            branding.get("headline_color", ""),
            branding.get("headline_color", ""),
            concessions.get("description", ""),
            sponsor.get("name", ""),
            sponsor.get("url", ""),
            ",".join(lists_cfg.get("whitelist", []) or []),
            ",".join(lists_cfg.get("blacklist", []) or []),
            theatre.get("location", {}).get("latitude", ""),
            theatre.get("location", {}).get("longitude", ""),
            theatre.get("radius_meters", ""),
            theatre.get("whitelist_radius_meters", ""),
            data,
            status
        )
    except Exception as exc:  # pragma: no cover
        status = dbc.Alert(f"Failed to load config: {exc}", color="danger", dismissable=True)
        return (dash.no_update,) * 22 + (status,)


@app.callback(
    Output("show-title", "value"),
    Output("timezone-abbrev", "value"),
    Output("audience-rating", "value"),
    Output("doors-open", "value"),
    Output("show-start", "value"),
    Output("show-end", "value"),
    Output("intermission", "value"),
    Output("content-warnings", "value"),
    Output("show-store", "data"),
    Output("show-load-status", "children"),
    Input("upload-show", "contents"),
    State("upload-show", "filename"),
    prevent_initial_call=True
)
def load_show_upload(contents, filename):
    if not contents:
        raise PreventUpdate
    try:
        decoded = decode_upload(contents)
        data = json.load(io.BytesIO(decoded))
        status = dbc.Alert(f"Loaded show data from {filename}.", color="success", dismissable=True)
        return (
            data.get("show_title", ""),
            data.get("timezone_abbreviation", ""),
            data.get("audience_rating", ""),
            data.get("doors_open_time", ""),
            data.get("start_time", ""),
            data.get("end_time", ""),
            data.get("intermission_description", ""),
            data.get("content_warnings", ""),
            data,
            status
        )
    except Exception as exc:  # pragma: no cover
        status = dbc.Alert(f"Failed to load show file: {exc}", color="danger", dismissable=True)
        return (dash.no_update,) * 9 + (status,)


@app.callback(
    Output("preview-frame", "srcDoc"),
    Output("generated-html", "data"),
    Output("preview-status", "children"),
    Output("preview-frame", "style"),
    Input("preview-btn", "n_clicks"),
    Input("theme-toggle", "value"),
    Input("viewport-toggle", "value"),
    State("generated-html", "data"),
    State("config-store", "data"),
    State("show-title", "value"),
    State("show-start", "value"),
    State("show-end", "value"),
    State("doors-open", "value"),
    State("intermission", "value"),
    State("timezone-abbrev", "value"),
    State("audience-rating", "value"),
    State("content-warnings", "value"),
    State("theatre-name", "value"),
    State("theatre-address", "value"),
    State("theatre-phone", "value"),
    State("theatre-email", "value"),
    State("theatre-accessibility", "value"),
    State("logo-url", "value"),
    State("primary-color", "value"),
    State("primary-color-hex", "value"),
    State("secondary-color", "value"),
    State("secondary-color-hex", "value"),
    State("headline-color", "value"),
    State("headline-color-hex", "value"),
    State("concession-description", "value"),
    State("sponsor-name", "value"),
    State("sponsor-url", "value"),
    State("whitelist", "value"),
    State("blacklist", "value"),
    State("latitude", "value"),
    State("longitude", "value"),
    State("radius", "value"),
    State("whitelist-radius", "value")
)
def generate_preview(n_clicks, theme_mode, viewport_mode, cached_html, config_data, show_title, start_time,
                     end_time, doors_open, intermission, tz_abbrev, audience_rating, content_warnings,
                     theatre_name, theatre_address, theatre_phone, theatre_email, theatre_accessibility,
                     logo_url, primary_color, primary_color_hex, secondary_color, secondary_color_hex,
                     headline_color, headline_color_hex, concession_description, sponsor_name, sponsor_url,
                     whitelist_csv, blacklist_csv, latitude, longitude, radius, whitelist_radius):
    ctx = dash.callback_context
    triggered = ctx.triggered_id
    if not triggered and not cached_html:
        raise PreventUpdate

    regenerate = triggered == "preview-btn" or not cached_html

    try:
        if regenerate:
            show_data = build_show_data_from_inputs(show_title, start_time, end_time, doors_open,
                                                    intermission, tz_abbrev, audience_rating,
                                                    content_warnings)
            config = build_config_from_inputs(
                config_data, theatre_name, theatre_address, theatre_phone, theatre_email,
                theatre_accessibility, logo_url, primary_color, secondary_color,
                headline_color, latitude, longitude, radius, whitelist_radius,
                concession_description, sponsor_name, sponsor_url, whitelist_csv, blacklist_csv,
                primary_color_hex, secondary_color_hex, headline_color_hex
            )
            html_body = generate_email_html(show_data, config)
            status = dbc.Alert("Preview updated with latest inputs.", color="success", dismissable=True, fade=True)
        else:
            html_body = cached_html
            status = dash.no_update

        preview_html = apply_preview_overrides(html_body, theme_mode)
        iframe_style = {
            "width": "420px" if viewport_mode == "mobile" else "100%",  # Constrain preview to mobile width toggle
            "height": "85vh",                                          # Show long emails without scrolling page
            "border": "1px solid #1f1f1f",                             # Frame around iframe
            "borderRadius": "8px",                                     # Rounded preview corners
            "margin": "0 auto",                                        # Center preview frame
            "display": "block"
        }
        return preview_html, html_body, status, iframe_style
    except Exception as exc:  # pragma: no cover - UI feedback path
        status = dbc.Alert(f"Could not generate preview: {exc}", color="danger", dismissable=True)
        return dash.no_update, dash.no_update, status, dash.no_update


@app.callback(
    Output("download-html", "data"),
    Output("generated-html", "data", allow_duplicate=True),
    Output("export-status", "children"),
    Input("export-btn", "n_clicks"),
    State("generated-html", "data"),
    State("config-store", "data"),
    State("show-title", "value"),
    State("show-start", "value"),
    State("show-end", "value"),
    State("doors-open", "value"),
    State("intermission", "value"),
    State("timezone-abbrev", "value"),
    State("audience-rating", "value"),
    State("content-warnings", "value"),
    State("theatre-name", "value"),
    State("theatre-address", "value"),
    State("theatre-phone", "value"),
    State("theatre-email", "value"),
    State("theatre-accessibility", "value"),
    State("logo-url", "value"),
    State("primary-color", "value"),
    State("primary-color-hex", "value"),
    State("secondary-color", "value"),
    State("secondary-color-hex", "value"),
    State("headline-color", "value"),
    State("headline-color-hex", "value"),
    State("concession-description", "value"),
    State("sponsor-name", "value"),
    State("sponsor-url", "value"),
    State("whitelist", "value"),
    State("blacklist", "value"),
    State("latitude", "value"),
    State("longitude", "value"),
    State("radius", "value"),
    State("whitelist-radius", "value"),
    prevent_initial_call=True
)
def export_html(n_clicks, cached_html, config_data, show_title, start_time, end_time, doors_open,
                intermission, tz_abbrev, audience_rating, content_warnings,
                theatre_name, theatre_address, theatre_phone, theatre_email, theatre_accessibility,
                logo_url, primary_color, primary_color_hex, secondary_color, secondary_color_hex,
                headline_color, headline_color_hex, concession_description, sponsor_name, sponsor_url,
                whitelist_csv, blacklist_csv, latitude, longitude, radius, whitelist_radius):
    if not n_clicks:
        raise PreventUpdate

    html_body = cached_html
    status = None
    if not html_body:
        try:
            show_data = build_show_data_from_inputs(show_title, start_time, end_time, doors_open,
                                                    intermission, tz_abbrev, audience_rating,
                                                    content_warnings)
            config = build_config_from_inputs(
                config_data, theatre_name, theatre_address, theatre_phone, theatre_email,
                theatre_accessibility, logo_url, primary_color, secondary_color,
                headline_color, latitude, longitude, radius, whitelist_radius,
                concession_description, sponsor_name, sponsor_url, whitelist_csv, blacklist_csv,
                primary_color_hex, secondary_color_hex, headline_color_hex
            )
            html_body = generate_email_html(show_data, config)
        except Exception as exc:  # pragma: no cover
            status = dbc.Alert(f"Export failed: {exc}", color="danger", dismissable=True)
            return dash.no_update, dash.no_update, status

    download_payload = dict(content=html_body, filename="email.html")
    status = status or dbc.Alert("HTML exported. Check your downloads.", color="info", dismissable=True)
    return download_payload, html_body, status


@app.callback(
    Output("send-status", "children"),
    Input("send-btn", "n_clicks"),
    State("generated-html", "data"),
    State("config-store", "data"),
    State("show-title", "value"),
    State("show-start", "value"),
    State("show-end", "value"),
    State("doors-open", "value"),
    State("intermission", "value"),
    State("timezone-abbrev", "value"),
    State("audience-rating", "value"),
    State("content-warnings", "value"),
    State("theatre-name", "value"),
    State("theatre-address", "value"),
    State("theatre-phone", "value"),
    State("theatre-email", "value"),
    State("theatre-accessibility", "value"),
    State("logo-url", "value"),
    State("primary-color", "value"),
    State("primary-color-hex", "value"),
    State("secondary-color", "value"),
    State("secondary-color-hex", "value"),
    State("headline-color", "value"),
    State("headline-color-hex", "value"),
    State("concession-description", "value"),
    State("sponsor-name", "value"),
    State("sponsor-url", "value"),
    State("whitelist", "value"),
    State("blacklist", "value"),
    State("latitude", "value"),
    State("longitude", "value"),
    State("radius", "value"),
    State("whitelist-radius", "value"),
    prevent_initial_call=True
)
def send_now(n_clicks, cached_html, config_data, show_title, start_time, end_time, doors_open,
             intermission, tz_abbrev, audience_rating, content_warnings, theatre_name, theatre_address,
             theatre_phone, theatre_email, theatre_accessibility, logo_url, primary_color,
             primary_color_hex, secondary_color, secondary_color_hex, headline_color,
             headline_color_hex, concession_description, sponsor_name, sponsor_url,
             whitelist_csv, blacklist_csv, latitude, longitude, radius, whitelist_radius):
    if not n_clicks:
        raise PreventUpdate
    if not MAILCHIMP_READY:
        return dbc.Alert("Mailchimp credentials missing; cannot send.", color="secondary", dismissable=True)

    try:
        html_body = cached_html
        if not html_body:
            show_data = build_show_data_from_inputs(show_title, start_time, end_time, doors_open,
                                                    intermission, tz_abbrev, audience_rating,
                                                    content_warnings)
            config = build_config_from_inputs(
                config_data, theatre_name, theatre_address, theatre_phone, theatre_email,
                theatre_accessibility, logo_url, primary_color, secondary_color,
                headline_color, latitude, longitude, radius, whitelist_radius,
                concession_description, sponsor_name, sponsor_url, whitelist_csv, blacklist_csv,
                primary_color_hex, secondary_color_hex, headline_color_hex
            )
            html_body = generate_email_html(show_data, config)
        else:
            config = build_config_from_inputs(
                config_data, theatre_name, theatre_address, theatre_phone, theatre_email,
                theatre_accessibility, logo_url, primary_color, secondary_color,
                headline_color, latitude, longitude, radius, whitelist_radius,
                concession_description, sponsor_name, sponsor_url, whitelist_csv, blacklist_csv,
                primary_color_hex, secondary_color_hex, headline_color_hex
            )
        subject = f"Upcoming Performance: {show_title}"
        from_name = config["theatre"]["name"]
        reply_to = config["details"]["contact_email"]

        draft = sender.create_draft_campaign(html_body, subject, from_name, reply_to)
        if not draft:
            return dbc.Alert("Draft creation failed. Check Mailchimp credentials.", color="danger", dismissable=True)

        if sender.send_campaign_now(draft["id"]):
            return dbc.Alert("Campaign sent to Mailchimp.", color="success", dismissable=True)
        return dbc.Alert("Campaign draft created but sending failed.", color="warning", dismissable=True)
    except Exception as exc:  # pragma: no cover
        return dbc.Alert(f"Send failed: {exc}", color="danger", dismissable=True)


@app.callback(
    Output("schedule-status", "children"),
    Output("schedule-modal", "is_open", allow_duplicate=True),
    Input("schedule-confirm", "n_clicks"),
    State("schedule-datetime", "value"),
    State("generated-html", "data"),
    State("config-store", "data"),
    State("show-title", "value"),
    State("show-start", "value"),
    State("show-end", "value"),
    State("doors-open", "value"),
    State("intermission", "value"),
    State("timezone-abbrev", "value"),
    State("audience-rating", "value"),
    State("content-warnings", "value"),
    State("theatre-name", "value"),
    State("theatre-address", "value"),
    State("theatre-phone", "value"),
    State("theatre-email", "value"),
    State("theatre-accessibility", "value"),
    State("logo-url", "value"),
    State("primary-color", "value"),
    State("primary-color-hex", "value"),
    State("secondary-color", "value"),
    State("secondary-color-hex", "value"),
    State("headline-color", "value"),
    State("headline-color-hex", "value"),
    State("concession-description", "value"),
    State("sponsor-name", "value"),
    State("sponsor-url", "value"),
    State("whitelist", "value"),
    State("blacklist", "value"),
    State("latitude", "value"),
    State("longitude", "value"),
    State("radius", "value"),
    State("whitelist-radius", "value"),
    prevent_initial_call=True
)
def schedule_campaign(n_clicks, schedule_time, cached_html, config_data, show_title, start_time, end_time,
                      doors_open, intermission, tz_abbrev, audience_rating, content_warnings,
                      theatre_name, theatre_address, theatre_phone, theatre_email, theatre_accessibility,
                      logo_url, primary_color, primary_color_hex, secondary_color, secondary_color_hex,
                      headline_color, headline_color_hex, concession_description, sponsor_name, sponsor_url,
                      whitelist_csv, blacklist_csv, latitude, longitude, radius, whitelist_radius):
    if not n_clicks:
        raise PreventUpdate
    if not MAILCHIMP_READY:
        return dbc.Alert("Mailchimp credentials missing; cannot schedule.", color="secondary", dismissable=True), False
    try:
        html_body = cached_html
        if not html_body:
            show_data = build_show_data_from_inputs(show_title, start_time, end_time, doors_open,
                                                    intermission, tz_abbrev, audience_rating,
                                                    content_warnings)
            config = build_config_from_inputs(
                config_data, theatre_name, theatre_address, theatre_phone, theatre_email,
                theatre_accessibility, logo_url, primary_color, secondary_color,
                headline_color, latitude, longitude, radius, whitelist_radius,
                concession_description, sponsor_name, sponsor_url, whitelist_csv, blacklist_csv,
                primary_color_hex, secondary_color_hex, headline_color_hex
            )
            html_body = generate_email_html(show_data, config)
        else:
            config = build_config_from_inputs(
                config_data, theatre_name, theatre_address, theatre_phone, theatre_email,
                theatre_accessibility, logo_url, primary_color, secondary_color,
                headline_color, latitude, longitude, radius, whitelist_radius,
                concession_description, sponsor_name, sponsor_url, whitelist_csv, blacklist_csv,
                primary_color_hex, secondary_color_hex, headline_color_hex
            )
        subject = f"Upcoming Performance: {show_title}"
        from_name = config["theatre"]["name"]
        reply_to = config["details"]["contact_email"]

        draft = sender.create_draft_campaign(html_body, subject, from_name, reply_to)
        if not draft:
            return dbc.Alert("Draft creation failed. Check Mailchimp credentials.", color="danger", dismissable=True), False

        schedule_time_utc = to_utc_iso(schedule_time)
        if sender.schedule_campaign(draft["id"], schedule_time_utc):
            msg = f"Campaign scheduled for {schedule_time_utc} UTC."
            return dbc.Alert(msg, color="success", dismissable=True), False
        return dbc.Alert("Scheduling failed after creating draft.", color="warning", dismissable=True), False
    except Exception as exc:  # pragma: no cover
        return dbc.Alert(f"Schedule failed: {exc}", color="danger", dismissable=True), False


@app.callback(
    Output("scheduled-table", "children"),
    Output("management-status", "children"),
    Input("scheduled-refresh", "n_clicks"),
    Input({"type": "cancel-campaign", "index": ALL}, "n_clicks"),
    Input("main-tabs", "active_tab"),
    prevent_initial_call=True
)
def load_scheduled(refresh_clicks, cancel_clicks, active_tab):
    triggered = dash.callback_context.triggered_id
    if active_tab != "tab-scheduled":
        raise PreventUpdate

    status = None
    if isinstance(triggered, dict) and triggered.get("type") == "cancel-campaign":
        campaign_id = triggered.get("index")
        if campaign_id and sender.unschedule_campaign(campaign_id):
            status = dbc.Alert(f"Campaign {campaign_id} unscheduled.", color="success", dismissable=True)
        elif campaign_id:
            status = dbc.Alert(f"Could not unschedule {campaign_id}.", color="danger", dismissable=True)

    campaigns = sender.get_campaigns(status="scheduled")
    return campaign_cards(campaigns, "No scheduled campaigns yet."), status


@app.callback(
    Output("sent-list", "children"),
    Input("sent-refresh", "n_clicks"),
    Input("main-tabs", "active_tab"),
    State("date-range", "start_date"),
    State("date-range", "end_date"),
    prevent_initial_call=True
)
def load_sent(n_clicks, active_tab, start_date, end_date):
    if active_tab != "tab-archive" or not n_clicks:
        raise PreventUpdate
    campaigns = sender.get_campaigns(status="sent", since_date=start_date, until_date=end_date)
    return sent_list(campaigns)


@app.callback(
    Output("sent-preview", "srcDoc"),
    Input({"type": "sent-campaign", "index": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def show_sent_preview(clicks):
    triggered = dash.callback_context.triggered_id
    if not triggered:
        raise PreventUpdate
    campaign_id = triggered.get("index")
    if not campaign_id:
        raise PreventUpdate
    content = sender.get_campaign_content(campaign_id)
    if not content:
        return ""
    return content


if __name__ == "__main__":
    # Dash dev tools rely on deprecated pkgutil APIs in newer Python; keep debug off for compatibility.
    app.run_server(debug=False)
