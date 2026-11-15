Set sh = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
sh.CurrentDirectory = fs.GetParentFolderName(WScript.ScriptFullName)
q = Chr(34)
py = ".venv\Scripts\python.exe"
If Not fs.FileExists(py) Then
    sh.Run q & "ABRIR_SMARTPICK.bat" & q, 1, False
ElseIf sh.Run(q & py & q & " -c " & q & "import streamlit, serial, xlsxwriter; assert hasattr(streamlit, 'fragment')" & q, 0, True) <> 0 Then
    sh.Run q & "ABRIR_SMARTPICK.bat" & q, 1, False
Else
    sh.Run "cmd.exe /c " & q & "call ABRIR_SMARTPICK.bat > smartpick.log 2>&1" & q, 0, False
End If
