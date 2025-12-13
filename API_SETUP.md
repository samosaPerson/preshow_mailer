# API Access Setup

This project only needs two APIs to generate the pre-show email content (weather + nearby dining). Mailchimp is optional and only required if you want to send or schedule campaigns directly from the dashboard/CLI.

## Which API is used for what
- Google Places API (required): Looks up nearby restaurants/bars and filters them by open hours and distance. Used in `src/services/places.py`.
- WeatherAPI.com Forecast API (required): Pulls arrival and departure forecasts for the show times. Used in `src/services/weather.py`.
- Mailchimp Marketing API (optional): Creates/sends/schedules campaigns when using the dashboard “Send/Schedule” buttons or `--action upload` in the CLI. Used in `src/sender.py`.

## Environment variables to set
Create a `.env` file in the repo root (do not commit it). Use placeholder values until you have real keys:
```dotenv
GOOGLE_PLACES_API_KEY="YOUR_GOOGLE_PLACES_KEY"
WEATHER_API_KEY="YOUR_WEATHERAPI_KEY"
# Optional (only if sending/scheduling via Mailchimp)
MAILCHIMP_API_KEY="YOUR_MAILCHIMP_KEY"
MAILCHIMP_SERVER_PREFIX="usX"    # e.g., us1, us16
MAILCHIMP_LIST_ID="YOUR_AUDIENCE_ID"
```

## How to get each API key

### Google Places API (required)
1) Go to the [Google Cloud Console](https://console.cloud.google.com/) and create/select a project.  
2) Enable **Places API** (APIs & Services → Enable APIs & Services → search “Places API”).  
3) Create credentials: APIs & Services → Credentials → “Create credentials” → **API key**.  
4) Restrict the key: set API restrictions to **Places API**; add IP or HTTP referrer restrictions as needed.  
5) Copy the key into `GOOGLE_PLACES_API_KEY` in `.env`.

### WeatherAPI.com (required)
1) Sign up at [weatherapi.com](https://www.weatherapi.com/), confirm your account.  
2) In your dashboard, copy the **API key** (the free tier includes the `forecast.json` endpoint used here).  
3) Put it in `WEATHER_API_KEY` in `.env`.

### Mailchimp (optional)
Only needed for sending/scheduling through the app; HTML generation works without it.
1) Create or log into a Mailchimp account.  
2) Find the server prefix (the `usX` part of the API key) from the dashboard URL or when you create a key.  
3) Create an API key: Profile → Extras → API keys & tokens → Create A Key; copy to `MAILCHIMP_API_KEY`.  
4) Get your Audience/List ID: Audience → All contacts → Settings → Audience name and defaults; copy the **Audience ID** to `MAILCHIMP_LIST_ID`.  
5) Save `MAILCHIMP_SERVER_PREFIX` (e.g., `us1`) and the list ID in `.env`. Without these, “Send/Schedule” buttons stay disabled.

## Quick validation
- Generate locally (no Mailchimp required):  
  `python3 src/main.py --config data/examples/theatre_config.yaml --show data/examples/show_info.json --action generate --compliance both`
- If you added Mailchimp keys, try creating a draft (no send):  
  `python3 src/main.py --config data/examples/theatre_config.yaml --show data/examples/show_info.json --action upload --mode draft --compliance mailchimp`
