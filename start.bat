@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"
title Ses'Club - Serveur de developpement
color 0B

echo.
echo  +===========================================+
echo  ^|   SES'CLUB - SESAME School Platform      ^|
echo  ^|   Plateforme de gestion des clubs        ^|
echo  +===========================================+
echo.

:: 1. Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python introuvable.
    echo         Installez-le depuis https://python.org puis relancez.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2>&1') do echo [OK] %%v detecte.

:: 2. Pipenv
pipenv --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Pipenv absent -- installation en cours...
    pip install pipenv
    if errorlevel 1 (
        echo [ERREUR] Echec installation Pipenv.
        pause & exit /b 1
    )
)
echo [OK] Pipenv pret.

:: 3. Dependances
if exist Pipfile (
    echo [INFO] Pipfile trouve -- installation des dependances...
    echo [INFO] Cela peut prendre 1-2 minutes la premiere fois...
    pipenv install
    if errorlevel 1 (
        echo [ERREUR] Echec installation des dependances.
        pause & exit /b 1
    )
    echo [OK] Dependances installees.
) else (
    echo [AVERTISSEMENT] Pas de Pipfile trouve -- etape ignoree.
)

:: 4. Fichier .env
if not exist .env (
    if exist .env.example (
        echo [AVERTISSEMENT] .env manquant -- copie depuis .env.example...
        copy .env.example .env >nul
    ) else (
        echo [ERREUR] Ni .env ni .env.example trouves.
        pause & exit /b 1
    )
    echo [ACTION] Configurez vos identifiants DB dans .env puis fermez Notepad.
    start /wait notepad .env
    echo [OK] .env configure.
)
echo [OK] .env present.

:: 5. Port
set PORT_CHOICE=8000
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo [AVERTISSEMENT] Le port 8000 est deja utilise.
    set /p PORT_CHOICE="Entrez un autre port (ex: 8080) ou Entree pour 8000 : "
    if "!PORT_CHOICE!"=="" set PORT_CHOICE=8000
)

:: 6. Migrations
echo [INFO] Application des migrations...
pipenv run python manage.py migrate
if errorlevel 1 (
    echo [ERREUR] Les migrations ont echoue. Verifiez votre config DB dans .env.
    pause & exit /b 1
)
echo [OK] Base de donnees prete.

:: 7. Portail
if exist "%~dp0frontend\index.html" (
    echo [INFO] Ouverture du portail frontend...
    start "" "%~dp0frontend\index.html"
) else (
    echo [AVERTISSEMENT] frontend\index.html introuvable -- portail non ouvert.
)

:: 8. Lancement
echo.
echo  +===========================================+
echo  ^|  Serveur:  http://127.0.0.1:!PORT_CHOICE!
echo  ^|  Portail:  frontend/index.html
echo  ^|  Etudiant: frontend/student.html
echo  ^|  Club:     frontend/club.html
echo  ^|  Admin:    frontend/admin.html
echo  ^|  Ctrl+C pour arreter
echo  +===========================================+
echo.
pipenv run python manage.py runserver !PORT_CHOICE!

echo.
echo [INFO] Serveur arrete.
pause