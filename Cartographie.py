import numpy as np
import math
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

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

        ratio = self.lignes / self.colonnes
        largeur_fenetre = 10
        hauteur_fenetre = largeur_fenetre * ratio

        fig, ax = plt.subplots(figsize=(largeur_fenetre, hauteur_fenetre))
        ax.imshow(self.grille, cmap=cmap, norm=norm, origin='lower', aspect='equal')
        
        ax.set_xticks(np.arange(-.5, self.colonnes + 0.5, 1), minor=True)
        ax.set_yticks(np.arange(-.5, self.lignes + 0.5, 1), minor=True)
        ax.grid(which="minor", color="black", linestyle='-', linewidth=0.5, alpha=0.3)
        ax.tick_params(which="both", bottom=False, left=False, labelbottom=False, labelleft=False)
        
        for spine in ax.spines.values():
            spine.set_visible(False)
            
        plt.tight_layout()
        plt.show()

    def sauvegarder_carte(self, nom_fichier="carte_herbinator.png"):
        """Sauvegarde la carte en tant qu'image PNG sans bloquer le programme."""
        cmap = mcolors.ListedColormap(['#e2e8f0', '#ffffff', '#ef4444', '#10b981'])
        bounds = [0, 1, 2, 3, 4]
        norm = mcolors.BoundaryNorm(bounds, cmap.N)

        ratio = self.lignes / self.colonnes
        largeur_fenetre = 8
        hauteur_fenetre = largeur_fenetre * ratio

        fig, ax = plt.subplots(figsize=(largeur_fenetre, hauteur_fenetre))
        ax.imshow(self.grille, cmap=cmap, norm=norm, origin='lower', aspect='equal')
        
        ax.set_xticks(np.arange(-.5, self.colonnes + 0.5, 1), minor=True)
        ax.set_yticks(np.arange(-.5, self.lignes + 0.5, 1), minor=True)
        ax.grid(which="minor", color="black", linestyle='-', linewidth=0.5, alpha=0.3)
        ax.tick_params(which="both", bottom=False, left=False, labelbottom=False, labelleft=False)
        
        for spine in ax.spines.values():
            spine.set_visible(False)
            
        plt.tight_layout()
        plt.savefig(nom_fichier, bbox_inches='tight', pad_inches=0, dpi=100)
        plt.close(fig)

    def obtenir_surface_exploree_m2(self):
        """Compte les cases découvertes (!= 0) et retourne la superficie en m²."""
        nb_cases_explorees = np.count_nonzero(self.grille)
        surface_une_case_m2 = (self.resolution / 100.0) ** 2
        return round(nb_cases_explorees * surface_une_case_m2, 3)

    # --- SÉQUENCE UNIQUE AJOUTÉE : TRADUCTION COORDONNÉES REELLES VERS INDICES DE LA GRILLE ---
    def coord_vers_indices(self, x_cm, y_cm):
        """Retourne les indices de case (colonne, ligne) sous forme de tuple pour l'application."""
        lig, col = self.coord_vers_grille(x_cm, y_cm)
        if lig is not None and col is not None:
            return col, lig
        return 0, 0