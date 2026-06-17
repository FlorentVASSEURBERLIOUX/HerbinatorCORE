import cv2
import time
import math
import os
from ultralytics import YOLO

from ArduinoCommunicator import ArduinoCommunicator
from BluetoothCommunicator import BluetoothCommunicator
from Cartographie import Cartographie

class VisionController:
    # On met par défaut le chemin de ta LifeCam en texte
    def __init__(self, camera_path="/dev/video2", sans_app=False): 
        self.sans_app = sans_app
        
        # 1. Gestion ULTRA-SÉCURISÉE de la Caméra (Forçage V4L2)
        print(f"[VISION] Tentative d'ouverture de la caméra sur {camera_path}...")
        self.cap = cv2.VideoCapture(camera_path, cv2.CAP_V4L2)
        
        if not self.cap.isOpened():
            print("[ATTENTION] Échec sur /dev/video2, essai de repli sur /dev/video1...")
            self.cap = cv2.VideoCapture("/dev/video1", cv2.CAP_V4L2)
            
            if not self.cap.isOpened():
                print("[ATTENTION] Échec sur /dev/video1, essai de l'index par défaut (0)...")
                self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
                
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        os.makedirs("img_test", exist_ok=True)
        
        # 2. IA et QR
        dictionnaire = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        parametres = cv2.aruco.DetectorParameters()
        self.aruco_detector = cv2.aruco.ArucoDetector(dictionnaire, parametres)        
        
        try:
            self.modele_ia = YOLO("IA/best (1).pt")
            print("[IA] Modèle YOLO chargé !")
        except Exception as e:
            print(f"[ERREUR IA] Impossible de charger le modèle : {e}")
            self.modele_ia = None

        # 3. Arduino
        try:
            self.robot = ArduinoCommunicator(port='/dev/ttyACM0')
        except Exception as e:
            print(f"[ATTENTION] Arduino non connecté sur /dev/ttyACM0 : {e}")
            self.robot = None

        # 4. Bluetooth (Actif uniquement si on n'est pas en mode sans_app)
        if not self.sans_app:
            self.bluetooth = BluetoothCommunicator(port=1)
            self.en_veille = True
        else:
            self.bluetooth = None
            self.en_veille = False
            print("\n[MODE TEST] Bluetooth désactivé. Démarrage autonome immédiat !")

        # 5. Cartographie et Variables globales
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

    def capturer_image(self):
        if not self.cap.isOpened():
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
            return True, {"texte": f"ID_{id_trouve}", "position_x": centre_x, "position_y": centre_y, "largeur_px": largeur, "hauteur_px": hauteur}
        return False, None

    def detecter_mauvaise_herbe(self, image, seuil_certitude=0.5):
        if self.modele_ia is None: return False, 0, 0
        resultats = self.modele_ia(image, verbose=False)
        for r in resultats:
            for boite in r.boxes:
                certitude = float(boite.conf[0]) * 100 
                print(certitude)
                if certitude >= seuil_certitude:
                    x1, y1, x2, y2 = boite.xyxy[0]
                    centre_x, centre_y = int((x1 + x2) / 2), int((y1 + y2) / 2)
                    angle = int(((centre_x - 320) / 320.0) * 45)
                    distance = int(math.sqrt((centre_x - 320)**2 + (centre_y - 480)**2))
                    print(f"[IA] Herbe ciblée ! (Angle: {angle}° | Dist: {distance}px)")
                    return True, angle, distance
        return False, 0, 0

    def lancer_routine_vision(self, fps=0.5):
        print("\n==================================================")
        print(" DÉMARRAGE DU CERVEAU HERBINATOR")
        print("==================================================")
        
        # Attente de Flutter si activé
        if not self.sans_app:
            self.bluetooth.attendre_connexion()
        
        try:
            while True:
                start_time = time.time()
                qr_trouve = False 
                herbe_trouvee = False
                
                # --- LECTURE BLUETOOTH ---
                if not self.sans_app:
                    commande_app = self.bluetooth.recevoir()
                    if commande_app == "VEILLE":
                        if self.robot: self.robot.send("V")
                        self.en_veille = True
                    elif commande_app == "START":
                        self.en_veille = False

                # --- VISION ET ARDUINO ---
                if not self.en_veille:
                    ret, frame = self.capturer_image()
                    if ret:
                        qr_trouve, infos_qr = self.chercher_limite_qr(frame)
                        
                        if qr_trouve:
                            if self.robot: self.robot.send(f"B:{infos_qr['texte']}:{infos_qr['largeur_px']}:{infos_qr['hauteur_px']}:{infos_qr['position_x']}:{infos_qr['position_y']}")
                            self.cap_degres = (self.cap_degres + 180) % 360
                            print(f"[NAV] Bordure vue, nouveau cap : {self.cap_degres}°")
                        else:
                            herbe_trouvee, angle, distance = self.detecter_mauvaise_herbe(frame)
                            if herbe_trouvee:
                                self.nb_herbe += 1 
                                if self.robot: self.robot.send(f"P:{angle}:{distance}")
                                # Sauvegarde Image
                                nom_fichier = f"img_test/herbe_n{self.nb_herbe}_{time.strftime('%H%M%S')}.jpg"
                                cv2.imwrite(nom_fichier, frame)
                                print(f"[VISION] Image sauvegardée : {nom_fichier}")

                # --- ODOMÉTRIE ET CARTOGRAPHIE ---
                dist_obs = None
                if self.robot:
                    donnees_arduino = self.robot.recevoir()
                    if donnees_arduino and donnees_arduino.startswith("DATA:"):
                        parts = donnees_arduino.split(":")
                        if len(parts) == 6:
                            encG, encD = int(parts[1]), int(parts[2])
                            avancee_cm = (((encG - self.last_encG) + (encD - self.last_encD)) / 2.0) * self.cm_par_tick
                            self.last_encG, self.last_encD = encG, encD
                            self.distance_cm += avancee_cm
                            cap_rad = math.radians(self.cap_degres)
                            self.x_robot += avancee_cm * math.cos(cap_rad)
                            self.y_robot += avancee_cm * math.sin(cap_rad)
                            if int(parts[3]) == 1: dist_obs = 15 
                
                if not self.en_veille:
                    self.carte.mettre_a_jour(self.x_robot, self.y_robot, self.cap_degres, dist_obstacle_cm=dist_obs, cible_yolo_detectee=herbe_trouvee)
                    if int(time.time()) % 15 == 0: # Sauvegarde la carte toutes les 15 secondes
                        self.carte.sauvegarder_carte("carte_herbinator.png")

                # --- ENVOI TÉLÉMÉTRIE FLUTTER ---
                if not self.sans_app:
                    telemetrie = {
                        "OperationTime": int(time.time() - self.start_time_global),
                        "Tours": qr_trouve, 
                        "Distance": int(self.distance_cm),
                        "NbHerbe": self.nb_herbe,
                        "Batterie PI": 0.85 
                    }
                    self.bluetooth.envoyer(telemetrie)

                # --- SYNCHRONISATION FPS ---
                time.sleep(max(0, fps - (time.time() - start_time)))
                #print(time.time() - start_time)
                
        finally:
            self.cap.release()
            if self.robot: self.robot.fermer_connexion()
            if not self.sans_app: self.bluetooth.fermer()
    
if __name__ == '__main__':
    controleur = VisionController(camera_path=2, sans_app=True) 
    controleur.lancer_routine_vision()