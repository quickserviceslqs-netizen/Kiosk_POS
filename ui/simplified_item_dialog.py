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
        self.trace_ids: Dict[str, str] = {}  # Store trace IDs for cleanup

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

        # Use pack layout for main container - more reliable for ensuring buttons stay visible
        main_container = ttk.Frame(self.dialog)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Button frame at BOTTOM using pack - this ensures it's always visible
        button_frame = ttk.Frame(main_container)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        # Add a separator above buttons
        ttk.Separator(button_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 10))
        
        # Button container with explicit height
        btn_container = ttk.Frame(button_frame)
        btn_container.pack(fill=tk.X, pady=(0, 5))
        
        cancel_btn = ttk.Button(btn_container, text="Cancel", command=self._on_cancel, width=12)
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))
        save_btn = ttk.Button(btn_container, text="Save Item", command=self._on_save, width=14)
        save_btn.pack(side=tk.RIGHT)

        # Create notebook for wizard-style interface - fills remaining space
        notebook = ttk.Notebook(main_container)
        notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

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
        self.fields["item_type"] = tk.StringVar(value="discrete")  # discrete or measurable

        # Unit fields
        self.fields["unit_of_measure"] = tk.StringVar(value=self.existing.get("unit_of_measure", "pieces") if self.existing else "pieces")
        self.fields["package_size"] = tk.StringVar(value="1")  # How many base units per package

        # Advanced fields
        self.fields["vat_rate"] = tk.StringVar(value=str(self.existing.get("vat_rate", 16.0) if self.existing else 16.0))
        self.fields["low_stock_threshold"] = tk.StringVar(value=str(self.existing.get("low_stock_threshold", 10) if self.existing else 10))
        # Quantity only for editing existing items, not for new items
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
            self.fields["item_type"].set("measurable")
            # For measurable items, base price is price per unit
            unit_multiplier = items._get_unit_multiplier(self.existing.get("unit_of_measure", "pieces"))
            if self.existing.get("price_per_ml"):
                self.fields["base_price"].set(f"{self.existing['price_per_ml'] * unit_multiplier:.2f}")
            elif self.existing.get("selling_price_per_unit"):
                self.fields["base_price"].set(f"{self.existing['selling_price_per_unit']:.2f}")
        else:
            self.fields["item_type"].set("discrete")
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

        # Required fields note
        required_note = ttk.Label(scrollable_frame, text="* Required fields", font=("Segoe UI", 8), foreground="#666666")
        required_note.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(5, 10), padx=10)
        row += 1

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
        self.trace_ids["name"] = self.fields["name"].trace_add("write", validate_name)
        validate_name()
        row += 2

        # ...existing code for other fields...

        # Category
        ttk.Label(scrollable_frame, text="Category", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.category_combo = ttk.Combobox(scrollable_frame, textvariable=self.fields["category"], width=47, state="readonly")
        # Populate values once - categories rarely change during item editing
        self.category_combo['values'] = self._get_category_list()
        self.category_combo.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(0, 10))
        self.error_labels["category"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["category"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))
        def validate_category(*_):
            value = self.fields["category"].get().strip()
            if len(value) > 50:
                self.error_labels["category"].config(text="Max 50 characters")
            else:
                self.error_labels["category"].config(text="")
        self.trace_ids["category"] = self.fields["category"].trace_add("write", validate_category)
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
        self.trace_ids["barcode"] = self.fields["barcode"].trace_add("write", validate_barcode)
        validate_barcode()
        row += 2

        # Item Type Selection
        ttk.Label(scrollable_frame, text="Item Type *", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=(15, 5), padx=10)
        type_frame = ttk.Frame(scrollable_frame)
        type_frame.grid(row=row, column=1, sticky=tk.W, pady=(15, 5), padx=(0, 10))

        ttk.Radiobutton(type_frame, text="Discrete (sold as whole units: pieces, packs, boxes)", variable=self.fields["item_type"],
                       value="discrete", command=self._on_item_type_change).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(type_frame, text="Measurable (sold by weight/volume: kg, liters)", variable=self.fields["item_type"],
                       value="measurable", command=self._on_item_type_change).pack(side=tk.LEFT)
        row += 1

        # Unit of Measure (shown for all types)
        ttk.Label(scrollable_frame, text="Unit of Measure", font=("Segoe UI", 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.unit_combo = ttk.Combobox(scrollable_frame, textvariable=self.fields["unit_of_measure"], width=47, state="readonly")
        self.unit_combo['values'] = self._get_unit_list()
        # Units are updated by _on_item_type_change when item type changes
        self.unit_combo.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(0, 10))
        self.unit_combo.bind("<<ComboboxSelected>>", lambda e: self._on_unit_change())
        self.error_labels["unit_of_measure"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["unit_of_measure"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))

        # Manage Portions (only enabled for measurable items when editing an existing item)
        # State is set by _on_item_type_change() which is called after tabs are built
        self.manage_portions_btn = ttk.Button(scrollable_frame, text="Manage Portions...", command=self._manage_portions, width=18)
        try:
            # Place to the right of the unit combobox (column 2)
            self.manage_portions_btn.grid(row=row, column=2, sticky=tk.W, padx=(8, 0))
        except Exception:
            # If layout grid doesn't have a column 2, just pack below
            self.manage_portions_btn.grid(row=row+2, column=1, sticky=tk.W, padx=(0, 10))
        # Initial state set by _on_item_type_change() after UI is built
        def validate_unit_of_measure(*_):
            value = self.fields["unit_of_measure"].get().strip()
            if not value:
                self.error_labels["unit_of_measure"].config(text="Required")
            else:
                self.error_labels["unit_of_measure"].config(text="")
        self.trace_ids["unit_of_measure"] = self.fields["unit_of_measure"].trace_add("write", validate_unit_of_measure)
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
        self.trace_ids["package_size"] = self.fields["package_size"].trace_add("write", validate_package_size)
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
        self.trace_ids["base_price"] = self.fields["base_price"].trace_add("write", validate_base_price)
        validate_base_price()
        row += 2

        # Cost price with guidance for new items
        cost_label = ttk.Label(scrollable_frame, text="Estimated Cost Price", font=("Segoe UI", 9))
        cost_label.grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
        self.pricing_widgets.append(cost_label)
        cost_frame = ttk.Frame(scrollable_frame)
        cost_frame.grid(row=row, column=1, sticky=tk.EW, pady=5, padx=(0, 10))
        self.pricing_widgets.append(cost_frame)
        ttk.Label(cost_frame, text=f"{self.currency_symbol}", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        cost_price_entry = ttk.Entry(cost_frame, textvariable=self.fields["cost_price"], width=20, state="normal" if self.is_admin else "readonly")
        cost_price_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.fields["cost_unit_label"] = ttk.Label(cost_frame, text="(per unit)", font=("Segoe UI", 8), foreground="gray")
        self.fields["cost_unit_label"].pack(side=tk.RIGHT, padx=(10, 0))
        self.error_labels["cost_price"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        self.error_labels["cost_price"].grid(row=row+1, column=1, sticky=tk.W, padx=(0, 10))
        self.pricing_widgets.append(self.error_labels["cost_price"])
        row += 2
        
        # Cost price guidance text
        cost_info = ttk.Label(scrollable_frame,
            text="💡 Tip: Actual costs are tracked per stock lot via Stock Receiving. This is an estimated cost for profit margin display.",
            font=("Segoe UI", 8), foreground="#666666", wraplength=500)
        cost_info.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10), padx=10)
        self.pricing_widgets.append(cost_info)
        row += 1
        
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
        self.trace_ids["cost_price"] = self.fields["cost_price"].trace_add("write", validate_cost_price)
        validate_cost_price()

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
                    color = "green" if margin >= 20 else ("orange" if margin >= 0 else "red")
                    self.fields["profit_margin"].config(text=f"{margin:.1f}%", foreground=color)
                elif sell > 0:
                    self.fields["profit_margin"].config(text="--", foreground="gray")
                else:
                    self.fields["profit_margin"].config(text="--", foreground="gray")
            except ValueError:
                self.fields["profit_margin"].config(text="--", foreground="gray")

        self.trace_ids["base_price_profit"] = self.fields["base_price"].trace_add("write", update_profit_margin)
        self.trace_ids["cost_price_profit"] = self.fields["cost_price"].trace_add("write", update_profit_margin)

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

        # Ensure minimum size that fits all content including button frame
        # Add extra height for button frame and padding
        min_width = max(req_width, 850)
        min_height = max(req_height + 100, 700)  # +100 for button frame margin

        # Cap to a percentage of the screen so dialog doesn't exceed visible area
        final_width = min(min_width, int(screen_w * 0.95))
        final_height = min(min_height, int(screen_h * 0.85))

        # Center horizontally, position higher vertically (1/4 from top instead of center)
        x = (screen_w - final_width) // 2
        y = (screen_h - final_height) // 4  # Position closer to top

        # Set the dialog size and position
        self.dialog.geometry(f"{final_width}x{final_height}+{x}+{y}")
        
        # Set minimum size to prevent shrinking below usable dimensions
        self.dialog.minsize(800, 600)

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

        # For new items, show guidance about using Stock Receiving
        # For existing items, show current quantity as read-only with edit option
        if self.existing:
            # Existing item - show current quantity (read-only) with guidance
            qty_label = ttk.Label(scrollable_frame, text="Current Stock", font=("Segoe UI", 9))
            qty_label.grid(row=row, column=0, sticky=tk.W, pady=5, padx=10)
            self.quantity_widgets.append(qty_label)
            
            qty_display_frame = ttk.Frame(scrollable_frame)
            qty_display_frame.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(0, 10))
            self.quantity_widgets.append(qty_display_frame)
            
            qty_value = ttk.Label(qty_display_frame, text=str(self.existing.get("quantity", 0)), font=("Segoe UI", 9, "bold"))
            qty_value.pack(side=tk.LEFT)
            self.fields["qty_display"] = qty_value
            
            ttk.Label(qty_display_frame, text="  (Use Stock Receiving to add inventory)", font=("Segoe UI", 8), foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
            row += 1
        else:
            # New item - show info message about Stock Receiving
            info_frame = ttk.Frame(scrollable_frame)
            info_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5, padx=10)
            self.quantity_widgets.append(info_frame)
            
            ttk.Label(info_frame, text="📦", font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=(0, 5))
            info_text = ttk.Label(info_frame, 
                text="Initial stock will be 0. After saving, use Stock Receiving to add inventory with proper cost tracking.",
                font=("Segoe UI", 9), foreground="#666666", wraplength=450)
            info_text.pack(side=tk.LEFT)
            row += 1

        # Hidden quantity field for internal use (always 0 for new items)
        self.fields["quantity"].set("0" if not self.existing else str(self.existing.get("quantity", 0)))
        self.error_labels["quantity"] = ttk.Label(scrollable_frame, text="", foreground="red", font=("Segoe UI", 8))
        # Don't grid the error label, keep it hidden
        row += 1

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
        self.trace_ids["low_stock_threshold"] = self.fields["low_stock_threshold"].trace_add("write", validate_low_stock)
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
        self.trace_ids["vat_rate"] = self.fields["vat_rate"].trace_add("write", validate_vat_rate)
        validate_vat_rate()
        row += 2

        # Configure grid weights
        scrollable_frame.columnconfigure(1, weight=1)

    def _on_item_type_change(self) -> None:
        """Handle item type changes to show/hide relevant fields."""
        item_type = self.fields["item_type"].get()

        # Enable/disable Manage Portions button: enabled for measurable items (even new ones)
        # If clicked on a new item, _manage_portions() will show a "save first" message
        if hasattr(self, 'manage_portions_btn'):
            if item_type == 'measurable':
                self.manage_portions_btn.config(state='normal')
            else:
                self.manage_portions_btn.config(state='disabled')

        # Update unit of measure list based on item type
        if hasattr(self, 'unit_combo'):
            new_units = self._get_unit_list()
            self.unit_combo['values'] = new_units
            current_unit = self.fields["unit_of_measure"].get()
            # If current unit is not valid for this item type, reset to first option
            if current_unit not in new_units and new_units:
                self.fields["unit_of_measure"].set(new_units[0])
                self._on_unit_change()

        if item_type == "discrete":
            # Discrete items: hide package size, price per unit
            if "package_size_label" in self.fields:
                self.fields["package_size_label"].grid_remove()
            if "package_size_entry" in self.fields:
                self.fields["package_size_entry"].grid_remove()
            if "package_size" in self.error_labels:
                self.error_labels["package_size"].grid_remove()
            if "price_unit_label" in self.fields:
                self.fields["price_unit_label"].config(text="(per unit)")
            if "cost_unit_label" in self.fields:
                self.fields["cost_unit_label"].config(text="(per unit)")

        elif item_type == "measurable":
            # Measurable items: show package size, price per base unit
            if "package_size_label" in self.fields:
                self.fields["package_size_label"].grid()
            if "package_size_entry" in self.fields:
                self.fields["package_size_entry"].grid()
            if "package_size" in self.error_labels:
                self.error_labels["package_size"].grid()
            unit = self.fields["unit_of_measure"].get().lower()
            if "liter" in unit or "l" == unit or "litre" in unit:
                if "price_unit_label" in self.fields:
                    self.fields["price_unit_label"].config(text="(per liter)")
                if "cost_unit_label" in self.fields:
                    self.fields["cost_unit_label"].config(text="(per liter)")
            elif "kilo" in unit or "kg" in unit:
                if "price_unit_label" in self.fields:
                    self.fields["price_unit_label"].config(text="(per kg)")
                if "cost_unit_label" in self.fields:
                    self.fields["cost_unit_label"].config(text="(per kg)")
            elif "meter" in unit or "m" == unit or "metre" in unit:
                if "price_unit_label" in self.fields:
                    self.fields["price_unit_label"].config(text="(per meter)")
                if "cost_unit_label" in self.fields:
                    self.fields["cost_unit_label"].config(text="(per meter)")
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
        if item_type == "measurable":
            if "liter" in unit or "l" == unit or "litre" in unit:
                if not self.fields["package_size"].get() or self.fields["package_size"].get() == "1":
                    self.fields["package_size"].set("1000")  # 1000ml per liter
            elif "kilo" in unit or "kg" in unit:
                if not self.fields["package_size"].get() or self.fields["package_size"].get() == "1":
                    self.fields["package_size"].set("1000")  # 1000g per kg
            elif "meter" in unit or "m" == unit or "metre" in unit:
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

        # Get current unit of measure from the dialog (not from database)
        current_unit = self.fields["unit_of_measure"].get() if "unit_of_measure" in self.fields else None
        
        # Open management dialog with current unit
        ManagePortionsDialog(self.parent, self.existing['item_id'], unit_of_measure=current_unit)

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
            self._cleanup_traces()
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

        # Validate name is not a duplicate (for new items or name changes)
        name = self.fields["name"].get().strip()
        if name:
            existing_items = items.list_items(search=name)
            for existing_item in existing_items:
                if existing_item.get("name", "").lower() == name.lower():
                    # Allow if it's the same item being edited
                    if self.existing and existing_item.get("item_id") == self.existing.get("item_id"):
                        continue
                    raise ValidationError(f"An item with name '{name}' already exists")

        # Base data
        data = {
            "name": name,
            "category": self.fields["category"].get().strip() or None,
            "barcode": self.fields["barcode"].get().strip() or None,
            "image_path": self.fields["image_path"].get().strip() or None,
            "unit_of_measure": unit,
            "vat_rate": validate_numeric(self.fields["vat_rate"].get(), 0, 100),
            "low_stock_threshold": validate_integer(self.fields["low_stock_threshold"].get(), 0),
            "has_variants": 1 if has_variants else 0,
        }

        # Quantity handling: 
        # - For new items without variants: always 0 (use Stock Receiving)
        # - For existing items: keep current quantity
        # - For items with variants: always 0
        if has_variants:
            data["quantity"] = 0
        elif self.existing:
            data["quantity"] = self.existing.get("quantity", 0)  # Keep existing quantity
        else:
            data["quantity"] = 0  # New items start at 0

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

            # Warn if cost > selling (but don't block - it might be intentional for promos)
            if cost_price > 0 and base_price > 0 and base_price < cost_price:
                if not messagebox.askyesno(
                    "Low Margin Warning",
                    f"Selling price ({base_price:.2f}) is less than cost price ({cost_price:.2f}).\n\n"
                    "This will result in a loss on each sale. Continue anyway?"
                ):
                    raise ValidationError("Cancelled due to pricing concern")

            if item_type == "discrete":
                # Discrete items: price per unit, no special volume
                data.update({
                    "selling_price": base_price,
                    "cost_price": cost_price,
                    "is_special_volume": 0,
                    "unit_size_ml": 1,
                    "price_per_ml": None,
                    "selling_price_per_unit": None,
                    "cost_price_per_unit": None,
                })

            elif item_type == "measurable":
                # Measurable items: price per base unit, enable special volume
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
            # Refresh category combobox directly if we have a reference to it
            if hasattr(self, 'category_combo'):
                self.category_combo['values'] = self._get_category_list()
        except Exception:
            pass

    def _get_category_list(self) -> list:
        """Get list of existing categories for the combobox."""
        try:
            categories = items.get_categories()
            return sorted(categories)
        except:
            return []

    def _get_unit_list(self) -> list:
        """Get list of units of measure appropriate for the current item type."""
        item_type = self.fields["item_type"].get() if "item_type" in self.fields else "discrete"
        
        # Default units as fallback
        discrete_defaults = ["piece", "unit", "pack", "box", "bottle", "can", "bag", "carton", "dozen", "pair", "set", "roll", "bundle"]
        measurable_defaults = ["kg", "g", "liter", "ml", "meter", "cm", "lb", "oz", "gallon", "quart", "pint", "yard", "foot", "inch"]
        
        # Try to get units from database using helper functions
        try:
            from modules import units_of_measure
            if item_type == "measurable":
                db_units = units_of_measure.get_measurable_units()
            else:
                db_units = units_of_measure.get_discrete_units()
            
            if db_units:
                return sorted(db_units, key=str.lower)
        except:
            pass
        
        # Fallback to defaults
        base_units = measurable_defaults if item_type == "measurable" else discrete_defaults
        return sorted(base_units, key=str.lower)

    def _on_category_focus(self, event=None) -> None:
        """Handle category combobox focus - refresh category list."""
        if hasattr(self, 'category_combo'):
            self.category_combo['values'] = self._get_category_list()

    def _on_unit_focus(self, event=None) -> None:
        """Handle unit combobox focus - refresh unit list based on item type."""
        if hasattr(self, 'unit_combo'):
            self.unit_combo['values'] = self._get_unit_list()

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

    def _cleanup_traces(self) -> None:
        """Remove all trace variables to prevent tkinter command deletion errors."""
        for field_name, trace_id in self.trace_ids.items():
            if trace_id and field_name in self.fields:
                try:
                    self.fields[field_name].trace_remove("write", trace_id)
                except (tk.TclError, KeyError):
                    # Trace might already be removed or field might not exist
                    pass
        self.trace_ids.clear()

    def _on_cancel(self) -> None:
        """Handle cancel button."""
        self._cleanup_traces()
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


