import serial
import time

def send(command):
	arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
	time.sleep(2)

	arduino.write(f"{command}\n".encode('utf-8'))
	print(f"Ordre '{command}' envoyé avec succès !")


	arduino.close()

send('A')