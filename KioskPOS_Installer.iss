; Kiosk POS Inno Setup Script
; Generated for Windows installer



[Setup]
AppName=Kiosk POS v1.000
AppVersion=1.000
DefaultDirName={commonpf}\KioskPOS
DefaultGroupName=Kiosk POS v1.000
OutputDir=dist
OutputBaseFilename=KioskPOS_Installer_v1.000
Compression=lzma
SolidCompression=yes
PrivilegesRequired=none
SetupIconFile=assets\app_icon.ico

[Files]
Source: "dist\main.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "database\init_db.py"; DestDir: "{app}\database"; Flags: ignoreversion
Source: "database\__init__.py"; DestDir: "{app}\database"; Flags: ignoreversion
Source: "email_config.json"; DestDir: "{app}"; Flags: ignoreversion


[Icons]
Name: "{group}\Kiosk POS v1.000"; Filename: "{app}\main.exe"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{group}\Uninstall Kiosk POS v1.000"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Kiosk POS v1.000"; Filename: "{app}\main.exe"; IconFilename: "{app}\assets\app_icon.ico"

[Run]
Filename: "{app}\main.exe"; Description: "Launch Kiosk POS"; Flags: nowait postinstall skipifsilent
