; Declarative installer recipe for an unsigned onboard-next preview.
; The compiler receives AppVersion, Architecture, InputDir and OutputDir from
; tools/build.py. This is not a stable release installer and must not be signed
; or published until the protected stable-release process is enabled.

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#ifndef Architecture
  #define Architecture "x64"
#endif
#ifndef InputDir
  #error "InputDir must identify the staged preview directory"
#endif
#ifndef OutputDir
  #error "OutputDir must identify the installer output directory"
#endif

#define AppName "Onboard Next"
#define AppPublisher "Onboard"
#define AppURL "https://github.com/Alaa91H/onboard"
#define AppExecutable "onboard-next.exe"
#define AppId "{{B147D4C2-62FE-4B64-85A8-8A4BF6B87078}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\Onboard Next
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=onboard-next-preview-{#AppVersion}-windows-{#Architecture}-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExecutable}
ArchitecturesAllowed={#if Architecture == "arm64"}arm64{#else}x64compatible{#endif}
ArchitecturesInstallIn64BitMode={#if Architecture == "arm64"}arm64{#else}x64compatible{#endif}

[Files]
Source: "{#InputDir}\{#AppExecutable}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#InputDir}\provenance.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#InputDir}\SHA256SUMS"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExecutable}"
Name: "{autoprograms}\Uninstall {#AppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#AppExecutable}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
