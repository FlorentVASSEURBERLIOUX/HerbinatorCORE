import cv2
import time
import random
import ArduinoCommunicator

class VisionController:
    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.qr_detector = cv2.QRCodeDetector()
        
        self.robot = ArduinoCommunicator(port='/dev/ttyACM0')

    def capturer_image(self):
        """Demande une image fraîche à la webcam USB."""
        if not self.cap.isOpened():
            print("[ERREUR] Pas de webcam")
            return False, None
        
        ret, frame = self.cap.read()
        return ret, frame

    def chercher_limite_qrcode(self, image):
        """
        Recherche un QR code.
        Retourne True et un dictionnaire contenant les données, la taille et la position.
        """
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
        """
        Fait appel au modèle d'IA.
        Retourne True si une herbe est détectée avec une certitude >= seuil_certitude.
        """
        certitude_ia = random.uniform(0.0, 100.0) # Test temporaire en attente de l'IA
        
        if certitude_ia >= seuil_certitude:
            print(f"[IA] Herbe détectée ! ({certitude_ia:.1f}%)")
            return True
        return False

    def lancer_routine_vision(self, fps=1.0):
        """Orchestre la prise d'image et le traitement à 1 image par seconde (1 FPS)."""
        print(" Démarrage de la routine de vision")
        
        try:
            while True:
                start_time = time.time()
                
                ret, frame = self.capturer_image()
                if not ret:
                    print("[ERREUR] Pas d'image prise")
                    time.sleep(1)
                    continue

                qr_trouve, infos_qr = self.chercher_limite_qrcode(frame)
                
                if qr_trouve:
                    t = infos_qr["texte"]
                    w = infos_qr["largeur_px"]
                    h = infos_qr["hauteur_px"]
                    x = infos_qr["position_x"]
                    y = infos_qr["position_y"]
                    
                    commande_bordure = f"B:{t}:{w}:{h}:{x}:{y}"
                    print(f"[QR] Limite détectée ('{t}') - Envoi des coordonnées à l'Arduino.")
                    
                    self.robot.send(commande_bordure)
                    
                else:
                    herbe_trouvee = self.detecter_mauvaise_herbe(frame, seuil_certitude=85.0)
                    if herbe_trouvee:
                        print("[ACTION] Cible validée - Envoi de l'ordre de pulvérisation.")
                        self.robot.send("P")

                processing_time = time.time() - start_time
                sleep_time = max(0, fps - processing_time)
                
                if sleep_time == 0: 
                    print(f"[ALERTE] Temps traitement > {fps}s !")
                
                time.sleep(sleep_time)
                
        finally:
            self.cap.release()
            self.robot.fermer_connexion()

if __name__ == '__main__':
    controleur = VisionController()
    controleur.lancer_routine_vision()