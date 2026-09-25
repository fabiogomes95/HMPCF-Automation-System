' Atalho "HMPCF - BPA": liga o BPA local (porta 8503) sem janela e abre o
' sistema do servidor no navegador. Faz o mesmo que o iniciar.bat, so que
' escondido. Se o BPA ja estiver rodando, o executar.py percebe e sai sozinho.
Option Explicit

Const URL_SISTEMA = "http://192.168.1.29:8001/"
Const URL_BPA = "http://127.0.0.1:8503/api/status"

Dim fso, sh, pasta, i
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
pasta = fso.GetParentFolderName(WScript.ScriptFullName)

Function BpaNoAr()
    Dim http
    BpaNoAr = False
    On Error Resume Next
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    http.setTimeouts 1000, 1000, 2000, 2000
    http.Open "GET", URL_BPA, False
    http.Send
    If Err.Number = 0 Then BpaNoAr = (http.Status > 0)
    On Error GoTo 0
End Function

If Not BpaNoAr() Then
    sh.CurrentDirectory = pasta
    ' 0 = sem janela, False = nao espera terminar
    sh.Run """" & pasta & "\.venv\Scripts\pythonw.exe"" executar.py", 0, False
    ' Espera o BPA responder (ate ~40s) pra tela ja abrir com ele ligado
    For i = 1 To 40
        If BpaNoAr() Then Exit For
        WScript.Sleep 1000
    Next
End If

' Chrome se tiver; senao o navegador padrao
On Error Resume Next
sh.Run "chrome """ & URL_SISTEMA & """", 1, False
If Err.Number <> 0 Then
    Err.Clear
    sh.Run """" & URL_SISTEMA & """", 1, False
End If
