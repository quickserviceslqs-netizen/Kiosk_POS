import py_compile
try:
    py_compile.compile(r'c:\Users\ADMIN\Kiosk_Pos\ui\inventory.py', doraise=True)
    print('compiled ok')
except Exception as e:
    print('compile failed:', e)