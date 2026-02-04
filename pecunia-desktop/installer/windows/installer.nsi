; ============================================================================
; Pecunia Desktop - NSIS Installer Script
; ============================================================================
;
; NSIS (Nullsoft Scriptable Install System) installer for Windows
; Requires NSIS 3.x: https://nsis.sourceforge.io/
;
; Build command:
;   makensis /DVERSION=1.0.0 /DEXE_PATH="..\..\dist\Pecunia.exe" installer.nsi
;
; ============================================================================

; ----------------------------------------------------------------------------
; Installer Attributes
; ----------------------------------------------------------------------------

!ifndef VERSION
    !define VERSION "1.0.0"
!endif

!ifndef APP_NAME
    !define APP_NAME "Pecunia"
!endif

!define PUBLISHER "Pecunia Inc."
!define WEB_SITE "https://pecunia.com"
!define INSTALL_DIR "$PROGRAMFILES64\${APP_NAME}"
!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
!define UNINST_ROOT_KEY "HKLM"

; File associations
!define FILE_EXT ".pecunia"
!define FILE_TYPE "Pecunia.DataFile"

; Input files (can be overridden via command line)
!ifndef EXE_PATH
    !define EXE_PATH "..\..\dist\Pecunia.exe"
!endif

!ifndef OUTPUT_PATH
    !define OUTPUT_PATH "..\..\dist\${APP_NAME}-${VERSION}-Setup.exe"
!endif

; ----------------------------------------------------------------------------
; Modern UI Configuration
; ----------------------------------------------------------------------------

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"
!include "WinVer.nsh"
!include "x64.nsh"

; General settings
Name "${APP_NAME} ${VERSION}"
OutFile "${OUTPUT_PATH}"
InstallDir "${INSTALL_DIR}"
InstallDirRegKey ${UNINST_ROOT_KEY} "${UNINST_KEY}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
Unicode True

; Branding
BrandingText "${APP_NAME} ${VERSION}"

; Version information for the installer
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${APP_NAME}"
VIAddVersionKey "CompanyName" "${PUBLISHER}"
VIAddVersionKey "LegalCopyright" "Copyright (c) 2024 ${PUBLISHER}"
VIAddVersionKey "FileDescription" "${APP_NAME} Installer"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"

; ----------------------------------------------------------------------------
; Modern UI Settings
; ----------------------------------------------------------------------------

!define MUI_ABORTWARNING
!define MUI_UNABORTWARNING
!define MUI_FINISHPAGE_NOAUTOCLOSE
!define MUI_UNFINISHPAGE_NOAUTOCLOSE

; Icons (optional - uncomment if you have custom icons)
; !define MUI_ICON "..\..\resources\icons\installer.ico"
; !define MUI_UNICON "..\..\resources\icons\uninstaller.ico"

; Header image (optional - 150x57 pixels recommended)
; !define MUI_HEADERIMAGE
; !define MUI_HEADERIMAGE_RIGHT
; !define MUI_HEADERIMAGE_BITMAP "header.bmp"

; Welcome page image (optional - 164x314 pixels recommended)
; !define MUI_WELCOMEFINISHPAGE_BITMAP "welcome.bmp"

; Finish page settings
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_NAME}.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME}"
!define MUI_FINISHPAGE_LINK "Visit ${APP_NAME} website"
!define MUI_FINISHPAGE_LINK_LOCATION "${WEB_SITE}"

; ----------------------------------------------------------------------------
; Installer Pages
; ----------------------------------------------------------------------------

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; ----------------------------------------------------------------------------
; Languages
; ----------------------------------------------------------------------------

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "French"

; Language strings
LangString DESC_SecMain ${LANG_ENGLISH} "Install ${APP_NAME} application files."
LangString DESC_SecMain ${LANG_FRENCH} "Installer les fichiers de l'application ${APP_NAME}."

LangString DESC_SecShortcuts ${LANG_ENGLISH} "Create Start Menu and Desktop shortcuts."
LangString DESC_SecShortcuts ${LANG_FRENCH} "Creer des raccourcis dans le menu Demarrer et sur le Bureau."

LangString DESC_SecFileAssoc ${LANG_ENGLISH} "Associate .pecunia files with ${APP_NAME}."
LangString DESC_SecFileAssoc ${LANG_FRENCH} "Associer les fichiers .pecunia avec ${APP_NAME}."

LangString DESC_SecStartup ${LANG_ENGLISH} "Start ${APP_NAME} automatically when Windows starts."
LangString DESC_SecStartup ${LANG_FRENCH} "Demarrer ${APP_NAME} automatiquement au demarrage de Windows."

; ----------------------------------------------------------------------------
; Installer Sections
; ----------------------------------------------------------------------------

