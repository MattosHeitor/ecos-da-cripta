; O instalador do Ecos da Cripta para Windows (Inno Setup 6). Não compile direto: use
;     python ferramentas/instalador/construir.py
; (ele faz antes a pasta do jogo com o PyInstaller e passa /DVersao=... e /DRaiz=...).
;
; Instala só para quem está usando o PC (sem pedir administrador): %LOCALAPPDATA%\Programs\Ecos da Cripta.
; Atalhos no Menu Iniciar e (marcado) na Área de Trabalho; desinstalador em "Aplicativos" do Windows.
; Os saves ficam em %APPDATA%\Ecos da Cripta: desinstalar ou reinstalar NÃO mexe neles.

#ifndef Versao
  #define Versao "0.0.0"
#endif
#ifndef Raiz
  #define Raiz AddBackslash(SourcePath) + "..\.."
#endif
#define Nome "Ecos da Cripta"
#define Executavel "Ecos da Cripta.exe"
#define IdDoApp "EcosDaCripta.Jogo"
#define Tutorial "Como instalar e jogar.html"

[Setup]
AppId={{93A4C2A6-E9E7-4694-9CCC-44AD0A0A04B8}
AppName={#Nome}
AppVersion={#Versao}
AppVerName={#Nome} {#Versao}
AppPublisher={#Nome}
DefaultDirName={autopf}\{#Nome}
DefaultGroupName={#Nome}
DisableProgramGroupPage=yes
DisableDirPage=yes
DisableReadyPage=yes
PrivilegesRequired=lowest
OutputDir={#Raiz}\dist
OutputBaseFilename=Instalar {#Nome} {#Versao}
SetupIconFile={#Raiz}\assets\icone\ecos_da_cripta.ico
UninstallDisplayIcon={app}\{#Executavel}
UninstallDisplayName={#Nome}
VersionInfoVersion={#Versao}
VersionInfoProductName={#Nome}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "atalho"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; (a versão nova não herda arquivos que a antiga tinha e ela não tem mais)
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#Raiz}\dist\{#Nome}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; (o tutorial com as imagens embutidas, que o construir.py monta em build/)
Source: "{#Raiz}\build\{#Tutorial}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#Nome}"; Filename: "{app}\{#Executavel}"; AppUserModelID: "{#IdDoApp}"
Name: "{autodesktop}\{#Nome}"; Filename: "{app}\{#Executavel}"; Tasks: atalho; AppUserModelID: "{#IdDoApp}"
Name: "{autoprograms}\{#Nome} - como instalar e jogar"; Filename: "{app}\{#Tutorial}"

[Run]
Filename: "{app}\{#Executavel}"; Description: "{cm:LaunchProgram,{#Nome}}"; Flags: nowait postinstall skipifsilent
