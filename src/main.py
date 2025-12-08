# src/main.py

import argparse
import yaml
import json
from dotenv import load_dotenv # <-- NEW IMPORT
from urllib.parse import quote
import os
import sys
# Load environment variables from the .env file
load_dotenv() # <-- NEW: This must run first!
from src.generator import generate_email
from src.sender import create_draft_campaign
from src.sender import create_draft_campaign, send_campaign_now, schedule_campaign # <--- Update imports

def main():
    parser = argparse.ArgumentParser(description="Generate and upload pre-show emails.")
    
    # ... (Keep your existing arguments for --config and --show) ...
    parser.add_argument('--config', default='data/examples/theatre_config.yaml', help='Theatre config file')
    parser.add_argument('--show', default='data/examples/show_info.json', help='Show info file')
    parser.add_argument('--action', choices=['generate', 'upload'], default='generate',
        help='Choose "generate" to make local files, or "upload" to send to Mailchimp.')
    # NEW ARGUMENT: Mode for uploading
    parser.add_argument('--mode', choices=['draft', 'send', 'schedule'], default='draft',
                        help='If uploading: "draft" (default), "send" (immediate), or "schedule".')
    
    # NEW ARGUMENT: Schedule Time
    parser.add_argument('--time', help='UTC Schedule time (e.g. 2025-11-25T14:00:00+00:00). Required if mode=schedule.')
    args = parser.parse_args()

    # Load Theatre Configuration
    with open(args.config, 'r') as f:
        try:
            theatre_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"Error loading config file: {e}")
            return
    
    # Load Show Information (assuming JSON for now, could handle YAML too)
    with open(args.show, 'r') as f:
        try:
            show_info = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error loading show file: {e}")
            return

    # Pass the data to the core generation function
    html_body, text_body = generate_email(theatre_config, show_info)

    if args.action == 'generate':
        # Save locally (Existing Logic)
        with open('email.html', 'w', encoding='utf-8') as f: f.write(html_body)
        with open('email.txt', 'w', encoding='utf-8') as f: f.write(text_body)
        print("✅ Local files generated: email.html, email.txt")

    elif args.action == 'upload':
        print("🚀 Connectig to Mailchimp...")
        
        # 1. ALWAYS Create the Draft first (This uploads the HTML)
        subject = f"Upcoming Performance: {show_info['show_title']}"
        from_name = theatre_config['theatre']['name']
        reply_to = theatre_config['details']['contact_email']

        # We need the create_draft_campaign to return the CAMPAIGN ID now, not just the link.
        # Note: You might need to slightly adjust create_draft_campaign to return (link, id)
        # Let's assume you updated src/sender.py to return the ID as well.
        # For this example, let's say create_draft_campaign returns a dictionary or tuple.
        
        # *QUICK FIX in src/sender.py*: Change the return to: return {"link": dashboard_link, "id": campaign_id}
        result = create_draft_campaign(html_body, subject, from_name, reply_to)
        
        if not result:
            return

        campaign_id = result['id'] # Access the ID
        print(f"📝 Draft created. ID: {campaign_id}")

        # 2. Handle Modes
        if args.mode == 'draft':
            print(f"👉 Review here: {result['link']}")

        elif args.mode == 'send':
            # --- NEW: Review Link Logic ---
            abs_path = os.path.abspath("email.html")
            # Create a clickable file URI (Command + Click in macOS terminal)
            file_link = f"file://{quote(abs_path)}"
            
            print("\n" + "="*60)
            print(f"⚠️  DANGER ZONE: SENDING TO LIVE LIST")
            print(f"   Review the file locally first: {file_link}")
            print("="*60 + "\n")
            
            confirm = input(f"Type 'YES' to verify you have reviewed the file and want to SEND: ")
            
            if confirm == 'YES':
                send_campaign_now(campaign_id)
            else:
                print("🚫 Send cancelled. Campaign saved as draft.")

        elif args.mode == 'schedule':
            if not args.time:
                print("❌ Error: --time is required for scheduling.")
                return
            schedule_campaign(campaign_id, args.time)


if __name__ == '__main__':
    # Make sure to run this file via the command line for the arguments to work:
    # python src/main.py --config data/examples/theatre_config.yaml --show data/examples/show_info.json
    main()