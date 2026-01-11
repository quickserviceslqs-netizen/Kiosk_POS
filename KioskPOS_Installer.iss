; Kiosk POS Inno Setup Script
; Version 1.003 - Production Build
;
; CRITICAL: This script MUST be run from the project root directory
; that contains the dist/, assets/, and email_config.json files.
;
; Correct usage:
;   cd C:\path\to\Kiosk_POS
;   ISCC KioskPOS_Installer.iss
;
; Or use the provided build_installer.bat file
;
; If you get "source file does not exist" errors, you are NOT in the correct directory!
;
; Alternative: Use ISCC with explicit source directory:
;   ISCC /dSourceDir="C:\path\to\Kiosk_POS" KioskPOS_Installer.iss
;
; Or define SourceDir at compile time:
;   ISCC /dSourceDir="C:\path\to\Kiosk_POS" KioskPOS_Installer.iss

#ifndef SourceDir
#define SourceDir "."
#endif

; #define SourceDir "."  ; Removed - using direct relative paths

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
; SetupIconFile=dist\main.exe  ; Removed to avoid path issues
UninstallDisplayIcon={app}\main.exe
WizardStyle=modern
DisableProgramGroupPage=yes
; SourceDir=.  ; Removed - trying explicit paths
[Dirs]
Name: "{app}\database"


[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

 [Files]
; Main executable (contains all bundled code)
Source: "{#SourceDir}\dist\main.exe"; DestDir: "{app}"; Flags: ignoreversion restartreplace

; Assets folder
Source: "{#SourceDir}\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

; Email config template
Source: "{#SourceDir}\email_config.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

[Code]
var
  ResultCode: Integer;

function CheckPythonDependencies(PythonPath: String): Boolean;
var
  TestScript: String;
  TestResult: Boolean;
begin
  // Create a temporary Python script to test dependencies
  TestScript := PythonPath + '\python.exe -c "import sys; sys.exit(0 if (';
  TestScript := TestScript + 'hasattr(__import__(\"PIL\"), \"Image\") and ';
  TestScript := TestScript + '__import__(\"tkcalendar\") and ';
  TestScript := TestScript + '__import__(\"pycountry\")) else 1)"';
  
  Exec(PythonPath + '\python.exe', '-c "import PIL.Image, tkcalendar, pycountry; print(\"Dependencies OK\")"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := (ResultCode = 0);
end;

function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  PythonPath: String;
  TestResult: Boolean;
begin
	// Check for Python installation
	PythonPath := '';
	if RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.12\InstallPath', '', PythonPath) or
	   RegQueryStringValue(HKCU, 'SOFTWARE\Python\PythonCore\3.12\InstallPath', '', PythonPath) or
	   RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.11\InstallPath', '', PythonPath) or
	   RegQueryStringValue(HKCU, 'SOFTWARE\Python\PythonCore\3.11\InstallPath', '', PythonPath) or
	   RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.10\InstallPath', '', PythonPath) or
	   RegQueryStringValue(HKCU, 'SOFTWARE\Python\PythonCore\3.10\InstallPath', '', PythonPath) then
	begin
		// Python found, check if required packages are installed
		TestResult := CheckPythonDependencies(PythonPath);
		if not TestResult then
		begin
			MsgBox('Required Python packages are missing. Please install them using: pip install pillow tkcalendar pycountry', mbError, MB_OK);
			Result := False;
			Exit;
		end;
	end
	else
	begin
		MsgBox('Python 3.10 or higher is required but not found. Please install Python from https://python.org', mbError, MB_OK);
		Result := False;
		Exit;
	end;

	// Attempt to close main.exe if running
	// Use the system taskkill.exe to terminate main.exe if it's running
	Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM main.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
	Result := True;
end;

[Icons]
Name: "{group}\Kiosk POS"; Filename: "{app}\main.exe"; IconFilename: "{app}\main.exe"
Name: "{group}\{cm:UninstallProgram,Kiosk POS}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Kiosk POS"; Filename: "{app}\main.exe"; IconFilename: "{app}\main.exe"; Tasks: desktopicon

[Run]

; Initialize database during install (prepares config and DB file) and do NOT launch GUI as admin
Filename: "{app}\main.exe"; Parameters: "--initialize-db"; Description: "Initialize database"; Flags: nowait postinstall skipifsilent
Filename: "{app}\main.exe"; Parameters: "--recalc-prices"; Description: "Recalculate per-unit prices"; Flags: nowait postinstall skipifsilent
Filename: "{app}\main.exe"; Parameters: "--health-check"; Description: "Run setup health check"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up database and backups on uninstall (optional - comment out to keep data)
; Type: filesandordirs; Name: "{app}\database"
; Type: filesandordirs; Name: "{app}\backups"
