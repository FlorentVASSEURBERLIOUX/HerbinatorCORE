import json
import time
from bluedot.btcomm import BluetoothServer

class BluetoothCommunicator:
    def __init__(self, port=1):
        """Initialise le serveur Bluetooth de manière asynchrone avec BlueDot."""
        self.dernier_message = None
        
        print("[BLUETOOTH] Initialisation de l'antenne avec BlueDot...")
        self.server = BluetoothServer(
            data_received_callback=self._quand_message_recu,
            when_client_connects=self._quand_connecte,
            when_client_disconnects=self._quand_deconnecte
        )
        print("[BLUETOOTH] Serveur prêt.")

    def _quand_connecte(self):
        print("[BLUETOOTH] Application Flutter connectée !")

    def _quand_deconnecte(self):
        print("[BLUETOOTH] Application déconnectée.")

    def _quand_message_recu(self, data):
        """Callback interne déclenché instantanément quand le téléphone parle."""
        message = data.strip()
        if message:
            self.dernier_message = message

    def attendre_connexion(self):
        """Met le programme en pause jusqu'à ce que l'application mobile se connecte."""
        print("[BLUETOOTH] En attente de l'application...")
        try:
            while not self.server.client_connected:
                time.sleep(0.1)
            return True
        except KeyboardInterrupt:
            return False

    def envoyer(self, donnees_dict):
        """Convertit le dictionnaire de télémétrie en JSON strict et l'envoie."""
        if self.server.client_connected:
            try:
                self.server.send(message_json)
            except Exception as e:
                print(f"[ERREUR ENVOI BLUETOOTH] {e}")

    def recevoir(self):
        """
        Consulte la boîte de réception. Fonction non-bloquante idéale pour 
        la boucle vidéo (VisionController) qui doit tourner à haut FPS.
        """
        if self.dernier_message is not None:
            msg = self.dernier_message
            self.dernier_message = None
            return msg
        return None

    def fermer(self):
        """Coupe proprement l'antenne Bluetooth à l'arrêt du robot."""
        if self.server:
            self.server.stop()


if __name__ == '__main__':
    bt = BluetoothCommunicator()
    
    if bt.attendre_connexion():
        print("Début du test. Lance ton application FlutterFlow !")
        print("(Appuie sur Ctrl+C pour arrêter le test)")
        
        start_time_global = time.time()
        distance_simulee = 0
        herbe_simulee = 0
        
        try:
            while True:
                commande_app = bt.recevoir()
                if commande_app:
                    print(f"-> Ordre reçu de l'application : {commande_app}")

                telemetrie = {
                    "OperationTime": int(time.time() - start_time_global), # Int (Secondes)
                    "Tours": False,                                        # Bool
                    "Distance": int(distance_simulee),                     # Int (Centimètres)
                    "NbHerbe": int(herbe_simulee),                         # Int
                    "Batterie PI": 0.85                                    # Double (0 à 1)
                }
                
                bt.envoyer(telemetrie)
                print(f"Télémétrie envoyée : {telemetrie}")
                
                distance_simulee += 1.5
                if int(distance_simulee) % 15 == 0:
                    herbe_simulee += 1
                    
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nFin du test demandée.")
        
                message_json = json.dumps(donnfinally:
            bt.fermer()