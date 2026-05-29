import serial
import time

class ArduinoCommunicator:
    def __init__(self, port='/dev/ttyACM0', baudrate=9600):
        try:
            self.arduino = serial.Serial(port, baudrate, timeout=1)
            print(f"Connecté port {port}")
        except Exception as e:
            print(f"[ERREUR] {e}")
            self.arduino = None

    def send(self, command):
        """Envoie une commande texte brute à l'Arduino."""
        if self.arduino and self.arduino.is_open:
            self.arduino.write(f"{command}\n".encode('utf-8'))
            print(f"[ENVOI] {command}")

    def recevoir(self):
        """Lit les données de l'Arduino de manière strictement non-bloquante."""
        if self.arduino and self.arduino.is_open:
            try:
                if self.arduino.in_waiting > 0:
                    return self.arduino.readline().decode('utf-8').strip()
            except Exception as e:
                print(f"[ERREUR LECTURE ARDUINO] {e}")
        return None

    def fermer_connexion(self):
        """Ferme proprement le port série à la fin de l'utilisation."""
        if self.arduino and self.arduino.is_open:
            self.arduino.close()