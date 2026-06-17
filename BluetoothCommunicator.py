import socket
import threading
import json
import time

class BluetoothCommunicator:
    def __init__(self, port=1):
        self.port = port
        self.server_sock = None
        self.client_sock = None
        self.client_info = None
        self.dernier_message = None
        self.connecte = False
        self.thread_ecoute = None

    def demarrer_serveur(self):
        print(f"[BLUETOOTH] Ouverture de l'antenne sur le port {self.port}...")
        try:
            self.server_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            self.server_sock.bind((socket.BDADDR_ANY, self.port))
            self.server_sock.listen(1)
            print("[BLUETOOTH] Serveur prêt. En attente de l'application Flutter...")
            return True
        except Exception as e:
            print(f"[ERREUR BLUETOOTH] Impossible de créer le serveur : {e}")
            return False

    def attendre_connexion(self):
        """Met le script en pause tant que le téléphone n'est pas connecté."""
        if not self.demarrer_serveur():
            return False
            
        try:
            # Le code s'arrête ici et attend le téléphone
            self.client_sock, self.client_info = self.server_sock.accept()
            self.connecte = True
            print(f"[BLUETOOTH] ✅ Application connectée : {self.client_info}")
            
            # On lance un thread (tâche de fond) pour écouter sans bloquer la vidéo
            self.thread_ecoute = threading.Thread(target=self._ecouter_client, daemon=True)
            self.thread_ecoute.start()
            return True
        except Exception as e:
            print(f"[ERREUR BLUETOOTH] Échec de la connexion : {e}")
            return False

    def _ecouter_client(self):
        """Tourne en boucle en arrière-plan pour intercepter les ordres de l'app."""
        while self.connecte and self.client_sock:
            try:
                data = self.client_sock.recv(1024)
                if not data:
                    break # Si on reçoit du vide, c'est que le client a quitté
                message = data.decode("utf-8").strip()
                if message:
                    self.dernier_message = message
            except:
                break # En cas de coupure brutale
                
        self.connecte = False
        print("[BLUETOOTH] ❌ Application déconnectée.")

    def envoyer(self, donnees_dict):
        """Convertit les données en JSON et les envoie au téléphone."""
        if self.connecte and self.client_sock:
            try:
                message_json = json.dumps(donnees_dict) + "\n"
                self.client_sock.send(message_json.encode("utf-8"))
            except Exception as e:
                print(f"[ERREUR ENVOI BLUETOOTH] {e}")
                self.connecte = False

    def recevoir(self):
        """Vide la boîte de réception pour que VisionController puisse la lire."""
        if self.dernier_message is not None:
            msg = self.dernier_message
            self.dernier_message = None
            return msg
        return None

    def fermer(self):
        """Coupe proprement toutes les connexions."""
        self.connecte = False
        if self.client_sock:
            try: self.client_sock.close()
            except: pass
        if self.server_sock:
            try: self.server_sock.close()
            except: pass
        print("[BLUETOOTH] Portes fermées.")