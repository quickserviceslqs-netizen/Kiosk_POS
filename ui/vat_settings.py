"""VAT rates management UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from modules import vat_rates
from utils import set_window_icon


class VatSettingsFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_home=None, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.on_home = on_home
        self.tree = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.grid_propagate(True)  # Allow frame to expand

        # Top bar
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Label(top, text="VAT Rate Settings", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        if self.on_home:
            ttk.Button(top, text="🏠 Home", command=self.on_home).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Add VAT Rate", command=self._add_rate).pack(side=tk.RIGHT, padx=4)

        # Tree view
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=1, column=0, sticky=tk.NSEW, pady=(0, 8))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("rate", "description", "active"),
            show="headings"
        )
        self.tree.heading("rate", text="Rate (%)")
        self.tree.heading("description", text="Description")
        self.tree.heading("active", text="Active")
        self.tree.column("rate", width=100, anchor=tk.E)
        self.tree.column("description", width=300, anchor=tk.W)
        self.tree.column("active", width=100, anchor=tk.CENTER)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky=tk.NS)
        self.tree.configure(yscroll=scroll.set)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, sticky=tk.W, pady=(4, 0))
        ttk.Button(btn_frame, text="Edit", command=self._edit_rate).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Toggle Active", command=self._toggle_active).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Delete", command=self._delete_rate).pack(side=tk.LEFT, padx=2)

    def refresh(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        rates = vat_rates.list_vat_rates(active_only=False)
        for rate in rates:
            self.tree.insert(
                "",
                tk.END,
                iid=str(rate["vat_id"]),
                values=(
                    f"{rate['rate']:.1f}",
                    rate.get("description", ""),
                    "Yes" if rate["active"] else "No"
                )
            )

    def _selected_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None

    def _add_rate(self) -> None:
        self._open_dialog(title="Add VAT Rate", existing=None)

    def _edit_rate(self) -> None:
        vat_id = self._selected_id()
        if not vat_id:
            messagebox.showinfo("Edit", "Select a VAT rate to edit")
            return
        record = vat_rates.get_vat_rate(vat_id)
        self._open_dialog(title="Edit VAT Rate", existing=record)

    def _toggle_active(self) -> None:
        vat_id = self._selected_id()
        if not vat_id:
            messagebox.showinfo("Toggle", "Select a VAT rate")
            return
        record = vat_rates.get_vat_rate(vat_id)
        new_active = not bool(record["active"])
        vat_rates.update_vat_rate(vat_id, active=new_active)
        self.refresh()

    def _delete_rate(self) -> None:
        vat_id = self._selected_id()
        if not vat_id:
            messagebox.showinfo("Delete", "Select a VAT rate to delete")
            return
        if not messagebox.askyesno("Confirm", "Deactivate this VAT rate?"):
            return
        vat_rates.delete_vat_rate(vat_id)
        self.refresh()

    def _open_dialog(self, *, title: str, existing: dict | None) -> None:
        dialog = tk.Toplevel(self)
        dialog.withdraw()
        dialog.title(title)
        set_window_icon(dialog)
        dialog.resizable(True, True)

        outer = ttk.Frame(dialog, padding=(14, 12, 14, 10))
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(1, weight=1)

        rate_var = tk.StringVar(value=f"{existing['rate']:.2f}" if existing else "")
        desc_var = tk.StringVar(value=existing.get("description", "") if existing else "")
        active_var = tk.BooleanVar(value=bool(existing.get("active", True)) if existing else True)

        ttk.Label(outer, text="Rate (%) *").grid(row=0, column=0, sticky=tk.W, pady=6, padx=(0, 10))
        rate_entry = ttk.Entry(outer, textvariable=rate_var, width=18)
        rate_entry.grid(row=0, column=1, sticky=tk.W, pady=6)

        ttk.Label(outer, text="Description").grid(row=1, column=0, sticky=tk.W, pady=6, padx=(0, 10))
        ttk.Entry(outer, textvariable=desc_var, width=28).grid(row=1, column=1, sticky=tk.EW, pady=6)

        ttk.Checkbutton(outer, text="Active", variable=active_var).grid(
            row=2, column=1, sticky=tk.W, pady=6)

        def on_submit():
            raw = rate_var.get().strip()
            if not raw:
                messagebox.showerror("Required", "Please enter a rate.", parent=dialog)
                rate_entry.focus_set()
                return
            try:
                rate = float(raw)
                if rate < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid", "Rate must be a non-negative number.", parent=dialog)
                rate_entry.focus_set()
                return

            payload = {
                "rate": rate,
                "description": desc_var.get().strip(),
                "active": active_var.get(),
            }
            try:
                if existing:
                    vat_rates.update_vat_rate(existing["vat_id"], **payload)
                else:
                    vat_rates.create_vat_rate(**payload)
                self.refresh()
                dialog.destroy()
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to save VAT rate:\n{exc}", parent=dialog)

        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(10, 4))
        ttk.Button(btn_frame, text="💾  Save", command=on_submit, width=10).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=8).pack(side=tk.LEFT)
        dialog.bind("<Return>", lambda e: on_submit())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        dialog.update_idletasks()
        sw, sh = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
        w, h = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        dialog.geometry(f"+{(sw - w) // 2}+{max(30, (sh - h) // 2 - 40)}")
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()
        rate_entry.focus_set()
