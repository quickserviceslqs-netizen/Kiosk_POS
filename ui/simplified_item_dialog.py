"""Simplified Item Dialog for Kiosk POS - Improved UX"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Dict, Any
import logging
from modules import items
from utils import set_window_icon
from utils.validation import ValidationError, validate_numeric, validate_integer

logger = logging.getLogger(__name__)


class SimplifiedItemDialog:
    """Simplified item creation/editing dialog with wizard-style interface."""

    def __init__(self, parent: tk.Misc, existing: Optional[Dict[str, Any]] = None, is_admin: bool = True):
        self.parent = parent
        self.existing = existing
        self.is_admin = is_admin
        self.currency_symbol = "$"  # TODO: Get from config
        self.fields: Dict[str, Any] = {}
        self.dialog: Optional[tk.Toplevel] = None

    def show(self) -> None:
        """Show the item dialog."""
        self._create_dialog()
        self._build_ui()
        self._show_dialog()

    def _create_dialog(self) -> None:
        """Create the main dialog window."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.withdraw()
        title = "Create Item" if not self.existing else f"Edit Item - {self.existing.get('name', '')}"
        self.dialog.title(title)
        set_window_icon(self.dialog)
        self.dialog.transient(self.parent)
        self.dialog.geometry("700x600")
        self.dialog.resizable(True, True)

    def _build_ui(self) -> None:
        """Build the dialog UI with notebook tabs."""
        if not self.dialog:
            return

        # Create notebook for wizard-style interface
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Basic Information
        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="Basic Info")

        # Tab 2: Pricing
        pricing_frame = ttk.Frame(notebook)
        notebook.add(pricing_frame, text="Pricing")

        # Tab 3: Advanced Settings
        advanced_frame = ttk.Frame(notebook)
        notebook.add(advanced_frame, text="Advanced")

        # Initialize form fields
        self._init_form_fields()

        # Build each tab
        self._build_basic_info_tab(basic_frame)
        self._build_pricing_tab(pricing_frame)
        self._build_advanced_tab(advanced_frame)

        # Button frame at bottom
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        save_btn = ttk.Button(button_frame, text="Save Item", command=self._on_save)
        save_btn.pack(side=tk.RIGHT)

    def _init_form_fields(self) -> None:
        """Initialize form fields with defaults and existing values, and error labels."""
        self.fields = {}
        self.error_labels = {}

        # Basic fields
        self.fields["name"] = tk.StringVar(value=self.existing.get("name", "") if self.existing else "")
        self.fields["category"] = tk.StringVar(value=self.existing.get("category", "") if self.existing else "")
        self.fields["barcode"] = tk.StringVar(value=self.existing.get("barcode", "") if self.existing else "")
        self.fields["image_path"] = tk.StringVar(value=self.existing.get("image_path", "") if self.existing else "")

        # Pricing fields - simplified to single base price approach
        self.fields["base_price"] = tk.StringVar(value="")
        self.fields["cost_price"] = tk.StringVar(value="")
        self.fields["item_type"] = tk.StringVar(value="standard")  # standard, bulk_package, fractional

        # Unit fields
        self.fields["unit_of_measure"] = tk.StringVar(value=self.existing.get("unit_of_measure", "pieces") if self.existing else "pieces")
        self.fields["package_size"] = tk.StringVar(value="1")  # How many base units per package

        # Advanced fields
        self.fields["vat_rate"] = tk.StringVar(value=str(self.existing.get("vat_rate", 16.0) if self.existing else 16.0))
        self.fields["low_stock_threshold"] = tk.StringVar(value=str(self.existing.get("low_stock_threshold", 10) if self.existing else 10))
        self.fields["quantity"] = tk.StringVar(value=str(self.existing.get("quantity", 0) if self.existing else 0))

        # Error labels for each field
        for key in ["name", "base_price", "cost_price", "quantity", "barcode", "category", "vat_rate", "unit_of_measure", "package_size"]:
            self.error_labels[key] = None

        # Set initial values based on existing item
        if self.existing:
            self._populate_fields_from_existing()

    def _populate_fields_from_existing(self) -> None:
        """Populate form fields from existing item data."""
        if not self.existing:
            return

        # Determine item type based on existing data
        if self.existing.get("is_special_volume"):
            self.fields["item_type"].set("fractional")
            # For fractional items, base price is price per unit
            unit_multiplier = items._get_unit_multiplier(self.existing.get("unit_of_measure", "pieces"))
            if self.existing.get("price_per_ml"):
                self.fields["base_price"].set(f"{self.existing['price_per_ml'] * unit_multiplier:.2f}")
            elif self.existing.get("selling_price_per_unit"):
                self.fields["base_price"].set(f"{self.existing['selling_price_per_unit']:.2f}")
        else:
            self.fields["item_type"].set("bulk_package")
            self.fields["base_price"].set(f"{self.existing.get('selling_price', 0):.2f}")

        self.fields["cost_price"].set(f"{self.existing.get('cost_price', 0):.2f}")
        self.fields["package_size"].set(str(self.existing.get("unit_size_ml", 1)))

    def _build_basic_info_tab(self, parent: ttk.Frame) -> None:
        """Build the basic information tab with error labels and real-time validation."""
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        row = 0

        # Item Name
        ttk.Label(scrollable_frame, text="Item Name *", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=(10, 5), padx=10)
        name_entry = ttk.Entry(scrollable_frame, textvariable=self.fields["name"], width=50)
        name_entry.grid(row=row, column=1, sticky=tk.EW, pady=(10, 5), padx=(0, 10))
        self.error_labels["name"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["name"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))
        def validate_name(*_):
            value = self.fields["name"].get().strip()
            if not value:
                self.error_labels["name"].config(text="Name is required")
            elif len(value) > 100:
                self.error_labels["name"].config(text="Max 100 characters")
            else:
                self.error_labels["name"].config(text="")
        self.fields["name"].trace_add("write", validate_name)
        validate_name()
        row += 2

        # ...existing code for other fields...

        # Category
        ttk.Label(scrollable_frame, text="Category", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        category_combo = ttk.Combobox(scrollable_frame, textvariable=self.fields["category"], width=47)
        category_combo['values'] = self._get_category_list()
        category_combo.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(0, 10))
        self.error_labels["category"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["category"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))
        def validate_category(*_):
            value = self.fields["category"].get().strip()
            if len(value) > 50:
                self.error_labels["category"].config(text="Max 50 characters")
            else:
                self.error_labels["category"].config(text="")
        self.fields["category"].trace_add("write", validate_category)
        validate_category()
        row += 2

        # Barcode
        ttk.Label(scrollable_frame, text="Barcode", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        barcode_frame = ttk.Frame(scrollable_frame)
        barcode_frame.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(0, 10))
        ttk.Entry(barcode_frame, textvariable=self.fields["barcode"], width=35).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(barcode_frame, text="Scan", width=10, command=self._scan_barcode).pack(side=tk.RIGHT, padx=(5, 0))
        self.error_labels["barcode"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["barcode"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))
        def validate_barcode(*_):
            value = self.fields["barcode"].get().strip()
            if value and len(value) > 50:
                self.error_labels["barcode"].config(text="Max 50 characters")
            else:
                self.error_labels["barcode"].config(text="")
        self.fields["barcode"].trace_add("write", validate_barcode)
        validate_barcode()
        row += 2

        # Item Type Selection
        ttk.Label(scrollable_frame, text="Item Type", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=(15, 5), padx=10)
        type_frame = ttk.Frame(scrollable_frame)
        type_frame.grid(row=row, column=1, sticky=tk.W, pady=(15, 5), padx=(0, 10))

        ttk.Radiobutton(type_frame, text="Standard Item (sold whole)", variable=self.fields["item_type"],
                       value="standard", command=self._on_item_type_change).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(type_frame, text="Bulk Package (sold by package)", variable=self.fields["item_type"],
                       value="bulk_package", command=self._on_item_type_change).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(type_frame, text="Fractional Item (sold by weight/volume)", variable=self.fields["item_type"],
                       value="fractional", command=self._on_item_type_change).pack(side=tk.LEFT)
        row += 1

        # Unit of Measure (shown for all types)
        ttk.Label(scrollable_frame, text="Unit of Measure", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        unit_combo = ttk.Combobox(scrollable_frame, textvariable=self.fields["unit_of_measure"], width=47, state="readonly")
        unit_combo['values'] = ["pieces", "liters", "kilograms", "meters", "grams", "milliliters"]
        unit_combo.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(0, 10))
        unit_combo.bind("<<ComboboxSelected>>", lambda e: self._on_unit_change())
        row += 1

        # Package Size (shown for bulk_package and fractional types)
        self.fields["package_size_label"] = ttk.Label(scrollable_frame, text="Package Size", font=("Segoe UI", 9))
        self.fields["package_size_entry"] = ttk.Entry(scrollable_frame, textvariable=self.fields["package_size"], width=50)

        # Image
        ttk.Label(scrollable_frame, text="Image", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        image_frame = ttk.Frame(scrollable_frame)
        image_frame.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(0, 10))
        ttk.Entry(image_frame, textvariable=self.fields["image_path"], width=35).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(image_frame, text="Browse", width=10, command=self._browse_image).pack(side=tk.RIGHT, padx=(5, 0))
        row += 1

        # Configure grid weights
        scrollable_frame.columnconfigure(1, weight=1)

        # Initialize type-specific fields
        self._on_item_type_change()

    def _build_pricing_tab(self, parent: ttk.Frame) -> None:
        """Build the pricing tab with simplified pricing model."""
        # Scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        row = 0

        # Pricing explanation
        pricing_info = ttk.Label(scrollable_frame,
            text="Set prices for your item. The system will automatically calculate unit prices.",
            font=("Segoe UI", 9), wraplength=600, justify=tk.LEFT)
        pricing_info.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(10, 15), padx=10)
        row += 1

        # Base selling price
        ttk.Label(scrollable_frame, text="Selling Price *", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        price_frame = ttk.Frame(scrollable_frame)
        price_frame.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(0, 10))
        ttk.Label(price_frame, text=f"{self.currency_symbol}", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        base_price_entry = ttk.Entry(price_frame, textvariable=self.fields["base_price"], width=20)
        base_price_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.fields["price_unit_label"] = ttk.Label(price_frame, text="(per piece)", font=("Segoe UI", 8), foreground="gray")
        self.fields["price_unit_label"].pack(side=tk.RIGHT, padx=(10, 0))
        self.error_labels["base_price"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["base_price"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))
        def validate_base_price(*_):
            value = self.fields["base_price"].get().strip()
            try:
                v = float(value)
                if v < 0:
                    self.error_labels["base_price"].config(text="Must be >= 0")
                else:
                    self.error_labels["base_price"].config(text="")
            except Exception:
                if value:
                    self.error_labels["base_price"].config(text="Invalid number")
                else:
                    self.error_labels["base_price"].config(text="Required")
        self.fields["base_price"].trace_add("write", validate_base_price)
        validate_base_price()
        row += 2

        # Cost price
        ttk.Label(scrollable_frame, text="Cost Price", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        cost_frame = ttk.Frame(scrollable_frame)
        cost_frame.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(0, 10))
        ttk.Label(cost_frame, text=f"{self.currency_symbol}", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        cost_price_entry = ttk.Entry(cost_frame, textvariable=self.fields["cost_price"], width=20, state="normal" if self.is_admin else "readonly")
        cost_price_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.fields["cost_unit_label"] = ttk.Label(cost_frame, text="(per piece)", font=("Segoe UI", 8), foreground="gray")
        self.fields["cost_unit_label"].pack(side=tk.RIGHT, padx=(10, 0))
        self.error_labels["cost_price"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["cost_price"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))
        def validate_cost_price(*_):
            value = self.fields["cost_price"].get().strip()
            try:
                v = float(value)
                if v < 0:
                    self.error_labels["cost_price"].config(text="Must be >= 0")
                else:
                    self.error_labels["cost_price"].config(text="")
            except Exception:
                if value:
                    self.error_labels["cost_price"].config(text="Invalid number")
                else:
                    self.error_labels["cost_price"].config(text="")
        self.fields["cost_price"].trace_add("write", validate_cost_price)
        validate_cost_price()
        row += 2

        # Profit margin display
        ttk.Label(scrollable_frame, text="Profit Margin", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.fields["profit_margin"] = ttk.Label(scrollable_frame, text="--", font=("Segoe UI", 9, "bold"), foreground="green")
        self.fields["profit_margin"].grid(row=row, column=1, sticky=tk.W, pady=5, padx=(0, 10))
        row += 1

        # Auto-calculate profit margin
        def update_profit_margin(*args):
            try:
                sell = float(self.fields["base_price"].get() or 0)
                cost = float(self.fields["cost_price"].get() or 0)
                if sell > 0 and cost > 0:
                    margin = ((sell - cost) / sell) * 100
                    self.fields["profit_margin"].config(text=f"{margin:.1f}%", foreground="green" if margin >= 0 else "red")
                else:
                    self.fields["profit_margin"].config(text="--")
            except ValueError:
                self.fields["profit_margin"].config(text="--")

        self.fields["base_price"].trace_add("write", update_profit_margin)
        self.fields["cost_price"].trace_add("write", update_profit_margin)

        # Configure grid weights
        scrollable_frame.columnconfigure(1, weight=1)

    def _build_advanced_tab(self, parent: ttk.Frame) -> None:
        """Build the advanced settings tab."""
        # Scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        row = 0

        # Stock settings
        ttk.Label(scrollable_frame, text="Stock Settings", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(10, 5), padx=10)
        row += 1

        ttk.Label(scrollable_frame, text="Current Quantity", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        ttk.Entry(scrollable_frame, textvariable=self.fields["quantity"], width=20).grid(row=row, column=1, sticky=tk.W, pady=5, padx=(0, 10))
        row += 1

        ttk.Label(scrollable_frame, text="Low Stock Alert Threshold", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        ttk.Entry(scrollable_frame, textvariable=self.fields["low_stock_threshold"], width=20).grid(row=row, column=1, sticky=tk.W, pady=5, padx=(0, 10))
        row += 1

        # Tax settings
        ttk.Label(scrollable_frame, text="Tax Settings", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(20, 5), padx=10)
        row += 1

        ttk.Label(scrollable_frame, text="VAT Rate (%)", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        vat_frame = ttk.Frame(scrollable_frame)
        vat_frame.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(0, 10))
        ttk.Entry(vat_frame, textvariable=self.fields["vat_rate"], width=10).pack(side=tk.LEFT)
        ttk.Label(vat_frame, text="(e.g., 16.0 for 16%)", font=("Segoe UI", 8), foreground="gray").pack(side=tk.LEFT, padx=(10, 0))
        row += 1

        # Configure grid weights
        scrollable_frame.columnconfigure(1, weight=1)

    def _on_item_type_change(self) -> None:
        """Handle item type changes to show/hide relevant fields."""
        item_type = self.fields["item_type"].get()

        if item_type == "standard":
            # Standard items: hide package size, price per piece
            self.fields["package_size_label"].grid_remove()
            self.fields["package_size_entry"].grid_remove()
            self.fields["price_unit_label"].config(text="(per piece)")
            self.fields["cost_unit_label"].config(text="(per piece)")

        elif item_type == "bulk_package":
            # Bulk packages: show package size, price per package
            self.fields["package_size_label"].grid()
            self.fields["package_size_entry"].grid()
            self.fields["price_unit_label"].config(text="(per package)")
            self.fields["cost_unit_label"].config(text="(per package)")

        elif item_type == "fractional":
            # Fractional items: show package size, price per base unit
            self.fields["package_size_label"].grid()
            self.fields["package_size_entry"].grid()
            unit = self.fields["unit_of_measure"].get().lower()
            if "liter" in unit or "l" == unit:
                self.fields["price_unit_label"].config(text="(per liter)")
                self.fields["cost_unit_label"].config(text="(per liter)")
            elif "kilo" in unit or "kg" in unit:
                self.fields["price_unit_label"].config(text="(per kg)")
                self.fields["cost_unit_label"].config(text="(per kg)")
            else:
                self.fields["price_unit_label"].config(text="(per unit)")
                self.fields["cost_unit_label"].config(text="(per unit)")

    def _on_unit_change(self) -> None:
        """Handle unit of measure changes."""
        unit = self.fields["unit_of_measure"].get().lower()
        item_type = self.fields["item_type"].get()

        # Set default package sizes for common units
        if item_type == "fractional":
            if "liter" in unit or "l" == unit:
                if not self.fields["package_size"].get() or self.fields["package_size"].get() == "1":
                    self.fields["package_size"].set("1000")  # 1000ml per liter
            elif "kilo" in unit or "kg" in unit:
                if not self.fields["package_size"].get() or self.fields["package_size"].get() == "1":
                    self.fields["package_size"].set("1000")  # 1000g per kg
            elif "meter" in unit or "m" == unit:
                if not self.fields["package_size"].get() or self.fields["package_size"].get() == "1":
                    self.fields["package_size"].set("100")  # 100cm per meter

        self._on_item_type_change()

    def _on_save(self) -> None:
        """Save the item with validation."""
        try:
            # Validate required fields
            if not self.fields["name"].get().strip():
                messagebox.showerror("Validation Error", "Item name is required")
                return

            if not self.fields["base_price"].get().strip():
                messagebox.showerror("Validation Error", "Selling price is required")
                return

            # Parse and validate numeric fields
            item_data = self._parse_item_data()

            # Create or update item
            if self.existing:
                items.update_item(self.existing["item_id"], **item_data)
                messagebox.showinfo("Success", "Item updated successfully")
            else:
                items.create_item(**item_data)
                messagebox.showinfo("Success", "Item created successfully")

            # Close dialog and refresh parent
            if self.dialog:
                self.dialog.destroy()
            # Note: Parent refresh should be handled by the caller

        except ValidationError as e:
            messagebox.showerror("Validation Error", str(e))
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your input values: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save item: {e}")

    def _parse_item_data(self) -> Dict[str, Any]:
        """Parse form data into item creation/update format."""
        item_type = self.fields["item_type"].get()
        unit = self.fields["unit_of_measure"].get()

        # Base data
        data = {
            "name": self.fields["name"].get().strip(),
            "category": self.fields["category"].get().strip() or None,
            "barcode": self.fields["barcode"].get().strip() or None,
            "image_path": self.fields["image_path"].get().strip() or None,
            "unit_of_measure": unit,
            "vat_rate": validate_numeric(self.fields["vat_rate"].get(), 0, 100),
            "low_stock_threshold": validate_integer(self.fields["low_stock_threshold"].get(), 0),
            "quantity": validate_numeric(self.fields["quantity"].get(), 0),
        }

        # Pricing logic based on item type
        base_price = validate_numeric(self.fields["base_price"].get(), 0)
        cost_price = validate_numeric(self.fields["cost_price"].get(), 0) if self.is_admin else 0

        if item_type == "standard":
            # Standard items: price per piece, no special volume
            data.update({
                "selling_price": base_price,
                "cost_price": cost_price,
                "is_special_volume": 0,
                "unit_size_ml": 1,
                "price_per_ml": None,
                "selling_price_per_unit": None,
                "cost_price_per_unit": None,
            })

        elif item_type == "bulk_package":
            # Bulk packages: price per package
            package_size = validate_integer(self.fields["package_size"].get(), 1)
            data.update({
                "selling_price": base_price,
                "cost_price": cost_price,
                "is_special_volume": 0,
                "unit_size_ml": package_size,
                "price_per_ml": None,
                "selling_price_per_unit": None,
                "cost_price_per_unit": None,
            })

        elif item_type == "fractional":
            # Fractional items: price per base unit, enable special volume
            package_size = validate_integer(self.fields["package_size"].get(), 1)
            unit_multiplier = items._get_unit_multiplier(unit)

            data.update({
                "selling_price": base_price * package_size,  # Total package price
                "cost_price": cost_price * package_size if cost_price > 0 else 0,
                "is_special_volume": 1,
                "unit_size_ml": package_size,
                "price_per_ml": base_price / unit_multiplier,  # Price per smallest unit
                "selling_price_per_unit": base_price,
                "cost_price_per_unit": cost_price,
            })

        return data

    def _get_category_list(self) -> list:
        """Get list of existing categories for the combobox."""
        try:
            categories = items.get_categories()
            return sorted([cat["category"] for cat in categories if cat["category"]])
        except:
            return []

    def _scan_barcode(self) -> None:
        """Placeholder for barcode scanning functionality."""
        messagebox.showinfo("Barcode Scan", "Barcode scanning not yet implemented")

    def _browse_image(self) -> None:
        """Browse for item image file."""
        if not self.dialog:
            return

        filename = filedialog.askopenfilename(
            title="Select Item Image",
            parent=self.dialog,
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")]
        )
        if filename:
            self.fields["image_path"].set(filename)

    def _on_cancel(self) -> None:
        """Handle cancel button."""
        if self.dialog:
            self.dialog.destroy()

    def _show_dialog(self) -> None:
        """Show the dialog after it's fully built."""
        if self.dialog:
            self.dialog.deiconify()
            self.dialog.grab_set()
            self.dialog.wait_window()