import cv2
import os

dictionnaire = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

print("Génération des 26 Tags ArUco en cours...")
for i in range(26):
    tag_image = cv2.aruco.generateImageMarker(dictionnaire, i, 400)
    
    tag_image = cv2.copyMakeBorder(tag_image, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    nom_fichier = f"QR/Tag_ID_{i}.png"
    cv2.imwrite(nom_fichier, tag_image)
    print(f" -> Créé : {nom_fichier}")

print("Terminé ! Tu peux les imprimer.")