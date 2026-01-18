"""Simplified Item Dialog for Kiosk POS - Improved UX"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Dict, Any
import logging
from modules import items
from utils import set_window_icon
from utils.validation import ValidationError, validate_numeric, validate_integer
from utils.i18n import get_currency_symbol

logger = logging.getLogger(__name__)


class SimplifiedItemDialog:
    """Simplified item creation/editing dialog with wizard-style interface."""

    def __init__(self, parent: tk.Misc, existing: Optional[Dict[str, Any]] = None, is_admin: bool = True):
        self.parent = parent
        self.existing = existing
        self.is_admin = is_admin
        self.currency_symbol = get_currency_symbol()
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
        is_variant = self.existing and 'variant_id' in self.existing
        item_type = "Variant" if is_variant else "Item"
        title = f"Create {item_type}" if not self.existing else f"Edit {item_type} - {self.existing.get('name', '')}"
        self.dialog.title(title)
        set_window_icon(self.dialog)
        self.dialog.transient(self.parent)

        # Choose a reasonable initial size relative to screen, keep it resizable
        screen_w = self.dialog.winfo_screenwidth()
        screen_h = self.dialog.winfo_screenheight()
        init_w = min(1000, int(screen_w * 0.8))
        init_h = min(800, int(screen_h * 0.75))
        self.dialog.geometry(f"{init_w}x{init_h}")
        self.dialog.resizable(True, True)

    def _build_ui(self) -> None:
        """Build the dialog UI with notebook tabs."""
        if not self.dialog:
            return

        # Create notebook for wizard-style interface
        notebook = ttk.Notebook(self.dialog)
        notebook.grid(row=0, column=0, sticky=tk.NSEW, padx=10, pady=(10, 0))

        # Tab 1: Basic Information
        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="Basic Info")

        # Tab 2: Pricing
        pricing_frame = ttk.Frame(notebook)
        notebook.add(pricing_frame, text="Pricing")

        # Tab 3: Advanced Settings
        advanced_frame = ttk.Frame(notebook)
        notebook.add(advanced_frame, text="Advanced")

        # Keep references so tabs can be hidden/shown when variants toggled
        self.notebook = notebook
        self.basic_frame = basic_frame
        self.pricing_frame = pricing_frame
        self.advanced_frame = advanced_frame

        # Initialize form fields
        self._init_form_fields()

        # Build each tab
        self._build_basic_info_tab(basic_frame)
        self._build_pricing_tab(pricing_frame)
        self._build_advanced_tab(advanced_frame)

        # Initialize type-specific fields after all tabs are built
        self._on_item_type_change()

        # Initialize variant-specific fields
        self._on_variants_change()

        # Auto-size the dialog to fit content
        self._auto_size_dialog()

        # Button frame at bottom
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=1, column=0, sticky=tk.EW, padx=10, pady=(5, 10))

        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        save_btn = ttk.Button(button_frame, text="Save Item", command=self._on_save)
        save_btn.pack(side=tk.RIGHT)

        # Configure grid weights to push buttons to bottom
        self.dialog.grid_rowconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(1, weight=0)
        self.dialog.grid_columnconfigure(0, weight=1)

    def _init_form_fields(self) -> None:
        """Initialize form fields with defaults and existing values, and error labels."""
        self.fields = {}
        self.error_labels = {}

        # Basic fields
        self.fields["name"] = tk.StringVar(value=self.existing.get("name", "") if self.existing else "")
        self.fields["category"] = tk.StringVar(value=self.existing.get("category", "") if self.existing else "")
        self.fields["barcode"] = tk.StringVar(value=self.existing.get("barcode", "") if self.existing else "")
        self.fields["image_path"] = tk.StringVar(value=self.existing.get("image_path", "") if self.existing else "")
        self.fields["has_variants"] = tk.BooleanVar(value=bool(self.existing.get("has_variants", False)) if self.existing else False)

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
        for key in ["name", "base_price", "cost_price", "quantity", "barcode", "category", "vat_rate", "unit_of_measure", "package_size", "low_stock_threshold"]:
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
        v_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        h_scrollbar = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        # Use the dialog-level persistent horizontal scrollbar for all tabs
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        # Pack the per-tab horizontal scrollbar
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        # Keep reference (not strictly required) to this canvas
        self.basic_canvas = canvas

        # Ensure the inner frame width follows the canvas width so content auto-fits and horizontal
        # scrollbar appears only when needed. Also update scrollregion when inner size changes.
        def _on_canvas_configure(e, _canvas=canvas, _window=canvas_window, _inner=scrollable_frame):
            inner_w = _inner.winfo_reqwidth()
            # Let the inner frame be at least the canvas width, but allow it to grow bigger than canvas
            target_w = max(inner_w, e.width)
            _canvas.itemconfigure(_window, width=target_w)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        # Per-tab horizontal scrollbar is not packed; the dialog-level persistent scrollbar is used instead
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
        category_combo = ttk.Combobox(scrollable_frame, textvariable=self.fields["category"], width=47, state="readonly")
        # Populate values and ensure the dropdown can be shown on click/focus
        category_combo['values'] = self._get_category_list()
        # Refresh the list when the widget receives focus so it stays up-to-date
        category_combo.bind("<FocusIn>", lambda e: category_combo.configure(values=self._get_category_list()))
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
        unit_combo['values'] = self._get_unit_list()
        # Refresh the list when the widget receives focus so it stays up-to-date
        unit_combo.bind("<FocusIn>", lambda e: unit_combo.configure(values=self._get_unit_list()))
        unit_combo.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(0, 10))
        unit_combo.bind("<<ComboboxSelected>>", lambda e: self._on_unit_change())
        self.error_labels["unit_of_measure"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["unit_of_measure"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))

        # Manage Portions (only enabled for fractional items and when editing an existing item)
        self.manage_portions_btn = ttk.Button(scrollable_frame, text="Manage Portions...", command=self._manage_portions, width=18)
        try:
            # Place to the right of the unit combobox (column 2)
            self.manage_portions_btn.grid(row=row, column=2, sticky=tk.W, padx=(8, 0))
        except Exception:
            # If layout grid doesn't have a column 2, just pack below
            self.manage_portions_btn.grid(row=row+2, column=1, sticky=tk.W, padx=(0, 10))
        self.manage_portions_btn.config(state="disabled")
        def validate_unit_of_measure(*_):
            value = self.fields["unit_of_measure"].get().strip()
            if not value:
                self.error_labels["unit_of_measure"].config(text="Required")
            else:
                self.error_labels["unit_of_measure"].config(text="")
        self.fields["unit_of_measure"].trace_add("write", validate_unit_of_measure)
        validate_unit_of_measure()
        row += 2

        # Package Size (shown for bulk_package and fractional types)
        self.fields["package_size_label"] = ttk.Label(scrollable_frame, text="Package Size", font=("Segoe UI", 9))
        self.fields["package_size_entry"] = ttk.Entry(scrollable_frame, textvariable=self.fields["package_size"], width=50)
        self.error_labels["package_size"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        def validate_package_size(*_):
            value = self.fields["package_size"].get().strip()
            if not value:
                self.error_labels["package_size"].config(text="")
                return
            try:
                v = int(float(value))
                if v <= 0:
                    self.error_labels["package_size"].config(text="Must be > 0")
                elif v > 1000000:
                    self.error_labels["package_size"].config(text="Max 1,000,000")
                else:
                    self.error_labels["package_size"].config(text="")
            except Exception:
                self.error_labels["package_size"].config(text="Invalid number")
        self.fields["package_size"].trace_add("write", validate_package_size)
        validate_package_size()

        # Image
        ttk.Label(scrollable_frame, text="Image", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        image_frame = ttk.Frame(scrollable_frame)
        image_frame.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(0, 10))
        ttk.Entry(image_frame, textvariable=self.fields["image_path"], width=35).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(image_frame, text="Browse", width=10, command=self._browse_image).pack(side=tk.RIGHT, padx=(5, 0))
        row += 1

        # Has Variants checkbox - only show for regular items, not variants
        is_variant = self.existing and 'variant_id' in self.existing
        if not is_variant:
            ttk.Label(scrollable_frame, text="Has Variants", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
            variants_check = ttk.Checkbutton(scrollable_frame, text="This item has multiple variants (sizes, colors, etc.)",
                                            variable=self.fields["has_variants"], command=self._on_variants_change)
            variants_check.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(0, 10))
            row += 1

        # Configure grid weights
        scrollable_frame.columnconfigure(1, weight=1)

    def _build_pricing_tab(self, parent: ttk.Frame) -> None:
        """Build the pricing tab with simplified pricing model."""
        # Initialize pricing widgets list
        self.pricing_widgets = []
        # Scrollable frame
        canvas = tk.Canvas(parent)
        v_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        h_scrollbar = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.pricing_canvas = canvas

        # Resize inner window to follow canvas width so controls and 'tables' auto-fit
        def _on_pricing_canvas_configure(e, _canvas=canvas, _window=canvas_window, _inner=scrollable_frame):
            inner_w = _inner.winfo_reqwidth()
            target_w = max(inner_w, e.width)
            _canvas.itemconfigure(_window, width=target_w)
        canvas.bind("<Configure>", _on_pricing_canvas_configure)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Ensure columns expand
        scrollable_frame.columnconfigure(1, weight=1)

        # Initial sizing pass
        canvas.update_idletasks()
        _on_pricing_canvas_configure(type("E", (), {"width": canvas.winfo_width()}))

        row = 0

        # Pricing explanation
        pricing_info = ttk.Label(scrollable_frame,
            text="Set prices for your item. The system will automatically calculate unit prices.",
            font=("Segoe UI", 9), wraplength=600, justify=tk.LEFT)
        pricing_info.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(10, 15), padx=10)
        self.pricing_widgets.append(pricing_info)
        row += 1

        # Base selling price
        price_label = ttk.Label(scrollable_frame, text="Selling Price *", font=("Segoe UI", 10, "bold"))
        price_label.grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.pricing_widgets.append(price_label)
        price_frame = ttk.Frame(scrollable_frame)
        price_frame.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(0, 10))
        self.pricing_widgets.append(price_frame)
        ttk.Label(price_frame, text=f"{self.currency_symbol}", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        base_price_entry = ttk.Entry(price_frame, textvariable=self.fields["base_price"], width=20)
        base_price_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.fields["price_unit_label"] = ttk.Label(price_frame, text="(per piece)", font=("Segoe UI", 8), foreground="gray")
        self.fields["price_unit_label"].pack(side=tk.RIGHT, padx=(10, 0))
        self.error_labels["base_price"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["base_price"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))
        self.pricing_widgets.append(self.error_labels["base_price"])
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
        cost_label = ttk.Label(scrollable_frame, text="Cost Price", font=("Segoe UI", 9))
        cost_label.grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.pricing_widgets.append(cost_label)
        cost_frame = ttk.Frame(scrollable_frame)
        cost_frame.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(0, 10))
        self.pricing_widgets.append(cost_frame)
        ttk.Label(cost_frame, text=f"{self.currency_symbol}", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        cost_price_entry = ttk.Entry(cost_frame, textvariable=self.fields["cost_price"], width=20, state="normal" if self.is_admin else "readonly")
        cost_price_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.fields["cost_unit_label"] = ttk.Label(cost_frame, text="(per piece)", font=("Segoe UI", 8), foreground="gray")
        self.fields["cost_unit_label"].pack(side=tk.RIGHT, padx=(10, 0))
        self.error_labels["cost_price"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["cost_price"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))
        self.pricing_widgets.append(self.error_labels["cost_price"])
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
        profit_margin_label = ttk.Label(scrollable_frame, text="Profit Margin", font=("Segoe UI", 9))
        profit_margin_label.grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.pricing_widgets.append(profit_margin_label)
        self.fields["profit_margin"] = ttk.Label(scrollable_frame, text="--", font=("Segoe UI", 9, "bold"), foreground="green")
        self.fields["profit_margin"].grid(row=row, column=1, sticky=tk.W, pady=5, padx=(0, 10))
        self.pricing_widgets.append(self.fields["profit_margin"])
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

        self.fields["cost_unit_label"].pack(side=tk.RIGHT, padx=(10, 0))
        self.error_labels["cost_price"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["cost_price"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))
        self.pricing_widgets.append(self.error_labels["cost_price"])
        row += 1

        # Profit margin display
        profit_label = ttk.Label(scrollable_frame, text="Profit Margin", font=("Segoe UI", 9))
        profit_label.grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.pricing_widgets.append(profit_label)
        self.fields["profit_margin"] = ttk.Label(scrollable_frame, text="--", font=("Segoe UI", 9, "bold"), foreground="green")
        self.fields["profit_margin"].grid(row=row, column=1, sticky=tk.W, pady=5, padx=(0, 10))
        self.pricing_widgets.append(self.fields["profit_margin"])
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

    def _auto_size_dialog(self) -> None:
        """Auto-size the dialog to fit all content properly."""
        if not self.dialog:
            return

        # Update the dialog to calculate widget sizes
        self.dialog.update_idletasks()

        # Get the required size
        req_width = self.dialog.winfo_reqwidth()
        req_height = self.dialog.winfo_reqheight()

        # Respect screen size and keep reasonable minimums so dialog remains usable
        screen_w = self.dialog.winfo_screenwidth()
        screen_h = self.dialog.winfo_screenheight()

        min_width = max(req_width, 800)
        min_height = max(req_height, 600)

        # Cap to a percentage of the screen so dialog doesn't exceed visible area
        final_width = min(min_width, int(screen_w * 0.95))
        final_height = min(min_height, int(screen_h * 0.9))

        # Set the dialog size
        self.dialog.geometry(f"{final_width}x{final_height}")

        # Force a geometry update so canvases receive the configure event
        self.dialog.update_idletasks()

    def _build_advanced_tab(self, parent: ttk.Frame) -> None:
        """Build the advanced settings tab."""
        # Initialize quantity widgets list
        self.quantity_widgets = []
        # Scrollable frame
        canvas = tk.Canvas(parent)
        v_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        h_scrollbar = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.advanced_canvas = canvas

        # Resize inner window to follow canvas width so controls and 'tables' auto-fit
        def _on_advanced_canvas_configure(e, _canvas=canvas, _window=canvas_window, _inner=scrollable_frame):
            inner_w = _inner.winfo_reqwidth()
            target_w = max(inner_w, e.width)
            _canvas.itemconfigure(_window, width=target_w)
        canvas.bind("<Configure>", _on_advanced_canvas_configure)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Ensure columns expand
        scrollable_frame.columnconfigure(1, weight=1)

        # Initial sizing pass
        canvas.update_idletasks()
        _on_advanced_canvas_configure(type("E", (), {"width": canvas.winfo_width()}))

        row = 0

        # Stock settings
        ttk.Label(scrollable_frame, text="Stock Settings", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(10, 5), padx=10)
        row += 1

        qty_label = ttk.Label(scrollable_frame, text="Current Quantity", font=("Segoe UI", 9))
        qty_label.grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.quantity_widgets.append(qty_label)
        qty_entry = ttk.Entry(scrollable_frame, textvariable=self.fields["quantity"], width=20)
        qty_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(0, 10))
        self.quantity_widgets.append(qty_entry)
        self.error_labels["quantity"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["quantity"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))
        self.quantity_widgets.append(self.error_labels["quantity"])
        def validate_quantity(*_):
            value = self.fields["quantity"].get().strip()
            if not value:
                self.error_labels["quantity"].config(text="")
                return
            try:
                v = float(value)
                if v < 0:
                    self.error_labels["quantity"].config(text="Must be >= 0")
                else:
                    self.error_labels["quantity"].config(text="")
            except Exception:
                self.error_labels["quantity"].config(text="Invalid number")
        self.fields["quantity"].trace_add("write", validate_quantity)
        validate_quantity()
        row += 2

        ttk.Label(scrollable_frame, text="Low Stock Alert Threshold", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        low_stock_entry = ttk.Entry(scrollable_frame, textvariable=self.fields["low_stock_threshold"], width=20)
        low_stock_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(0, 10))
        self.error_labels["low_stock_threshold"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["low_stock_threshold"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))
        def validate_low_stock(*_):
            value = self.fields["low_stock_threshold"].get().strip()
            if not value:
                self.error_labels["low_stock_threshold"].config(text="")
                return
            try:
                v = int(float(value))
                if v < 0:
                    self.error_labels["low_stock_threshold"].config(text="Must be >= 0")
                elif v > 10000:
                    self.error_labels["low_stock_threshold"].config(text="Max 10000")
                else:
                    self.error_labels["low_stock_threshold"].config(text="")
            except Exception:
                self.error_labels["low_stock_threshold"].config(text="Invalid number")
        self.fields["low_stock_threshold"].trace_add("write", validate_low_stock)
        validate_low_stock()
        row += 2

        # Tax settings
        ttk.Label(scrollable_frame, text="Tax Settings", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(20, 5), padx=10)
        row += 1

        ttk.Label(scrollable_frame, text="VAT Rate (%)", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        vat_frame = ttk.Frame(scrollable_frame)
        vat_frame.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(0, 10))
        vat_entry = ttk.Entry(vat_frame, textvariable=self.fields["vat_rate"], width=10)
        vat_entry.pack(side=tk.LEFT)
        ttk.Label(vat_frame, text="(e.g., 16.0 for 16%)", font=("Segoe UI", 8), foreground="gray").pack(side=tk.LEFT, padx=(10, 0))
        self.error_labels["vat_rate"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["vat_rate"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))
        def validate_vat_rate(*_):
            value = self.fields["vat_rate"].get().strip()
            if not value:
                self.error_labels["vat_rate"].config(text="")
                return
            try:
                v = float(value)
                if v < 0:
                    self.error_labels["vat_rate"].config(text="Must be >= 0")
                elif v > 100:
                    self.error_labels["vat_rate"].config(text="Max 100%")
                else:
                    self.error_labels["vat_rate"].config(text="")
            except Exception:
                self.error_labels["vat_rate"].config(text="Invalid number")
        self.fields["vat_rate"].trace_add("write", validate_vat_rate)
        validate_vat_rate()
        row += 2

        # Configure grid weights
        scrollable_frame.columnconfigure(1, weight=1)

    def _on_item_type_change(self) -> None:
        """Handle item type changes to show/hide relevant fields."""
        item_type = self.fields["item_type"].get()

        # Enable/disable Manage Portions button: only enabled for fractional items when editing an existing item
        if hasattr(self, 'manage_portions_btn'):
            if item_type == 'fractional' and self.existing and self.existing.get('item_id'):
                self.manage_portions_btn.config(state='normal')
            else:
                self.manage_portions_btn.config(state='disabled')

        if item_type == "standard":
            # Standard items: hide package size, price per piece
            if "package_size_label" in self.fields:
                self.fields["package_size_label"].grid_remove()
            if "package_size_entry" in self.fields:
                self.fields["package_size_entry"].grid_remove()
            if "package_size" in self.error_labels:
                self.error_labels["package_size"].grid_remove()
            if "price_unit_label" in self.fields:
                self.fields["price_unit_label"].config(text="(per piece)")
            if "cost_unit_label" in self.fields:
                self.fields["cost_unit_label"].config(text="(per piece)")

        elif item_type == "bulk_package":
            # Bulk packages: show package size, price per package
            if "package_size_label" in self.fields:
                self.fields["package_size_label"].grid()
            if "package_size_entry" in self.fields:
                self.fields["package_size_entry"].grid()
            if "package_size" in self.error_labels:
                self.error_labels["package_size"].grid()
            if "price_unit_label" in self.fields:
                self.fields["price_unit_label"].config(text="(per package)")
            if "cost_unit_label" in self.fields:
                self.fields["cost_unit_label"].config(text="(per package)")

        elif item_type == "fractional":
            # Fractional items: show package size, price per base unit
            if "package_size_label" in self.fields:
                self.fields["package_size_label"].grid()
            if "package_size_entry" in self.fields:
                self.fields["package_size_entry"].grid()
            if "package_size" in self.error_labels:
                self.error_labels["package_size"].grid()
            unit = self.fields["unit_of_measure"].get().lower()
            if "liter" in unit or "l" == unit:
                if "price_unit_label" in self.fields:
                    self.fields["price_unit_label"].config(text="(per liter)")
                if "cost_unit_label" in self.fields:
                    self.fields["cost_unit_label"].config(text="(per liter)")
            elif "kilo" in unit or "kg" in unit:
                if "price_unit_label" in self.fields:
                    self.fields["price_unit_label"].config(text="(per kg)")
                if "cost_unit_label" in self.fields:
                    self.fields["cost_unit_label"].config(text="(per kg)")
            else:
                if "price_unit_label" in self.fields:
                    self.fields["price_unit_label"].config(text="(per unit)")
                if "cost_unit_label" in self.fields:
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

    def _manage_portions(self) -> None:
        """Open the Manage Portions dialog for the current item.

        If the item is not yet saved, prompt the user to save first.
        """
        # Must have an existing item id to manage portions
        if not self.existing or not self.existing.get('item_id'):
            messagebox.showinfo("Save Item First", "Please save the item before managing portions.")
            return

        # Open management dialog
        ManagePortionsDialog(self.parent, self.existing['item_id'])

    def _on_variants_change(self) -> None:
        """Handle has variants checkbox changes to show/hide pricing and quantity fields.

        For items with variants, hide the Pricing tab and the Advanced tab (they are not applicable),
        and show only the Basic Info tab. When variants are unchecked, restore the tabs.
        """
        has_variants = self.fields["has_variants"].get()

        # Hide/show pricing fields
        if has_variants:
            for widget in self.pricing_widgets:
                widget.grid_remove()
        else:
            for widget in self.pricing_widgets:
                widget.grid()

        # Hide/show quantity field
        if has_variants:
            for widget in self.quantity_widgets:
                widget.grid_remove()
        else:
            for widget in self.quantity_widgets:
                widget.grid()

        # Hide or show entire tabs as appropriate. Use notebook to add/remove Advanced and Pricing tabs
        try:
            # Remove Advanced tab when variants enabled
            if has_variants:
                # Remove pricing and advanced tabs if present
                for frame in (self.pricing_frame, self.advanced_frame):
                    try:
                        idx = self.notebook.index(frame)
                        self.notebook.forget(idx)
                    except Exception:
                        pass
            else:
                # Ensure pricing tab present (insert after basic)
                frames = [self.notebook.tab(i, option='text') for i in range(self.notebook.index('end'))]
                current_tabs = [self.notebook.tab(i, option='text') for i in range(self.notebook.index('end'))]
                # Re-add pricing if missing
                if 'Pricing' not in current_tabs:
                    self.notebook.add(self.pricing_frame, text='Pricing')
                # Re-add advanced if missing
                if 'Advanced' not in current_tabs:
                    self.notebook.add(self.advanced_frame, text='Advanced')
        except Exception:
            logger.exception('Error toggling variant tabs')


    def _on_save(self) -> None:
        """Save the item with validation."""
        # Clear all error labels first
        for label in self.error_labels.values():
            if label:
                label.config(text="")

        try:
            # Parse and validate numeric fields
            item_data = self._parse_item_data()

            # Check if this is a variant edit
            is_variant = self.existing and 'variant_id' in self.existing

            if is_variant:
                # Import variants module
                from modules import variants
                
                # Update variant
                variants.update_variant(
                    variant_id=self.existing['variant_id'],
                    variant_name=item_data.get('name'),
                    selling_price=item_data.get('selling_price'),
                    cost_price=item_data.get('cost_price'),
                    quantity=item_data.get('quantity'),
                    barcode=item_data.get('barcode'),
                    vat_rate=item_data.get('vat_rate'),
                    low_stock_threshold=item_data.get('low_stock_threshold'),
                    image_path=item_data.get('image_path')
                )
                messagebox.showinfo("Success", "Variant updated successfully")
            else:
                # Create or update item
                if self.existing:
                    items.update_item(self.existing["item_id"], **item_data)
                    messagebox.showinfo("Success", "Item updated successfully")
                else:
                    # Filter out keys that are not accepted by create_item signature
                    create_keys = [
                        'name', 'category', 'cost_price', 'selling_price', 'quantity', 'image_path',
                        'barcode', 'vat_rate', 'low_stock_threshold', 'unit_of_measure',
                        'is_special_volume', 'unit_size_ml', 'price_per_ml', 'has_variants'
                    ]
                    create_kwargs = {k: item_data[k] for k in create_keys if k in item_data}
                    items.create_item(**create_kwargs)
                    messagebox.showinfo("Success", "Item created successfully")

            # Close dialog and refresh parent
            if self.dialog:
                self.dialog.destroy()
            # Note: Parent refresh should be handled by the caller

        except ValidationError as e:
            # Surface validation errors next to fields
            error_msg = str(e)
            if "name" in error_msg.lower():
                self.error_labels["name"].config(text=error_msg)
            elif "price" in error_msg.lower() or "selling" in error_msg.lower():
                self.error_labels["base_price"].config(text=error_msg)
            elif "cost" in error_msg.lower():
                self.error_labels["cost_price"].config(text=error_msg)
            elif "quantity" in error_msg.lower():
                self.error_labels["quantity"].config(text=error_msg)
            elif "barcode" in error_msg.lower():
                self.error_labels["barcode"].config(text=error_msg)
            elif "category" in error_msg.lower():
                self.error_labels["category"].config(text=error_msg)
            elif "vat" in error_msg.lower():
                self.error_labels["vat_rate"].config(text=error_msg)
            elif "unit" in error_msg.lower():
                self.error_labels["unit_of_measure"].config(text=error_msg)
            elif "package" in error_msg.lower() or "size" in error_msg.lower():
                self.error_labels["package_size"].config(text=error_msg)
            elif "threshold" in error_msg.lower():
                self.error_labels["low_stock_threshold"].config(text=error_msg)
            else:
                messagebox.showerror("Validation Error", error_msg)
        except ValueError as e:
            # Surface value errors next to fields
            error_msg = str(e)
            if "name" in error_msg.lower():
                self.error_labels["name"].config(text="Invalid name")
            elif "price" in error_msg.lower() or "selling" in error_msg.lower():
                self.error_labels["base_price"].config(text="Invalid price")
            elif "cost" in error_msg.lower():
                self.error_labels["cost_price"].config(text="Invalid cost")
            elif "quantity" in error_msg.lower():
                self.error_labels["quantity"].config(text="Invalid quantity")
            elif "vat" in error_msg.lower():
                self.error_labels["vat_rate"].config(text="Invalid VAT rate")
            elif "threshold" in error_msg.lower():
                self.error_labels["low_stock_threshold"].config(text="Invalid threshold")
            elif "package" in error_msg.lower():
                self.error_labels["package_size"].config(text="Invalid package size")
            else:
                messagebox.showerror("Invalid Input", f"Please check your input values: {e}")
        except Exception as e:
            # Log full exception and surface full traceback to help debugging
            import traceback
            tb = traceback.format_exc()
            logger.exception('Failed to save item')
            # Keep the full traceback available for programmatic inspection
            self._last_save_traceback = tb
            # Show a helpful error dialog with details and instruct user to share the traceback if needed
            messagebox.showerror("Error", f"Failed to save item: {e}\n\nFull traceback:\n{tb}")

    def _parse_item_data(self) -> Dict[str, Any]:
        """Parse form data into item creation/update format."""
        item_type = self.fields["item_type"].get()
        unit = self.fields["unit_of_measure"].get()
        has_variants = self.fields["has_variants"].get()

        # Base data
        data = {
            "name": self.fields["name"].get().strip(),
            "category": self.fields["category"].get().strip() or None,
            "barcode": self.fields["barcode"].get().strip() or None,
            "image_path": self.fields["image_path"].get().strip() or None,
            "unit_of_measure": unit,
            "vat_rate": validate_numeric(self.fields["vat_rate"].get(), 0, 100),
            "low_stock_threshold": validate_integer(self.fields["low_stock_threshold"].get(), 0),
            "quantity": 0 if has_variants else validate_numeric(self.fields["quantity"].get(), 0),
            "has_variants": 1 if has_variants else 0,
        }

        # Pricing logic based on item type
        if has_variants:
            # For items with variants, don't set pricing or quantity - variants will handle this
            data.update({
                "selling_price": 0,
                "cost_price": 0,
                "is_special_volume": 0,
                "unit_size_ml": 1,
                "price_per_ml": None,
                "selling_price_per_unit": None,
                "cost_price_per_unit": None,
            })
        else:
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

    def _refresh_comboboxes(self) -> None:
        """Refresh combobox values after dialog is shown."""
        try:
            # Find and refresh category combobox
            def find_and_refresh(widget):
                for child in widget.winfo_children():
                    if isinstance(child, tk.ttk.Combobox) and hasattr(child, 'configure'):
                        # Check if this is the category combobox by checking if it has values
                        if 'values' in child.configure() and len(child['values']) > 0:
                            child.configure(values=self._get_category_list())
                    find_and_refresh(child)
            find_and_refresh(self.dialog)
        except Exception:
            pass

    def _get_category_list(self) -> list:
        """Get list of existing categories for the combobox."""
        try:
            categories = items.get_categories()
            return sorted(categories)
        except:
            return []


class ManagePortionsDialog:
    """Modal dialog to manage preset portions for a fractional item."""

    def __init__(self, parent: tk.Misc, item_id: int):
        self.parent = parent
        self.item_id = item_id
        self.top = tk.Toplevel(parent)
        self.top.title("Manage Portions")
        set_window_icon(self.top)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.columnconfigure(0, weight=1)

        # Treeview for portions
        cols = ("portion_name", "portion_ml", "selling_price", "cost_price", "is_active")
        self.tree = ttk.Treeview(self.top, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("portion_name", text="Name")
        self.tree.heading("portion_ml", text="ml")
        self.tree.heading("selling_price", text="Price")
        self.tree.heading("cost_price", text="Cost")
        self.tree.heading("is_active", text="Active")
        self.tree.column("portion_name", width=200)
        self.tree.column("portion_ml", width=80, anchor=tk.CENTER)
        self.tree.column("selling_price", width=100, anchor=tk.E)
        self.tree.column("cost_price", width=100, anchor=tk.E)
        self.tree.column("is_active", width=60, anchor=tk.CENTER)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW, padx=10, pady=(10, 0))

        # Buttons
        btn_frame = ttk.Frame(self.top)
        btn_frame.grid(row=1, column=0, sticky=tk.EW, padx=10, pady=10)
        ttk.Button(btn_frame, text="Add", command=self._add).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Edit", command=self._edit).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Create Defaults", command=self._create_defaults).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Close", command=self.top.destroy).pack(side=tk.RIGHT)

        self._refresh()

    def _refresh(self) -> None:
        """Reload portions list."""
        for i in self.tree.get_children():
            self.tree.delete(i)
        from modules import portions
        rows = portions.list_portions(self.item_id, active_only=False)
        for r in rows:
            self.tree.insert("", tk.END, iid=str(r["portion_id"]), values=(r["portion_name"], r["portion_ml"], f"{r["selling_price"]:.2f}", f"{r["cost_price"]:.2f}", "Yes" if r["is_active"] else "No"))

    def _add(self) -> None:
        self._edit(create=True)

    def _edit(self, create: bool = False) -> None:
        """Open a small dialog to create or edit a portion."""
        sel = None if create else self.tree.selection()
        data = None
        if sel:
            pid = int(sel[0])
            from modules import portions
            data = portions.get_portion(pid)

        top = tk.Toplevel(self.top)
        top.title("Add Portion" if create else "Edit Portion")
        set_window_icon(top)
        top.transient(self.top)
        top.grab_set()

        fields = {}
        ttk.Label(top, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        fields["name"] = tk.StringVar(value=data["portion_name"] if data else "")
        ttk.Entry(top, textvariable=fields["name"], width=40).grid(row=0, column=1, padx=8, pady=6)

        ttk.Label(top, text="ml:").grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        fields["ml"] = tk.StringVar(value=str(data["portion_ml"]) if data else "0")
        ttk.Entry(top, textvariable=fields["ml"], width=20).grid(row=1, column=1, padx=8, pady=6, sticky=tk.W)

        ttk.Label(top, text="Price:").grid(row=2, column=0, sticky=tk.W, padx=8, pady=6)
        fields["price"] = tk.StringVar(value=f"{data['selling_price']:.2f}" if data else "0.00")
        ttk.Entry(top, textvariable=fields["price"], width=20).grid(row=2, column=1, padx=8, pady=6, sticky=tk.W)

        ttk.Label(top, text="Cost:").grid(row=3, column=0, sticky=tk.W, padx=8, pady=6)
        fields["cost"] = tk.StringVar(value=f"{data['cost_price']:.2f}" if data else "0.00")
        ttk.Entry(top, textvariable=fields["cost"], width=20).grid(row=3, column=1, padx=8, pady=6, sticky=tk.W)

        active_var = tk.BooleanVar(value=(data["is_active"] if data else True))
        ttk.Checkbutton(top, text="Active", variable=active_var).grid(row=4, column=1, sticky=tk.W, padx=8, pady=6)

        def save():
            try:
                name = fields["name"].get().strip()
                ml = float(fields["ml"].get())
                price = float(fields["price"].get())
                cost = float(fields["cost"].get())
                active = 1 if active_var.get() else 0
                from modules import portions
                if create:
                    portions.create_portion(self.item_id, name, ml, price, cost_price=cost)
                else:
                    portions.update_portion(pid, portion_name=name, portion_ml=ml, selling_price=price, cost_price=cost, is_active=active)
                top.destroy()
                self._refresh()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save portion: {e}")

        ttk.Button(top, text="Save", command=save).grid(row=5, column=0, padx=8, pady=10)
        ttk.Button(top, text="Cancel", command=top.destroy).grid(row=5, column=1, padx=8, pady=10)

    def _delete(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Portion", "Please select a portion to delete")
            return
        pid = int(sel[0])
        if not messagebox.askyesno("Confirm Delete", "Delete selected portion?"):
            return
        from modules import portions
        try:
            portions.delete_portion(pid)
            self._refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete portion: {e}")

    def _create_defaults(self) -> None:
        # Try to estimate price_per_liter from item data (if available)
        try:
            item = None
            from modules import items
            item = items.get_item(self.item_id)
            if not item:
                messagebox.showerror("Error", "Item not found")
                return
            # price_per_liter estimation if unit is liters
            price_per_liter = 0
            cost_per_liter = 0
            if item.get("unit_of_measure") and ("liter" in item.get("unit_of_measure").lower() or item.get("unit_of_measure").lower() == "l"):
                price_per_liter = item.get("selling_price", 0)
                cost_per_liter = item.get("cost_price", 0)
            from modules import portions
            portions.create_default_portions(self.item_id, price_per_liter, cost_per_liter)
            self._refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create default portions: {e}")

    def _get_unit_list(self) -> list:
        """Get list of existing units of measure for the combobox."""
        try:
            from modules import units_of_measure
            units = units_of_measure.list_units()
            return sorted([unit['name'] for unit in units])
        except:
            return ["pieces", "liters", "kilograms", "meters", "grams", "milliliters"]

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
            # Ensure combobox values are set after dialog is visible
            self.dialog.after(100, self._refresh_comboboxes)
            self.dialog.grab_set()
            self.dialog.wait_window()