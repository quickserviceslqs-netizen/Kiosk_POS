; Kiosk POS Inno Setup Script
; Version 1.003 - Production Build

[Setup]
AppName=Kiosk POS
AppVersion=1.004
AppPublisher=Kiosk POS
AppPublisherURL=https://kioskpos.com
DefaultDirName={autopf}\KioskPOS
DefaultGroupName=Kiosk POS
OutputDir=dist
OutputBaseFilename=KioskPOS_Installer_v1.004
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
SetupIconFile=assets\app_icon.ico
UninstallDisplayIcon={app}\assets\app_icon.ico
WizardStyle=modern
DisableProgramGroupPage=yes

[Dirs]
Name: "{app}\database"


[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

 [Files]
; Main executable (contains all bundled code)
Source: "dist\main.exe"; DestDir: "{app}"; Flags: ignoreversion restartreplace

; Assets folder
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

; Email config template
Source: "email_config.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

[Code]
var
  ResultCode: Integer;

function InitializeSetup(): Boolean;
begin
	// Attempt to close main.exe if running
	// Use the system taskkill.exe to terminate main.exe if it's running
	Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM main.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
	Result := True;
end;

[Icons]
Name: "{group}\Kiosk POS"; Filename: "{app}\main.exe"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{group}\{cm:UninstallProgram,Kiosk POS}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Kiosk POS"; Filename: "{app}\main.exe"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: desktopicon

[Run]

; Initialize database during install (prepares config and DB file) and do NOT launch GUI as admin
Filename: "{app}\main.exe"; Parameters: "--initialize-db"; Description: "Initialize database"; Flags: nowait postinstall skipifsilent
Filename: "{app}\main.exe"; Parameters: "--recalc-prices"; Description: "Recalculate per-unit prices"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up database and backups on uninstall (optional - comment out to keep data)
; Type: filesandordirs; Name: "{app}\database"
; Type: filesandordirs; Name: "{app}\backups"
