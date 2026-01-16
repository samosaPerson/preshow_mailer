# src/generator.py
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timedelta
from urllib.parse import quote
import base64
import mimetypes
import os
import re
import sys

import requests

from src.services.weather import get_forecast
from src.services.places import get_nearby_places

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def format_date(iso_date_str):
    try: return datetime.fromisoformat(iso_date_str).strftime("%A, %B %d at %I:%M %p")
    except ValueError: return iso_date_str

def runtime(end_iso_str, start_iso_str):
    try:
        start = datetime.fromisoformat(start_iso_str)
        end = datetime.fromisoformat(end_iso_str)
        mins = int((end - start).total_seconds() / 60)
        h, m = divmod(mins, 60)
        if h > 0: return f"{h} hour{'s' if h>1 else ''} and {m} minutes"
        return f"{m} minutes"
    except: return "TBD"

def simple_time(iso_date_str):
    """Formats just the time (7:00 PM)."""
    try: return datetime.fromisoformat(iso_date_str).strftime("%I:%M %p")
    except: return "TBD"

def build_context(config_data, show_data):
    """Fetch data and build the render context once."""
    # 1. Fetch Weather
    weather_data = get_forecast(
        latitude=config_data['theatre']['location']['latitude'],
        longitude=config_data['theatre']['location']['longitude'],
        start_time=show_data['start_time'],
        end_time=show_data['end_time'],
        units=config_data['settings'].get('units', 'imperial')
    )

    # 2. Calculate Place Check Times
    start_dt = datetime.fromisoformat(show_data['start_time'])
    end_dt = datetime.fromisoformat(show_data['end_time'])

    pre_show_checks = [
        start_dt - timedelta(minutes=60),
        start_dt - timedelta(minutes=15)
    ]

    post_show_checks = [
        end_dt + timedelta(minutes=5),
        end_dt + timedelta(minutes=40)
    ]

    # 3. Fetch Places
    google_api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    loc = config_data['theatre']['location']
    radius = config_data['theatre']['radius_meters']
    whitelist_radius = config_data['theatre'].get('whitelist_radius_meters', 1500)

    pre_show_places = get_nearby_places(
        loc['latitude'], loc['longitude'], radius,
        config_data['business_categories']['pre_show'],
        pre_show_checks,
        config_data.get('lists', {}),
        google_api_key, whitelist_radius
    )

    post_show_places = get_nearby_places(
        loc['latitude'], loc['longitude'], radius,
        config_data['business_categories']['post_show'],
        post_show_checks,
        config_data.get('lists', {}),
        google_api_key, whitelist_radius
    )

    return {
        'config': config_data,
        'show_info': show_data,
        'weather': weather_data,
        'places': {'pre_show': pre_show_places, 'post_show': post_show_places}
    }

DEFAULT_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
LOGO_EMBED_WIDTH = 150


def fetch_url(url, timeout=6):
    return requests.get(url, timeout=timeout, headers={"User-Agent": DEFAULT_UA})


def rasterize_svg_url(svg_url, width=None):
    encoded = quote(svg_url, safe="")
    raster_url = f"https://images.weserv.nl/?url={encoded}&output=png"
    if width:
        raster_url += f"&w={width}"
    response = fetch_url(raster_url, timeout=8)
    response.raise_for_status()
    return response.content, "image/png"


def build_raster_url(image_url, width=None):
    encoded = quote(image_url, safe="")
    raster_url = f"https://images.weserv.nl/?url={encoded}&output=png"
    if width:
        raster_url += f"&w={width}"
    return raster_url


def resize_remote_image(url, width=None):
    encoded = quote(url, safe="")
    raster_url = f"https://images.weserv.nl/?url={encoded}&output=png"
    if width:
        raster_url += f"&w={width}"
    response = fetch_url(raster_url, timeout=8)
    response.raise_for_status()
    content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip()
    if not content_type:
        content_type = mimetypes.guess_type(url)[0] or "image/png"
    return response.content, content_type


