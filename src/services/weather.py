# src/services/weather.py
import requests
import os
from datetime import datetime, timedelta

WEATHER_API_URL = "http://api.weatherapi.com/v1/forecast.json"

def get_forecast(latitude, longitude, start_time, end_time, units="imperial"):
    """
    Fetches weather. Handles units (imperial/metric).
    """
    api_key = os.environ.get("WEATHER_API_KEY")
    if not api_key:
        return _get_fallback_weather()

    start_dt = datetime.fromisoformat(start_time)
    
    params = {
        "key": api_key,
        "q": f"{latitude},{longitude}",
        "dt": start_dt.strftime('%Y-%m-%d'), 
        "days": 2
    }
    
    try:
        response = requests.get(WEATHER_API_URL, params=params)
        data = response.json()
        
        if 'forecast' not in data: return _get_fallback_weather()

        forecast_days = data['forecast']['forecastday']
        
        arrival_dt = start_dt - timedelta(hours=1)
        end_dt = datetime.fromisoformat(end_time)

        arrival_data = _find_hour_data(forecast_days, arrival_dt)
        departure_data = _find_hour_data(forecast_days, end_dt)

        # Unit Logic
        temp_key = "temp_f" if units == "imperial" else "temp_c"
        unit_symbol = "°F" if units == "imperial" else "°C"

        return {
            "arrival": {
                "temp": f"{round(arrival_data[temp_key])}{unit_symbol}",
                "condition": arrival_data['condition']['text'],
                "icon": _map_icon(arrival_data['condition']['code'], arrival_data['is_day']),
                "is_day": arrival_data['is_day'] # 1 = Day, 0 = Night
            },
            "departure": {
                "temp": f"{round(departure_data[temp_key])}{unit_symbol}",
                "condition": departure_data['condition']['text'],
                "icon": _map_icon(departure_data['condition']['code'], departure_data['is_day']),
                "is_day": departure_data['is_day']
            }
        }

    except Exception as e:
        print(f"Weather Error: {e}")
        return _get_fallback_weather()

def _find_hour_data(forecast_days, target_dt):
    target_date_str = target_dt.strftime('%Y-%m-%d')
    target_hour = target_dt.hour
    day_data = next((d for d in forecast_days if d['date'] == target_date_str), forecast_days[0])
    return day_data['hour'][target_hour]

def _get_fallback_weather():
    return {
        "arrival": {"temp": "--", "condition": "", "icon": "❓", "is_day": 1},
        "departure": {"temp": "--", "condition": "", "icon": "❓", "is_day": 0}
    }

def _map_icon(code, is_day):
    if code == 1000: return "☀️" if is_day else "🌙"
    if code == 1003: return "⛅" if is_day else "☁️"
    if code in [1006, 1009, 1030, 1135, 1147]: return "☁️"
    if code in [1063, 1150, 1153, 1180, 1183, 1186, 1189, 1192, 1195, 1240, 1243, 1246]: return "🌧️"
    if code in [1066, 1114, 1210, 1213, 1216, 1219, 1222, 1225, 1255, 1258]: return "❄️"
    if code in [1087, 1273, 1276, 1279, 1282]: return "⛈️"
    return "⛅"