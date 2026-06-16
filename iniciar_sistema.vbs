Dim objHTTP, WshShell
Set WshShell = CreateObject("WScript.Shell")
Set objHTTP = CreateObject("WinHttp.WinHttpRequest.5.1")

On Error Resume Next
objHTTP.Open "GET", "http://localhost:8001", False
objHTTP.SetTimeouts 3000, 3000, 3000, 3000
objHTTP.Send

If Err.Number = 0 And objHTTP.Status = 200 Then
    WshShell.Run "http://localhost:8001", 1, False
Else
    Err.Clear
    WshShell.CurrentDirectory = "C:\HMPCF-Automation-System\backend"
    WshShell.Run """C:\HMPCF-Automation-System\backend\.venv\Scripts\python.exe"" -m uvicorn app.main:app --host 0.0.0.0 --port 8001", 0, False
    WScript.Sleep 7000
    WshShell.Run "http://localhost:8001", 1, False
End If
