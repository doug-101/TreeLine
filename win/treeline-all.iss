; treeline-all.iss

; Inno Setup installer script for Treeline, an information storage program.
; This will install for a all users, admin rights are required.

[Setup]
AppName=TreeLine
AppVersion=3.2.0
ChangesAssociations=yes
DefaultDirName={commonpf}\TreeLine-3
DefaultGroupName=TreeLine
DisableProgramGroupPage=yes
OutputDir=.
OutputBaseFilename=treeline-3.2.0-install-all
PrivilegesRequired=poweruser
SetupIconFile=treeline.ico
Uninstallable=WizardIsTaskSelected('adduninstall')
UninstallDisplayIcon={app}\treeline.exe,0

[Tasks]
Name: "fileassoc"; Description: "Add *.trln file association"
Name: "startmenu"; Description: "Add start menu shortcuts"
Name: "deskicon"; Description: "Add a desktop shortcut"
Name: "adduninstall"; Description: "Create an uninstaller"
Name: "translate"; Description: "Include language translations"
Name: "source"; Description: "Include source code"

[InstallDelete]
Type: files; Name: "{app}\library.zip"
Type: files; Name: "{app}\python*.zip"
Type: files; Name: "{app}\*.pyd"
Type: files; Name: "{app}\*.dll"
Type: files; Name: "{app}\doc\documentation.trl"
Type: filesandordirs; Name: "{app}\lib"
Type: filesandordirs; Name: "{app}\imageformats"
Type: filesandordirs; Name: "{app}\platforms"
Type: dirifempty; Name: "{app}\plugins"
Type: files; Name: "{app}\samples\*.trl"
Type: files; Name: "{app}\source\*.py"
Type: files; Name: "{app}\templates\*.trl"
Type: files; Name: "{app}\translations\*.qm"

[Files]
Source: "treeline.exe"; DestDir: "{app}"
Source: "base_library.zip"; DestDir: "{app}"
Source: "*.dll"; DestDir: "{app}"
Source: "*.pyd"; DestDir: "{app}"
Source: "PyQt6\*"; DestDir: "{app}\PyQt6"; Flags: recursesubdirs
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
Source: "source\treeline.pro"; DestDir: "{app}\source"; Tasks: "source"
Source: "source\treeline.spec"; DestDir: "{app}\source"; Tasks: "source"
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
