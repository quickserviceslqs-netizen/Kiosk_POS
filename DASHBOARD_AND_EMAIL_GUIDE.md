# Dashboard & Email Notifications Guide

## 🎯 What's New

### 1. **Dashboard (Default Home Screen)**
The dashboard is now your home screen after login, providing real-time business insights:

#### Summary Cards
- **Today**: Revenue and transaction count for current day
- **This Week**: 7-day rolling revenue and transactions
- **This Month**: Month-to-date performance

#### Visual Charts
- **7-Day Sales Trend**: Bar chart showing daily revenue for the last week
- Green bars for sales days, gray for no-sales days
- Hover-friendly with date labels and revenue amounts

#### Data Tables
- **Top 5 Products**: Best sellers for today with quantity and revenue
- **Low Stock Alerts**: Items below threshold (red highlight for ≤5 units)
- **Recent Transactions**: Last 10 sales with date, total, and payment method

#### Controls
- **🔄 Refresh**: Updates all dashboard data (auto-refresh on load)

---

## 📧 Email Notification System

### Accessing Email Settings
1. Login as **admin**
2. Click **⚙ Settings** button in navigation bar
3. Select **📧 Email Notifications**

### Configuration Steps

#### 1. SMTP Server Setup
Configure your email provider's SMTP settings:

**For Gmail:**
```
SMTP Server: smtp.gmail.com
SMTP Port: 587
Username: your-email@gmail.com
Password: [App Password - not your regular password]
```

**To get Gmail App Password:**
1. Go to Google Account → Security
2. Enable 2-Step Verification
3. Go to "App passwords"
4. Generate new app password for "Mail"
5. Use this 16-character password in settings

**For Outlook/Office365:**
```
SMTP Server: smtp.office365.com
SMTP Port: 587
Username: your-email@outlook.com
Password: your-password
```

#### 2. Email Addresses
- **From Email**: The sender address (must match SMTP username)
- **To Emails**: Comma-separated list of recipients
  - Example: `manager@company.com, owner@company.com`

#### 3. Notification Preferences

**Daily Report:**
- Toggle: Enable/disable automated daily sales reports
- Contains: Summary stats, top products, category breakdown
- Format: Text email with formatted tables

**Low Stock Alerts:**
- Toggle: Enable/disable stock alerts
- Threshold: Set minimum stock level (1-50 units)
- Status indicators:
  - 🔴 CRITICAL: ≤ threshold/2 units
  - 🟡 LOW: ≤ threshold units

### Testing Email Setup

1. **Test SMTP Connection:**
   - Click **📧 Send Test Email**
   - Check recipient inbox for test message
   - If fails, verify SMTP credentials and server settings

2. **Test Daily Report:**
   - Click **📊 Send Daily Report Now**
   - Generates report for today's sales
   - Check inbox for formatted report

3. **Test Stock Alert:**
   - Click **⚠ Send Stock Alert Now**
   - Sends current low-stock items
   - Works even if threshold is 0 (shows all items below 10)

### Email Formats

#### Daily Report Email
```
Subject: Daily Sales Report - [Date]

DAILY SALES SUMMARY
-------------------
Date: [Date]
Total Revenue: $XXX.XX
Transactions: XX
Average Sale: $XX.XX
Items Sold: XXX

TOP PRODUCTS
------------
1. [Product Name]
   Quantity: XX | Revenue: $XXX.XX

2. [Product Name]
   Quantity: XX | Revenue: $XXX.XX
...

CATEGORY BREAKDOWN
------------------
[Category]: $XXX.XX
[Category]: $XXX.XX
```

#### Low Stock Alert Email
```
Subject: Low Stock Alert - [Date]

INVENTORY ALERT
---------------
The following items are running low:

🔴 CRITICAL (≤X units):
- [Item Name]: X units remaining
- [Item Name]: X units remaining

🟡 LOW (≤XX units):
- [Item Name]: XX units remaining
- [Item Name]: XX units remaining

Please restock these items promptly.
```

---

## 🔧 Troubleshooting

### Dashboard Issues

**Dashboard shows all zeros:**
- Make sure you have sales data in database
- Use main POS screen to create test sales
- Click 🔄 Refresh button

