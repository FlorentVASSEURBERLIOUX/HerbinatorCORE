#!/bin/bash

echo "Initialisation du contrôleur Bluetooth pour Herbinator..."

# Sécurité d'attente : tant que bluetoothctl ne répond pas, on attend 1 seconde
until bluetoothctl show >/dev/null 2>&1; do
    echo "[BLUETOOTH] En attente de l'initialisation de la pile BlueZ..."
    sleep 1
done

# Injection des configurations
bluetoothctl <<EOF
power on
pairable on
discoverable on
menu advertise
name on
back
advertise on
quit
EOF

# Petite pause pour laisser le temps au contrôleur d'appliquer les changements
sleep 1

# Enregistrement du profil de port série (SPP)
sdptool add SP

echo "Configuration terminée : visibilité classique et diffusion BLE activées."