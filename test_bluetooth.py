from bluedot.btcomm import BluetoothServer
import time
import threading

def quand_connecte():
    print("Génial ! Le téléphone est connecté.")
    threading.Thread(target=envoyer_en_boucle, daemon=True).start()

def quand_deconnecte():
    print("Téléphone déconnecté.")

def quand_message_recu(data):
    print(f"Reçu du téléphone : {data.strip()}")

def envoyer_en_boucle():
    compteur = 1
    while server.client_connected:
        message = f"Message n°{compteur} de la Pi 5 !\n"
        server.send(message)
        print(f"Envoyé : {message.strip()}")
        compteur += 1
        time.sleep(2)

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