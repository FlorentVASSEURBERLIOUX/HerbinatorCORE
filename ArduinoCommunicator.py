import serial
import time

class ArduinoCommunicator:
    def __init__(self, port='/dev/ttyACM0', baudrate=115200):
        try:
            self.arduino = serial.Serial(port, baudrate, timeout=0.05)
            time.sleep(1)
            self.arduino.reset_input_buffer()
        except Exception as e:
            self.arduino = None

    def send(self, command):
        """Envoie une commande texte brute à l'Arduino."""
        if self.arduino and self.arduino.is_open:
            self.arduino.write(f"{command}\n".encode('utf-8'))
            print(f"[ENVOI ARDUINO] {command}")

    def recevoir(self):
        """Lit les données et avale tout le retard pour ne garder que le temps réel."""
        if self.arduino and self.arduino.is_open:
            try:
                derniere_ligne_valide = None
                while self.arduino.in_waiting > 0:
                    ligne_brute = self.arduino.readline()
                    if ligne_brute:
                        derniere_ligne_valide = ligne_brute.decode('utf-8', errors='ignore').strip()
                
                return derniere_ligne_valide
                
            except Exception as e:
                print(f"[ERREUR LECTURE ARDUINO] {e}")
        return None

    def fermer_connexion(self):
        """Ferme proprement le port série à la fin de l'utilisation."""
        if self.arduino and self.arduino.is_open:
            self.arduino.close()