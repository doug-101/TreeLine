; treeline-all.iss

; Inno Setup installer script for Treeline, an information storage program.
; This will install for a all users, admin rights are required.

[Setup]
AppName=TreeLine
AppVersion=3.0.1
ChangesAssociations=yes
DefaultDirName={pf}\TreeLine-3
DefaultGroupName=TreeLine
DisableProgramGroupPage=yes
OutputDir=.
OutputBaseFilename=treeline-3.0.1-install-all
PrivilegesRequired=poweruser
SetupIconFile=treeline.ico
Uninstallable=IsTaskSelected('adduninstall')
UninstallDisplayIcon={app}\treeline.exe,0

[Tasks]
Name: "fileassoc"; Description: "Add *.trln file association"
Name: "startmenu"; Description: "Add start menu shortcuts"
Name: "deskicon"; Description: "Add a desktop shortcut"
Name: "adduninstall"; Description: "Create an uninstaller"
Name: "translate"; Description: "Include language translations"
Name: "source"; Description: "Include source code"

[Files]
Source: "treeline.exe"; DestDir: "{app}"
Source: "*.dll"; DestDir: "{app}"
Source: "lib\*.dll"; DestDir: "{app}\lib"
Source: "lib\*.pyd"; DestDir: "{app}\lib"
Source: "lib\*.zip"; DestDir: "{app}\lib"
Source: "lib\*140.dll"; DestDir: "{app}"
Source: "imageformats\*.dll"; DestDir: "{app}\imageformats"
Source: "platforms\*.dll"; DestDir: "{app}\platforms"
Source: "doc\LICENSE"; DestDir: "{app}\doc"
Source: "doc\basichelp.html"; DestDir: "{app}\doc"
Source: "doc\documentation.trln"; DestDir: "{app}\doc"; Attribs: readonly; \
        Flags: overwritereadonly uninsremovereadonly
Source: "doc\*.html"; DestDir: "{app}\doc"; Tasks: "translate"
Source: "doc\*.trln"; DestDir: "{app}\doc"; Attribs: readonly; \
        Tasks: "translate"; Flags: overwritereadonly uninsremovereadonly
Source: "samples\*.trln"; DestDir: "{app}\samples"; Attribs: readonly; \
        Flags: overwritereadonly uninsremovereadonly
Source: "icons\toolbar\32x32\*.png"; DestDir: "{app}\icons\toolbar\32x32"
Source: "icons\tree\*.png"; DestDir: "{app}\icons\tree"
Source: "templates\exports\*.*"; DestDir: "{app}\templates\exports"
Source: "templates\*en_*.trln"; DestDir: "{app}\templates"; Attribs: readonly; \
        Flags: overwritereadonly uninsremovereadonly
Source: "templates\*.trln"; DestDir: "{app}\templates"; Attribs: readonly; \
        Tasks: "translate"; Flags: overwritereadonly uninsremovereadonly
Source: "translations\*.qm"; DestDir: "{app}\translations"; Tasks: "translate"
Source: "source\*.py"; DestDir: "{app}\source"; Tasks: "source"
Source: "treeline.ico"; DestDir: "{app}"; Tasks: "source"
Source: "*.iss"; DestDir: "{app}"; Tasks: "source"

[Icons]
Name: "{commonstartmenu}\TreeLine 3"; Filename: "{app}\treeline.exe"; \
      WorkingDir: "{app}"; Tasks: "startmenu"
Name: "{group}\TreeLine 3"; Filename: "{app}\treeline.exe"; \
      WorkingDir: "{app}"; Tasks: "startmenu"
Name: "{group}\Uninstall"; Filename: "{uninstallexe}"; Tasks: "startmenu"
Name: "{commondesktop}\TreeLine 3"; Filename: "{app}\treeline.exe"; \
      WorkingDir: "{app}"; Tasks: "deskicon"

[Registry]
Root: HKCR; Subkey: ".trln"; ValueType: string; \
      ValueName: ""; ValueData: "TreeLineFile"; Flags: uninsdeletevalue; \
      Tasks: "fileassoc"
Root: HKCR; Subkey: "TreeLineFile"; ValueType: \
      string; ValueName: ""; ValueData: "TreeLine File"; \
      Flags: uninsdeletekey; Tasks: "fileassoc"
Root: HKCR; Subkey: "TreeLineFile\DefaultIcon"; \
      ValueType: string; ValueName: ""; ValueData: "{app}\treeline.exe,0"; \
      Tasks: "fileassoc"
Root: HKCR; Subkey: "TreeLineFile\shell\open\command"; \
      ValueType: string; ValueName: ""; \
      ValueData: """{app}\treeline.exe"" ""%1"""; Tasks: "fileassoc"
