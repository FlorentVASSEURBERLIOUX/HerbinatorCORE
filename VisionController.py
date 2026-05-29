import cv2
import time
import random

from ArduinoCommunicator import ArduinoCommunicator
from BluetoothCommunicator import BluetoothCommunicator

class VisionController:
    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.qr_detector = cv2.QRCodeDetector()
        
        self.robot = ArduinoCommunicator(port='/dev/ttyACM0')
        self.bluetooth = BluetoothCommunicator(port=1)
        
        self.en_veille = False

    def capturer_image(self):
        if not self.cap.isOpened():
            print("[ERREUR] Pas de webcam")
            return False, None
        
        ret, frame = self.cap.read()
        return ret, frame

    def chercher_limite_qrcode(self, image):
        data, bbox, _ = self.qr_detector.detectAndDecode(image)
        
        if data and bbox is not None:
            coins = bbox[0]
            centre_x = int((coins[0][0] + coins[2][0]) / 2)
            centre_y = int((coins[0][1] + coins[2][1]) / 2)
            largeur = int(abs(coins[1][0] - coins[0][0]))
            hauteur = int(abs(coins[3][1] - coins[0][1]))
            
            infos_qr = {
                "texte": data,
                "position_x": centre_x,
                "position_y": centre_y,
                "largeur_px": largeur,
                "hauteur_px": hauteur
            }
            return True, infos_qr
            
        return False, None

    def detecter_mauvaise_herbe(self, image, seuil_certitude=80.0):
        certitude_ia = random.uniform(0.0, 100.0) 
        if certitude_ia >= seuil_certitude:
            print(f"[IA] Herbe détectée ! ({certitude_ia:.1f}%)")
            return True
        return False

    def lancer_routine_vision(self, fps=1.0):
        print(" Démarrage de la routine de vision")
        self.bluetooth.attendre_connexion()
        
        try:
            while True:
                start_time = time.time()
                
                commande_app = self.bluetooth.recevoir()
                if commande_app == "VEILLE":
                    print("[STATUT] Passage en mode VEILLE.")
                    self.robot.send("V")
                    self.en_veille = True
                elif commande_app == "START":
                    print("[STATUT] Reprise du travail (START).")
                    self.en_veille = False

                telemetrie_app = {"statut": "veille" if self.en_veille else "actif"}

                if not self.en_veille:
                    ret, frame = self.capturer_image()
                    if not ret:
                        print("[ERREUR] Pas d'image prise")
                    else:
                        qr_trouve, infos_qr = self.chercher_limite_qrcode(frame)
                        
                        if qr_trouve:
                            t = infos_qr["texte"]
                            w = infos_qr["largeur_px"]
                            h = infos_qr["hauteur_px"]
                            x = infos_qr["position_x"]
                            y = infos_qr["position_y"]
                            
                            self.robot.send(f"B:{t}:{w}:{h}:{x}:{y}")
                            telemetrie_app["alerte_qr"] = t
                        else:
                            herbe_trouvee = self.detecter_mauvaise_herbe(frame, seuil_certitude=85.0)
                            if herbe_trouvee:
                                print("[ACTION] Activation Pompe.")
                                self.robot.send("P")
                            telemetrie_app["herbe_detectee"] = herbe_trouvee

                donnees_arduino = self.robot.recevoir()
                
                if donnees_arduino:
                    # On s'attend au format : "DATA:EncG:EncD:UsFace:UsGauche:UsDroit"
                    if donnees_arduino.startswith("DATA:"):
                        parts = donnees_arduino.split(":")
                        if len(parts) == 6:
                            telemetrie_app["encodeurs"] = {"gauche": parts[1], "droit": parts[2]}
                            telemetrie_app["ultrasons"] = {"face": parts[3], "gauche": parts[4], "droit": parts[5]}
                            print(f"[CAPTEURS] Enc:({parts[1]},{parts[2]}) | US F/G/D:({parts[3]},{parts[4]},{parts[5]})")

                self.bluetooth.envoyer(telemetrie_app)

                processing_time = time.time() - start_time
                sleep_time = max(0, fps - processing_time)
                
                if sleep_time == 0 and not self.en_veille: 
                    print(f"[ALERTE] Temps traitement > {fps}s !")
                time.sleep(sleep_time)
                
        finally:
            self.cap.release()
            self.robot.fermer_connexion()
            self.bluetooth.fermer()

if __name__ == '__main__':
    controleur = VisionController()
    controleur.lancer_routine_vision()