import serial
import time

class ArduinoCommunicator:
    def __init__(self, port='/dev/ttyACM0', baudrate=9600):
        try:
            self.arduino = serial.Serial(port, baudrate, timeout=1)
            print(f"Connécté port {port}")
        except Exception as e:
            print(f"[ERREUR] {e}")
            self.arduino = None

    def send(self, command):
        """Envoie une commande texte brute à l'Arduino."""
        if self.arduino and self.arduino.is_open:
            self.arduino.write(f"{command}\n".encode('utf-8'))
            print(f"[ENVOIE] {command}")

    def fermer_connexion(self):
        """Ferme proprement le port série à la fin de l'utilisation."""
        if self.arduino and self.arduino.is_open:
            self.arduino.close()
