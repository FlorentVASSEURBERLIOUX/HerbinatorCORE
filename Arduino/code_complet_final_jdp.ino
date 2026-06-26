#include <Arduino.h>

// --- PINS CAPTEURS ULTRASON HC-SR04 ---
const int PIN_TRIG_AVANT  = A10; const int PIN_ECHO_AVANT  = A11;
const int PIN_TRIG_GAUCHE = A14; const int PIN_ECHO_GAUCHE = A15;
const int PIN_TRIG_DROIT  = A12; const int PIN_ECHO_DROIT  = A13; 

// --- PINS ENCODEURS ---
const int ENCODER_L_A = 18; const int ENCODER_L_B = 30;
const int ENCODER_R_A = 19; const int ENCODER_R_B = 31;

// --- PINS DRIVER L298N ---
const int ENA = 10; const int IN1 = 22; const int IN2 = 23;   
const int ENB = 11; const int IN3 = 24; const int IN4 = 25;

// --- PIN POMPE  ---
const int PIN_POMPE = 8;

// --- CONSTANTES CONFIGURATION ---
const float DIST_DECALAGE_CM = 15.0; // Fixé à 10 cm selon tes instructions
const float DIST_OBSTACLE_DETECTION = 12.0;

// Spécifications de l'encodeur
const float TICKS_PAR_TOUR_ROUE = 600.0; 
const float DIAMETRE_ROUE_CM = 6.5; 
const float PERIMETRE_ROUE_CM = DIAMETRE_ROUE_CM * 3.14159;
const float TICKS_PAR_CM = TICKS_PAR_TOUR_ROUE / PERIMETRE_ROUE_CM;

const float ENTRAXE_ROUES_CM = 15.0; 
const long TICKS_90_DEGRES = (long)(((ENTRAXE_ROUES_CM * 3.14159) / 4.0/* * (105.0 / 360.0)*/) * TICKS_PAR_CM*2.5);

// Constantes pour les mouvements de l'esquive
const long MARGE_ELOIGNEMENT_SECURITE = 700; 
const long MARGE_LONGUEUR_ROBOT = 1000; 

// --- PUISSANCES MOTEURS EN BOUCLE OUVERTE (PWM direct -255 à 255) ---
const int PWM_AVANCE_NORMAL = 180;
const int PWM_PIVOT         = 130;

// --- VARIABLES GLOBALES ET CAPTEURS ---
volatile long ticksMoteurGauche = 0;
volatile long ticksMoteurDroit = 0;
long cumulTicksG = 0; 
long cumulTicksD = 0;

float distAvant = -1, distGauche = -1, distDroit = -1;
int capteurAInterroger = 0;

// RPM réels calculés (lecture seule)
float rpmReelG = 0.0;
float rpmReelD = 0.0;

// --- TIMERS ---
unsigned long prevMsCapteurs = 0;
unsigned long prevMsRpm = 0;
unsigned long prevMsData = 0;
unsigned long timerPompe = 0;
unsigned long timerEsquive = 0;
const long intervalleRpm = 100; 

// --- ÉTATS ---
// Remplacement de DECALAGE_20CM par DECALAGE_10CM dans la FSM Principale
enum EtatRobot { VEILLE, AVANCER_VERS_CHECKPOINT, TURN_90_1, DECALAGE_10CM, TURN_90_2, ARRIVEE };
EtatRobot etatPrincipal = VEILLE;
EtatRobot etatPrecedentVeille = AVANCER_VERS_CHECKPOINT;

enum EtatPompe { POMPE_OFF, POMPE_ON };
EtatPompe etatPompe = POMPE_OFF;

enum EtatEsquive { 
  PAS_D_ESQUIVE, 
  ESQ_PAUSE_ANALYSE, 
  ESQ_PIVOT_1, 
  ESQ_ELOIGNEMENT, 
  ESQ_ELOIGNEMENT_SECURITE, 
  ESQ_PIVOT_2, 
  ESQ_LONGER_1, 
  ESQ_DETECTION_CAPTEUR, 
  ESQ_LONGER_2, 
  ESQ_PIVOT_3, 
  ESQ_RETOUR_AXE, 
  ESQ_RETOUR_SECURITE, 
  ESQ_PIVOT_4 
};
EtatEsquive etatEsquive = PAS_D_ESQUIVE;

bool directionHaut = true; 
bool virageADroite = true; // true = Droite (Impair), false = Gauche (Pair)
long targetTicksMouvement = 0;

