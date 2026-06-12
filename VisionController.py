import cv2
import time
import random
import math
from ultralytics import YOLO

from ArduinoCommunicator import ArduinoCommunicator
from BluetoothCommunicator import BluetoothCommunicator
from Cartographie import Cartographie

class VisionController:
    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        dictionnaire = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        parametres = cv2.aruco.DetectorParameters()
        self.aruco_detector = cv2.aruco.ArucoDetector(dictionnaire, parametres)        
        
        self.robot = ArduinoCommunicator(port='/dev/ttyACM0')
        self.bluetooth = BluetoothCommunicator(port=1)
        
        self.en_veille = False

        self.start_time_global = time.time()
        self.nb_herbe = 0
        self.distance_cm = 0
        
        self.carte = Cartographie((300, 300), 10) 
        
        self.x_robot = 150.0 
        self.y_robot = 20.0
        self.cap_degres = 90.0
        
        self.last_encG = 0
        self.last_encD = 0
        self.cm_par_tick = 0.02

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

    def chercher_limite_qr(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = self.aruco_detector.detectMarkers(gray)
        if ids is not None and len(ids) > 0:
            id_trouve = ids[0][0]
            coins = corners[0][0]
            centre_x = int((coins[0][0] + coins[2][0]) / 2)
            centre_y = int((coins[0][1] + coins[2][1]) / 2)
            largeur = int(abs(coins[1][0] - coins[0][0]))
            hauteur = int(abs(coins[3][1] - coins[0][1]))
            infos_aruco = {
                "texte": f"ID_{id_trouve}",
                "position_x": centre_x,
                "position_y": centre_y,
                "largeur_px": largeur,
                "hauteur_px": hauteur
            }
            return True, infos_aruco
        return False, None

    def detecter_mauvaise_herbe(self, image, seuil_certitude=0.5):
        if self.modele_ia is None:
            return False, 0, 0
            
        resultats = self.modele_ia(image, verbose=False)
        
        for r in resultats:
            for boite in r.boxes:
                certitude = float(boite.conf[0]) * 100 
                
                if certitude >= seuil_certitude:
                    x1, y1, x2, y2 = boite.xyxy[0]
                    
                    centre_x = int((x1 + x2) / 2)
                    centre_y = int((y1 + y2) / 2)
                    
                    angle = int(((centre_x - 320) / 320.0) * 45)
                    
                    distance_pixels = math.sqrt((centre_x - 320)**2 + (centre_y - 480)**2)
                    distance = int(distance_pixels)
                    
                    print(f"[IA] Herbe ciblée ! (Angle: {angle}° | Dist: {distance}px)")
                    return True, angle, distance
                    
        return False, 0, 0

    def lancer_routine_vision(self, fps=1.0):
        print(" Démarrage de la routine de vision")
        #self.bluetooth.attendre_connexion()
        
        try:
            while True:
                start_time = time.time()
                qr_trouve = False 
                herbe_trouvee = False
                
                # 1. Écoute Bluetooth
                commande_app = self.bluetooth.recevoir()
                if commande_app == "VEILLE":
                    self.robot.send("V")
                    self.en_veille = True
                elif commande_app == "START":
                    self.en_veille = False

                # 2. Vision IA et QR
                if not self.en_veille:
                    ret, frame = self.capturer_image()
                    if ret:
                        qr_trouve, infos_qr = self.chercher_limite_qr(frame)
                        
                        if qr_trouve:
                            t, w, h, x, y = infos_qr["texte"], infos_qr["largeur_px"], infos_qr["hauteur_px"], infos_qr["position_x"], infos_qr["position_y"]
                            self.robot.send(f"B:{t}:{w}:{h}:{x}:{y}")
                            
                            self.cap_degres = (self.cap_degres + 180) % 360
                            print(f"[NAV] Bordure vue, nouveau cap : {self.cap_degres}°")
                            
                        else:
                            herbe_trouvee, angle, distance = self.detecter_mauvaise_herbe(frame)
                            if herbe_trouvee:
                                self.nb_herbe += 1 
                                self.robot.send(f"P:{angle}:{distance}")

                donnees_arduino = self.robot.recevoir()
                dist_obs = None
                
                if donnees_arduino and donnees_arduino.startswith("DATA:"):
                    parts = donnees_arduino.split(":")
                    if len(parts) == 6:
                        encG, encD = int(parts[1]), int(parts[2])
                        deltaG = encG - self.last_encG
                        deltaD = encD - self.last_encD
                        self.last_encG, self.last_encD = encG, encD
                        
                        avancee_cm = ((deltaG + deltaD) / 2.0) * self.cm_par_tick
                        self.distance_cm += avancee_cm
                        
                        cap_rad = math.radians(self.cap_degres)
                        self.x_robot += avancee_cm * math.cos(cap_rad)
                        self.y_robot += avancee_cm * math.sin(cap_rad)
                        
                        if int(parts[3]) == 1:
                            dist_obs = 15 # Si obstacle détecté par Arduino, on simule à 15cm
                
                if not self.en_veille:
                    self.carte.mettre_a_jour(self.x_robot, self.y_robot, self.cap_degres, dist_obstacle_cm=dist_obs, cible_yolo_detectee=herbe_trouvee)
                    
                    if int(time.time()) % 60 == 0:
                        self.carte.sauvegarder_carte("carte_herbinator.png")

                telemetrie_app = {
                    "OperationTime": int(time.time() - self.start_time_global),
                    "Tours": qr_trouve, 
                    "Distance": int(self.distance_cm),
                    "NbHerbe": self.nb_herbe,
                    "Batterie PI": 0.85 
                }
                self.bluetooth.envoyer(telemetrie_app)

                processing_time = time.time() - start_time
                sleep_time = max(0, fps - processing_time)
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

    def tester_qr_seul(self):
        """Méthode de test minimaliste : Caméra + QR Code (ArUco) uniquement."""
        print("\n==================================================")
        print(" MODE TEST : Caméra et QR Code (Sans Arduino/Bluetooth/IA)")
        print("==================================================")
        try:
            while True:
                ret, frame = self.capturer_image()
                if not ret:
                    print("[ERREUR] Impossible de lire la caméra.")
                    time.sleep(1)
                    continue
                    
                print("\nRecherche de Tag ArUco en cours...")
                # CORRECTION ICI AUSSI : chercher_limite_qr
                qr_trouve, infos_qr = self.chercher_limite_qr(frame)
                
                if qr_trouve:
                    print(f"-> [SUCCÈS] Tag détecté !")
                    print(f"   Texte    : '{infos_qr['texte']}'")
                    print(f"   Position : X={infos_qr['position_x']}, Y={infos_qr['position_y']}")
                    print(f"   Taille   : {infos_qr['largeur_px']} x {infos_qr['hauteur_px']} pixels")
                else:
                    print("-> [INFO] Aucun Tag visible dans le champ.")
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n[!] Fin du test manuel.")
        finally:
            self.cap.release()

if __name__ == '__main__':
    controleur = VisionController()
    
    #controleur.tester_ia_seule()
    #controleur.tester_qr_seul()
    controleur.lancer_routine_vision()