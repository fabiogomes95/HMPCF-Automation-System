Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

' Pega a pasta onde este .vbs esta
strPath = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = fso.BuildPath(strPath, "iniciar_painel.bat")

If Not fso.FileExists(batPath) Then
    MsgBox "Arquivo nao encontrado:" & vbCrLf & batPath, vbCritical, "start_painel"
    WScript.Quit 1
End If

' 0 = esconde a janela do console
WshShell.Run chr(34) & batPath & chr(34), 0, False

Set fso = Nothing
Set WshShell = Nothing
