#!/bin/bash

echo "Initialisation du contrôleur Bluetooth pour Herbinator..."

# S'assurer que le service principal tourne
sudo systemctl start bluetooth

# Injection des commandes dans bluetoothctl
sudo bluetoothctl <<EOF
power on
pairable on
discoverable on
menu advertise
name on
back
advertise on
quit
EOF

sudo sdptool add SP

echo "Configuration terminée : visibilité classique et diffusion BLE activées."
