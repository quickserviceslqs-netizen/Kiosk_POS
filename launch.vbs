Set oShell = CreateObject("WScript.Shell")
oShell.Run "pythonw """ & oShell.CurrentDirectory & "\main.py""", 0, False
