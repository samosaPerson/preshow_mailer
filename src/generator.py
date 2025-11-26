# src/generator.py
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timedelta
import os
import sys

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

def generate_email(config_data, show_data):
    template_dir = resource_path('src/templates')
    file_loader = FileSystemLoader(template_dir)
    env = Environment(loader=file_loader)
    
    env.filters['format_date'] = format_date
    env.filters['runtime'] = runtime
    env.filters['simple_time'] = simple_time # Replaced logic-heavy filters with this simple one
    
    template = env.get_template('email_body.html')

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
    
    # Pre-Show: Open from T-60 to T-15
    pre_show_checks = [
        start_dt - timedelta(minutes=60),
        start_dt - timedelta(minutes=15)
    ]
    
    # Post-Show: Open from T+5 to T+40
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
        pre_show_checks, # Pass list
        config_data.get('lists', {}),
        google_api_key, whitelist_radius
    )
    
    post_show_places = get_nearby_places(
        loc['latitude'], loc['longitude'], radius,
        config_data['business_categories']['post_show'],
        post_show_checks, # Pass list
        config_data.get('lists', {}),
        google_api_key, whitelist_radius
    )

    context = {
        'config': config_data,
        'show_info': show_data,
        'weather': weather_data,
        'places': {'pre_show': pre_show_places, 'post_show': post_show_places}
    }

    return template.render(context=context), "Text version placeholder"