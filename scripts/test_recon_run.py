import os, sys
# Ensure project root is on sys.path so we can import application modules when run from scripts/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tkinter as tk
import time
import main
# Ensure AppShell class is available (it's defined in ui.shell)
from ui.shell import AppShell
main.AppShell = AppShell

root = tk.Tk()
root.geometry('1000x700')
root.minsize(800,600)
root.title('Reconciliation Layout Test')
# Build shell directly (avoid loading other pages)
shell = AppShell(root, user={'username':'admin','role':'admin','user_id':1}, on_nav=lambda k: main._handle_nav(root,k), on_logout=lambda: None)
shell.grid(row=0, column=0, sticky='nsew')
root.shell = shell
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
# Navigate to reconciliation
main._handle_nav(root, 'reconciliation')
print('Reconciliation rendered inside shell. Waiting for inspection...')
root.update()
# Shrink to small size to force scrolls
root.geometry('900x600')
root.update()
print('Resized to 900x600')
# Wait a moment so a human could visually verify (if watching)
time.sleep(1)
# Expand to large size
root.geometry('1400x900')
root.update()
print('Resized to 1400x900')
# Open a popped-out window directly (avoid header dependency)
try:
    print('Opening separate reconciliation window')
    main.show_reconciliation_window(root)
except Exception as e:
    print('Popup failed:', e)
# Wait then close
time.sleep(1)
root.destroy()
print('Test complete')
