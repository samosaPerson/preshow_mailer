# Pre-Show Mailer: Theatre Audience Experience Tool

An open-source Python tool designed to improve the patron experience at community theatres by automatically generating polished, accurate, pre-show logistical emails.

Preview a sample email: see `example.html` in the repository.

## Project Value Proposition

The **Pre-Show Mailer** solves the common problem of audience members missing key logistical details (parking, weather, start time). By integrating real-time API data (Weather, Nearby Dining) and automating the generation of perfectly formatted, accessible HTML email content, the tool ensures every patron arrives informed and ready for the show.

* **Target Audience:** Community Theatre staff, especially those utilizing ticketing systems (like Salesforce-based platforms) that handle email sending but lack dynamic content generation.
* **Safety:** This tool **generates content only** (email.html and email.txt). It **does not** touch mailing lists or send emails (that remains the responsibility of your theatre's existing ticketing system).

---

## Quickstart: Generating an Email

Two options:

1) **Dash Dashboard (recommended for staff)**
   - Start the app: `source venv/bin/activate && python3 dashboard.py`
   - Open `http://127.0.0.1:8050/` in your browser.
   - Edit **Show Details** and **Theatre Details** directly in the UI.
   - Use **Generate Preview** to see live HTML (light/dark + mobile/desktop toggles).
   - Export HTML, Send Now, or Schedule (Mailchimp creds required; Send/Schedule buttons auto-disable if missing).
   - Load starter files: upload theatre YAML or show JSON from the UI.
   - Manage scheduled/sent campaigns from tabs (archive accuracy depends on using Mailchimp).

2) **CLI (legacy)**
   - Place show data: `data/examples/show_info.json`
   - Run generator:
     ```bash
     # Standard (no Mailchimp merge tags, includes TXT):
     python3 src/main.py --config data/examples/theatre_config.yaml --show data/examples/show_info.json --action generate --compliance standard

     # Mailchimp merge-tag version (unsubscribe/address footer):
     python3 src/main.py --config data/examples/theatre_config.yaml --show data/examples/show_info.json --action generate --compliance mailchimp

     # Generate both with one data fetch:
     python3 src/main.py --config data/examples/theatre_config.yaml --show data/examples/show_info.json --action generate --compliance both
     ```
   - Outputs `email.html` and `email.txt`.

---

## Setup for Developers (Initial Configuration)

This tool is designed to be reusable by any theatre. All theatre-specific information and API keys must be configured once.

### 1. Prerequisites

You must have **Python 3.10+** and access to the **Google Maps Platform** and **WeatherAPI.com** to enable dynamic features.

    * **Google Places API Key:** Required for Dining/Business lookups.
    * **Weather API Key:** Required for accurate weather forecasting.

### 2. Installation (Standard Python Setup)

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/samosaPerson/preshow_mailer.git
    cd preshow_mailer
    ```
2.  **Create & Activate Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    # (or) pip install -e .
    ```
4.  **Environment Setup (create .env from template):**
    ```bash
    cp .env.example .env
    # Edit .env and paste your API keys
    ```

### 3. API Keys and Configuration

1.  **Environment Variables:** Create a file named **.env** in the project root to store your private API keys. **Do not commit this file to Git.**
    ```dotenv
    # .env
    GOOGLE_PLACES_API_KEY="PASTE_YOUR_KEY_HERE"   # Required for dining/nearby lookups
    WEATHER_API_KEY="PASTE_YOUR_KEY_HERE"         # Required for hyper-local forecast
    # Mailchimp (only if using Send/Schedule buttons in the dashboard)
    MAILCHIMP_API_KEY="PASTE_YOUR_KEY_HERE"
    MAILCHIMP_SERVER_PREFIX="usX"                 # e.g., us1, us16
    MAILCHIMP_LIST_ID="PASTE_YOUR_LIST_ID"
    ```
2.  **Theatre Configuration:** Edit `data/examples/theatre_config.yaml` with address, colors, latitude/longitude, radii, concessions, sponsor info, and lists.
3.  **Lists:** Customize `lists.whitelist` and `lists.blacklist` (comma-separated in the dashboard UI or YAML) to prioritize sponsors and exclude unwanted businesses.

---

## Features

| Element | Data Source | Purpose |
| :--- | :--- | :--- |
| **Logistics Summary** | show_info.json | Displays Start Time, Doors Open (calculated), End Time (with Run Time). |
| **Hyper-Local Weather** | WeatherAPI.com | Checks specific conditions for **Arrival** and **Departure** times. Displays large, accessible icons and temperatures. |
| **Dining & Drinks** | Google Places API | Filters nearby businesses open during the Pre-Show [T-60 to T-15 mins] and Post-Show [T+5 to T+40 mins] windows. |
| **Promotions** | theatre_config.yaml | Whitelisted sponsors are shown at the top of the list, regardless of proximity. |
| **Dashboard UI** | dash / dbc | Live preview, export, send/schedule via Mailchimp (requires Mailchimp keys); theme toggles; mobile/desktop preview; upload config/show files. |
| **Accessibility** | theatre_config.yaml | Prominently features accessibility details and Box Office contact information. |

---

## Open Source & Contribution

This project is licensed under the **MIT License** and is open to contributions. Please submit pull requests for bug fixes, feature additions, or alternative configurations (e.g., metric units support).

* **Author:** samosaPerson
* **Version:** 0.1.0 (Initial Release)
