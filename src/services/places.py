# src/services/places.py
import requests
from datetime import datetime
from src.utils.geo import calculate_distance
from urllib.parse import quote_plus

SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

def get_nearby_places(latitude, longitude, radius_meters, categories_list, check_times, lists_config, api_key=None, whitelist_radius=1500):
    """
    check_times: A list of datetime objects. The place must be open for ALL of them.
    """
    results = {}
    
    # Pre-calculate search radius
    search_radius = max(radius_meters, whitelist_radius)
    
    whitelist = [w.lower() for w in lists_config.get('whitelist', []) or []]
    blacklist = [b.lower() for b in lists_config.get('blacklist', []) or []]

    for category in categories_list:
        cat_name = category['name']
        keyword = category['keyword']
        
        if not api_key:
            results[cat_name] = _get_mock_places(keyword)
        else:
            candidates = _fetch_candidates(latitude, longitude, search_radius, keyword, api_key)
            processed_candidates = []
            
            for place in candidates:
                p_name = place['name'].lower()
                
                # Blacklist
                if any(b_term in p_name for b_term in blacklist): continue

                # Whitelist
                is_whitelisted = any(w_term in p_name for w_term in whitelist)
                place['is_promoted'] = 1 if is_whitelisted else 0
                
                # Distance
                dist = calculate_distance(latitude, longitude, place['lat'], place['lng'])
                place['distance_m'] = dist

                # Uses Google Maps Universal Link with Place ID for accuracy
                query = quote_plus(f"{place['name']}, {place['address']}")
                place['map_url'] = f"https://www.google.com/maps/search/?api=1&query={query}&query_place_id={place['place_id']}"

                # Radius Filter
                if is_whitelisted:
                    if dist > whitelist_radius: continue
                else:
                    if dist > radius_meters: continue
                
                processed_candidates.append(place)

            # Sort: Promoted first, then Distance
            processed_candidates.sort(key=lambda x: (-x['is_promoted'], x['distance_m']))

            # TIME GUARD CHECK (The New Logic)
            valid_places = []
            for place in processed_candidates:
                # Must be open at EVERY check time provided
                is_open_interval = True
                for t in check_times:
                    if not _check_is_open(place['place_id'], t, api_key):
                        is_open_interval = False
                        break
                
                if is_open_interval:
                    valid_places.append(place)
                    if len(valid_places) >= 3:
                        break
            
            results[cat_name] = valid_places

    return results

def _fetch_candidates(lat, lng, radius, keyword, api_key):
    # (Same as before)
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "keyword": keyword,
        "key": api_key,
        "type": "establishment"
    }
    try:
        response = requests.get(SEARCH_URL, params=params)
        data = response.json()
        candidates = []
        for place in data.get('results', []):
            loc = place.get('geometry', {}).get('location', {})
            candidates.append({
                "place_id": place.get('place_id'),
                "name": place.get('name'),
                "rating": place.get('rating', 'N/A'),
                "address": place.get('vicinity'),
                "lat": loc.get('lat'),
                "lng": loc.get('lng')
            })
        return candidates
    except Exception:
        return []

# In src/services/places.py

def _check_is_open(place_id, target_dt, api_key):
    """
    Checks if a place is open at a specific FUTURE date and time.
    """
    params = {
        "place_id": place_id,
        "fields": "opening_hours",
        "key": api_key
    }
    
    try:
        response = requests.get(DETAILS_URL, params=params)
        data = response.json()
        
        # 1. Check if hours exist
        if 'result' not in data or 'opening_hours' not in data['result']:
            # If Google has no hours for this place, we assume it's risky
            # Better to return False (don't show it) than send people to a closed door
            return False 
            
        periods = data['result']['opening_hours'].get('periods', [])
        
        # 2. Convert Times
        # Python: Mon=0...Sun=6. Google: Sun=0...Sat=6
        python_day = target_dt.weekday()
        google_day = (python_day + 1) % 7
        
        # Target time as an integer (e.g. 1930 for 7:30 PM)
        target_time_int = int(target_dt.strftime('%H%M'))
        
        # 3. Check all open periods
        for period in periods:
            open_day = period['open']['day']
            
            # Special Case: Open 24/7 (Day 0, Time 0000, No Close)
            if open_day == 0 and period.get('open', {}).get('time') == "0000" and not period.get('close'):
                return True

            # Match the Day
            if open_day == google_day:
                open_time = int(period['open']['time'])
                close_time = int(period['close']['time'])
                
                # Logic A: Standard Hours (e.g. 0900 to 1700)
                if open_time < close_time:
                    if open_time <= target_time_int < close_time:
                        return True
                        
                # Logic B: Late Night Hours (e.g. 1800 to 0200 next day)
                # If a bar opens at 1800 and closes at 0200, and show is at 2300 (11PM)
                else: 
                    # It is open if time is AFTER open (1900) OR BEFORE close (0100)
                    if target_time_int >= open_time or target_time_int < close_time:
                        return True
                        
        return False # No matching period found

    except Exception as e:
        print(f"Error checking hours for {place_id}: {e}")
        return False # Fail safe: Don't show if we can't verify

def _get_mock_places(keyword):
    return [{"name": "Mock Place", "rating": 5.0, "address": "123 Mock St", "distance_m": 100}]