Section "!${APP_NAME} Core" SecMain
    SectionIn RO  ; Required section

    ; Set output path
    SetOutPath "$INSTDIR"

    ; Check if application is running
    Call CloseRunningApp

    ; Install main executable
    File "${EXE_PATH}"

    ; Install additional resources (if using one-dir build)
    ; File /r "..\..\dist\${APP_NAME}\*.*"

    ; Store installation folder
    WriteRegStr ${UNINST_ROOT_KEY} "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr ${UNINST_ROOT_KEY} "${UNINST_KEY}" "DisplayName" "${APP_NAME}"
    WriteRegStr ${UNINST_ROOT_KEY} "${UNINST_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr ${UNINST_ROOT_KEY} "${UNINST_KEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
    WriteRegStr ${UNINST_ROOT_KEY} "${UNINST_KEY}" "DisplayIcon" "$INSTDIR\${APP_NAME}.exe"
    WriteRegStr ${UNINST_ROOT_KEY} "${UNINST_KEY}" "Publisher" "${PUBLISHER}"
    WriteRegStr ${UNINST_ROOT_KEY} "${UNINST_KEY}" "URLInfoAbout" "${WEB_SITE}"
    WriteRegStr ${UNINST_ROOT_KEY} "${UNINST_KEY}" "DisplayVersion" "${VERSION}"
    WriteRegDWORD ${UNINST_ROOT_KEY} "${UNINST_KEY}" "NoModify" 1
    WriteRegDWORD ${UNINST_ROOT_KEY} "${UNINST_KEY}" "NoRepair" 1

    ; Calculate installed size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD ${UNINST_ROOT_KEY} "${UNINST_KEY}" "EstimatedSize" "$0"

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Shortcuts" SecShortcuts
    ; Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_NAME}.exe" "" "$INSTDIR\${APP_NAME}.exe" 0
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0

    ; Desktop shortcut
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_NAME}.exe" "" "$INSTDIR\${APP_NAME}.exe" 0
SectionEnd

Section "File Associations" SecFileAssoc
    ; Register file extension
    WriteRegStr HKCR "${FILE_EXT}" "" "${FILE_TYPE}"
    WriteRegStr HKCR "${FILE_TYPE}" "" "${APP_NAME} Data File"
    WriteRegStr HKCR "${FILE_TYPE}\DefaultIcon" "" "$INSTDIR\${APP_NAME}.exe,0"
    WriteRegStr HKCR "${FILE_TYPE}\shell\open\command" "" '"$INSTDIR\${APP_NAME}.exe" "%1"'

    ; Register URL protocol (pecunia://)
    WriteRegStr HKCR "pecunia" "" "URL:${APP_NAME} Protocol"
    WriteRegStr HKCR "pecunia" "URL Protocol" ""
    WriteRegStr HKCR "pecunia\DefaultIcon" "" "$INSTDIR\${APP_NAME}.exe,0"
    WriteRegStr HKCR "pecunia\shell\open\command" "" '"$INSTDIR\${APP_NAME}.exe" "%1"'

    ; Refresh shell icons
    System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, i 0, i 0)'
SectionEnd

Section "Start with Windows" SecStartup
    ; Add to startup (current user)
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}" '"$INSTDIR\${APP_NAME}.exe" --minimized'
SectionEnd

; ----------------------------------------------------------------------------
; Section Descriptions
; ----------------------------------------------------------------------------

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} $(DESC_SecMain)
    !insertmacro MUI_DESCRIPTION_TEXT ${SecShortcuts} $(DESC_SecShortcuts)
    !insertmacro MUI_DESCRIPTION_TEXT ${SecFileAssoc} $(DESC_SecFileAssoc)
    !insertmacro MUI_DESCRIPTION_TEXT ${SecStartup} $(DESC_SecStartup)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ----------------------------------------------------------------------------
; Uninstaller Section
; ----------------------------------------------------------------------------

Section "Uninstall"
    ; Close running application
    Call un.CloseRunningApp

    ; Remove files
    Delete "$INSTDIR\${APP_NAME}.exe"
    Delete "$INSTDIR\Uninstall.exe"

    ; Remove directories (if using one-dir build)
    ; RMDir /r "$INSTDIR\_internal"

    ; Remove installation directory (if empty)
    RMDir "$INSTDIR"

    ; Remove Start Menu shortcuts
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"

    ; Remove Desktop shortcut
    Delete "$DESKTOP\${APP_NAME}.lnk"

    ; Remove registry keys
    DeleteRegKey ${UNINST_ROOT_KEY} "${UNINST_KEY}"

    ; Remove file associations
    DeleteRegKey HKCR "${FILE_EXT}"
    DeleteRegKey HKCR "${FILE_TYPE}"
    DeleteRegKey HKCR "pecunia"

    ; Remove startup entry
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}"

    ; Refresh shell icons
    System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, i 0, i 0)'

    ; Optional: Remove user data (ask first)
    MessageBox MB_YESNO|MB_ICONQUESTION "Do you want to remove your ${APP_NAME} data and settings?$\n$\nThis includes your financial data, preferences, and settings." IDNO SkipDataRemoval
        RMDir /r "$LOCALAPPDATA\${APP_NAME}"
        RMDir /r "$APPDATA\${APP_NAME}"
    SkipDataRemoval:
