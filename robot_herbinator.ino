// --- PINS ENCODEURS ---
const int ENCODER_L_A = 2; // Interruption 0
const int ENCODER_L_B = 4;
const int ENCODER_R_A = 3; // Interruption 1
const int ENCODER_R_B = 5;

// --- PINS DRIVER L298N ---
const int ENA = 9;   // Contrôle Vitesse Gauche (PWM)
const int IN1 = 7;   // Sens Gauche
const int IN2 = 8;   // Sens Gauche
const int ENB = 10;  // Contrôle Vitesse Droit (PWM)
const int IN3 = 11;  // Sens Droit
const int IN4 = 12;  // Sens Droit

// --- VARIABLES ENCODEURS ---
volatile long ticksMoteurGauche = 0;
volatile long volatile ticksMoteurDroit = 0;
unsigned long precedentMillis = 0;
const long intervalle = 100; // Échantillonnage toutes les 100ms (dt = 0.1s)
const float TICKS_PER_REV = 750.0; // À ajuster selon votre test (ex: 3 PPR * 250)

// --- VARIABLES PID ---
float consigneG = 40.0; // Vitesse cible pour le moteur gauche (en RPM)
float consigneD = 40.0; // Vitesse cible pour le moteur droit (en RPM)

// Coefficients PID à affiner lors de vos tests à l'ESIEE
float Kp = 2.0; 
float Ki = 0.5;
float Kd = 0.1;

float erreurPrecedenteG = 0, sommeErreursG = 0;
float erreurPrecedenteD = 0, sommeErreursD = 0;

void setup() {
  Serial.begin(115200);

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
  unsigned long actuelMillis = millis();

  if (actuelMillis - precedentMillis >= intervalle) {
    precedentMillis = actuelMillis;

    // 1. Lecture sécurisée des ticks
    noInterrupts();
    long copieG = ticksMoteurGauche; ticksMoteurGauche = 0;
    long copieD = ticksMoteurDroit;  ticksMoteurDroit = 0;
    interrupts();

    // 2. Calcul des RPM réels
    float rpmReelG = (copieG / TICKS_PER_REV) * (60.0 / (intervalle / 1000.0));
    float rpmReelD = (copieD / TICKS_PER_REV) * (60.0 / (intervalle / 1000.0));

    // 3. Calcul du PID - Moteur Gauche
    float erreurG = consigneG - rpmReelG;
    sommeErreursG += erreurG * 0.1;
    float deriveeG = (erreurG - erreurPrecedenteG) / 0.1;
    float commandeG = (Kp * erreurG) + (Ki * sommeErreursG) + (Kd * deriveeG);
    erreurPrecedenteG = erreurG;

    // 4. Calcul du PID - Moteur Droit
    float erreurD = consigneD - rpmReelD;
    sommeErreursD += erreurD * 0.1;
    float deriveeD = (erreurD - erreurPrecedenteD) / 0.1;
    float commandeD = (Kp * erreurD) + (Ki * sommeErreursD) + (Kd * deriveeD);
    erreurPrecedenteD = erreurD;

    // 5. Envoi des commandes de puissance au L298N
    piloterMoteurGauche(commandeG);
    piloterMoteurDroit(commandeD);

    // 6. Debug / Affichage pour le traceur série
    Serial.print("Target_G:"); Serial.print(consigneG);
    Serial.print("\tRPM_G:");    Serial.print(rpmReelG);
    Serial.print("\tTarget_D:"); Serial.print(consigneD);
    Serial.print("\tRPM_D:");    Serial.println(rpmReelD);
  }
}

// --- FONCTIONS DE PILOTAGE L298N ---
void piloterMoteurGauche(float commande) {
  int pwm = constrain((int)commande, -255, 255);
  if (pwm >= 0) {
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
    analogWrite(ENA, pwm);
  } else {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);
    analogWrite(ENA, abs(pwm));
  }
}

void piloterMoteurDroit(float commande) {
  int pwm = constrain((int)commande, -255, 255);
  if (pwm >= 0) {
    digitalWrite(IN3, HIGH);
    digitalWrite(IN4, LOW);
    analogWrite(ENB, pwm);
  } else {
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, HIGH);
    analogWrite(ENB, abs(pwm));
  }
}

// --- ROUTINES D'INTERRUPTIONS ---
void isrG() {
  if (digitalRead(ENCODER_L_B) == LOW) ticksMoteurGauche++; else ticksMoteurGauche--;
}

void isrD() {
  if (digitalRead(ENCODER_R_B) == LOW) ticksMoteurDroit++; else ticksMoteurDroit--;
}
