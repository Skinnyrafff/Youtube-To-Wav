; Instalador de LA CIFRA DOWNLOADER (Inno Setup 6).
; Se compila con tools\build.ps1, que le pasa /DAppVersion=X.Y.Z

#define AppName "LA CIFRA DOWNLOADER"
#define AppExe "LaCifraDownloader.exe"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
; No cambiar AppId: es lo que permite que una versión nueva actualice a la anterior
AppId={{6E0C9B52-2F7A-4C1E-9A3D-5B8C1F4E7A21}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=LA CIFRA
AppPublisherURL=https://github.com/Skinnyrafff/Youtube-To-Wav
; Se instala para el usuario actual: no pide permisos de administrador
PrivilegesRequired=lowest
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
OutputDir=..\dist\installer
OutputBaseFilename=LaCifraDownloader-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[InstallDelete]
; Al actualizar, borra los archivos de la versión anterior antes de copiar los nuevos
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\LaCifraDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; Instalación normal: casilla "Abrir" al final
Filename: "{app}\{#AppExe}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent
; Actualización desde la app (modo silencioso): la vuelve a abrir sola
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: WizardSilent