int sensContournement = -1;  
long distanceL1 = 0;         
bool obstacleEnVue = false;
int compteurAbsence = 0; 

// --- PROTOTYPES ---
void actualiserCapteursSequentiel();
float calculerDistanceUnitaire(int trigPin, int echoPin);
void piloterMoteurGauche(float commande);
void piloterMoteurDroit(float commande);
void isrG();
void isrD();
void calculerRpmReels();
void gererSerial();
void fsmPrincipale();
void fsmPompe();
void fsmEsquiveDynamique();
void stopperMoteursEtResetCumul();

void setup() {
  Serial.begin(115200);
  
  pinMode(PIN_TRIG_AVANT, OUTPUT);  pinMode(PIN_ECHO_AVANT, INPUT);
  pinMode(PIN_TRIG_GAUCHE, OUTPUT); pinMode(PIN_ECHO_GAUCHE, INPUT);
  pinMode(PIN_TRIG_DROIT, OUTPUT);  pinMode(PIN_ECHO_DROIT, INPUT);
  
  digitalWrite(PIN_TRIG_AVANT, LOW); 
  digitalWrite(PIN_TRIG_GAUCHE, LOW); digitalWrite(PIN_TRIG_DROIT, LOW);

  pinMode(ENCODER_L_A, INPUT_PULLUP); pinMode(ENCODER_L_B, INPUT_PULLUP);
  pinMode(ENCODER_R_A, INPUT_PULLUP); pinMode(ENCODER_R_B, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENCODER_L_A), isrG, RISING);
  attachInterrupt(digitalPinToInterrupt(ENCODER_R_A), isrD, RISING);
  
  pinMode(ENA, OUTPUT); pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT); pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  pinMode(PIN_POMPE, OUTPUT);
  digitalWrite(PIN_POMPE, LOW); 
  
  etatPrincipal = AVANCER_VERS_CHECKPOINT;
}

void loop() {
  unsigned long currentMs = millis();
  
  if (currentMs - prevMsCapteurs >= 20) {
    actualiserCapteursSequentiel();
    prevMsCapteurs = currentMs;
  }
  
  calculerRpmReels();
  gererSerial();
  fsmPompe();
  
  if (etatPrincipal == VEILLE) {
    piloterMoteurDroit(0);
    piloterMoteurGauche(0);
  } 
  else if (etatPompe == POMPE_ON) {
    piloterMoteurDroit(0);
    piloterMoteurGauche(0);
  } 
  else {
    if (etatEsquive == PAS_D_ESQUIVE) {
      // Les capteurs US ne déclenchent l'esquive que si on est en train d'avancer en ligne droite (AVANCER_VERS_CHECKPOINT ou DECALAGE_10CM)
      if (distAvant > 0 && distAvant <= DIST_OBSTACLE_DETECTION && (etatPrincipal == AVANCER_VERS_CHECKPOINT || etatPrincipal == DECALAGE_10CM)) {
        etatEsquive = ESQ_PAUSE_ANALYSE;
        timerEsquive = currentMs;
        stopperMoteursEtResetCumul();
      } else {
        fsmPrincipale();
      }
    } else {
      fsmEsquiveDynamique(); // Reste strictement identique à ton code initial
    }
  }
  
  if (currentMs - prevMsData >= 500) {
    // On fait une copie locale rapide des cumuls pour éviter les conflits d'horloge
    noInterrupts();
    long copieCumulG = cumulTicksG;
    long copieCumulD = cumulTicksD;
    interrupts();

    // Détermination de l'état de détection d'obstacle (1 si ESQ_PAUSE_ANALYSE, 0 sinon)
    int obstacleDetecte = (etatEsquive == ESQ_PAUSE_ANALYSE) ? 1 : 0;

    Serial.print("DATA:");
    Serial.print(copieCumulG); Serial.print(":");
    Serial.print(copieCumulD); Serial.print(":");
    Serial.print((int)distAvant); Serial.print(":");
    Serial.print((int)distGauche); Serial.print(":");
    Serial.print((int)distDroit); Serial.print(":");
    Serial.println(obstacleDetecte);
    //Serial.print((int)rpmReelG); Serial.print(":");
    //Serial.println((int)rpmReelD);
    
    prevMsData = currentMs;
  }
}

