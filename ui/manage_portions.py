#!/usr/bin/env python3
"""
Portions Management Dialog for preset fractional quantities.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any
import logging

from modules import portions, items
from modules.inventory_costing import get_effective_selling_price
from utils.i18n import get_currency_symbol
from utils import set_window_icon

logger = logging.getLogger(__name__)


class ManagePortionsDialog:
    """Dialog for managing preset portions for an item."""

    def __init__(self, parent: tk.Widget, item_id: int, unit_of_measure: Optional[str] = None):
        self.parent = parent
        self.item_id = item_id
        self.unit_of_measure = unit_of_measure or "pieces"
        self.currency_symbol = get_currency_symbol()

        # Get item info
        self.item = items.get_item(item_id)
        if not self.item:
            messagebox.showerror("Error", "Item not found")
            return

        # Get unit info
        self.unit_info = portions.get_unit_info_from_name(self.unit_of_measure)
        self.small_unit = self.unit_info["small_unit"]
        self.base_unit = self.unit_info["base_unit"]
        self.multiplier = self.unit_info["multiplier"]

        # Get current effective price
        try:
            self.effective_price, _, _ = get_effective_selling_price(item_id)
        except Exception:
            self.effective_price = float(self.item.get("selling_price") or 0)

        self.price_per_base = self.effective_price / float(self.item.get("unit_size_ml") or 1) if float(self.item.get("unit_size_ml") or 1) > 0 else self.effective_price
        self.price_per_small = self.price_per_base / self.multiplier if self.multiplier > 0 else self.price_per_base

        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create the portions management dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.withdraw()  # Hide until fully built
        self.dialog.title(f"Manage Portions - {self.item['name']}")
        set_window_icon(self.dialog)
        self.dialog.transient(self.parent.winfo_toplevel())
        self.dialog.grab_set()
        self.dialog.resizable(True, True)

        main_frame = ttk.Frame(self.dialog, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header info
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(header_frame, text=f"Item: {self.item['name']}", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(header_frame, text=f"Unit: {self.unit_of_measure} ({self.small_unit})").pack(anchor=tk.W)
        ttk.Label(header_frame, text=f"Price per {self.base_unit}: {self.currency_symbol} {self.price_per_base:.2f}").pack(anchor=tk.W)
        ttk.Label(header_frame, text=f"Price per {self.small_unit}: {self.currency_symbol} {self.price_per_small:.4f}").pack(anchor=tk.W)

        # Portions list
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        # Treeview for portions
        columns = ("name", "amount", "selling_price", "cost_price", "lot", "active")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)

        self.tree.heading("name", text="Portion Name")
        self.tree.heading("amount", text=f"Amount ({self.small_unit})")
        self.tree.heading("selling_price", text="Selling Price")
        self.tree.heading("cost_price", text="Cost Price")
        self.tree.heading("lot", text="Based on Lot")
        self.tree.heading("active", text="Active")

        # Set column widths to avoid excessive horizontal scrolling
        self.tree.column("name", width=140, minwidth=100, anchor=tk.W)
        self.tree.column("amount", width=80, minwidth=70, anchor=tk.E)
        self.tree.column("selling_price", width=90, minwidth=70, anchor=tk.E)
        self.tree.column("cost_price", width=90, minwidth=70, anchor=tk.E)
        self.tree.column("lot", width=110, minwidth=90, anchor=tk.W)
        self.tree.column("active", width=60, minwidth=50, anchor=tk.CENTER)

        # Scrollbars (use grid layout to prevent incorrect positioning)
        v_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=v_scroll.set, xscroll=h_scroll.set)

        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        v_scroll.grid(row=0, column=1, sticky=tk.NS)
        h_scroll.grid(row=1, column=0, columnspan=2, sticky=tk.EW)

        # Load portions
        self._load_portions()

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(12, 0))

        ttk.Button(btn_frame, text="Add Portion", command=self._add_portion).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Edit Portion", command=self._edit_portion).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Delete Portion", command=self._delete_portion).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Create Defaults", command=self._create_defaults).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Clear Portions", command=self._clear_portions).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(btn_frame, text="Close", command=self.dialog.destroy).pack(side=tk.RIGHT)

        # Set minimum dialog size based on content and show
        self.dialog.update_idletasks()
        self.dialog.minsize(self.dialog.winfo_width(), self.dialog.winfo_height())
        self.dialog.deiconify()

    def _load_portions(self) -> None:
        """Load portions into the treeview."""
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Get portions
        portions_list = portions.list_portions(self.item_id, active_only=False)

        for portion in portions_list:
            amount = portion.get("portion_amount", portion.get("portion_ml", 0))
            selling_price = float(portion.get("selling_price", 0))
            cost_price = float(portion.get("cost_price", 0))
            active = "Yes" if portion.get("is_active", 1) else "No"
            
            # Get lot info
            lot_info = "Effective Price"
            lot_id = portion.get("lot_id")
            if lot_id:
                lot_info = f"Lot {lot_id}"

            self.tree.insert("", tk.END, values=(
                portion["portion_name"],
                f"{amount:.0f}",
                f"{self.currency_symbol} {selling_price:.2f}",
                f"{self.currency_symbol} {cost_price:.2f}",
                lot_info,
                active
            ), tags=(str(portion["portion_id"]),))

    def _add_portion(self) -> None:
        """Add a new portion."""
        PortionEditDialog(self.dialog, self.item_id, self.unit_info, self.price_per_base, self.price_per_small, callback=self._load_portions)

    def _edit_portion(self) -> None:
        """Edit the selected portion."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Select Portion", "Please select a portion to edit")
            return

        portion_id = int(self.tree.item(selection[0], "tags")[0])
        portion = portions.get_portion(portion_id)
        if portion:
            PortionEditDialog(self.dialog, self.item_id, self.unit_info, self.price_per_base, self.price_per_small,
                            existing_portion=portion, callback=self._load_portions)

    def _delete_portion(self) -> None:
        """Delete the selected portion."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Select Portion", "Please select a portion to delete")
            return

        portion_id = int(self.tree.item(selection[0], "tags")[0])
        portion = portions.get_portion(portion_id)
        if not portion:
            return

        if messagebox.askyesno("Confirm Delete", f"Delete portion '{portion['portion_name']}'?"):
            if portions.delete_portion(portion_id):
                self._load_portions()
                messagebox.showinfo("Success", "Portion deleted")
            else:
                messagebox.showerror("Error", "Failed to delete portion")

    def _create_defaults(self) -> None:
        """Create default portions for the item."""
        # Get available lots for this item
        from modules.inventory_costing import get_stock_lots
        available_lots = get_stock_lots(self.item_id, include_empty=False)

        # Create lot selection dialog
        lot_dialog = tk.Toplevel(self.dialog)
        lot_dialog.withdraw()
        lot_dialog.title("Select Lot for Default Portions")
        set_window_icon(lot_dialog)
        lot_dialog.transient(self.dialog)
        lot_dialog.grab_set()
        lot_dialog.resizable(False, False)

        main_frame = ttk.Frame(lot_dialog, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Choose which lot to use for pricing the default portions:",
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 10))

        # Lot selection
        lot_var = tk.StringVar()
        lot_combo = ttk.Combobox(main_frame, textvariable=lot_var, width=40, state="readonly")

        # Create lot options
        lot_options = ["(Use effective price)"]
        lot_id_map = {0: None}

        for i, lot in enumerate(available_lots, 1):
            price_display = f"{lot.selling_price:.2f}" if lot.selling_price else "Not set"
            option_text = f"Lot {lot.lot_id}: {self.currency_symbol} {price_display} ({lot.quantity_remaining:.0f} remaining)"
            lot_options.append(option_text)
            lot_id_map[i] = lot.lot_id

        lot_combo['values'] = lot_options
        lot_combo.set(lot_options[0])  # Default to effective price
        lot_combo.pack(pady=(0, 15))

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        selected_lot_id = [None]  # Use list to modify from inner function

        def on_ok():
            idx = lot_combo.current()
            selected_lot_id[0] = lot_id_map.get(idx, None)
            lot_dialog.destroy()

        def on_cancel():
            selected_lot_id[0] = None
            lot_dialog.destroy()

        ttk.Button(btn_frame, text="Create Portions", command=on_ok).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT)

        # Center and show dialog
        lot_dialog.update_idletasks()
        width = lot_dialog.winfo_width()
        height = lot_dialog.winfo_height()
        screen_width = lot_dialog.winfo_screenwidth()
        screen_height = lot_dialog.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        lot_dialog.geometry(f"{width}x{height}+{x}+{y}")
        lot_dialog.deiconify()
        lot_dialog.wait_window()

        # If user cancelled, return
        if selected_lot_id[0] is None:
            return

        # Now create the portions with the selected lot
        try:
            created = portions.create_default_portions(
                self.item_id,
                price_per_base=self.price_per_base,
                unit_of_measure=self.unit_of_measure,
                lot_id=selected_lot_id[0]  # Pass the selected lot
            )
            self._load_portions()
            lot_name = f"Lot {selected_lot_id[0]}" if selected_lot_id[0] else "effective price"
            messagebox.showinfo("Success", f"Created {len(created)} default portions using {lot_name}")
        except Exception as e:
            logger.exception("Failed to create default portions")
            messagebox.showerror("Error", f"Failed to create portions: {e}")

    def _clear_portions(self) -> None:
        """Delete all portions for this item."""
        if not messagebox.askyesno(
            "Clear Portions",
            "This will DELETE ALL portions for this item.\n\nThis action cannot be undone.\n\nContinue?"
        ):
            return

        try:
            portions_list = portions.list_portions(self.item_id, active_only=False)
            if not portions_list:
                messagebox.showinfo("No Portions", "There are no portions to delete")
                return

            deleted = 0
            for portion in portions_list:
                if portions.delete_portion(portion["portion_id"]):
                    deleted += 1

            messagebox.showinfo("Success", f"Deleted {deleted} portion(s)")
            self._load_portions()
        except Exception as e:
            logger.exception("Failed to clear portions")
            messagebox.showerror("Error", f"Failed to clear portions: {e}")


class PortionEditDialog:
    """Dialog for adding/editing a portion."""

    def __init__(self, parent: tk.Widget, item_id: int, unit_info: Dict[str, Any],
                 price_per_base: float, price_per_small: float,
                 existing_portion: Optional[Dict[str, Any]] = None,
                 callback: Optional[callable] = None):
        self.parent = parent
        self.item_id = item_id
        self.unit_info = unit_info
        self.price_per_base = price_per_base
        self.price_per_small = price_per_small
        self.existing = existing_portion
        self.callback = callback
        self.currency_symbol = get_currency_symbol()

        # Get available lots for this item
        from modules.inventory_costing import get_stock_lots
        self.available_lots = get_stock_lots(self.item_id, include_empty=False)

        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create the portion edit dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.withdraw()
        self.dialog.title("Add Portion" if not self.existing else "Edit Portion")
        set_window_icon(self.dialog)
        self.dialog.transient(self.parent.winfo_toplevel())
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        main_frame = ttk.Frame(self.dialog, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Fields
        row = 0

        ttk.Label(main_frame, text="Portion Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar(value=self.existing.get("portion_name", "") if self.existing else "")
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        ttk.Label(main_frame, text=f"Amount ({self.unit_info['small_unit']}):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.amount_var = tk.StringVar(value=str(self.existing.get("portion_amount", self.existing.get("portion_ml", 0))) if self.existing else "")
        amount_entry = ttk.Entry(main_frame, textvariable=self.amount_var, width=15)
        amount_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Lot selection
        ttk.Label(main_frame, text="Based on Lot:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.lot_var = tk.StringVar()
        lot_combo = ttk.Combobox(main_frame, textvariable=self.lot_var, width=25, state="readonly")
        
        # Create lot options
        lot_options = ["(Use effective price)"]
        self.lot_id_map = {0: None}  # Map option index to lot_id
        
        for i, lot in enumerate(self.available_lots, 1):
            # Handle cases where selling_price might be None
            price_display = f"{lot.selling_price:.2f}" if lot.selling_price else "Not set"
            option_text = f"Lot {lot.lot_id}: {self.currency_symbol} {price_display} ({lot.quantity_remaining:.0f} remaining)"
            lot_options.append(option_text)
            self.lot_id_map[i] = lot.lot_id
        
        lot_combo['values'] = lot_options
        
        # Set current selection
        current_lot_id = self.existing.get("lot_id") if self.existing else None
        if current_lot_id:
            for idx, lot_id in self.lot_id_map.items():
                if lot_id == current_lot_id:
                    self.lot_var.set(lot_options[idx])
                    break
        else:
            self.lot_var.set(lot_options[0])  # Default to effective price
        
        lot_combo.grid(row=row, column=1, sticky=tk.W, pady=5)
        lot_combo.bind("<<ComboboxSelected>>", self._on_lot_change)
        row += 1

        # Price fields
        ttk.Label(main_frame, text="Selling Price:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.selling_price_var = tk.StringVar(value=f"{self.existing.get('selling_price', 0):.2f}" if self.existing else "")
        self.selling_entry = ttk.Entry(main_frame, textvariable=self.selling_price_var, width=15)
        self.selling_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Set initial state of selling price field
        self._on_lot_change()

        ttk.Label(main_frame, text="Cost Price:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.cost_price_var = tk.StringVar(value=f"{self.existing.get('cost_price', 0):.2f}" if self.existing else "")
        ttk.Entry(main_frame, textvariable=self.cost_price_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1

        # Active checkbox
        self.active_var = tk.BooleanVar(value=self.existing.get("is_active", True) if self.existing else True)
        ttk.Checkbutton(main_frame, text="Active", variable=self.active_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(12, 0))

        ttk.Button(btn_frame, text="Save", command=self._save).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT)

        # Bind events
        amount_entry.bind("<KeyRelease>", self._on_amount_change)
        # lot_combo binding is already done above

        # Set dialog size and show
        self.dialog.update_idletasks()
        self.dialog.geometry("400x300")
        self.dialog.deiconify()

    def _on_lot_change(self, event=None) -> None:
        """Update pricing when lot selection changes."""
        self._update_price_from_lot()
        # Selling price field remains enabled for manual editing even when lot is selected

    def _on_amount_change(self, event=None) -> None:
        """Update selling price when amount changes."""
        self._update_price_from_lot()

    def _update_price_from_lot(self) -> None:
        """Update the selling price based on selected lot and amount."""
        try:
            amount = float(self.amount_var.get() or 0)
            if amount <= 0:
                return

            # Find the selected lot_id
            current_selection = self.lot_var.get()
            
            if current_selection == "(Use effective price)":
                # Use effective price
                selling_price = (amount / self.unit_info["multiplier"]) * self.price_per_base if self.unit_info["multiplier"] > 0 else amount * self.price_per_small
            else:
                # Find the lot_id by matching the selection text
                selected_lot_id = None
                for idx, option in enumerate(self.lot_var.get().split('\n')):
                    if option == current_selection and idx in self.lot_id_map:
                        selected_lot_id = self.lot_id_map[idx]
                        break
                
                # If not found by text matching, try to find by comparing with built options
                if not selected_lot_id:
                    for i, lot in enumerate(self.available_lots, 1):
                        price_display = f"{lot.selling_price:.2f}" if lot.selling_price else "Not set"
                        option_text = f"Lot {lot.lot_id}: {self.currency_symbol} {price_display} ({lot.quantity_remaining:.0f} remaining)"
                        if current_selection == option_text:
                            selected_lot_id = lot.lot_id
                            break
                
                if selected_lot_id:
                    from modules.inventory_costing import get_lot_by_id
                    lot = get_lot_by_id(selected_lot_id)
                    if lot and lot.selling_price and lot.selling_price > 0:
                        # Calculate price proportionally - assume lot selling price is for full item unit
                        # For portions, we need to scale based on the portion amount relative to item unit size
                        item_unit_size = float(self.item.get("unit_size_ml") or 1)
                        portion_ratio = amount / (item_unit_size * self.unit_info["multiplier"])
                        selling_price = portion_ratio * lot.selling_price
                    else:
                        # Lot has no selling price set, fall back to effective price
                        selling_price = (amount / self.unit_info["multiplier"]) * self.price_per_base if self.unit_info["multiplier"] > 0 else amount * self.price_per_small
                else:
                    selling_price = 0

            self.selling_price_var.set(f"{selling_price:.2f}")
        except ValueError:
            pass

    def _save(self) -> None:
        """Save the portion."""
        try:
            name = self.name_var.get().strip()
            amount = float(self.amount_var.get() or 0)
            selling_price = float(self.selling_price_var.get() or 0)
            cost_price = float(self.cost_price_var.get() or 0)
            is_active = self.active_var.get()

            # Get selected lot_id
            lot_id = None
            current_selection = self.lot_var.get()
            if current_selection != "(Use effective price)":
                # Find the lot_id by matching the selection text
                for i, lot in enumerate(self.available_lots, 1):
                    price_display = f"{lot.selling_price:.2f}" if lot.selling_price else "Not set"
                    option_text = f"Lot {lot.lot_id}: {self.currency_symbol} {price_display} ({lot.quantity_remaining:.0f} remaining)"
                    if current_selection == option_text:
                        lot_id = lot.lot_id
                        break

            if not name:
                messagebox.showerror("Error", "Portion name is required")
                return

            if amount <= 0:
                messagebox.showerror("Error", "Amount must be greater than 0")
                return

            if self.existing:
                # Update existing
                portions.update_portion(self.existing["portion_id"],
                                       portion_name=name,
                                       portion_amount=amount,
                                       selling_price=selling_price,
                                       cost_price=cost_price,
                                       is_active=is_active,
                                       lot_id=lot_id)
                messagebox.showinfo("Success", "Portion updated")
            else:
                # Create new
                portions.create_portion(self.item_id, name, amount, selling_price, cost_price, lot_id=lot_id)
                messagebox.showinfo("Success", "Portion created")

            if self.callback:
                self.callback()

            self.dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
        except Exception as e:
            logger.exception("Failed to save portion")
            messagebox.showerror("Error", f"Failed to save portion: {e}")