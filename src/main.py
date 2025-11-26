# src/main.py

import argparse
import yaml
import json
from dotenv import load_dotenv # <-- NEW IMPORT

# Load environment variables from the .env file
load_dotenv() # <-- NEW: This must run first!
from src.generator import generate_email

def main():
    parser = argparse.ArgumentParser(
        description="Generate a pre-show logistics email for theatre patrons."
    )
    parser.add_argument(
        '--config', 
        required=True, 
        help='Path to the theatre-specific YAML configuration file.'
    )
    parser.add_argument(
        '--show', 
        required=True, 
        help='Path to the per-performance JSON/YAML file.'
    )

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

    # Output files
    with open('email.html', 'w', encoding='utf-8') as f:
        f.write(html_body)
    print("✅ Successfully generated email.html")
    
    with open('email.txt', 'w', encoding='utf-8') as f:
        f.write(text_body)
    print("✅ Successfully generated email.txt")


if __name__ == '__main__':
    # Make sure to run this file via the command line for the arguments to work:
    # python src/main.py --config data/examples/theatre_config.yaml --show data/examples/show_info.json
    main()