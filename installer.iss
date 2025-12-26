; Inno Setup Script for Conditioning Control Panel
; Download Inno Setup from: https://jrsoftware.org/isdl.php

#define MyAppName "Conditioning Control Panel"
#define MyAppVersion "2.1.0"
#define MyAppPublisher "Anonymous"
#define MyAppExeName "ConditioningControlPanel.exe"

[Setup]
; Basic info
AppId={{B4E7C8A1-9F3D-4E5B-A2C1-8D6F4E9B3C7A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=ConditioningControlPanel_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Require admin for install (needed for some features)
PrivilegesRequired=admin

; Visual settings
SetupIconFile=assets\Conditioning Control Panel.ico
WizardImageFile=assets\installer_banner.bmp
WizardSmallImageFile=assets\installer_icon.bmp

; Uninstall info
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main executable
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Assets folder
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

; Presets file (if exists)
Source: "presets.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

; NOTE: Don't copy settings.json - let user start fresh or keep existing

[Dirs]
; Create required directories
Name: "{app}\assets\images"
Name: "{app}\assets\sounds"
Name: "{app}\assets\startle_videos"
Name: "{app}\assets\sub_audio"
Name: "{app}\assets\backgrounds"
Name: "{app}\logs"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Option to launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up logs on uninstall (but not user settings)
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\*.log"

[Code]
// Check if app is running before install/uninstall
function IsAppRunning(): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if Exec('tasklist', '/FI "IMAGENAME eq {#MyAppExeName}" /NH', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    // If tasklist finds the process, it returns specific output
    // This is a simplified check
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    // Could add pre-install checks here
  end;
end;

// Show custom welcome message
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  
  if CurPageID = wpWelcome then
  begin
    // Could add custom validation here
  end;
end;