**Chart not displaying:**
- Ensure you have sales in the last 7 days
- Check database/pos.db exists and has sales table data
- Restart application

**Low stock table empty:**
- Add items with low quantity via Inventory
- Default threshold is 10 units
- Items with quantity ≤ 10 will appear

### Email Issues

**Test email fails:**
- **Invalid credentials**: Double-check username/password
- **Gmail**: Must use App Password, not regular password
- **Port blocked**: Try port 465 with SSL if 587 fails
- **Firewall**: Check if SMTP traffic is allowed

**Daily report empty:**
- Normal if no sales today
- Report only includes current day's data
- Use "Reports" module for historical data

**Stock alert shows nothing:**
- Check if any items are below threshold
- Threshold setting in email preferences
- Click inventory to verify stock levels

---

## 💡 Best Practices

### Dashboard
1. **Check dashboard daily** for quick overview
2. **Monitor low stock alerts** proactively
3. **Use 7-day trend** to spot patterns
4. **Compare Today vs Week** to gauge performance

### Email Notifications
1. **Set realistic thresholds**:
   - Fast-moving items: Higher threshold (20-30)
   - Slow-moving items: Lower threshold (5-10)
2. **Use multiple recipients** for redundancy
3. **Test configuration** before relying on auto-reports
4. **Schedule reviews**: Check emails match dashboard data

### Security
1. **Never share App Passwords** - regenerate if exposed
2. **Use dedicated email** for POS notifications
3. **Limit admin access** to email settings
4. **Keep SMTP credentials secure**

---

## 📊 Data Sources

All dashboard and email data comes from `database/pos.db`:
- **Sales**: `sales` table (date, total, payment_method, user_id)
- **Sale Items**: `sales_items` table (item_id, quantity, price, cost_price)
- **Inventory**: `items` table (name, category, quantity, selling_price, cost_price)

Data is calculated in real-time when dashboard loads or email sends.

---

## 🚀 Quick Start Checklist

### First Time Setup
- [x] Dashboard modules created
- [x] Email system integrated
- [ ] Login as admin
- [ ] Configure SMTP settings
- [ ] Send test email
- [ ] Verify dashboard displays
- [ ] Create test sale to see trend
- [ ] Set low stock threshold
- [ ] Send test stock alert

### Daily Use
1. Login → Dashboard loads automatically
2. Review summary cards
3. Check low stock alerts (red items)
4. Monitor sales trend chart
5. Click modules from navigation bar
6. Check email for automated reports

---

## 📁 File Structure

```
modules/
  dashboard.py       # Dashboard statistics functions
  notifications.py   # Email sending and formatting

ui/
  dashboard.py       # Dashboard UI with charts
  email_settings.py  # Email configuration interface

email_config.json    # SMTP and notification settings (auto-created)
```

---

## 🔄 Auto-Refresh

Dashboard refreshes automatically when:
- You navigate to home screen
- You click 🔄 Refresh button

To auto-refresh every X seconds, you can modify `ui/dashboard.py` to add:
```python
self.after(30000, self.load_data)  # Refresh every 30 seconds
```

---

## 🎨 Customization

### Change Dashboard Colors
Edit `ui/dashboard.py`:
- Revenue color: Line 89 (`foreground="#2E7D32"`)
- Chart bars: Line 189 (`fill="#4CAF50"`)
- Low stock critical: Line 253 (`tags=("critical",)`)

### Modify Email Templates
Edit `modules/notifications.py`:
- Daily report format: `generate_daily_report_email()`
- Stock alert format: `generate_low_stock_alert_email()`

### Adjust Threshold Defaults
Edit `ui/email_settings.py`:
- Line 51: `self.threshold_var.set(10)`  # Default threshold

---

## 📞 Support

Dashboard and email features are integrated with existing modules:
- **Reports** module: Historical data and detailed analytics
- **Inventory** module: Stock management and updates
- **POS** module: Transaction creation (feeds dashboard)
- **Backup** module: Protects dashboard data

For issues, check:
1. Database integrity: `database/pos.db`
2. Configuration files: `email_config.json`
3. Python console output for error messages
4. Email spam/junk folder for test emails
