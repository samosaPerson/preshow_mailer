# src/sender.py
import os

import mailchimp_marketing as MailchimpMarketing
from dotenv import load_dotenv
from mailchimp_marketing.api_client import ApiClientError


load_dotenv()


def _get_client():
    api_key = os.environ.get("MAILCHIMP_API_KEY")
    server = os.environ.get("MAILCHIMP_SERVER_PREFIX")
    if not api_key or not server:
        raise ValueError("Missing Mailchimp credentials (MAILCHIMP_API_KEY/MAILCHIMP_SERVER_PREFIX)")

    client = MailchimpMarketing.Client()
    client.set_config({"api_key": api_key, "server": server})
    return client, server


def send_campaign_now(campaign_id):
    """
    Triggers the immediate sending of a campaign.
    """
    try:
        client, _ = _get_client()
        client.campaigns.send(campaign_id)
        print(f"✅ SUCCESS: Campaign {campaign_id} has been sent!")
        return True
    except (ApiClientError, ValueError) as error:
        print(f"❌ Failed to send: {getattr(error, 'text', error)}")
        return False


def schedule_campaign(campaign_id, schedule_time_utc):
    """
    Schedules the campaign.
    schedule_time_utc: String in format "YYYY-MM-DDTHH:MM:SS+00:00" (Must be UTC)
    """
    try:
        client, _ = _get_client()
        client.campaigns.schedule(campaign_id, {"schedule_time": schedule_time_utc})
        print(f"✅ SUCCESS: Campaign {campaign_id} scheduled for {schedule_time_utc}")
        return True
    except (ApiClientError, ValueError) as error:
        print(f"❌ Failed to schedule: {getattr(error, 'text', error)}")
        return False

def create_draft_campaign(html_content, subject_line, from_name, reply_to):
    """
    Creates a new Draft Campaign in Mailchimp with the generated HTML.
    Returns the web link to preview/send the campaign.
    """
    try:
        client, server = _get_client()
    except ValueError as exc:
        print(f"❌ Error: {exc}")
        return None

    list_id = os.environ.get("MAILCHIMP_LIST_ID")
    if not list_id:
        print("❌ Error: Missing MAILCHIMP_LIST_ID in .env")
        return None

    # 3. Verify Connection (Optional but good for debugging)
    try:
        client.ping.get()
    except ApiClientError:
        print("❌ Error: Could not connect to Mailchimp. Check API Key/Server Prefix.")
        return None

    # 4. Create the Campaign
    try:
        # Step A: Define Campaign Settings
        campaign_data = {
            "type": "regular",
            "recipients": {
                "list_id": list_id
            },
            "settings": {
                "subject_line": subject_line,
                "title": f"Pre-Show: {subject_line}", # Internal name
                "from_name": from_name,
                "reply_to": reply_to,
                # Auto-footer handles the required legal links
                "auto_footer": False, 
                "inline_css": True # Helps with email styling
            }
        }
        
        campaign = client.campaigns.create(campaign_data)
        campaign_id = campaign['id']
        web_id = campaign['web_id'] # Used for the dashboard link
        
        print(f"✅ Draft Campaign Created! (ID: {campaign_id})")

        # Step B: Upload HTML Content
        client.campaigns.set_content(campaign_id, {"html": html_content})
        print("✅ HTML Content Uploaded.")
        
        # Return the direct link to open this specific campaign in the browser
        # Format: https://{server}.admin.mailchimp.com/campaigns/edit?id={web_id}
        dashboard_link = f"https://{server}.admin.mailchimp.com/campaigns/edit?id={web_id}"
        return {"link": dashboard_link, "id": campaign_id}

    except ApiClientError as error:
        print(f"❌ Mailchimp API Error: {error.text}")
        return None


def unschedule_campaign(campaign_id):
    """Reverts a scheduled campaign back to draft."""
    try:
        client, _ = _get_client()
        client.campaigns.unschedule(campaign_id)
        print(f"✅ Campaign {campaign_id} unscheduled.")
        return True
    except (ApiClientError, ValueError) as error:
        print(f"❌ Failed to unschedule: {getattr(error, 'text', error)}")
        return False


def get_campaigns(status="scheduled", since_date=None, until_date=None):
    """
    Returns simplified campaign data for the given status.
    status: 'scheduled' or 'sent'
    since_date/until_date: YYYY-MM-DD strings used for sent history filtering.
    """
    try:
        client, server = _get_client()
    except ValueError as exc:
        print(f"❌ Error: {exc}")
        return []

    params = {"status": status, "count": 100}
    if status == "sent" and since_date:
        # Mailchimp expects an ISO timestamp; use midnight of the start date
        params["since_send_time"] = f"{since_date}T00:00:00+00:00"
    if status == "sent" and until_date:
        params["before_send_time"] = f"{until_date}T23:59:59+00:00"

    try:
        response = client.campaigns.list(**params)
    except ApiClientError as error:
        print(f"❌ Failed to list campaigns: {error.text}")
        return []

    results = []
    for campaign in response.get("campaigns", []):
        results.append({
            "id": campaign.get("id"),
            "web_id": campaign.get("web_id"),
            "web_link": f"https://{server}.admin.mailchimp.com/campaigns/edit?id={campaign.get('web_id')}"
            if campaign.get("web_id") else None,
            "subject": campaign.get("settings", {}).get("subject_line"),
            "status": campaign.get("status"),
            "send_time": campaign.get("send_time") or campaign.get("schedule_time"),
            "emails_sent": campaign.get("emails_sent")
        })
    return results


def get_campaign_content(campaign_id):
    """Fetches the stored HTML for a given campaign."""
    try:
        client, _ = _get_client()
        content = client.campaigns.get_content(campaign_id)
        return content.get("html") or content.get("plain_text")
    except (ApiClientError, ValueError) as error:
        print(f"❌ Failed to fetch campaign content: {getattr(error, 'text', error)}")
        return None
