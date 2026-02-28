#!/usr/bin/env python3
"""
Demo script for the Modern Reports Interface

This script demonstrates the new modern, card-based reports interface
with improved UX and visual design.
"""

import tkinter as tk
from ui.reports import ModernReportsFrame

def demo_modern_reports():
    """Demonstrate the modern reports interface."""
    root = tk.Tk()
    root.title("Modern Reports Interface Demo")
    root.geometry("1400x900")

    # Create the modern reports frame
    reports_frame = ModernReportsFrame(root, on_home=lambda: print("Home clicked"))
    reports_frame.pack(fill=tk.BOTH, expand=True)

    print("Modern Reports Interface Demo")
    print("==============================")
    print("Features:")
    print("• Card-based layout with modern styling")
    print("• Sidebar navigation with report categories")
    print("• Quick action buttons for common reports")
    print("• Loading indicators and progress feedback")
    print("• Metric cards with key business indicators")
    print("• Responsive design with proper spacing")
    print("• Status filtering for reconciliation reports")
    print("• Export functionality (coming soon)")
    print("")
    print("Try clicking on different categories in the sidebar!")
    print("The interface provides a much more intuitive and modern experience.")

    root.mainloop()

if __name__ == "__main__":
    demo_modern_reports()