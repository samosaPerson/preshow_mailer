import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
import yaml

from src.generator import build_context, render_email_from_context
from src.sender import create_draft_campaign, send_campaign_now, schedule_campaign


load_dotenv()


def build_export_filename(show_title, start_time, provided=None):
    title = (show_title or "email").strip() or "email"
    safe_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in title)
    time_part = ""
    if start_time:
        time_part = "".join(c if c.isalnum() or c in ("-", "_", "T") else "-" for c in start_time)
    base = provided.strip() if provided else f"{safe_title}_{time_part}" if time_part else safe_title
    return base if base.lower().endswith(".html") else f"{base}.html"


def generate_variants(theatre_config, show_info):
    """Fetch data once and render both standard and mailchimp HTML."""
    ctx = build_context(theatre_config, show_info)
    html_mailchimp, text_body = render_email_from_context(ctx, include_mailchimp_footer=True)
    html_standard, _ = render_email_from_context(ctx, include_mailchimp_footer=False)
    return {
        "mailchimp": html_mailchimp,
        "standard": html_standard,
        "text": text_body
    }


def main():
    parser = argparse.ArgumentParser(description="Generate or upload pre-show emails (CLI).")
    parser.add_argument("--config", default="data/examples/theatre_config.yaml", help="Theatre config file")
    parser.add_argument("--show", default="data/examples/show_info.json", help="Show info file")
    parser.add_argument("--action", choices=["generate", "upload"], default="generate",
                        help='Generate local HTML/TXT or upload to Mailchimp (requires keys).')
    parser.add_argument("--mode", choices=["draft", "send", "schedule"], default="draft",
                        help='Mailchimp mode when using --action upload.')
    parser.add_argument("--schedule-time", help="UTC schedule time (e.g., 2025-11-25T14:00:00+00:00) when --mode schedule.")
    parser.add_argument("--output", help="Filename for HTML output. Default uses show title/start time.")
    parser.add_argument("--compliance", choices=["standard", "mailchimp", "both"], default="standard",
                        help="Include Mailchimp compliance footer (unsubscribe/address).")
    args = parser.parse_args()

    # Load config and show data
    with open(args.config, "r") as f:
        theatre_config = yaml.safe_load(f)
    with open(args.show, "r") as f:
        show_info = json.load(f)

    variants = generate_variants(theatre_config, show_info)

    if args.action == "generate":
        if args.compliance in ("standard", "both"):
            name = build_export_filename(show_info.get("show_title"), show_info.get("start_time"), args.output)
            Path(name).write_text(variants["standard"], encoding="utf-8")
            Path("email.txt").write_text(variants["text"], encoding="utf-8")
            print(f"✅ Generated standard HTML: {name}")
        if args.compliance in ("mailchimp", "both"):
            name_mc = build_export_filename(show_info.get("show_title"), show_info.get("start_time"),
                                            args.output or "email_mailchimp.html")
            Path(name_mc).write_text(variants["mailchimp"], encoding="utf-8")
            print(f"✅ Generated Mailchimp HTML: {name_mc}")
        return

    # Upload path (Mailchimp)
    print("🚀 Connecting to Mailchimp...")
    subject = f"Upcoming Performance: {show_info['show_title']}"
    from_name = theatre_config["theatre"]["name"]
    reply_to = theatre_config["details"]["contact_email"]
    html_body = variants["mailchimp"]  # Always send the compliance version to Mailchimp

    result = create_draft_campaign(html_body, subject, from_name, reply_to)
    if not result:
        print("❌ Draft creation failed.")
        return

    campaign_id = result["id"]
    print(f"📝 Draft created. ID: {campaign_id}")
    print(f"👉 Review draft in Mailchimp: {result.get('link', '(link unavailable)')}")

    if args.mode == "draft":
        return
    if args.mode == "send":
        # Safety prompt
        abs_path = os.path.abspath("email.html")
        file_link = f"file://{quote(abs_path)}"
        print("\n" + "=" * 60)
        print("⚠️  SENDING TO LIVE LIST")
        print(f"   Review locally before sending: {file_link}")
        print("=" * 60 + "\n")
        confirm = input("Type 'YES' to send now: ")
        if confirm == "YES":
            send_campaign_now(campaign_id)
        else:
            print("🚫 Send cancelled. Campaign left as draft.")
        return

    if args.mode == "schedule":
        if not args.schedule_time:
            print("❌ Error: --schedule-time is required for scheduling.")
            return
        schedule_campaign(campaign_id, args.schedule_time)
        return


if __name__ == "__main__":
    main()
