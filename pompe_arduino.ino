// Définition de la broche de commande du relais
const int PIN_RELAIS_POMPE = 8;

void setup() {
  // Configuration de la broche du relais en sortie
  pinMode(PIN_RELAIS_POMPE, OUTPUT);
  
  // Par sécurité, on s'assure que la pompe est éteinte au démarrage
  controlerPompe(false);
  
  Serial.begin(115200);
  Serial.println("Système de pompe prêt.");
}

void loop() {
  // --- ZONE DE TEST AUTONOME ---
  // (À remplacer plus tard par la logique de l'IA venant du Raspberry Pi)

  // 1. Activation de la pompe  
  Serial.println("Activation de la pompe");
  controlerPompe(true); // Active la pompe
  delay(5000);          // Attend 5 secondes
  
  // 2. Arrêt de la pompe
  Serial.println("Arrêt de la pompe");
  controlerPompe(false); // Éteint la pompe
  delay(5000);           // Attend 5 secondes
}

/**
 * Fonction qui contrôle l'état de la pompe péristaltique
 * @param activer : true pour allumer la pompe, false pour l'éteindre
 */
void controlerPompe(bool activer) {
  if (activer == true) {
    // On envoie du 5V sur la broche pour coller le relais
    digitalWrite(PIN_RELAIS_POMPE, HIGH); 
  } else {
    // On remet à 0V pour ouvrir le relais et couper le 12V
    digitalWrite(PIN_RELAIS_POMPE, LOW);  
  }
}