import socket
import json
import time
import subprocess

class BluetoothCommunicator:
    def __init__(self, port=1):
        """Initialise le serveur Bluetooth RFCOMM."""
        self.port = port
        self.server_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.client_sock = None
        self.client_info = None

        try:
            try:
                out = subprocess.check_output(['bluetoothctl', 'list']).decode('utf-8')
                mac_address = out.split()[1]
            except Exception:
                mac_address = "00:00:00:00:00:00"
            self.server_sock.bind((mac_address, self.port))
            self.server_sock.listen(1)
            print(f"[BLUETOOTH] Serveur démarré sur {mac_address} (Port {self.port}).")
        except Exception as e:
            print(f"[ERREUR INIT BLUETOOTH] {e}")
            raise SystemExit

    def attendre_connexion(self):
        """Met le programme en pause jusqu'à ce que l'application mobile se connecte."""
        print("[BLUETOOTH] En attente de l'application...")
        try:
            self.client_sock, self.client_info = self.server_sock.accept()
            
            self.client_sock.settimeout(0.05) 
            
            print(f"[BLUETOOTH] Connecté à {self.client_info}")
            return True
        except Exception as e:
            print(f"[ERREUR CONNEXION] {e}")
            return False

    def envoyer(self, donnees_dict):
        """Convertit un dictionnaire en JSON et l'envoie à l'application."""
        if self.client_sock:
            try:
                message = json.dumps(donnees_dict) + "\n"
                self.client_sock.send(message.encode('utf-8'))
            except Exception as e:
                print(f"[ERREUR ENVOI] {e}")
                self.client_sock = None

    def recevoir(self):
        """
        Vérifie si le téléphone a envoyé un message. 
        S'exécute instantanément (non-bloquant). Retourne le texte ou None.
        """
        if self.client_sock:
            try:
                data = self.client_sock.recv(1024)
                if data:
                    return data.decode('utf-8').strip()
            except socket.timeout:
                return None
            except Exception as e:
                print(f"[ERREUR RECEPTION] {e}")
                self.client_sock = None
        return None

    def fermer(self):
        """Ferme les ports de communication proprement."""
        if self.client_sock:
            self.client_sock.close()
        if self.server_sock:
            self.server_sock.close()


if __name__ == '__main__':
    bt = BluetoothCommunicator()
    
    if bt.attendre_connexion():
        print("'STOP' pour arrêter.")
        try:
            while True:
                commande_app = bt.recevoir()
                if commande_app:
                    print(f"-> Message de l'appli : {commande_app}")
                    if commande_app.upper() == "STOP":
                        break
                
                donnees_test = {"statut": "en_marche", "batterie": 85, "herbe_detectee": False}
                bt.envoyer(donnees_test)
                
                time.sleep(1)
        finally:
            bt.fermer()