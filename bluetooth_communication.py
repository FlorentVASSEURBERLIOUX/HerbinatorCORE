import socket
import json
import time

def start_bluetooth_server(datas):
    server_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    port = 1
    
    try:
        server_sock.bind(("", port))
        server_sock.listen(1)
        
        client_sock, client_info = server_sock.accept()
        print(f"\n[+] Connexion établie avec l'appareil : {client_info}")
        
        message = json.dumps(datas) + "\n"
        
        while True:
            client_sock.send(message.encode('utf-8'))
            print(f"> Données envoyées : {message.strip()}")
            time.sleep(2)
            
    except Exception as e:
        print(f"\n[ERREUR] {e}")
    finally:
        if 'client_sock' in locals():
            client_sock.close()
        server_sock.close()