// --- MACHINE PRINCIPALE MODIFIÉE POUR LE BOUSTROPHÉDON PAR SERIAL ---
void fsmPrincipale() {
  switch (etatPrincipal) {
    case AVANCER_VERS_CHECKPOINT:
      // Avance en ligne droite. Attend la réception d'une trame "B:..." dans gererSerial() pour changer d'état.
      piloterMoteurGauche(PWM_AVANCE_NORMAL);
      piloterMoteurDroit(PWM_AVANCE_NORMAL);
      break;

    case TURN_90_1:
      if (abs(cumulTicksG) >= TICKS_90_DEGRES || abs(cumulTicksD) >= TICKS_90_DEGRES) {
        stopperMoteursEtResetCumul();
        targetTicksMouvement = DIST_DECALAGE_CM * TICKS_PAR_CM; // Calcule la cible pour 10 cm
        etatPrincipal = DECALAGE_10CM;
      } else {
        // Sélection du sens déterminée par l'ID reçu (Impair -> Droite, Pair -> Gauche)
        if (virageADroite) { piloterMoteurGauche(PWM_PIVOT); piloterMoteurDroit(-PWM_PIVOT); }
        else               { piloterMoteurGauche(-PWM_PIVOT); piloterMoteurDroit(PWM_PIVOT); }
      }
      break;

    case DECALAGE_10CM:
      if (((abs(cumulTicksG) + abs(cumulTicksD)) / 2) >= targetTicksMouvement) {
        stopperMoteursEtResetCumul();
        etatPrincipal = TURN_90_2;
      } else {
        piloterMoteurGauche(PWM_AVANCE_NORMAL);
        piloterMoteurDroit(PWM_AVANCE_NORMAL);
      }
      break;

    case TURN_90_2:
      if (abs(cumulTicksG) >= TICKS_90_DEGRES || abs(cumulTicksD) >= TICKS_90_DEGRES) {
        stopperMoteursEtResetCumul();
        directionHaut = !directionHaut; 
        etatPrincipal = AVANCER_VERS_CHECKPOINT; // Repart tout droit pour la ligne suivante
      } else {
        // Tourne à nouveau dans le même sens que juste avant (virage répété)
        if (virageADroite) { piloterMoteurGauche(PWM_PIVOT); piloterMoteurDroit(-PWM_PIVOT); }
        else               { piloterMoteurGauche(-PWM_PIVOT); piloterMoteurDroit(PWM_PIVOT); }
      }
      break;
      
    case ARRIVEE:
      piloterMoteurDroit(0); piloterMoteurGauche(0);
      break;
      
    default: break;
  }
}

// --- SOUS-MACHINE : POMPE PERISTALTIQUE ---
void fsmPompe() {
  switch (etatPompe) {
    case POMPE_OFF:
      digitalWrite(PIN_POMPE, LOW);
      break;
    case POMPE_ON:
      digitalWrite(PIN_POMPE, HIGH);
      if (millis() - timerPompe >= 2500) {
        etatPompe = POMPE_OFF;
      }
      break;
  }
}

