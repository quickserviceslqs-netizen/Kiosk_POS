"""VAT rates management UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from modules import vat_rates


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

        # Top bar
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Label(top, text="VAT Rate Settings", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        if self.on_home:
            ttk.Button(top, text="← Home", command=self.on_home).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Add VAT Rate", command=self._add_rate).pack(side=tk.RIGHT, padx=4)

        # Tree view
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=1, column=0, sticky=tk.NSEW, pady=(0, 8))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("rate", "description", "active"),
            show="headings",
            height=15
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
        dialog.title(title)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.geometry("400x200")

        fields = {
            "rate": tk.StringVar(value=str(existing.get("rate", 0.0)) if existing else "0.0"),
            "description": tk.StringVar(value=existing.get("description", "") if existing else ""),
            "active": tk.BooleanVar(value=bool(existing.get("active", 1)) if existing else True),
        }

        # Fields
        ttk.Label(dialog, text="Rate (%):").grid(row=0, column=0, sticky=tk.W, pady=8, padx=12)
        ttk.Entry(dialog, textvariable=fields["rate"], width=20).grid(row=0, column=1, sticky=tk.W, pady=8, padx=12)

        ttk.Label(dialog, text="Description:").grid(row=1, column=0, sticky=tk.W, pady=8, padx=12)
        ttk.Entry(dialog, textvariable=fields["description"], width=30).grid(row=1, column=1, sticky=tk.EW, pady=8, padx=12)

        ttk.Checkbutton(dialog, text="Active", variable=fields["active"]).grid(row=2, column=1, sticky=tk.W, pady=8, padx=12)

        def on_submit():
            try:
                rate = float(fields["rate"].get())
            except ValueError:
                messagebox.showerror("Invalid", "Enter a valid rate number")
                return

            payload = {
                "rate": rate,
                "description": fields["description"].get().strip(),
                "active": fields["active"].get(),
            }

            try:
                if existing:
                    vat_rates.update_vat_rate(existing["vat_id"], **payload)
                else:
                    vat_rates.create_vat_rate(**payload)
                self.refresh()
                dialog.destroy()
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to save VAT rate: {exc}")

        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=16)
        ttk.Button(btn_frame, text="Save", command=on_submit).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=4)
