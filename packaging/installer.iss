; packaging/installer.iss
; Inno Setup script for Scan2Connect. Build:
;   1. pyinstaller packaging/scan2connect.spec   (produces dist/Scan2Connect/)
;   2. iscc /DAppVersion=<version> packaging/installer.iss
;
; <version> must match pyproject.toml's `version = "..."` (e.g. 0.1.0) — ISPP
; has no TOML parser, so the caller (a person, or the E-18 CI workflow) reads
; it from pyproject.toml and passes it in with /D rather than this script
; trying to parse TOML itself. AppVersion below is only a fallback for a
; manual `iscc packaging/installer.iss` run with no /D override.

#define AppName "Scan2Connect"
#define AppPublisher "Aadarsha Bhattarai"
#define AppURL "https://github.com/aadarshaAB/Scan2Connect"
#define RepoRoot ".."
#define DistDir RepoRoot + "\dist\Scan2Connect"
#define AppExeName "Scan2Connect.exe"

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{9A6E7C7E-9C0A-4A6B-9C3B-2F2D6F2D9A11}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir={#RepoRoot}\dist
OutputBaseFilename=Scan2Connect-{#AppVersion}-setup
SetupIconFile={#RepoRoot}\scan2connect\assets\app_icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