// --- SOUS-MACHINE : ÉVITEMENT DYNAMIQUE (CONSERVÉE STRICTEMENT À L'IDENTIQUE) ---
void fsmEsquiveDynamique() {
  long moyenTicks = (abs(cumulTicksG) + abs(cumulTicksD)) / 2;
  float distLaterale = (sensContournement == -1) ? distDroit : distGauche;

  switch (etatEsquive) {
    case ESQ_PAUSE_ANALYSE:
      piloterMoteurDroit(0); piloterMoteurGauche(0);
      if (millis() - timerEsquive >= 600) {
        stopperMoteursEtResetCumul();
        if (distGauche > 45 || distGauche == -1) { sensContournement = -1; } else { sensContournement = 1; }
        compteurAbsence = 0;
        etatEsquive = ESQ_PIVOT_1;
      }
      break;
    case ESQ_PIVOT_1:
      piloterMoteurGauche(PWM_PIVOT * sensContournement); piloterMoteurDroit(-PWM_PIVOT * sensContournement);
      if (moyenTicks >= TICKS_90_DEGRES) { stopperMoteursEtResetCumul(); distanceL1 = 0; obstacleEnVue = false; compteurAbsence = 0; etatEsquive = ESQ_ELOIGNEMENT; }
      break;
    case ESQ_ELOIGNEMENT:
      piloterMoteurGauche(PWM_AVANCE_NORMAL); piloterMoteurDroit(PWM_AVANCE_NORMAL);
      if (distLaterale > 0 && distLaterale <= 40) { obstacleEnVue = true; compteurAbsence = 0; }
      if (obstacleEnVue && (distLaterale > 40 || distLaterale == -1)) {
        compteurAbsence++;
        if (compteurAbsence >= 5) { distanceL1 = moyenTicks; stopperMoteursEtResetCumul(); obstacleEnVue = false; compteurAbsence = 0; etatEsquive = ESQ_ELOIGNEMENT_SECURITE; }
      } else if (obstacleEnVue) { compteurAbsence = 0; }
      break;
    case ESQ_ELOIGNEMENT_SECURITE:
      piloterMoteurGauche(PWM_AVANCE_NORMAL); piloterMoteurDroit(PWM_AVANCE_NORMAL);
      if (moyenTicks >= MARGE_ELOIGNEMENT_SECURITE) { stopperMoteursEtResetCumul(); etatEsquive = ESQ_PIVOT_2; }
      break;
    case ESQ_PIVOT_2:
      piloterMoteurGauche(-PWM_PIVOT * sensContournement); piloterMoteurDroit(PWM_PIVOT * sensContournement);
      if (moyenTicks >= TICKS_90_DEGRES) { stopperMoteursEtResetCumul(); obstacleEnVue = false; compteurAbsence = 0; etatEsquive = ESQ_LONGER_1; }
      break;
    case ESQ_LONGER_1:
      piloterMoteurGauche(PWM_AVANCE_NORMAL); piloterMoteurDroit(PWM_AVANCE_NORMAL);
      if (distLaterale > 0 && distLaterale <= 45) { stopperMoteursEtResetCumul(); compteurAbsence = 0; obstacleEnVue = true; etatEsquive = ESQ_DETECTION_CAPTEUR; }
      break;
    case ESQ_DETECTION_CAPTEUR:
      piloterMoteurGauche(PWM_AVANCE_NORMAL); piloterMoteurDroit(PWM_AVANCE_NORMAL);
      if (distLaterale > 45 || distLaterale == -1) {
        compteurAbsence++; if (compteurAbsence >= 5) { stopperMoteursEtResetCumul(); compteurAbsence = 0; etatEsquive = ESQ_LONGER_2; }
      } else { compteurAbsence = 0; }
      break;
    case ESQ_LONGER_2:
      piloterMoteurGauche(PWM_AVANCE_NORMAL); piloterMoteurDroit(PWM_AVANCE_NORMAL);
      if (moyenTicks >= MARGE_LONGUEUR_ROBOT) { stopperMoteursEtResetCumul(); etatEsquive = ESQ_PIVOT_3; }
      break;
    case ESQ_PIVOT_3:
      piloterMoteurGauche(-PWM_PIVOT * sensContournement); piloterMoteurDroit(PWM_PIVOT * sensContournement);
      if (moyenTicks >= TICKS_90_DEGRES) { stopperMoteursEtResetCumul(); etatEsquive = ESQ_RETOUR_AXE; }
      break;
    case ESQ_RETOUR_AXE:
      piloterMoteurGauche(PWM_AVANCE_NORMAL); piloterMoteurDroit(PWM_AVANCE_NORMAL);
      if (moyenTicks >= distanceL1) { stopperMoteursEtResetCumul(); etatEsquive = ESQ_RETOUR_SECURITE; }
      break;
    case ESQ_RETOUR_SECURITE:
      piloterMoteurGauche(PWM_AVANCE_NORMAL); piloterMoteurDroit(PWM_AVANCE_NORMAL);
      if (moyenTicks >= MARGE_ELOIGNEMENT_SECURITE) { stopperMoteursEtResetCumul(); etatEsquive = ESQ_PIVOT_4; }
      break;
    case ESQ_PIVOT_4:
      piloterMoteurGauche(PWM_PIVOT * sensContournement); piloterMoteurDroit(-PWM_PIVOT * sensContournement);
      if (moyenTicks >= TICKS_90_DEGRES) { stopperMoteursEtResetCumul(); etatEsquive = PAS_D_ESQUIVE; }
      break;
    default: break;
  }
}

void calculerRpmReels() {
  unsigned long actuelMillis = millis();
  if (actuelMillis - prevMsRpm >= intervalleRpm) {
    prevMsRpm = actuelMillis;
    noInterrupts(); long copieG = abs(ticksMoteurGauche); ticksMoteurGauche = 0; long copieD = abs(ticksMoteurDroit); ticksMoteurDroit = 0; interrupts();
    rpmReelG = (copieG / TICKS_PAR_TOUR_ROUE) * (60.0 / (intervalleRpm / 1000.0));
    rpmReelD = (copieD / TICKS_PAR_TOUR_ROUE) * (60.0 / (intervalleRpm / 1000.0));
  }
}

