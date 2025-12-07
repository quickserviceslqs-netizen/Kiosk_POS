"""Email notifications for reports and alerts."""
from __future__ import annotations

import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Optional

from modules import dashboard, reports


CONFIG_FILE = Path(__file__).parent.parent / "email_config.json"


def get_email_config() -> dict:
    """Load email configuration."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "enabled": False,
        "smtp_server": "",
        "smtp_port": 587,
        "smtp_username": "",
        "smtp_password": "",
        "from_email": "",
        "to_emails": [],
        "daily_report_enabled": False,
        "low_stock_alerts_enabled": True,
        "low_stock_threshold": 10
    }


def save_email_config(config: dict) -> None:
    """Save email configuration."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def send_email(subject: str, body: str, to_emails: list[str], config: dict) -> bool:
    """
    Send an email using configured SMTP settings.
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not config.get("enabled"):
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = config['from_email']
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
        server.starttls()
        server.login(config['smtp_username'], config['smtp_password'])
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def generate_daily_report_email() -> str:
    """Generate daily sales report email body."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    summary = dashboard.get_today_summary()
    top_products = dashboard.get_top_products(5)
    category_breakdown = dashboard.get_category_breakdown()
    
    body = f"""
DAILY SALES REPORT - {today}
{'='*60}

SUMMARY:
--------
Total Revenue:      KSH {summary['revenue']:.2f}
Transactions:       {summary['transactions']}
Items Sold:         {summary['items_sold']}
Average Sale:       KSH {summary['avg_sale']:.2f}

TOP SELLING PRODUCTS:
---------------------
"""
    
    for i, product in enumerate(top_products, 1):
        body += f"{i}. {product['name']}: {product['quantity_sold']} units, KSH {product['revenue']:.2f}\n"
    
    if category_breakdown:
        body += "\nSALES BY CATEGORY:\n------------------\n"
        for cat in category_breakdown:
            body += f"{cat['category']}: {cat['quantity']} items, KSH {cat['revenue']:.2f}\n"
    
    body += f"\n\nReport generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    body += "This is an automated email from your Kiosk POS system.\n"
    
    return body


def generate_low_stock_alert_email(threshold: int = 10) -> Optional[str]:
    """Generate low stock alert email body with items that have alerts."""
    low_stock = dashboard.get_low_stock_items(threshold)
    
    if not low_stock:
        return None
    
    body = """
LOW STOCK ALERT
===============================================================

The following items are running low on stock and need attention:

"""
    
    critical_items = []
    warning_items = []
    
    for item in low_stock:
        item_threshold = item.get("threshold", threshold)
        quantity = item["quantity"]
        
        if quantity <= item_threshold / 2:
            critical_items.append(item)
        else:
            warning_items.append(item)
    
    # Critical items
    if critical_items:
        body += "🔴 CRITICAL (Quantity ≤ 50% of threshold):\n"
        body += "-" * 50 + "\n"
        for item in critical_items:
            item_threshold = item.get("threshold", threshold)
            body += f"  • {item['name']}\n"
            body += f"    Current: {item['quantity']} units | Threshold: {item_threshold} units\n"
        body += "\n"
    
    # Warning items
    if warning_items:
        body += "🟡 LOW (Quantity ≤ Threshold):\n"
        body += "-" * 50 + "\n"
        for item in warning_items:
            item_threshold = item.get("threshold", threshold)
            body += f"  • {item['name']}\n"
            body += f"    Current: {item['quantity']} units | Threshold: {item_threshold} units\n"
        body += "\n"
    
    body += f"""
ACTION REQUIRED: Please restock these items as soon as possible.

Alert generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
This is an automated email from your Kiosk POS system.
"""
    
    return body


def send_daily_report() -> bool:
    """Send daily sales report email."""
    config = get_email_config()
    
    if not config.get("enabled") or not config.get("daily_report_enabled"):
        return False
    
    if not config.get("to_emails"):
        return False
    
    subject = f"Daily Sales Report - {datetime.now().strftime('%Y-%m-%d')}"
    body = generate_daily_report_email()
    
    return send_email(subject, body, config['to_emails'], config)


def send_low_stock_alert() -> bool:
    """Send low stock alert email."""
    config = get_email_config()
    
    if not config.get("enabled") or not config.get("low_stock_alerts_enabled"):
        return False
    
    if not config.get("to_emails"):
        return False
    
    threshold = config.get("low_stock_threshold", 10)
    body = generate_low_stock_alert_email(threshold)
    
    if body is None:
        return False  # No low stock items
    
    subject = "⚠ Low Stock Alert - Action Required"
    
    return send_email(subject, body, config['to_emails'], config)


def test_email_configuration(config: dict) -> tuple[bool, str]:
    """
    Test email configuration by sending a test email.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    if not config.get("to_emails"):
        return False, "No recipient email addresses configured"
    
    subject = "Test Email from Kiosk POS"
    body = f"""
This is a test email from your Kiosk POS system.

If you're receiving this, your email configuration is working correctly!

Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    try:
        success = send_email(subject, body, config['to_emails'], config)
        if success:
            return True, "Test email sent successfully!"
        else:
            return False, "Failed to send test email. Check your configuration."
    except Exception as e:
        return False, f"Error: {str(e)}"
