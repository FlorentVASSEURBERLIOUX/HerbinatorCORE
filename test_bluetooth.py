from bluedot.btcomm import BluetoothServer
import time
import threading
import json 
import cv2
import base64
import os

print("Démarrage du serveur Bluetooth (Mode Image alternée chaque seconde)...")

compteur = 1
etat_robot = "START"         # Par défaut, le robot est en pause
alternance_image = True     # True = .jpg, False = .png

def quand_connecte():
    print("✅ Génial ! Le téléphone est connecté.")
    threading.Thread(target=envoyer_donnees_regulieres, daemon=True).start()

def quand_deconnecte():
    print("❌ Téléphone déconnecté.")

def quand_message_recu(data):
    global compteur, etat_robot
    message = data.strip()
    
    print("\n" + "="*50)
    print(f"🎯 BOUTON PRESSÉ SUR L'APPLI : {message}")
    print("="*50 + "\n")

    if message == "START":
        print("▶️ Action : Le robot démarre. Alternance des images activée !")
        etat_robot = "START"
        
    elif message == "STOP":
        print("⏸️ Action : Le robot est en pause. Arrêt de la mise à jour de l'image.")
        etat_robot = "STOP"
        
    elif message == "RESET":
        compteur = 1
        print("🔄 Action : Le robot reset ses données.")
    else:
        print(f"❓ Commande inconnue : {message}")

def envoyer_donnees_regulieres():
    global compteur, etat_robot, alternance_image
    
    while server.client_connected:
        # Base du dictionnaire de données
        donnees = {
            "titre": f"MODE {etat_robot}",
            "valeur_compteur": compteur,
            "alerte": "Actif"
        }
        
        # Si le robot est sur START, on ajoute l'image au dictionnaire
        if etat_robot == "START":
            # On choisit le nom du fichier selon la variable d'alternance
            nom_fichier = "carte_herbinator.jpg" if alternance_image else "carte_herbinator.png"
            alternance_image = not alternance_image # On inverse pour la prochaine seconde
            
            if os.path.exists(nom_fichier):
                frame = cv2.imread(nom_fichier)
                if frame is not None:
                    try:
                        # Réduction et compression
                        frame_miniature = cv2.resize(frame, (160, 120))
                        _, buffer = cv2.imencode('.jpg', frame_miniature, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
                        
                        # Ajout de l'image encodée dans le dictionnaire
                        donnees["image_base64"] = base64.b64encode(buffer).decode('utf-8')
                        donnees["alerte"] = f"Image {nom_fichier} envoyée"
                    except Exception as e:
                        print(f"❌ Erreur d'encodage : {e}")
                else:
                    print(f"⚠️ Impossible de lire l'image {nom_fichier} avec OpenCV.")
            else:
                print(f"⚠️ Image {nom_fichier} introuvable à la racine.")

        # On convertit le tout en JSON
        message_json = json.dumps(donnees) + "\n"
        
        try:
            server.send(message_json)
            # Affichage console adapté
            if "image_base64" in donnees:
                print(f"📤 Envoyé : Télémétrie + {nom_fichier} (Compteur n°{compteur})")
            else:
                print(f"📤 Envoyé : Télémétrie légère (Compteur n°{compteur})")
        except Exception as e:
            print(f"❌ Erreur de transmission : {e}")
            break
            
        compteur += 1
        time.sleep(1)

print("Initialisation du serveur Bluetooth...")

server = BluetoothServer(
    data_received_callback=quand_message_recu,
    when_client_connects=quand_connecte,
    when_client_disconnects=quand_deconnecte
)

print("🚀 Serveur prêt ! En attente de l'application FlutterFlow...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    server.stop()
    print("Serveur arrêté.")