import cv2
import time
import math
import os
import sys
import base64

from ultralytics import YOLO

from ArduinoCommunicator import ArduinoCommunicator
from BluetoothCommunicator import BluetoothCommunicator
from Cartographie import Cartographie

class VisionController:
    # --- PARAMÈTRES DE TAILLE ET INITIALISATION BLUETOOTH ---
    def __init__(self, sans_app=False, taille_terrain_cm=(300, 300), resolution_cm=10): 
        print("[BLUETOOTH] Exécution de ./init_bluetooth.sh...")
        os.system("./init_bluetooth.sh")
        print("[BLUETOOTH] Attente de 2 secondes pour l'activation de l'antenne...")
        time.sleep(2)
        
        self.sans_app = sans_app
        self.moy_cert = [0,0]
        
        print("[VISION] Lancement de la recherche de caméra...")
        self.cap = None
        
        for index in range(10):
            print(f"[VISION] -> Essai sur l'index {index}...")
            cap_test = cv2.VideoCapture(index, cv2.CAP_V4L2)
            
            if cap_test.isOpened():
                ret, frame = cap_test.read()
                if ret and frame is not None:
                    print(f"[VISION] ✅ Vraie caméra matérielle trouvée sur l'index {index} !")
                    self.cap = cap_test
                    break
            cap_test.release()
            
        if self.cap is None or not self.cap.isOpened():
            print("\n==================================================")
            print("[ERREUR CRITIQUE] Aucune caméra fonctionnelle trouvée.")
            print("Vérifie le branchement USB ou tape: sudo killall python3")
            print("==================================================\n")
            sys.exit(1)
                
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        os.makedirs("img_test", exist_ok=True)
        
        # 2. CONFIGURATION IA ET QR CODE
        dictionnaire = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        parametres = cv2.aruco.DetectorParameters()
        self.aruco_detector = cv2.aruco.ArucoDetector(dictionnaire, parametres)        
        
        try:
            self.modele_ia = YOLO("IA/best_herbinator_v3.pt")
            print("[IA] Modèle YOLO chargé avec succès !")
        except Exception as e:
            print(f"[ERREUR IA] Impossible de charger le modèle : {e}")
            self.modele_ia = None

        # 3. FILAIRE ARDUINO
        try:
            self.robot = ArduinoCommunicator(port='/dev/ttyACM0')
            print("[ARDUINO] Connecté sur /dev/ttyACM0")
        except Exception as e:
            print(f"[ATTENTION] Arduino non connecté sur /dev/ttyACM0 : {e}")
            self.robot = None

        # 4. SANS FIL BLUETOOTH
        if not self.sans_app:
            self.bluetooth = BluetoothCommunicator(port=1)
            self.en_veille = True
        else:
            self.bluetooth = None
            self.en_veille = False
            print("\n[MODE TEST] Bluetooth désactivé. Démarrage autonome immédiat !")

        # 5. CARTOGRAPHIE ET ODOMÉTRIE
        self.start_time_global = time.time()
        self.nb_herbe = 0
        self.distance_cm = 0
        self.carte = Cartographie(taille_terrain_cm, resolution_cm) 
        self.x_robot = 150.0 
        self.y_robot = 20.0
        self.cap_degres = 90.0
        self.last_encG = 0
        self.last_encD = 0
        self.cm_par_tick = 0.02

        # --- SUIVI DES OBSTACLES DU CAPTEUR DE FACE ---
        self.nb_obstacles = 0
        self.obstacle_en_cours = False

        # --- SUIVI DES QR CODES DE QR_NEW ---
        self.qr_trouves = set()
        try:
            self.total_qr = len([f for f in os.listdir("QR_new") if f.endswith('.png')])
        except:
            self.total_qr = 26
        if self.total_qr == 0:
            self.total_qr = 26

    def encoder_image_b64(self, chemin_fichier):
        if not os.path.exists(chemin_fichier):
            return ""
        frame = cv2.imread(chemin_fichier)
        if frame is None:
            return ""
        try:
            frame_mini = cv2.resize(frame, (160, 120))
            _, buffer = cv2.imencode('.jpg', frame_mini, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            print(f"[ERREUR ENCODAGE] {chemin_fichier}: {e}")
            return ""

    def capturer_image(self):
        if self.cap is None or not self.cap.isOpened():
            return False, None
        return self.cap.read()

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

    def detecter_mauvaise_herbe(self, image, seuil_certitude=10.0):
        if self.modele_ia is None: 
            return False, 0, 0
        resultats = self.modele_ia(image, verbose=False)
        for r in resultats:
            for boite in r.boxes:
                certitude = float(boite.conf[0]) * 100 
                self.moy_cert[0]+=1
                self.moy_cert[1]= (1/self.moy_cert[0]*certitude)+((1-(1/self.moy_cert[0]))*self.moy_cert[1])
                print(f"[IA] Objet détecté avec une certitude de : {certitude:.1f}%")
                
                if certitude >= seuil_certitude:
                    x1, y1, x2, y2 = boite.xyxy[0]
                    centre_x, centre_y = int((x1 + x2) / 2), int((y1 + y2) / 2)
                    angle = int(((centre_x - 320) / 320.0) * 45)
                    distance = int(math.sqrt((centre_x - 320)**2 + (centre_y - 480)**2))
                    print(f"🎯 [IA] MAUVAISE HERBE CIBLÉE ! (Angle: {angle}° | Dist: {distance}px)")
                    return True, angle, distance
        return False, 0, 0

    def lancer_routine_vision(self, fps=0.5):
        print("\n==================================================")
        print(" DÉMARRAGE DU CERVEAU HERBINATOR")
        print("==================================================")
        
        if not self.sans_app:
            self.bluetooth.attendre_connexion()
        
        last_photo_time = 0
        last_carto_time = 0
        photo_b64_cache = ""
        carto_b64_cache = ""
        
        try:
            while True:
                start_time = time.time()
                now = time.time()
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
                    elif commande_app == "RESET":
                        self.distance_cm = 0.0
                        self.start_time_global = time.time()
                        self.nb_herbe = 0
                        self.moy_cert = [0, 0]
                        self.nb_obstacles = 0
                        self.obstacle_en_cours = False
                        self.qr_trouves.clear()
                        print("[BLUETOOTH] 🔄 Réinitialisation des compteurs effectuée.")

                # --- VISION ET ARDUINO ---
                if not self.en_veille:
                    ret, frame = self.capturer_image()
                    if ret and frame is not None:
                        print(f"[IA] Analyse en cours... {time.strftime('%H:%M:%S')}")
                        
                        qr_trouve, infos_qr = self.chercher_limite_qr(frame)
                        if qr_trouve:
                            index_attendu = len(self.qr_trouves)
                            nom_attendu = f"H{index_attendu // 2 + 1}" if index_attendu % 2 == 0 else f"B{index_attendu // 2 + 1}"
                            
                            nom_decouvert = infos_qr['texte'].replace("ID_", "")
                            
                            if nom_decouvert == nom_attendu and infos_qr['position_y'] < 5000000:
                                self.qr_trouves.add(infos_qr['texte'])
                                
                                if self.robot: 
                                    self.robot.send(f"B:{infos_qr['texte']}:{infos_qr['largeur_px']}:{infos_qr['hauteur_px']}:{infos_qr['position_x']}:{infos_qr['position_y']}")
                                self.cap_degres = (self.cap_degres + 180) % 360
                                print(f"[NAV] Séquence validée ! Bordure vue ({infos_qr['texte']}), nouveau cap : {self.cap_degres}°")
                            else:
                                # Le tag est soit hors-séquence, soit trop loin sur l'axe Y (Y >= 200)
                                print(f"[NAV] QR Code ignoré ou en attente ({infos_qr['texte']} | Y:{infos_qr['position_y']}), attendu: {nom_attendu} à Y<200")
                        else:
                            herbe_trouvee, angle, distance = self.detecter_mauvaise_herbe(frame)
                            if herbe_trouvee:
                                self.nb_herbe += 1 
                                if self.robot: self.robot.send(f"P:{angle}:{distance}")
                                
                                nom_fichier = f"img_test/herbe_n{self.nb_herbe}_{time.strftime('%H%M%S')}.jpg"
                                cv2.imwrite("photo.png", frame)
                                print(f"[VISION] Capture de l'herbe sauvegardée : {nom_fichier}")
                    else:
                        print("[⚠️ ATTENTION] La caméra est active mais refuse de renvoyer un flux d'images.")

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
                            
                            dist_front = int(parts[3])
                            if dist_front != -1:
                                dist_obs = dist_front
                                if not self.obstacle_en_cours:
                                    self.nb_obstacles += 1
                                    self.obstacle_en_cours = True
                            else:
                                self.obstacle_en_cours = False
                
                if not self.en_veille:
                    self.carte.mettre_a_jour(self.x_robot, self.y_robot, self.cap_degres, dist_obstacle_cm=dist_obs, cible_yolo_detectee=herbe_trouvee)
                    if int(time.time()) % 15 == 0: 
                        self.carte.sauvegarder_carte("carto.png")

                # --- FILTRAGE DE L'ENVOI DES IMAGES BLUETOOTH ---
                if not self.sans_app:
                    if now - last_photo_time >= 10:
                        photo_b64_cache = self.encoder_image_b64("photo.png")
                        last_photo_time = now
                    
                    if now - last_carto_time >= 30:
                        carto_b64_cache = self.encoder_image_b64("carto.png")
                        last_carto_time = now

                    col_case, lig_case = self.carte.coord_vers_indices(self.x_robot, self.y_robot)

                    telemetrie = {
                        "coorApp": f"X:{col_case} Y:{lig_case}",
                        "aiApp": f"{self.moy_cert[1]:.2f}%",
                        "herbeApp": self.nb_herbe,
                        "obsApp": self.nb_obstacles,
                        "timeApp": int(time.time() - self.start_time_global),
                        "terrainApp": self.carte.obtenir_surface_exploree_m2(),
                        
                        # --- LA BARRE DE PROGRESSION REFLETE UNIQUEMENT LES QR VALIDÉS EN SÉQUENCE ---
                        "pourcentApp": round(len(self.qr_trouves) / self.total_qr, 2),
                        
                        "distanceApp": round(self.distance_cm, 1),
                        "photoRecue": photo_b64_cache, 
                        "cartoRecue": carto_b64_cache   
                    }
                    self.bluetooth.envoyer(telemetrie)

                # --- SYNCHRONISATION FPS ---
                time.sleep(max(0, fps - (time.time() - start_time)))
                
        finally:
            if self.cap is not None:
                self.cap.release()
            if self.robot: self.robot.fermer_connexion()
            if not self.sans_app and self.bluetooth: self.bluetooth.fermer()
    
if __name__ == '__main__':
    controleur = VisionController(sans_app=False) 
    controleur.lancer_routine_vision()