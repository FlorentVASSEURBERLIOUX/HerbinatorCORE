// --- PINS CAPTEUR ULTRASON HC-SR04 ---
const int PIN_TRIG = 12; // Pin Trigger du capteur ultrason
const int PIN_ECHO = 13; // Pin Echo du capteur ultrason

// --- PINS ENCODEURS ---
const int ENCODER_L_A = 18; 
const int ENCODER_L_B = 30;
const int ENCODER_R_A = 19; 
const int ENCODER_R_B = 31;

// --- PINS DRIVER L298N ---
const int ENA = 10;   // Contrôle Vitesse Gauche (PWM)
const int IN1 = 22;   // Sens Gauche
const int IN2 = 23;   // Sens Gauche
const int ENB = 11;  // Contrôle Vitesse Droit (PWM)
const int IN3 = 25;  // Sens Droit
const int IN4 = 24;  // Sens Droit

// --- VARIABLES ENCODEURS ---
volatile long ticksMoteurGauche = 0;
volatile long ticksMoteurDroit = 0;
unsigned long precedentMillis = 0;
const long intervalle = 100; // Échantillonnage toutes les 100ms
const float TICKS_PER_REV = 750.0; 

// --- VARIABLES DE POSITION GLOBALE ---
long totalTicksG = 0;
long totalTicksD = 0;

// --- VARIABLES PID  ---
float consigneG = 33.4; 
float consigneD = 35.0; 

// Coefficients PID
float Kp = 5.0; 
float Ki = 1.8;
float Kd = 0.25;

float erreurPrecedenteG = 0, sommeErreursG = 0;
float erreurPrecedenteD = 0, sommeErreursD = 0;

void setup() {
  Serial.begin(115200);

  // Configuration Capteur Ultrason
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  digitalWrite(PIN_TRIG, LOW);

  // Configuration L298N
  pinMode(ENA, OUTPUT); pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT); pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);

  // Configuration Encodeurs
  pinMode(ENCODER_L_A, INPUT_PULLUP); pinMode(ENCODER_L_B, INPUT_PULLUP);
  pinMode(ENCODER_R_A, INPUT_PULLUP); pinMode(ENCODER_R_B, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(ENCODER_L_A), isrG, RISING);
  attachInterrupt(digitalPinToInterrupt(ENCODER_R_A), isrD, RISING);
}

void loop() {
  // 1. MESURE DE LA DISTANCE DE SÉCURITÉ (HC-SR04)
  float distance = obtenirDistanceUltrason();

  // Si un obstacle est détecté à moins de 20 cm, arrêt d'urgence immédiat
  if (distance > 0 && distance < 20.0) {
    analogWrite(ENA, 0);
    analogWrite(ENB, 0);
    digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
    digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
    Serial.print("--- OBSTACLE DETECTE ! Arrêt de sécurité à : ");
    Serial.print(distance); Serial.println(" cm ---");
    delay(200); // Petite pause pour éviter de saturer le processeur
    return;     // On saute le reste de la boucle pour ne pas exécuter le PID
  }

  // 2. RÉGULATION DU DÉPLACEMENT (PID)
  unsigned long actuelMillis = millis();

  if (actuelMillis - precedentMillis >= intervalle) {
    precedentMillis = actuelMillis;
  
    // Lecture sécurisée des ticks (et reset pour la vitesse instantanée)
    noInterrupts();
    long copieG = abs(ticksMoteurGauche); ticksMoteurGauche = 0;
    long copieD = abs(ticksMoteurDroit);  ticksMoteurDroit = 0;
    interrupts();

    // Accumulation dans le compteur global pour la future cartographie
    totalTicksG += copieG;
    totalTicksD += copieD;

    float toursG = (float)totalTicksG / TICKS_PER_REV;
    float toursD = (float)totalTicksD / TICKS_PER_REV;

    // Calcul des RPM réels (toujours positifs pour stabiliser la boucle)
    float rpmReelG = (copieG / TICKS_PER_REV) * (60.0 / (intervalle / 1000.0));
    float rpmReelD = (copieD / TICKS_PER_REV) * (60.0 / (intervalle / 1000.0));

    // Calcul PID - Moteur Gauche
    float erreurG = consigneG - rpmReelG;
    sommeErreursG += erreurG * 0.1;
    sommeErreursG = constrain(sommeErreursG, -150, 150); // Anti-windup pour éviter les emballements
    float deriveeG = (erreurG - erreurPrecedenteG) / 0.1;
    float commandeG = (Kp * erreurG) + (Ki * sommeErreursG) + (Kd * deriveeG);
    erreurPrecedenteG = erreurG;

    // Calcul PID - Moteur Droit
    float erreurD = consigneD - rpmReelD;
    sommeErreursD += erreurD * 0.1;
    sommeErreursD = constrain(sommeErreursD, -150, 150); 
    float deriveeD = (erreurD - erreurPrecedenteD) / 0.1;
    float commandeD = (Kp * erreurD) + (Ki * sommeErreursD) + (Kd * deriveeD);
    erreurPrecedenteD = erreurD;

    // Envoi des commandes aux moteurs
    piloterMoteurGauche(commandeG);
    piloterMoteurDroit(commandeD);

    // Affichage Moniteur Série
    Serial.print("G: "); Serial.print(rpmReelG, 1); Serial.print(" RPM (Cmd: "); Serial.print(commandeG, 0);
    Serial.print(") || D: "); Serial.print(rpmReelD, 1); Serial.print(" RPM (Cmd: "); Serial.print(commandeD, 0);
    Serial.print(") || Dist: "); Serial.print(distance, 1); Serial.println(" cm");
  }
}

// --- FONCTION CAPTEUR ULTRASON ---
float obtenirDistanceUltrason() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  
  // Mesure du temps de retour de l'onde (timeout à 25ms pour ne pas bloquer le code)
  long duree = pulseIn(PIN_ECHO, HIGH, 25000); 
  
  if (duree == 0) return -1; // Pas d'écho détecté
  return (duree * 0.034) / 2.0; // Conversion en cm
}

// --- FONCTIONS DE PILOTAGE L298N ---
void piloterMoteurGauche(float commande) {
  int pwm = constrain((int)commande, -255, 255);
  if (pwm >= 0) {
    digitalWrite(IN1, LOW);  digitalWrite(IN2, HIGH); // Marche avant mécanique
    analogWrite(ENA, pwm);
  } else {
    digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);  // Marche arrière mécanique
    analogWrite(ENA, abs(pwm));
  }
}

void piloterMoteurDroit(float commande) {
  int pwm = constrain((int)commande, -255, 255);
  if (pwm >= 0) {
    digitalWrite(IN3, LOW);  digitalWrite(IN4, HIGH); // Marche avant mécanique
    analogWrite(ENB, pwm);
  } else {
    digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);  // Marche arrière mécanique
    analogWrite(ENB, abs(pwm));
  }
}

// --- ROUTINES D'INTERRUPTIONS ---
// Simplifiées au maximum pour le calcul de vitesse brute
void isrG() { ticksMoteurGauche++; }
void isrD() { ticksMoteurDroit++; }