; =====================================================================
; GlassWidgets - Inno Setup 6 Installer Script
; =====================================================================

#define MyAppName "GlassWidgets"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "GlassWidgets"
#define MyAppURL "https://github.com/glasswidgets/widgets"
#define MyAppExeName "GlassWidgets.exe"

[Setup]
; Unique application GUID
AppId={{2EC6540B-3877-4EBC-90E8-52EFDA11AFA9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename=GlassWidgets_Setup
SetupIconFile=assets\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force
CloseApplicationsFilter=*.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Launch GlassWidgets on Windows startup"; GroupDescription: "Startup options:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\app_icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: isreadme ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
var
  RemoveDataCheckBox: TCheckBox;

procedure InitializeUninstallProgressForm();
begin
  RemoveDataCheckBox := TCheckBox.Create(UninstallProgressForm);
  RemoveDataCheckBox.Parent := UninstallProgressForm;
  RemoveDataCheckBox.Caption := 'Remove saved widget layouts, configurations, and cache (%APPDATA%\GlassWidgets)';
  RemoveDataCheckBox.Left := ScaleX(20);
  RemoveDataCheckBox.Top := UninstallProgressForm.ClientHeight - ScaleY(42);
  RemoveDataCheckBox.Width := UninstallProgressForm.ClientWidth - ScaleX(40);
  RemoveDataCheckBox.Checked := False;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataDir: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if (RemoveDataCheckBox <> nil) and (RemoveDataCheckBox.Checked) then
    begin
      AppDataDir := ExpandConstant('{userappdata}\GlassWidgets');
      if DirExists(AppDataDir) then
        DelTree(AppDataDir, True, True, True);
    end;
  end;
end;
