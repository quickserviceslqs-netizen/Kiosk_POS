# Kiosk POS - User Manual
**Version 1.001**

---

## Table of Contents
1. [Getting Started](#getting-started)
2. [First-Time Setup](#first-time-setup)
3. [Login](#login)
4. [Point of Sale (POS)](#point-of-sale-pos)
5. [Inventory Management](#inventory-management)
6. [Reports](#reports)
7. [Expenses](#expenses)
8. [User Management](#user-management)
9. [Settings](#settings)
10. [Backup & Restore](#backup--restore)
11. [Troubleshooting](#troubleshooting)

---

## Getting Started

### System Requirements
- Windows 10 or later
- 4GB RAM minimum
- 100MB free disk space
- Screen resolution: 1024x768 or higher

### Installation
1. Run `KioskPOS_Installer_v1.001.exe`
2. Follow the installation wizard
3. Choose installation location (default: Program Files)
4. Optionally create a desktop shortcut
5. Click **Install** and wait for completion
6. Launch the application

---

## First-Time Setup

When you launch Kiosk POS for the first time, you'll be prompted to create an administrator account.

### Creating Your Admin Account
1. **Username**: Enter a username (minimum 3 characters)
2. **Password**: Enter a secure password (minimum 6 characters)
3. **Confirm Password**: Re-enter your password
4. Click **Create Account**

> ⚠️ **Important**: Remember your admin credentials! You'll need them to access the system and manage users.

---

## Login

1. Enter your **Username**
2. Enter your **Password**
3. Click **Login**

### User Roles
- **Admin**: Full access to all features including user management, settings, and reports
- **Cashier**: Access to POS, basic inventory view, and limited reports

---

## Point of Sale (POS)

The POS screen is your main workspace for processing sales.

### Making a Sale

#### Adding Items to Cart
1. **Search**: Type item name in the search box
2. **Categories**: Click category buttons to filter items
3. **Click Item**: Click on an item tile to add it to cart

#### Item Quantities
- **Regular Items**: Click to add 1 unit, or use the quantity selector
- **Fractional Items** (liquids, bulk goods): Enter specific amounts (e.g., 500ml, 1.5kg)

#### Preset Portions
For items with preset portions (e.g., drinks):
1. Click the item
2. Select from available portions (e.g., Shot, Double, Bottle)
3. The correct price is automatically applied

### Cart Operations
| Action | How To |
|--------|--------|
| Increase quantity | Click **+** button |
| Decrease quantity | Click **-** button |
| Remove item | Click **🗑️** (trash) button |
| Clear cart | Click **Clear Cart** |

### Checkout Process
1. Review items in cart
2. Verify the **Total** amount
3. Click **Checkout**
4. Select payment method:
   - **Cash**: Enter amount received, system calculates change
   - **Card**: Confirm card payment
   - **Mobile Money**: Confirm mobile payment
5. Receipt is generated automatically

### Refunds
1. Go to **Sales History** or **Reports**
2. Find the transaction
3. Click **Refund**
4. Select items to refund
5. Confirm refund

---

## Inventory Management

### Viewing Inventory
- Navigate to **Inventory** from the main menu
- View all items with stock levels, prices, and categories

### Adding New Items

1. Click **Add Item**
2. Fill in the details:

| Field | Description |
|-------|-------------|
| **Name** | Item name (required) |
| **Category** | Select or create category |
| **Barcode** | Optional barcode/SKU |
| **Cost Price** | Your purchase cost |
| **Selling Price** | Customer price |
| **Stock Quantity** | Current inventory count |
| **Unit** | pieces, kg, L, m, etc. |
| **VAT Rate** | Select applicable VAT |
| **Low Stock Alert** | Threshold for notifications |

3. Click **Save**

### Special Volume Items (Liquids/Bulk)
For items sold in fractional quantities:

1. Check **"Sell by volume/weight"**
2. Set the **Unit** (L, kg, m)
3. Enter **Total Volume/Weight** in stock
4. Set **Price per unit** (e.g., price per liter)

The system automatically:
- Converts units (L↔ml, kg↔g, m↔cm)
- Tracks fractional sales
- Updates remaining stock

### Preset Portions
For items with standard serving sizes:

1. Open item for editing
2. Go to **Portions** tab
3. Click **Add Portion**
4. Enter:
   - Portion name (e.g., "Shot", "Glass", "Bottle")
   - Amount (e.g., 50ml)
   - Selling price
5. Save portions

### Editing Items
1. Click on item row
2. Click **Edit** or double-click
3. Modify fields
4. Click **Save**

### Deleting Items
1. Select item
2. Click **Delete**
3. Confirm deletion

> ⚠️ Deleting items removes them from inventory but preserves sales history.

### Import/Export
- **Export**: Download inventory as CSV
- **Import**: Upload CSV file (use template in `assets/inventory_import_template.csv`)

---

## Reports

Access comprehensive business analytics from the **Reports** menu.

### Available Reports

#### Sales Reports
- **Today's Sales**: Current day transactions
- **This Week**: Monday to today
- **This Month**: 1st of month to today
- **Custom Range**: Select specific dates

#### Report Types
| Report | Description |
|--------|-------------|
| **Sales Summary** | Total revenue, transactions, average sale |
| **Category Sales** | Sales breakdown by product category |
| **Item Sales** | Best/worst selling items |
| **Hourly Sales** | Peak hours analysis |
| **Payment Methods** | Cash vs Card vs Mobile breakdown |
| **Profit Report** | Revenue minus costs |

### Filtering Reports
1. Select **Date Range** (Today, This Week, This Month, Custom)
2. Choose **Category** filter (optional)
3. Click **Generate Report**

### Exporting Reports
- Click **Export** to download as CSV
- Reports can be opened in Excel

---

## Expenses

Track business expenses separate from inventory costs.

### Adding Expenses
1. Go to **Expenses**
2. Click **Add Expense**
3. Enter:
   - **Description**: What the expense is for
   - **Amount**: Cost
   - **Category**: Rent, Utilities, Supplies, etc.
   - **Date**: When incurred
4. Click **Save**

### Viewing Expenses
- Filter by date range
- Filter by category
- View totals and breakdowns

---

## User Management

*Admin access required*

### Adding Users
1. Go to **Settings** → **Users**
2. Click **Add User**
3. Enter:
   - Username
   - Password
   - Role (Admin/Cashier)
4. Click **Save**

### Editing Users
1. Select user
2. Click **Edit**
3. Modify details
4. Click **Save**

### Deleting Users
1. Select user
2. Click **Delete**
3. Confirm deletion

> ⚠️ You cannot delete your own account or the last admin account.

---

## Settings

### General Settings
- **Business Name**: Your store name (appears on receipts)
- **Currency**: Select your currency
- **Receipt Footer**: Custom message on receipts

### VAT Settings
1. Go to **Settings** → **VAT Rates**
2. Add/edit VAT rates:
   - Name (e.g., "Standard", "Reduced", "Zero")
   - Percentage (e.g., 15%)
3. Assign VAT rates to items

### Email Settings
Configure email for:
- Daily sales reports
- Low stock alerts
- Backup notifications

1. Go to **Settings** → **Email**
2. Enter SMTP settings:
   - Server, Port
   - Username, Password
   - Recipient email
3. Test connection
4. Save

---

## Backup & Restore

### Creating Backups
1. Go to **Settings** → **Backup**
2. Click **Create Backup**
3. Backup saved to `backups/` folder

### Automatic Backups
- Backups created automatically on app close
- Stored with timestamp

### Restoring from Backup
1. Go to **Settings** → **Backup**
2. Click **Restore**
3. Select backup file
4. Confirm restoration

> ⚠️ Restoring replaces ALL current data with backup data.

### Backup Location
Default: `C:\Users\[Username]\AppData\Local\KioskPOS\backups\`

---

## Troubleshooting

### Common Issues

#### App Won't Start
1. Check if another instance is running
2. Restart your computer
3. Reinstall the application

#### Login Failed
1. Verify username and password
2. Check Caps Lock
3. Contact admin for password reset

#### Items Not Showing
1. Check category filter
2. Use search to find item
3. Verify item is active (not deleted)

#### Incorrect Stock Levels
1. Check recent sales history
2. Verify no pending transactions
3. Manually adjust stock if needed

#### Printer Not Working
1. Check printer connection
2. Verify printer is set as default
3. Test print from Windows

### Data Location
- **Database**: `database/pos.db`
- **Backups**: `backups/`
- **Images**: `assets/item_images/`

### Getting Help
- Check `DASHBOARD_AND_EMAIL_GUIDE.md` for email setup
- Review `Kiosk_POS_Quick_Start.txt` for quick tips

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `F1` | Help |
| `F5` | Refresh |
| `Ctrl+N` | New Sale |
| `Ctrl+P` | Print Receipt |
| `Esc` | Cancel/Close Dialog |

---

## Glossary

| Term | Definition |
|------|------------|
| **SKU** | Stock Keeping Unit - unique item identifier |
| **VAT** | Value Added Tax |
| **POS** | Point of Sale |
| **Preset Portion** | Pre-defined serving size with fixed price |
| **Fractional Sale** | Selling partial units (ml, grams, cm) |

---

**© 2026 Kiosk POS** | Version 1.001
