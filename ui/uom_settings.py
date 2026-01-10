"""Unit of Measure Settings UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from modules import units_of_measure as uom
from utils import set_window_icon


class UomSettingsFrame(ttk.Frame):
    """Frame for managing units of measure."""

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
        ttk.Label(top, text="Units of Measure", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        if self.on_home:
            ttk.Button(top, text="🏠 Home", command=self.on_home).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Add Unit", command=self._add_unit).pack(side=tk.RIGHT, padx=4)

        # Tree view
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=1, column=0, sticky=tk.NSEW, pady=(0, 8))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("name", "abbreviation", "conversion", "base_unit", "active"),
            show="headings",
            height=15
        )
        self.tree.heading("name", text="Name")
        self.tree.heading("abbreviation", text="Abbrev.")
        self.tree.heading("conversion", text="Conversion Factor")
        self.tree.heading("base_unit", text="Base Unit")
        self.tree.heading("active", text="Active")
        self.tree.column("name", width=150, anchor=tk.W)
        self.tree.column("abbreviation", width=80, anchor=tk.CENTER)
        self.tree.column("conversion", width=120, anchor=tk.E)
        self.tree.column("base_unit", width=120, anchor=tk.W)
        self.tree.column("active", width=80, anchor=tk.CENTER)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky=tk.NS)
        self.tree.configure(yscroll=scroll.set)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, sticky=tk.W, pady=(4, 0))
        ttk.Button(btn_frame, text="Edit", command=self._edit_unit).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Toggle Active", command=self._toggle_active).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Delete", command=self._delete_unit).pack(side=tk.LEFT, padx=2)

    def refresh(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        units = uom.list_units(active_only=False)
        for unit in units:
            self.tree.insert(
                "",
                tk.END,
                iid=str(unit["uom_id"]),
                values=(
                    unit["name"],
                    unit.get("abbreviation", ""),
                    unit.get("conversion_factor", 1),
                    unit.get("base_unit", "") or "",
                    "Yes" if unit["is_active"] else "No"
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

    def _add_unit(self) -> None:
        self._open_dialog(title="Add Unit", existing=None)

    def _edit_unit(self) -> None:
        uom_id = self._selected_id()
        if not uom_id:
            messagebox.showinfo("Edit", "Select a unit to edit")
            return
        record = uom.get_unit(uom_id)
        self._open_dialog(title="Edit Unit", existing=record)

    def _toggle_active(self) -> None:
        uom_id = self._selected_id()
        if not uom_id:
            messagebox.showinfo("Toggle", "Select a unit to toggle")
            return
        uom.toggle_active(uom_id)
        self.refresh()

    def _delete_unit(self) -> None:
        uom_id = self._selected_id()
        if not uom_id:
            messagebox.showinfo("Delete", "Select a unit to delete")
            return
        record = uom.get_unit(uom_id)
        if not messagebox.askyesno("Delete Unit", f"Delete '{record['name']}'?"):
            return
        uom.delete_unit(uom_id)
        self.refresh()

    def _open_dialog(self, *, title: str, existing: dict | None) -> None:
        dialog = tk.Toplevel(self)
        dialog.withdraw()
        dialog.title(title)
        set_window_icon(dialog)
        dialog.transient(self.winfo_toplevel())

        # Get screen dimensions
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        dialog_width = max(450, min(550, int(screen_width * 0.4)))
        dialog_height = max(350, min(400, int(screen_height * 0.4)))
        x_pos = (screen_width - dialog_width) // 2
        y_pos = (screen_height - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x_pos}+{y_pos}")
        dialog.resizable(True, True)

        # Header
        header = ttk.Frame(dialog, relief="solid", borderwidth=1)
        header.pack(fill=tk.X, side=tk.TOP)
        ttk.Label(header, text=f"{title} - Unit Details", font=("Segoe UI", 12, "bold")).pack(padx=12, pady=8)

        # Button frame at bottom
        button_frame = ttk.Frame(dialog, relief="solid", borderwidth=1)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))

        # Form
        form_frame = ttk.Frame(dialog)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        form_frame.columnconfigure(1, weight=1)

        fields = {
            "name": tk.StringVar(value=existing.get("name", "") if existing else ""),
            "abbreviation": tk.StringVar(value=existing.get("abbreviation", "") if existing else ""),
            "conversion_factor": tk.StringVar(value=str(existing.get("conversion_factor", 1)) if existing else "1"),
            "base_unit": tk.StringVar(value=existing.get("base_unit", "") if existing else ""),
        }

        row = 0
        labels = [
            ("Name", "name"),
            ("Abbreviation", "abbreviation"),
            ("Conversion Factor", "conversion_factor"),
            ("Base Unit", "base_unit"),
        ]

        for label, key in labels:
            ttk.Label(form_frame, text=label, font=("Segoe UI", 10)).grid(row=row, column=0, sticky=tk.W, pady=8, padx=8)
            if key == "base_unit":
                # Combobox for base unit
                unit_names = uom.get_unit_names(active_only=False)
                combo = ttk.Combobox(form_frame, textvariable=fields[key], values=[""] + unit_names, width=30)
                combo.grid(row=row, column=1, sticky=tk.EW, pady=8, padx=8)
            else:
                entry = ttk.Entry(form_frame, textvariable=fields[key], width=30)
                entry.grid(row=row, column=1, sticky=tk.EW, pady=8, padx=8)
            row += 1

        # Help text
        help_text = ttk.Label(
            form_frame,
            text="Note: Conversion factor = how many base units in this unit.\nE.g., 1 kg = 1000 g, so kg has factor 1000 with base 'gram'.",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        help_text.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(15, 5), padx=8)

        def on_submit():
            try:
                name = fields["name"].get().strip()
                abbrev = fields["abbreviation"].get().strip()
                factor = float(fields["conversion_factor"].get() or 1)
                base = fields["base_unit"].get().strip() or None

                if not name:
                    messagebox.showerror("Invalid input", "Name is required")
                    return

                if existing:
                    uom.update_unit(
                        existing["uom_id"],
                        name=name,
                        abbreviation=abbrev,
                        conversion_factor=factor,
                        base_unit=base
                    )
                else:
                    uom.create_unit(name, abbrev, factor, base)

                self.refresh()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Invalid input", "Conversion factor must be a number")

        ttk.Button(button_frame, text="Save", command=on_submit, width=15).pack(side=tk.LEFT, padx=8, pady=8)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=4, pady=8)

        dialog.deiconify()
        dialog.grab_set()
        dialog.wait_window()
