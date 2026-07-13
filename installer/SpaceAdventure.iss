; Inno Setup script for Space Adventure.
; Compiled by CI:  ISCC /DMyAppVersion=x.y.z installer\SpaceAdventure.iss
; Packages the PyInstaller onedir output (dist\SpaceAdventure\) into a single
; installable Setup.exe: Program Files install, shortcuts, and an uninstaller.

#define MyAppName "Space Adventure"
#define MyAppPublisher "Faisal Rasheed"
#define MyAppExeName "SpaceAdventure.exe"
#define MyAppURL "https://github.com/faisalrasheed442/space-invaders-pygame"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

[Setup]
; AppId is a FIXED GUID — never change it. It makes every new version upgrade
; in place and keeps a single uninstall entry.
AppId={{B7E9B3B2-3C1A-4E4D-9F2A-8A1C5E7D6F01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\SpaceAdventure
DefaultGroupName=Space Adventure
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
; Paths are relative to this script's dir (installer/), so reach up to the repo
; root where the build output and generated icon live.
OutputDir=..\installer_output
OutputBaseFilename=SpaceAdventureSetup
SetupIconFile=..\app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
; Let a silent auto-update close the running app so its files aren't locked.
CloseApplications=yes
; We relaunch the app ourselves, so Windows shouldn't.
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "..\dist\SpaceAdventure\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Space Adventure"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall Space Adventure"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Space Adventure"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Interactive install: offer to launch (skipped during a silent auto-update).
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Space Adventure"; Flags: nowait postinstall skipifsilent
; Silent auto-update: relaunch the app de-elevated so it doesn't run as admin.
Filename: "{app}\{#MyAppExeName}"; Flags: nowait runasoriginaluser skipifnotsilent