def fetch_remote_logo(logo_url):
    response = fetch_url(logo_url)
    response.raise_for_status()
    content = response.content
    content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip()
    if not content_type:
        content_type = mimetypes.guess_type(logo_url)[0]
    return content, content_type


def strip_dark_mode_html(html_body):
    if not html_body:
        return html_body
    html_body = re.sub(r'<meta name="color-scheme"[^>]*>\s*', "", html_body, flags=re.IGNORECASE)
    html_body = re.sub(r'<meta name="supported-color-schemes"[^>]*>\s*', "", html_body, flags=re.IGNORECASE)
    html_body = re.sub(
        r"/\* DARK MODE START \*/.*?/\* DARK MODE END \*/\s*",
        "",
        html_body,
        flags=re.DOTALL
    )
    return html_body


def build_logo_src(logo_url, embed_logo):
    if not logo_url:
        return ""
    if not embed_logo:
        return logo_url
    try:
        if logo_url.startswith(("http://", "https://")):
            guessed_type = mimetypes.guess_type(logo_url)[0]
            is_svg = guessed_type == "image/svg+xml" or logo_url.lower().endswith(".svg")
            try:
                if is_svg:
                    content, content_type = rasterize_svg_url(logo_url, width=LOGO_EMBED_WIDTH)
                else:
                    content, content_type = resize_remote_image(logo_url, width=LOGO_EMBED_WIDTH)
            except Exception:
                content, content_type = fetch_remote_logo(logo_url)
        else:
            with open(logo_url, "rb") as handle:
                content = handle.read()
            content_type = mimetypes.guess_type(logo_url)[0]
        is_svg = content_type == "image/svg+xml" or logo_url.lower().endswith(".svg")
        if is_svg and logo_url.startswith(("http://", "https://")) and content_type != "image/png":
            content_type = "image/svg+xml"
        if not content_type:
            content_type = "image/png"
        encoded = base64.b64encode(content).decode("ascii")
        return f"data:{content_type};base64,{encoded}"
    except Exception:
        return logo_url


def render_email_from_context(context, include_mailchimp_footer=True, embed_logo=False, strip_dark_mode=False, fragment_mode=False):
    """Render HTML/text from a prebuilt context without refetching data."""
    template_dir = resource_path('src/templates')
    file_loader = FileSystemLoader(template_dir)
    env = Environment(loader=file_loader)

    env.filters['format_date'] = format_date
    env.filters['runtime'] = runtime
    env.filters['simple_time'] = simple_time

    template = env.get_template('email_body.html')
    render_context = dict(context)
    config = dict(render_context.get("config", {}))
    branding = dict(config.get("branding", {}))
    logo_url = branding.get("logo_url", "")
    if fragment_mode and logo_url.startswith(("http://", "https://")):
        if logo_url.lower().endswith(".svg"):
            branding["logo_src"] = build_raster_url(logo_url, width=LOGO_EMBED_WIDTH)
        else:
            branding["logo_src"] = logo_url
    else:
        branding["logo_src"] = build_logo_src(logo_url, embed_logo)
    config["branding"] = branding
    render_context["config"] = config
    render_context['include_mailchimp_footer'] = include_mailchimp_footer
    render_context["fragment_mode"] = fragment_mode
    html_body = template.render(context=render_context)
    if strip_dark_mode:
        html_body = strip_dark_mode_html(html_body)
    return html_body, "Text version placeholder"


def generate_email(config_data, show_data, include_mailchimp_footer=True):
    """Public entry point for generating email HTML/text."""
    ctx = build_context(config_data, show_data)
    embed_logo = not include_mailchimp_footer
    strip_dark_mode = not include_mailchimp_footer
    return render_email_from_context(
        ctx,
        include_mailchimp_footer,
        embed_logo=embed_logo,
        strip_dark_mode=strip_dark_mode
    )