SectionEnd

; ----------------------------------------------------------------------------
; Functions
; ----------------------------------------------------------------------------

Function .onInit
    ; Check Windows version (require Windows 10 or later)
    ${IfNot} ${AtLeastWin10}
        MessageBox MB_OK|MB_ICONSTOP "${APP_NAME} requires Windows 10 or later."
        Abort
    ${EndIf}

    ; Check 64-bit
    ${IfNot} ${RunningX64}
        MessageBox MB_OK|MB_ICONSTOP "${APP_NAME} requires a 64-bit version of Windows."
        Abort
    ${EndIf}

    ; Set 64-bit registry view and install dir
    SetRegView 64

    ; Check for existing installation
    ReadRegStr $0 ${UNINST_ROOT_KEY} "${UNINST_KEY}" "InstallLocation"
    ${If} $0 != ""
        MessageBox MB_YESNO|MB_ICONQUESTION "${APP_NAME} is already installed.$\n$\nDo you want to uninstall the previous version first?" IDNO ContinueInstall
            ; Run uninstaller
            ExecWait '"$0\Uninstall.exe" /S _?=$0'
            ; Refresh after uninstall
            Delete "$0\Uninstall.exe"
            RMDir "$0"
        ContinueInstall:
    ${EndIf}

    ; Language selection
    !insertmacro MUI_LANGDLL_DISPLAY
FunctionEnd

Function un.onInit
    ; Set 64-bit registry view
    SetRegView 64

    ; Language selection for uninstaller
    !insertmacro MUI_UNGETLANGUAGE
FunctionEnd

Function CloseRunningApp
    ; Try to close running instance gracefully
    FindWindow $0 "" "${APP_NAME}"
    ${If} $0 != 0
        MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "${APP_NAME} is currently running.$\n$\nClick OK to close it and continue installation, or Cancel to abort." IDOK CloseApp
            Abort
        CloseApp:
        ; Send WM_CLOSE message
        SendMessage $0 0x0010 0 0  ; WM_CLOSE = 0x0010
        ; Wait a moment for graceful shutdown
        Sleep 2000
        ; Force kill if still running
        FindWindow $0 "" "${APP_NAME}"
        ${If} $0 != 0
            ; Use taskkill as fallback
            nsExec::ExecToLog 'taskkill /F /IM "${APP_NAME}.exe"'
            Sleep 1000
        ${EndIf}
    ${EndIf}
FunctionEnd

Function un.CloseRunningApp
    ; Same logic for uninstaller
    FindWindow $0 "" "${APP_NAME}"
    ${If} $0 != 0
        MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "${APP_NAME} is currently running.$\n$\nClick OK to close it and continue uninstallation, or Cancel to abort." IDOK un.CloseApp
            Abort
        un.CloseApp:
        SendMessage $0 0x0010 0 0
        Sleep 2000
        FindWindow $0 "" "${APP_NAME}"
        ${If} $0 != 0
            nsExec::ExecToLog 'taskkill /F /IM "${APP_NAME}.exe"'
            Sleep 1000
        ${EndIf}
    ${EndIf}
FunctionEnd

; ----------------------------------------------------------------------------
; Include License File (create if not exists)
; ----------------------------------------------------------------------------

; Create a basic license file if building without one
!ifndef LICENSE_FILE
    !tempfile LICENSE_TEMP
    !appendfile "${LICENSE_TEMP}" "${APP_NAME} - Personal Finance Management Application$\r$\n"
    !appendfile "${LICENSE_TEMP}" "========================================$\r$\n"
    !appendfile "${LICENSE_TEMP}" "$\r$\n"
    !appendfile "${LICENSE_TEMP}" "Copyright (c) 2024 ${PUBLISHER}$\r$\n"
    !appendfile "${LICENSE_TEMP}" "All rights reserved.$\r$\n"
    !appendfile "${LICENSE_TEMP}" "$\r$\n"
    !appendfile "${LICENSE_TEMP}" "This software is proprietary and confidential.$\r$\n"
    !appendfile "${LICENSE_TEMP}" "Unauthorized copying, distribution, or use of this software,$\r$\n"
    !appendfile "${LICENSE_TEMP}" "via any medium, is strictly prohibited.$\r$\n"
    !appendfile "${LICENSE_TEMP}" "$\r$\n"
    !appendfile "${LICENSE_TEMP}" "By installing this software, you agree to the terms of use$\r$\n"
    !appendfile "${LICENSE_TEMP}" "available at ${WEB_SITE}/terms$\r$\n"
!endif
