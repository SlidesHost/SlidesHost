#define AppName "SlidesHost"
#define AppVersion "1.0.0"
#define AppPublisher "T3apps"
#define AppExeName "SlidesHost.exe"

[Setup]
AppId={{BCF12B0D-752F-4F87-B732-9C20A91F5663}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=SlidesHost Setup
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
VersionInfoVersion=1.0.0.0
DefaultDirName={autopf}\{#AppName}
UsePreviousAppDir=no
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
OutputDir=dist
OutputBaseFilename=SlidesHost-Setup
SetupIconFile=logo.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\SlidesHost\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SlidesHost"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\SlidesHost"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch SlidesHost"; Flags: postinstall skipifsilent
