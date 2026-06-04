import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import math

class Cartographie:
    def __init__(self, taille_terrain_cm, resolution_cm):
        """
        Initialise la grille d'occupation.
        taille_terrain_cm : tuple (largeur_X, hauteur_Y) en cm.
        resolution_cm : taille réelle que représente une case de la matrice (ex: 10 cm).
        """
        self.resolution = resolution_cm
        self.colonnes = int(taille_terrain_cm[0] / resolution_cm)
        self.lignes = int(taille_terrain_cm[1] / resolution_cm)
        
        # États possibles d'une case :
        # 0 = Non exploré (Gris)
        # 1 = Espace libre (Blanc)
        # 2 = Obstacle physique (Rouge)
        # 3 = Mauvaise herbe ciblée par l'IA (Vert)
        self.grille = np.zeros((self.lignes, self.colonnes), dtype=int)
        
    def coord_vers_grille(self, x_cm, y_cm):
        """Convertit les coordonnées réelles (cm) en indices de matrice (ligne, colonne)"""
        col = int(x_cm / self.resolution)
        lig = int(y_cm / self.resolution)
        
        # Sécurité : vérifier que l'on reste dans les limites du tableau
        if 0 <= lig < self.lignes and 0 <= col < self.colonnes:
            return lig, col
        return None, None

    def mettre_a_jour(self, x_robot, y_robot, cap_degres, dist_obstacle_cm=None, cible_yolo_detectee=False):
        """
        Met à jour la matrice avec les nouvelles informations de télémétrie.
        """
        lig_robot, col_robot = self.coord_vers_grille(x_robot, y_robot)
        
        if lig_robot is None or col_robot is None:
            return # Le robot est hors zone cartographiée

        # 1. Action métier : Cible détectée
        if cible_yolo_detectee:
            self.grille[lig_robot, col_robot] = 3
        
        # 2. Déplacement standard : Marquer la case actuelle comme "Libre"
        elif self.grille[lig_robot, col_robot] == 0:
            self.grille[lig_robot, col_robot] = 1

        # 3. Traitement du capteur à ultrasons : Enregistrer un obstacle
        if dist_obstacle_cm is not None and dist_obstacle_cm < 150: 
            # Calcul trigonométrique de la position de l'obstacle
            cap_rad = math.radians(cap_degres)
            x_obs = x_robot + dist_obstacle_cm * math.cos(cap_rad)
            y_obs = y_robot + dist_obstacle_cm * math.sin(cap_rad)
            
            lig_obs, col_obs = self.coord_vers_grille(x_obs, y_obs)
            if lig_obs is not None and col_obs is not None:
                # On ne marque l'obstacle que si la case n'est pas déjà ciblée comme une plante
                if self.grille[lig_obs, col_obs] != 3:
                    self.grille[lig_obs, col_obs] = 2

    def afficher_carte_pure(self):
        """Affiche UNIQUEMENT la grille et les cellules, sans axes ni texte."""
        cmap = mcolors.ListedColormap(['#e2e8f0', '#ffffff', '#ef4444', '#10b981'])
        bounds = [0, 1, 2, 3, 4]
        norm = mcolors.BoundaryNorm(bounds, cmap.N)

        # CORRECTION 1 : Calcul de la taille de la fenêtre pour respecter les proportions
        ratio = self.lignes / self.colonnes
        largeur_fenetre = 10
        hauteur_fenetre = largeur_fenetre * ratio

        fig, ax = plt.subplots(figsize=(largeur_fenetre, hauteur_fenetre))
        
        # CORRECTION 2 : Forcer aspect='equal' pour avoir des carrés parfaits
        ax.imshow(self.grille, cmap=cmap, norm=norm, origin='lower', aspect='equal')
        
        # CORRECTION 3 : + 0.5 ajouté pour que la grille aille bien jusqu'au bout du dessin
        ax.set_xticks(np.arange(-.5, self.colonnes + 0.5, 1), minor=True)
        ax.set_yticks(np.arange(-.5, self.lignes + 0.5, 1), minor=True)
        ax.grid(which="minor", color="black", linestyle='-', linewidth=0.5, alpha=0.3)
        
        # Masquer les numéros des axes et les petites graduations
        ax.tick_params(which="both", bottom=False, left=False, labelbottom=False, labelleft=False)
        
        # Masquer le cadre noir autour de l'image
        for spine in ax.spines.values():
            spine.set_visible(False)
            
        plt.tight_layout()
        plt.show()

# ==========================================
# EXEMPLE D'UTILISATION (SIMULATION DU ROBOT)
# ==========================================
if __name__ == "__main__":
    # Initialisation d'un terrain de 300x200 cm, avec des cases de 10x10 cm
    carte = Cartographie(taille_terrain_cm=(300, 300), resolution_cm=10)

    # Simulation d'une trajectoire et d'événements
    
    # 1. Le robot avance tout droit (Cap 0°) et détecte un mur devant lui
    carte.mettre_a_jour(x_robot=30, y_robot=50, cap_degres=0)
    carte.mettre_a_jour(x_robot=40, y_robot=50, cap_degres=0)
    carte.mettre_a_jour(x_robot=50, y_robot=50, cap_degres=0)
    carte.mettre_a_jour(x_robot=60, y_robot=50, cap_degres=0)
    carte.mettre_a_jour(x_robot=70, y_robot=50, cap_degres=0, dist_obstacle_cm=10) 
    
    # 2. Le robot esquive et monte (Cap 90°)
    carte.mettre_a_jour(x_robot=70, y_robot=60, cap_degres=90)
    carte.mettre_a_jour(x_robot=70, y_robot=70, cap_degres=90)
    
    # 3. L'IA repère une cible
    carte.mettre_a_jour(x_robot=70, y_robot=80, cap_degres=90, cible_yolo_detectee=True)
    
    # 4. Le robot repart
    carte.mettre_a_jour(x_robot=70, y_robot=90, cap_degres=90)
    
    # Affichage du résultat net et parfait
    carte.afficher_carte_pure()