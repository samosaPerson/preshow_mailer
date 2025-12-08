# Pre-Show Mailer: Theatre Audience Experience Tool

An open-source Python tool designed to improve the patron experience at community theatres by automatically generating polished, accurate, pre-show logistical emails.

## Project Value Proposition

The **Pre-Show Mailer** solves the common problem of audience members missing key logistical details (parking, weather, start time). By integrating real-time API data (Weather, Nearby Dining) and automating the generation of perfectly formatted, accessible HTML email content, the tool ensures every patron arrives informed and ready for the show.

* **Target Audience:** Community Theatre staff, especially those utilizing ticketing systems (like Salesforce-based platforms) that handle email sending but lack dynamic content generation.
* **Safety:** This tool **generates content only** (email.html and email.txt). It **does not** touch mailing lists or send emails (that remains the responsibility of your theatre's existing ticketing system).

---

## Quickstart: Generating an Email

Theatre staff can generate a complete email body in just three steps, assuming the system is set up.

1.  **Place Show Data:** Place your show-specific details (show_info.json) into the designated input folder.
2.  **Run the Generator:** Open your terminal and run the executable program:
    ```bash
    ./preshow-mailer
    ```
    (Note: The exact command may vary if the tool is not packaged as a single executable.)
3.  **Paste and Send:** Two files are generated (email.html and email.txt). Copy the HTML content and paste it directly into your ticketing system's email composer.

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
    git clone [https://github.com/your-username/preshow_mailer.git](https://github.com/your-username/preshow_mailer.git)
    cd preshow_mailer
    ```
2.  **Create & Activate Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -e .
    ```

### 3. API Keys and Configuration

1.  **Environment Variables:** Create a file named **.env** in the project root to store your private API keys. **Do not commit this file to Git.**
    ```dotenv
    # .env
    GOOGLE_PLACES_API_KEY="PASTE_YOUR_KEY_HERE"
    WEATHER_API_KEY="PASTE_YOUR_KEY_HERE"
    ```
2.  **Theatre Configuration:** Edit the file data/examples/theatre_config.yaml with your theatre's address, colors, latitude/longitude, and default radii.
3.  **Lists:** Customize the lists:whitelist and lists:blacklist sections in the YAML to prioritize sponsors and exclude unwanted businesses.

---

## Features

| Element | Data Source | Purpose |
| :--- | :--- | :--- |
| **Logistics Summary** | show_info.json | Displays Start Time, Doors Open (calculated), End Time (with Run Time). |
| **Hyper-Local Weather** | WeatherAPI.com | Checks specific conditions for **Arrival** and **Departure** times. Displays large, accessible icons and temperatures. |
| **Dining & Drinks** | Google Places API | Filters nearby businesses open during the Pre-Show [T-60 to T-15 mins] and Post-Show [T+5 to T+40 mins] windows. |
| **Promotions** | theatre_config.yaml | Whitelisted sponsors are shown at the top of the list, regardless of proximity. |
| **Accessibility** | theatre_config.yaml | Prominently features accessibility details and Box Office contact information. |

---

## Open Source & Contribution

This project is licensed under the **MIT License** and is open to contributions. Please submit pull requests for bug fixes, feature additions, or alternative configurations (e.g., metric units support).

* **Author:** samosaPerson
* **Version:** 0.1.0 (Initial Release)