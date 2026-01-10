import sys
import tkinter as tk
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from ui.upgrade_manager import UpgradeManager


def test_instantiate():
    root = tk.Tk()
    root.withdraw()
    dlg = UpgradeManager(master=root)
    dlg.update()
    dlg.destroy()
    root.destroy()


if __name__ == '__main__':
    test_instantiate()
    print('ui smoke test passed')
