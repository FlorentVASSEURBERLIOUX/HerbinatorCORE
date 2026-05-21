#!/bin/bash

# ==================================================================
# HERBINATOR - Script d'installation automatisé pour Raspberry Pi 5
# ==================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}          Installation de l'environnement HERBINATOR    ${NC}"

echo -e "\n${YELLOW} Mise à jour des paquets du système...${NC}"
sudo apt update && sudo apt upgrade -y

echo -e "\n${YELLOW}Installation des outils système...${NC}"
sudo apt install -y git htop tmux tree curl build-essential python3-pip python3-venv
sudo apt install -y libcamera-apps libcamera-dev python3-opencv python3-picamera2
sudo apt install -y bluez bluetooth pi-bluetooth
sudo apt install -y code
sudo apt install -y gedit

echo -e "\n${YELLOW}Configuration de l'environnement virtuel Python (PEP 668)...${NC}"
PROJECT_DIR="$HOME/HerbinatorCORE"

if [ ! -d "$PROJECT_DIR" ]; then
    mkdir -p "$PROJECT_DIR"
    echo -e "${GREEN}Dossier $PROJECT_DIR créé.${NC}"
fi

cd "$PROJECT_DIR" || exit

echo -e "Création de l'environnement virtuel (env) avec accès aux paquets système..."
python3 -m venv env --system-site-packages

echo -e "\n${YELLOW}Installation des bibliothèques Python dans l'environnement...${NC}"
./env/bin/pip install --upgrade pip
./env/bin/pip install pyserial bleak


cat << 'EOF' > start_env.sh
#!/bin/bash
cd ~/HerbinatorCORE

RC_TMP=$(mktemp)
cat ~/.bashrc > "$RC_TMP"
echo "source ~/HerbinatorCORE/env/bin/activate" >> "$RC_TMP"
echo "echo '======================================================='" >> "$RC_TMP"
echo "echo ' Environnement lancé ! (env)'" >> "$RC_TMP"
echo "echo ' Tapez 'exit' pour sortir.'" >> "$RC_TMP"
echo "echo '======================================================='" >> "$RC_TMP"
echo "rm -f \"\$RC_TMP\"" >> "$RC_TMP" 

exec bash --rcfile "$RC_TMP"
EOF

chmod +x start_env.sh

echo -e "${GREEN} Installation terminée avec succès !${NC}"
echo -e "Pour travailler dans votre environnement virtuel :"
echo -e "Lancez l'environnement avec ${BLUE}./start_env.sh${NC}"
