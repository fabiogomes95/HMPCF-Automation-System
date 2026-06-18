Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\HMPCF-Automation-System\backend"
WshShell.Run """C:\HMPCF-Automation-System\backend\.venv\Scripts\python.exe"" -m uvicorn app.main:app --host 0.0.0.0 --port 8001", 0, False
