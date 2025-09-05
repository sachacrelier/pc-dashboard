# 🖥️ PC Dashboard

Une application créée en **Python**, disponible sur **Windows, Linux et macOS**, qui permet de **surveiller son PC en temps réel** : CPU, RAM, disque, réseau, températures, batterie…  
Elle inclut également des **actions système** (redémarrage, arrêt, veille, verrouillage, gestionnaire de tâches, etc.).

---

## ✨ Fonctionnalités

- 📊 **CPU**
  - Utilisation globale et par cœur
  - Historique graphique (60 dernières secondes)

- 💾 **RAM et disque**
  - Mémoire utilisée et totale (en valeur et en pourcentage)
  - Utilisation du disque principal

- 🌐 **Réseau**
  - Débit montant et descendant en temps réel

- 🌡️ **Températures**
  - Récupérées via `psutil` (si supporté par l’OS et le matériel)

- 🔋 **Batterie**
  - Niveau en % et état (en charge ou sur batterie)

- 🖥️ **Infos système**
  - Nom du PC, OS, architecture, CPU, GPU, carte mère

- ⚡ **Actions système rapides**
  - 🔄 Redémarrer
  - ⏻ Éteindre
  - 👤 Fermer la session
  - 😴 Mettre en veille
  - 🔒 Verrouiller l’écran
  - 📂 Ouvrir le gestionnaire de tâches (ou équivalent selon OS)

---

## 🚀 Installation

### 1. Installer Python

#### Windows
1. Télécharger Python depuis [python.org](https://www.python.org/downloads/).
2. Lors de l’installation, cocher **"Add Python to PATH"**.
3. Vérifier l’installation avec :
```bash
python --version
```

#### macOS
1. Télécharger le fichier .pkg depuis [python.org](https://www.python.org/downloads/macos/)
2. Lancer l’installation.
3. Vérifier avec :
```bash
python3 --version
```

#### Linux
Python est souvent déjà installé. Vérifier avec :
```bash
python3 --version
```

Si nécessaire :
```bash
sudo apt install python3 python3-pip python3-tk
```

### 2. Cloner le dépôt
```bash
git clone https://github.com/sachacrelier/pc-dashboard.git
cd pc-dashboard
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Lancer l’application
```bash
python dashboard.py
```

## 📦 Prérequis

- Python **3.6 ou supérieur**
- Modules listés dans `requirements.txt`
- **tkinter** (inclus par défaut avec Python sur Windows/macOS, peut nécessiter installation sur Linux via `sudo apt install python3-tk`)

## ⚠️ Disclaimer

Ce logiciel est 100% légal et ne contient aucun malware ni virus.
Vous pouvez l’utiliser en toute confiance.