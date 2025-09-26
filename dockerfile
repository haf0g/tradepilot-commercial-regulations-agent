# Dockerfile
# Étape 1 : Image de base avec Python
FROM python:3.10-slim

# Étape 2 : Arguments et Variables d'Environnement
# Permet de passer la clé API lors du build (optionnel) ou de la définir à l'exécution
ARG GROQ_API_KEY_ARG
ENV GROQ_API_KEY=${GROQ_API_KEY_ARG}

# Définir le répertoire de travail à l'intérieur du conteneur
WORKDIR /app

# Étape 3 : Installation des Dépendances Système pour Playwright
# Installe les bibliothèques système nécessaires pour que Chromium (utilisé par Playwright) fonctionne
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libatk1.0-0 \
    libgtk-3-0 \
    xvfb \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Étape 4 : Copie des Fichiers de Dépendances
# Copier requirements.txt en premier pour tirer parti du cache Docker
# si les dépendances n'ont pas changé
COPY requirements.txt .

# Étape 5 : Installation des Dépendances Python
# Mettre à jour pip
RUN pip install --no-cache-dir --upgrade pip
# Installer les dépendances Python du projet
RUN pip install --no-cache-dir -r requirements.txt

# Étape 6 : Installation des Dépendances de Navigateur pour Playwright
# Cela télécharge et installe le(s) navigateur(s) (chromium, firefox, webkit)
# Comme Playwright est utilisé, on installe Chromium (navigateur par défaut souvent utilisé)
RUN playwright install-deps
RUN playwright install chromium

# Étape 7 : Copie du Code Source de l'Application
# Copier le reste du code de l'application
# (Cela inclut app.py, config.py, les dossiers data/, scraper/, core/, etc.)
COPY . .

# Étape 8 : Exposition du Port
# Gradio écoute par défaut sur le port 7860
EXPOSE 7860

# Étape 9 : Commande de Démarrage
# Démarre l'application Gradio
# '--host 0.0.0.0' permet à Gradio d'écouter sur toutes les interfaces réseau
# du conteneur, ce qui est nécessaire pour y accéder depuis l'extérieur.
CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "7860"]
