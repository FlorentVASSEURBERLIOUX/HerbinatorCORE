import cv2
import time
import random
from ultralytics import YOLO

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

        try:
            self.modele_ia = YOLO("IA/best (1).pt")
            print("[IA] Modèle chargé !")
        except Exception as e:
            print(f"[ERREUR IA] Impossible de charger le modèle : {e}")
            self.modele_ia = None

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

    def detecter_mauvaise_herbe(self, image, seuil_certitude=0.5):
        if self.modele_ia is None:
            return False
        
        resultats = self.modele_ia(image, verbose=False)
        
        for r in resultats:
            boites = r.boxes
            for boite in boites:
                certitude = float(boite.conf[0]) * 100 
                
                if certitude >= seuil_certitude:
                    print(f"[IA] Herbe ciblée ! (Certitude : {certitude:.1f}%)")
                    return True
        
                print(f"Certitude : {certitude:.1f}%")

                    
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
                            herbe_trouvee = self.detecter_mauvaise_herbe(frame)
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

    
    def tester_ia_seule(self):
        """Méthode de test minimaliste : Caméra + IA uniquement."""
        print("\n==================================================")
        print(" MODE TEST : Caméra et IA (Sans Arduino/Bluetooth)")
        print("==================================================")
        try:
            while True:
                ret, frame = self.capturer_image()
                if not ret:
                    print("[ERREUR] Impossible de lire la caméra.")
                    time.sleep(0.1)
                    continue
                    
                print("\nAnalyse en cours...")
                resultat = self.detecter_mauvaise_herbe(frame, seuil_certitude=0.5)
                
                print(f"-> Résultat du traitement : {resultat}")
                                
        except KeyboardInterrupt:
            print("\n[!] Fin du test manuel de l'IA.")
        finally:
            self.cap.release()

if __name__ == '__main__':
    controleur = VisionController()
    controleur.tester_ia_seule()