"""
Demo script for the new Simple Excel-like Reconciliation UI

This demonstrates the key features of the redesigned reconciliation module:
- Simple, Excel-like interface
- Direct cell editing
- Automatic calculations
- Easy data management
"""

import tkinter as tk
from ui.simple_reconciliation_ui import SimpleReconciliationUI
import time

def demo_reconciliation():
    """Demonstrate the simple reconciliation UI."""
    print("🚀 Starting Simple Reconciliation UI Demo")
    print("=" * 50)

    # Create root window
    root = tk.Tk()
    root.title('Kiosk POS - Simple Reconciliation Demo')
    root.geometry('1000x600')

    # Create UI
    ui = SimpleReconciliationUI(root)

    print("✓ UI created successfully")
    print("Features demonstrated:")
    print("  - Clean, minimal interface")
    print("  - Excel-like table with direct editing")
    print("  - Simple toolbar (New/Load/Save/Export)")
    print("  - Automatic variance calculations")
    print("  - Real-time totals")

    # Demo sequence
    def run_demo():
        print("\\n📋 Running demo sequence...")

        # Step 1: New session
        print("1. Creating new reconciliation session...")
        ui._new_session()
        time.sleep(1)

        # Step 2: Add some sample data
        print("2. Adding sample payment methods...")
        # The new session already adds default methods, let's modify them
        items = ui.tree.get_children()
        if len(items) >= 3:
            # Set some expected amounts
            ui.tree.set(items[0], 'expected', '$1,250.00')  # Cash
            ui.tree.set(items[1], 'expected', '$850.50')    # Credit Card
            ui.tree.set(items[2], 'expected', '$320.75')    # Debit Card

            # Set some actual amounts
            ui.tree.set(items[0], 'actual', '$1,240.00')    # Cash (short)
            ui.tree.set(items[1], 'actual', '$850.50')      # Credit Card (exact)
            ui.tree.set(items[2], 'actual', '$335.00')      # Debit Card (over)

            # Update calculations
            for item in items:
                ui._update_row_variance(item)
            ui._update_totals()

        time.sleep(1)

        # Step 3: Show results
        print("3. Results:")
        expected_total = ui.total_expected_var.get()
        actual_total = ui.total_actual_var.get()
        variance_total = ui.total_variance_var.get()
        status = ui.status_var.get()

        print(f"   Expected Total: {expected_total}")
        print(f"   Actual Total: {actual_total}")
        print(f"   Variance Total: {variance_total}")
        print(f"   Status: {status}")

        print("\\n✨ Demo complete!")
        print("\\nHow to use the Simple Reconciliation UI:")
        print("• Click 'New' to start a fresh reconciliation")
        print("• Double-click cells to edit amounts directly")
        print("• Use 'Add Row' for additional payment methods")
        print("• Press Enter to move between cells")
        print("• Use 'Save' to store your work")
        print("• Export to CSV for external analysis")
        print("\\n🎯 Much simpler than the old complex interface!")

    # Run demo after UI is fully loaded
    root.after(500, run_demo)

    # Close after demo
    root.after(5000, root.destroy)

    # Start the GUI
    root.mainloop()

    print("\\n" + "=" * 50)
    print("✅ Demo completed successfully!")
    print("The new Simple Reconciliation UI is ready for use.")

if __name__ == "__main__":
    demo_reconciliation()