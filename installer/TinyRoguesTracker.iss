#define MyAppName "Tiny Rogues Tracker"
#define MyAppVersion "0.4.6"
#define MyAppPublisher "JDollan"
#define MyAppExeName "TinyRoguesTracker-v0.4.6.exe"

[Setup]
AppId={{B412CE11-FE99-4F12-B724-040040040040}}
AppName={#MyAppName}
AppVersion=0.4.6
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\TinyRoguesTracker
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
OutputDir=..\dist\installer
OutputBaseFilename=TinyRoguesTracker-v0.4.6-Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\ids.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall
