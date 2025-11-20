# Script de lancement automatique pour Sondage Hassi Elbekay
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   INSTALLATION ET LANCEMENT DU SONDAGE VOCAL     " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Vérification de Python
$pythonExists = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonExists) {
    Write-Error "Python n'est pas installé. Veuillez installer Python (cochez 'Add to PATH') et relancez."
    Pause
    Exit
}

# 2. Création d'un environnement virtuel (pour ne pas polluer le PC)
if (-not (Test-Path "venv")) {
    Write-Host "Création de l'environnement virtuel..." -ForegroundColor Yellow
    python -m venv venv
}

# 3. Activation et Installation des dépendances
Write-Host "Installation des librairies nécessaires..." -ForegroundColor Yellow
.\venv\Scripts\python -m pip install --upgrade pip
.\venv\Scripts\python -m pip install streamlit gspread oauth2client pandas gtts

# 4. Vérification du fichier credentials
if (-not (Test-Path "credentials.json")) {
    Write-Host "⚠️ ATTENTION: Le fichier 'credentials.json' est manquant!" -ForegroundColor Red
    Write-Host "Veuillez placer votre clé JSON Google dans ce dossier."
    Pause
    Exit
}

# 5. Lancement de l'application
Write-Host "Lancement de l'application de sondage..." -ForegroundColor Green
Write-Host "Le navigateur va s'ouvrir dans 3 secondes..." -ForegroundColor Green

# On force l'ouverture du navigateur
Start-Process "http://localhost:8501"

# On lance le serveur
.\venv\Scripts\streamlit run app.py