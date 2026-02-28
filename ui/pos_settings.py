import tkinter as tk
from tkinter import ttk, messagebox
from database.init_db import get_setting, set_setting
from utils.security import (
    get_cart_vat_enabled, set_cart_vat_enabled,
    get_cart_discount_enabled, set_cart_discount_enabled,
    get_cart_suspend_enabled, set_cart_suspend_enabled,
    get_payment_methods, set_payment_methods,
    set_vat_rate, get_vat_rate, set_max_discount_percent,
    set_cart_auto_calculate_enabled, set_cart_show_images_enabled, set_cart_allow_negative_qty, set_cart_max_items
)

class POSSettingsFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self._build_ui()

    def _build_ui(self):
        # Create a scrollable container so the entire POS settings page can be scrolled
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
        v_scroll = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=v_scroll.set)
        canvas.grid(row=0, column=0, sticky=tk.NSEW)
        v_scroll.grid(row=0, column=1, sticky=tk.NS)

        # Frame inside canvas to hold the actual settings controls
        content = ttk.Frame(canvas)
        self._content = content
        window_id = canvas.create_window((0, 0), window=content, anchor='nw')

        def _on_content_config(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        content.bind("<Configure>", _on_content_config)

        def _on_canvas_config(event):
            # Keep inner frame width in sync with canvas width
            try:
                canvas.itemconfig(window_id, width=event.width)
            except Exception:
                pass
        canvas.bind("<Configure>", _on_canvas_config)

        # Mouse wheel scrolling (Windows / macOS / X11)
        def _on_mouse_wheel(event):
            """Handle mouse wheel scrolling for the settings canvas.

            This is defensive: the canvas may be destroyed while the global
            bindings are still active, so catch TclError and remove bindings
            when that happens.
            """
            try:
                # Map legacy X11 button events
                if getattr(event, 'num', None) == 4:
                    canvas.yview_scroll(-1, "units")
                elif getattr(event, 'num', None) == 5:
                    canvas.yview_scroll(1, "units")
                else:
                    # For Windows and macOS delta will be multiple of 120
                    canvas.yview_scroll(-int(event.delta / 120), "units")
            except tk.TclError:
                # Underlying canvas widget no longer exists; unbind global handlers
                try:
                    canvas.unbind_all("<MouseWheel>")
                    canvas.unbind_all("<Button-4>")
                    canvas.unbind_all("<Button-5>")
                except Exception:
                    pass
                return

        # Bind mouse wheel to canvas (use bind, not bind_all, to limit scope),
        # but keep a global fallback for child widgets
        try:
            canvas.bind("<MouseWheel>", _on_mouse_wheel)
            canvas.bind("<Button-4>", _on_mouse_wheel)
            canvas.bind("<Button-5>", _on_mouse_wheel)
        except Exception:
            # Fall back to bind_all if bind fails for some reason
            try:
                canvas.bind_all("<MouseWheel>", _on_mouse_wheel)
                canvas.bind_all("<Button-4>", _on_mouse_wheel)
                canvas.bind_all("<Button-5>", _on_mouse_wheel)
            except Exception:
                pass

        # Header label
        ttk.Label(self._content, text="Configure POS behavior and display settings:").pack(pady=(0, 16))

        # Display settings
        display_group = ttk.LabelFrame(self._content, text="Display Settings", padding=10)
        display_group.pack(fill=tk.X, pady=(0, 10))

        self.fullscreen_var = tk.BooleanVar()
        ttk.Checkbutton(display_group, text="Start in fullscreen mode",
                       variable=self.fullscreen_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.touchscreen_var = tk.BooleanVar()
        ttk.Checkbutton(display_group, text="Optimize for touchscreen",
                       variable=self.touchscreen_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)

        ttk.Label(display_group, text="Default item view:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.item_view_var = tk.StringVar()
        self.item_view_combo = ttk.Combobox(display_group, textvariable=self.item_view_var,
                                          values=["Grid View", "List View", "Category View"],
                                          state="readonly", width=15)
        self.item_view_combo.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        # Transaction settings
        transaction_group = ttk.LabelFrame(self._content, text="Transaction Settings", padding=10)
        transaction_group.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(transaction_group, text="Auto-logout after (minutes):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.auto_logout_var = tk.StringVar()
        self.auto_logout_spin = ttk.Spinbox(transaction_group, from_=5, to=480, textvariable=self.auto_logout_var, width=10)
        self.auto_logout_spin.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        self.confirm_large_transactions_var = tk.BooleanVar()
        ttk.Checkbutton(transaction_group, text="Confirm transactions over",
                       variable=self.confirm_large_transactions_var).grid(row=1, column=0, sticky=tk.W, pady=2)

        self.large_transaction_threshold_var = tk.StringVar()
        self.threshold_spin = ttk.Spinbox(transaction_group, from_=100, to=10000,
                                        textvariable=self.large_transaction_threshold_var, width=10)
        self.threshold_spin.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        # Input settings
        input_group = ttk.LabelFrame(self._content, text="Input Settings", padding=10)
        input_group.pack(fill=tk.X, pady=(0, 10))

        self.barcode_scanner_var = tk.BooleanVar()
        ttk.Checkbutton(input_group, text="Enable barcode scanner input",
                       variable=self.barcode_scanner_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.numeric_keypad_var = tk.BooleanVar()
        ttk.Checkbutton(input_group, text="Show numeric keypad for quantity input",
                       variable=self.numeric_keypad_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)

        # Sound settings
        sound_group = ttk.LabelFrame(self._content, text="Sound Settings", padding=10)
        sound_group.pack(fill=tk.X, pady=(0, 10))

        self.transaction_sound_var = tk.BooleanVar()
        ttk.Checkbutton(sound_group, text="Play sound on transaction completion",
                       variable=self.transaction_sound_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.error_sound_var = tk.BooleanVar()
        ttk.Checkbutton(sound_group, text="Play sound on errors",
                       variable=self.error_sound_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)

        # Cart management settings
        cart_group = ttk.LabelFrame(self._content, text="Cart Management Settings", padding=10)
        cart_group.pack(fill=tk.X, pady=(0, 10))

        # VAT settings
        self.vat_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(cart_group, text="Enable VAT calculation on cart items",
                       variable=self.vat_enabled_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
        # Apply immediately when toggled (use trace compatible with older Tkinter)
        self.vat_enabled_var.trace('w', lambda *a: (print(f"VAT checkbox toggled -> {self.vat_enabled_var.get()}"), set_cart_vat_enabled(self.vat_enabled_var.get())))

        ttk.Label(cart_group, text="Default VAT rate (%):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.vat_rate_var = tk.StringVar()
        self.vat_rate_spin = ttk.Spinbox(cart_group, from_=0, to=50, increment=0.1,
                                       textvariable=self.vat_rate_var, width=12)
        self.vat_rate_spin.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        # Apply VAT rate immediately on change
        def _apply_vat_rate(_=None):
            try:
                set_vat_rate(float(self.vat_rate_var.get() or get_vat_rate()))
            except Exception:
                pass
        self.vat_rate_spin.bind('<FocusOut>', _apply_vat_rate)
        self.vat_rate_spin.bind('<Return>', _apply_vat_rate)

        # Discount settings
        self.discount_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(cart_group, text="Enable discount functionality",
                       variable=self.discount_enabled_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
        # Apply immediately when toggled (use trace compatible with older Tkinter)
        self.discount_enabled_var.trace('w', lambda *a: (print(f"Discount checkbox toggled -> {self.discount_enabled_var.get()}"), set_cart_discount_enabled(self.discount_enabled_var.get())))

        ttk.Label(cart_group, text="Maximum discount (%):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.max_discount_var = tk.StringVar()
        self.max_discount_spin = ttk.Spinbox(cart_group, from_=0, to=100,
                                           textvariable=self.max_discount_var, width=12)
        self.max_discount_spin.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        def _apply_max_discount(_=None):
            try:
                set_max_discount_percent(float(self.max_discount_var.get() or 50.0))
            except Exception:
                pass
        self.max_discount_spin.bind('<FocusOut>', _apply_max_discount)
        self.max_discount_spin.bind('<Return>', _apply_max_discount)

        # Cart suspend/resume
        self.suspend_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(cart_group, text="Enable cart suspend/resume functionality",
                       variable=self.suspend_enabled_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=2)
        # Use trace for compatibility
        self.suspend_enabled_var.trace('w', lambda *a: (print(f"Suspend checkbox toggled -> {self.suspend_enabled_var.get()}"), set_cart_suspend_enabled(self.suspend_enabled_var.get())))

        # Payment methods management
        payment_group = ttk.LabelFrame(self._content, text="Payment Methods Management", padding=10)
        payment_group.pack(fill=tk.X, pady=(0, 10))

        # Current payment methods list
        ttk.Label(payment_group, text="Current Payment Methods:").grid(row=0, column=0, sticky=tk.W, pady=2)
        # Scrollable listbox for payment methods
        pl_frame = ttk.Frame(payment_group)
        pl_frame.grid(row=1, column=0, rowspan=3, sticky=tk.NSEW, padx=(0, 10), pady=2)
        pl_frame.columnconfigure(0, weight=1)
        pl_frame.rowconfigure(0, weight=1)

        self.payment_listbox = tk.Listbox(pl_frame, height=6, width=30, selectmode=tk.SINGLE, exportselection=False)
        self.payment_listbox.grid(row=0, column=0, sticky=tk.NSEW)

        v_scroll_pm = ttk.Scrollbar(pl_frame, orient=tk.VERTICAL, command=self.payment_listbox.yview)
        h_scroll_pm = ttk.Scrollbar(pl_frame, orient=tk.HORIZONTAL, command=self.payment_listbox.xview)
        self.payment_listbox.configure(yscrollcommand=v_scroll_pm.set, xscrollcommand=h_scroll_pm.set)
        v_scroll_pm.grid(row=0, column=1, sticky=tk.NS)
        h_scroll_pm.grid(row=1, column=0, columnspan=2, sticky=tk.EW)

        # Payment method controls
        ttk.Label(payment_group, text="Add/Remove Methods:").grid(row=0, column=1, sticky=tk.W, pady=2)
        self.new_payment_var = tk.StringVar()
        payment_entry = ttk.Entry(payment_group, textvariable=self.new_payment_var, width=20)
        payment_entry.grid(row=1, column=1, sticky=tk.W, pady=2)

        button_frame = ttk.Frame(payment_group)
        button_frame.grid(row=2, column=1, sticky=tk.W, pady=2)
        ttk.Button(button_frame, text="Add", width=8, command=self._add_payment_method).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Remove Selected", width=12, command=self._remove_payment_method).pack(side=tk.LEFT)

        # Cart behavior settings
        behavior_group = ttk.LabelFrame(self._content, text="Cart Behavior Settings", padding=10)
        behavior_group.pack(fill=tk.X, pady=(0, 10))

        self.auto_calculate_var = tk.BooleanVar()
        ttk.Checkbutton(behavior_group, text="Auto-calculate totals as items are added",
                       variable=self.auto_calculate_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
        # Use trace for compatibility
        self.auto_calculate_var.trace('w', lambda *a: set_cart_auto_calculate_enabled(self.auto_calculate_var.get()))

        self.show_item_images_var = tk.BooleanVar()
        ttk.Checkbutton(behavior_group, text="Show item images in cart",
                       variable=self.show_item_images_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        # Use trace for compatibility
        self.show_item_images_var.trace('w', lambda *a: set_cart_show_images_enabled(self.show_item_images_var.get()))

        self.allow_negative_qty_var = tk.BooleanVar()
        ttk.Checkbutton(behavior_group, text="Allow negative quantities (for returns)",
                       variable=self.allow_negative_qty_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
        # Use trace for compatibility
        self.allow_negative_qty_var.trace('w', lambda *a: set_cart_allow_negative_qty(self.allow_negative_qty_var.get()))

        ttk.Label(behavior_group, text="Maximum cart items:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.max_cart_items_var = tk.StringVar()
        self.max_cart_spin = ttk.Spinbox(behavior_group, from_=10, to=1000, increment=10,
                                       textvariable=self.max_cart_items_var, width=12)
        self.max_cart_spin.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        def _apply_max_items(_=None):
            try:
                set_cart_max_items(int(self.max_cart_items_var.get() or 100))
            except Exception:
                pass
        self.max_cart_spin.bind('<FocusOut>', _apply_max_items)
        self.max_cart_spin.bind('<Return>', _apply_max_items)

        ttk.Button(self._content, text="Save POS Settings", command=self.save_settings).pack(pady=16)

        self.load_settings()

    def load_settings(self):
        """Load current POS settings."""
        self.fullscreen_var.set(get_setting('pos_fullscreen') == 'true')
        self.touchscreen_var.set(get_setting('pos_touchscreen') == 'true')
        self.item_view_var.set(get_setting('pos_item_view') or "Grid View")

        auto_logout = get_setting('pos_auto_logout')
        self.auto_logout_var.set(auto_logout or "30")

        self.confirm_large_transactions_var.set(get_setting('pos_confirm_large') == 'true')
        threshold = get_setting('pos_large_threshold')
        self.large_transaction_threshold_var.set(threshold or "1000")

        self.barcode_scanner_var.set(get_setting('pos_barcode_scanner') == 'true')
        self.numeric_keypad_var.set(get_setting('pos_numeric_keypad') == 'true')
        self.transaction_sound_var.set(get_setting('pos_transaction_sound') != 'false')  # Default true
        self.error_sound_var.set(get_setting('pos_error_sound') != 'false')  # Default true

        # Cart management settings
        self.vat_enabled_var.set(get_cart_vat_enabled())
        vat_rate = get_setting('vat_rate')
        self.vat_rate_var.set(vat_rate or "16.0")

        self.discount_enabled_var.set(get_cart_discount_enabled())
        max_discount = get_setting('max_discount_percent')
        self.max_discount_var.set(max_discount or "50")

        self.suspend_enabled_var.set(get_cart_suspend_enabled())

        # Payment methods
        self._refresh_payment_methods()

        # Cart behavior settings
        self.auto_calculate_var.set(get_setting('cart_auto_calculate') != 'false')  # Default true
        self.show_item_images_var.set(get_setting('cart_show_images') != 'false')  # Default true
        self.allow_negative_qty_var.set(get_setting('cart_allow_negative_qty') == 'true')
        max_items = get_setting('cart_max_items')
        self.max_cart_items_var.set(max_items or "100")

    def refresh(self):
        """Reload POS settings from database."""
        self.load_settings()

    def save_settings(self):
        """Save POS settings."""
        try:
            set_setting('pos_fullscreen', 'true' if self.fullscreen_var.get() else 'false')
            set_setting('pos_touchscreen', 'true' if self.touchscreen_var.get() else 'false')
            set_setting('pos_item_view', self.item_view_var.get())
            set_setting('pos_auto_logout', self.auto_logout_var.get())
            set_setting('pos_confirm_large', 'true' if self.confirm_large_transactions_var.get() else 'false')
            set_setting('pos_large_threshold', self.large_transaction_threshold_var.get())
            set_setting('pos_barcode_scanner', 'true' if self.barcode_scanner_var.get() else 'false')
            set_setting('pos_numeric_keypad', 'true' if self.numeric_keypad_var.get() else 'false')
            set_setting('pos_transaction_sound', 'true' if self.transaction_sound_var.get() else 'false')
            set_setting('pos_error_sound', 'true' if self.error_sound_var.get() else 'false')

            # Cart management settings (use setters that notify)
            set_cart_vat_enabled(self.vat_enabled_var.get())
            try:
                set_vat_rate(float(self.vat_rate_var.get()))
            except Exception:
                pass
            set_cart_discount_enabled(self.discount_enabled_var.get())
            try:
                set_max_discount_percent(float(self.max_discount_var.get()))
            except Exception:
                pass
            set_cart_suspend_enabled(self.suspend_enabled_var.get())

            # Cart behavior settings
            set_cart_auto_calculate_enabled(self.auto_calculate_var.get())
            set_cart_show_images_enabled(self.show_item_images_var.get())
            set_cart_allow_negative_qty(self.allow_negative_qty_var.get())
            try:
                set_cart_max_items(int(self.max_cart_items_var.get()))
            except Exception:
                pass

            messagebox.showinfo("Success", "POS settings saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def _refresh_payment_methods(self):
        """Refresh the payment methods listbox."""
        self.payment_listbox.delete(0, tk.END)
        methods = get_payment_methods()
        for method in methods:
            self.payment_listbox.insert(tk.END, method)

    def _add_payment_method(self):
        """Add a new payment method."""
        new_method = self.new_payment_var.get().strip()
        if not new_method:
            messagebox.showwarning("Warning", "Please enter a payment method name.")
            return

        current_methods = get_payment_methods()
        if new_method in current_methods:
            messagebox.showwarning("Warning", f"Payment method '{new_method}' already exists.")
            return

        current_methods.append(new_method)
        set_payment_methods(current_methods)
        self._refresh_payment_methods()
        self.new_payment_var.set("")
        messagebox.showinfo("Success", f"Payment method '{new_method}' added successfully!")

    def _remove_payment_method(self):
        """Remove the selected payment method."""
        selection = self.payment_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a payment method to remove.")
            return

        method_to_remove = self.payment_listbox.get(selection[0])

        # Prevent removing default methods that might be critical
        default_methods = ["Cash", "Card", "M-Pesa"]
        if method_to_remove in default_methods:
            messagebox.showwarning("Warning", f"Cannot remove default payment method '{method_to_remove}'.")
            return

        current_methods = get_payment_methods()
        if method_to_remove not in current_methods:
            messagebox.showwarning("Warning", f"Payment method '{method_to_remove}' not found.")
            return

        # Confirm removal
        if not messagebox.askyesno("Confirm", f"Are you sure you want to remove payment method '{method_to_remove}'?"):
            return

        current_methods.remove(method_to_remove)
        set_payment_methods(current_methods)
        self._refresh_payment_methods()
        messagebox.showinfo("Success", f"Payment method '{method_to_remove}' removed successfully!")