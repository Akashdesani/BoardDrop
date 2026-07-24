#define MyAppName "BoardDrop"
#define MyAppVersion "2.4.1"
#define MyAppPublisher "Akash Desani"
#define MyAppURL "https://github.com/"
#define MyAppExeName "BoardDrop.exe"

[Setup]
AppId={{F95659F1-7598-4E7B-B901-79E606B7A2EB}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

PrivilegesRequired=admin

Compression=lzma2/max
SolidCompression=yes
LZMANumBlockThreads=4

WizardStyle=modern
WizardResizable=no

OutputDir=Installer
OutputBaseFilename=BoardDrop_Setup_v{#MyAppVersion}

SetupIconFile=assets\boarddrop.ico
UninstallDisplayIcon={app}\BoardDrop.exe

; Synced and updated version metadata
VersionInfoVersion=2.4.1.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=BoardDrop File Sharing Software
VersionInfoCopyright=© 2026 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

DisableProgramGroupPage=yes
DisableDirPage=no
DisableReadyMemo=no
DisableWelcomePage=no
DisableFinishedPage=no

SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create Desktop Shortcut"; GroupDescription: "Additional Icons:"; Flags: unchecked

[Files]
Source: "dist\BoardDrop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\Captcha.exe"; DestDir: "{app}"; Flags: ignoreversion
; Uninstall.exe is still copied in case you need it for debugging, 
; but the system now relies on Inno's native uninstaller to prevent double captchas.
Source: "dist\Uninstall.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\_internal"; Attribs: hidden system

[Icons]
Name: "{group}\BoardDrop"; Filename: "{app}\BoardDrop.exe"
; Pointing straight to the built-in uninstaller so it only asks for the Captcha once
Name: "{group}\Uninstall BoardDrop"; Filename: "{uninstallexe}"
Name: "{autodesktop}\BoardDrop"; Filename: "{app}\BoardDrop.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\BoardDrop.exe"; Description: "Launch BoardDrop"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    Exec(
      ExpandConstant('{cmd}'),
      '/C attrib +H +S "' + ExpandConstant('{app}\_internal') + '"',
      '',
      SW_HIDE,
      ewWaitUntilTerminated,
      ResultCode
    );
  end;
end;

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  // Executes Captcha.exe natively when the uninstaller is launched
  Result :=
    Exec(
      ExpandConstant('{app}\Captcha.exe'),
      '',
      '',
      SW_SHOWNORMAL,
      ewWaitUntilTerminated,
      ResultCode
    ) and (ResultCode = 0);

  if not Result then
    MsgBox(
      'CAPTCHA verification failed.' + #13#10 +
      'BoardDrop uninstall has been cancelled.',
      mbError,
      MB_OK
    );
end;