class ManagePortionsDialog:
    """Modal dialog to manage preset portions for a measurable item."""

    def __init__(self, parent: tk.Misc, item_id: int, unit_of_measure: str = None):
        self.parent = parent
        self.item_id = item_id
        self.unit_of_measure = unit_of_measure
        self.top = tk.Toplevel(parent)
        self.top.title("Manage Portions")
        set_window_icon(self.top)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.columnconfigure(0, weight=1)
        self.top.rowconfigure(0, weight=1)
        
        # Get unit info for this item - use provided unit or fetch from database
        from modules import portions
        if unit_of_measure:
            self.unit_info = self._get_unit_info_from_name(unit_of_measure)
        else:
            self.unit_info = portions.get_unit_info(item_id)
        self.small_unit = self.unit_info.get("small_unit", "unit")

        # Treeview for portions
        cols = ("portion_name", "portion_amount", "selling_price", "cost_price", "is_active")
        self.tree = ttk.Treeview(self.top, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("portion_name", text="Name")
        self.tree.heading("portion_amount", text=f"Amount ({self.small_unit})")
        self.tree.heading("selling_price", text="Price")
        self.tree.heading("cost_price", text="Cost")
        self.tree.heading("is_active", text="Active")
        self.tree.column("portion_name", width=200)
        self.tree.column("portion_amount", width=100, anchor=tk.CENTER)
        self.tree.column("selling_price", width=100, anchor=tk.E)
        self.tree.column("cost_price", width=100, anchor=tk.E)
        self.tree.column("is_active", width=60, anchor=tk.CENTER)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW, padx=10, pady=(10, 0))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.top, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky=tk.NS, pady=(10, 0))
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Buttons
        btn_frame = ttk.Frame(self.top)
        btn_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=10)
        ttk.Button(btn_frame, text="Add", command=self._add).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Edit", command=self._edit).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Toggle Active", command=self._toggle_active).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Create Defaults", command=self._create_defaults).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Close", command=self.top.destroy).pack(side=tk.RIGHT)

        # Set minimum size
        self.top.update_idletasks()
        self.top.minsize(600, 300)
        
        self._refresh()

    def _get_unit_info_from_name(self, unit_name: str) -> dict:
        """Get unit info from a unit name string."""
        unit = (unit_name or "").lower()
        
        # Volume units
        if unit in ("liters", "litre", "liter", "litres", "l"):
            return {"small_unit": "ml", "base_unit": "L", "multiplier": 1000}
        # Weight units - metric
        elif unit in ("kilograms", "kilogram", "kg", "kgs"):
            return {"small_unit": "g", "base_unit": "kg", "multiplier": 1000}
        elif unit in ("g", "gram", "grams"):
            return {"small_unit": "g", "base_unit": "g", "multiplier": 1}
        # Length units - metric
        elif unit in ("meters", "meter", "metre", "metres", "m"):
            return {"small_unit": "cm", "base_unit": "m", "multiplier": 100}
        elif unit in ("cm", "centimeter", "centimeters", "centimetres"):
            return {"small_unit": "cm", "base_unit": "cm", "multiplier": 1}
        # Pounds
        elif unit in ("lb", "lbs", "pound", "pounds"):
            return {"small_unit": "oz", "base_unit": "lb", "multiplier": 16}
        # Ounces
        elif unit in ("oz", "ounce", "ounces"):
            return {"small_unit": "oz", "base_unit": "oz", "multiplier": 1}
        # Gallons
        elif unit in ("gallon", "gallons", "gal"):
            return {"small_unit": "fl oz", "base_unit": "gal", "multiplier": 128}
        # Milliliters
        elif unit in ("ml", "milliliter", "milliliters", "millilitres"):
            return {"small_unit": "ml", "base_unit": "ml", "multiplier": 1}
        else:
            # Default for unknown units
            return {"small_unit": unit, "base_unit": unit, "multiplier": 1}

    def _refresh(self) -> None:
        """Reload portions list."""
        for i in self.tree.get_children():
            self.tree.delete(i)
        from modules import portions
        rows = portions.list_portions(self.item_id, active_only=False)
        for r in rows:
            amount = r.get("portion_amount", r.get("portion_ml", 0))
            self.tree.insert("", tk.END, iid=str(r["portion_id"]), values=(
                r["portion_name"], 
                f"{amount:.0f}" if amount == int(amount) else f"{amount:.2f}",
                f"{r['selling_price']:.2f}", 
                f"{r['cost_price']:.2f}", 
                "Yes" if r["is_active"] else "No"
            ))
    
    def _toggle_active(self) -> None:
        """Toggle active status of selected portion."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Portion", "Please select a portion to toggle")
            return
        pid = int(sel[0])
        from modules import portions
        data = portions.get_portion(pid)
        if data:
            new_active = 0 if data["is_active"] else 1
            portions.update_portion(pid, is_active=new_active)
            self._refresh()

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
        row = 0
        
        ttk.Label(top, text="Name:").grid(row=row, column=0, sticky=tk.W, padx=8, pady=6)
        fields["name"] = tk.StringVar(value=data["portion_name"] if data else "")
        ttk.Entry(top, textvariable=fields["name"], width=40).grid(row=row, column=1, padx=8, pady=6)
        row += 1

        ttk.Label(top, text=f"Amount ({self.small_unit}):").grid(row=row, column=0, sticky=tk.W, padx=8, pady=6)
        amount_val = data.get("portion_amount", data.get("portion_ml", 0)) if data else 0
        fields["amount"] = tk.StringVar(value=str(amount_val) if amount_val else "0")
        ttk.Entry(top, textvariable=fields["amount"], width=20).grid(row=row, column=1, padx=8, pady=6, sticky=tk.W)
        row += 1

        ttk.Label(top, text="Price:").grid(row=row, column=0, sticky=tk.W, padx=8, pady=6)
        fields["price"] = tk.StringVar(value=f"{data['selling_price']:.2f}" if data else "0.00")
        ttk.Entry(top, textvariable=fields["price"], width=20).grid(row=row, column=1, padx=8, pady=6, sticky=tk.W)
        row += 1

        ttk.Label(top, text="Cost:").grid(row=row, column=0, sticky=tk.W, padx=8, pady=6)
        fields["cost"] = tk.StringVar(value=f"{data['cost_price']:.2f}" if data else "0.00")
        ttk.Entry(top, textvariable=fields["cost"], width=20).grid(row=row, column=1, padx=8, pady=6, sticky=tk.W)
        row += 1

        active_var = tk.BooleanVar(value=(data["is_active"] if data else True))
        ttk.Checkbutton(top, text="Active", variable=active_var).grid(row=row, column=1, sticky=tk.W, padx=8, pady=6)
        row += 1

        def save():
            try:
                name = fields["name"].get().strip()
                if not name:
                    messagebox.showerror("Error", "Name is required")
                    return
                amount = float(fields["amount"].get() or 0)
                if amount <= 0:
                    messagebox.showerror("Error", f"Amount must be greater than 0 {self.small_unit}")
                    return
                price = float(fields["price"].get() or 0)
                cost = float(fields["cost"].get() or 0)
                active = 1 if active_var.get() else 0
                from modules import portions
                if create:
                    portions.create_portion(self.item_id, name, amount, price, cost_price=cost)
                else:
                    portions.update_portion(pid, portion_name=name, portion_amount=amount, selling_price=price, cost_price=cost, is_active=active)
                top.destroy()
                self._refresh()
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid number format: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save portion: {e}")

        btn_frame = ttk.Frame(top)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=save, width=12).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Cancel", command=top.destroy, width=12).pack(side=tk.LEFT, padx=4)
        
        # Center the dialog
        top.update_idletasks()
        top.geometry(f"+{self.top.winfo_x() + 50}+{self.top.winfo_y() + 50}")

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
        """Create default portions based on item's unit of measure."""
        try:
            # Confirm with user
            unit_info = self.unit_info
            base_unit = unit_info.get("base_unit", "unit")
            small_unit = unit_info.get("small_unit", "unit")
            if not messagebox.askyesno(
                "Create Default Portions",
                f"This will create default portion presets for this item based on its unit ({base_unit}).\n\n"
                f"Portions will be created in {small_unit}.\n\n"
                "Existing portions will NOT be modified.\n\nContinue?"
            ):
                return
            
            from modules import portions
            # Pass the unit_of_measure if we have it, so create_default_portions uses the correct unit
            created = portions.create_default_portions(self.item_id, unit_of_measure=self.unit_of_measure)
            
            if created:
                messagebox.showinfo("Success", f"Created {len(created)} default portions")
            else:
                messagebox.showinfo("Info", "No new portions created (defaults may already exist)")
            
            self._refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create default portions: {e}")