// --- PARSING DES MESSAGES SERIAL ---
void gererSerial() {
  if (Serial.available() > 0) {
    String msg = Serial.readStringUntil('\n');
    msg.trim();
    
    if (msg.startsWith("V")) {
      if (etatPrincipal != VEILLE) { etatPrecedentVeille = etatPrincipal; etatPrincipal = VEILLE; }
    } 
    else if (msg.startsWith("S")) {
      if (etatPrincipal == VEILLE) { etatPrincipal = etatPrecedentVeille; }
    } 
    else if (msg.startsWith("P:")) {
      timerPompe = millis(); etatPompe = POMPE_ON; 
    } 
    else if (msg.startsWith("B:")) {
      // SÉCURITÉ : Si le robot est déjà en train de faire son demi-tour, 
      // on ignore totalement les ordres répétitifs de la RPi pour ne pas spammer le reset !
      if (etatPrincipal == TURN_90_1 || etatPrincipal == DECALAGE_10CM || etatPrincipal == TURN_90_2) {
        return; 
      }

      int idx1 = msg.indexOf(':');
      int idx2 = msg.indexOf(':', idx1 + 1);
      
      if (idx1 != -1 && idx2 != -1) {
        String label = msg.substring(idx1 + 1, idx2);
        label.trim();
        
        String tempNum = "";
        for (int i = 0; i < label.length(); i++) {
          if (isDigit(label.charAt(i))) {
            tempNum += label.charAt(i);
          }
        }
        
        if (tempNum.length() > 0) {
          int numCheckpoint = tempNum.toInt();
          
          if (numCheckpoint == 0) {
            stopperMoteursEtResetCumul();
            etatPrincipal = AVANCER_VERS_CHECKPOINT;
            Serial.println("ACK:START");
          } else if (numCheckpoint == 6) { 
            stopperMoteursEtResetCumul();
            etatPrincipal = ARRIVEE;
            Serial.println("ACK:ARRIVEE");
          } else {
            // On ne reset et ne change d'état que si on venait bien de la ligne droite
            if (etatPrincipal == AVANCER_VERS_CHECKPOINT) {
              stopperMoteursEtResetCumul();
              
              if (numCheckpoint % 2 != 0) {
                virageADroite = true;  
              } else {
                virageADroite = false; 
              }
              etatPrincipal = TURN_90_1;
              Serial.print("ACK:VIRAGE:"); Serial.println(numCheckpoint);
            }
          }
        }
      }
    }
  }
}

void stopperMoteursEtResetCumul() {
  piloterMoteurDroit(0); piloterMoteurGauche(0);
  ticksMoteurGauche = 0; ticksMoteurDroit = 0;
  cumulTicksG = 0;       cumulTicksD = 0;
}

void actualiserCapteursSequentiel() {
  switch (capteurAInterroger) {
    case 0: distAvant  = calculerDistanceUnitaire(PIN_TRIG_AVANT, PIN_ECHO_AVANT);   capteurAInterroger = 1; break;
    case 1: distGauche = calculerDistanceUnitaire(PIN_TRIG_GAUCHE, PIN_ECHO_GAUCHE); capteurAInterroger = 2; break;
    case 2: distDroit  = calculerDistanceUnitaire(PIN_TRIG_DROIT, PIN_ECHO_DROIT);   capteurAInterroger = 0; break;
  }
}

float calculerDistanceUnitaire(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW); delayMicroseconds(2);
  digitalWrite(trigPin, HIGH); delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long duree = pulseIn(echoPin, HIGH, 15000); 
  if (duree == 0) return -1; 
  return (duree * 0.034) / 2.0; 
}

void piloterMoteurGauche(float commande) {
  int pwm = constrain((int)commande, -255, 255);
  if (pwm >= 0) { digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH); analogWrite(ENA, pwm); } 
  else { digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW); analogWrite(ENA, abs(pwm)); }
}

void piloterMoteurDroit(float commande) {
  int pwm = constrain((int)commande, -255, 255);
  if (pwm >= 0) { digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW); analogWrite(ENB, pwm); } 
  else { digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH); analogWrite(ENB, abs(pwm)); }
}

void isrG() { ticksMoteurGauche++; cumulTicksG++; }
void isrD() { ticksMoteurDroit++; cumulTicksD++; }