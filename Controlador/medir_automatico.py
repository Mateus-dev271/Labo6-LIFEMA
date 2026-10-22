import subprocess
import serial
import time
import sys

# ============================================================
#                    CONFIGURACIÓN
# ============================================================

# Ruta al ejecutable de DigiCamControl
#DCC_REMOTE = r"C:\Program Files\digiCamControl\CameraControlRemoteCmd.exe"
# Si está en Program Files (x86):
DCC_REMOTE = r"C:\Program Files (x86)\digiCamControl\CameraControlRemoteCmd.exe"

# Puerto serie del Arduino
ARDUINO_PORT = "COM3"          # ← cambialo
BAUD_RATE = 115200

# Carpeta donde se guardan los videos
#CARPETA_VIDEOS = r"C:\Users\mainumbi\Documents\Labo 6-7\juan-mateo\datos\prueba codigo vagancia"

# Lista de velocidades a probar
#VELOCIDADES = [210,220]  #velocidad de prueba
VELOCIDADES = [90,100,110,120,130,140,150,160,170,180,190,200,210,220,230,240,250]

# Tiempos de espera (segundos)
ESPERA_DESPUES_DERECHA = 6.0    # después de terminar el movimiento a la derecha
ESPERA_DESPUES_IZQUIERDA = 8.0  # después de terminar el movimiento a la izquierda
ESPERA_EXTRA_FIN = 1          # pequeño margen después de recibir "motor apagado"

# Texto que manda el Arduino cuando termina el movimiento
MENSAJE_FIN = "motor apagado"

# Timeout máximo esperando la señal del motor (segundos)
TIMEOUT_MOTOR = 20


# Prefijo para los nombres de archivo (se agrega velocidad y dirección)
# Ejemplo resultante: vel_120_derecha.MOV  /  vel_120_izquierda.MOV
PREFIJO_NOMBRE = "v"
#%%
# ============================================================

def dcc(cmd: str) -> bool:
    """Envía un comando a DigiCamControl"""
    try:
        result = subprocess.run(
            [DCC_REMOTE, "/c", cmd],
            capture_output=True,
            text=True,
            timeout=15
        )
        salida = (result.stdout or result.stderr or "").strip()
        print(f"  [DCC] {cmd}  →  {salida or 'OK'}")
        return True
    except Exception as e:
        print(f"  [ERROR DCC] {e}")
        return False

def set_nombre_archivo(nombre: str):
    """Configura el nombre de archivo para el próximo video"""
    # Sin extensión: DigiCamControl le pone la que corresponda (.MOV, .MP4, etc.)
    dcc(f'set session.filenametemplate {nombre}')

def start_recording():
    dcc("do LiveViewWnd_Show")
    time.sleep(1.0)
    dcc("do StartRecord")

def stop_recording():
    dcc("do StopRecord")

def enviar_arduino(ser, texto: str):
    """Envía un comando al Arduino y lo muestra"""
    cmd = texto.strip() + "\n"
    ser.write(cmd.encode("utf-8"))
    print(f"  [Arduino] Enviado → {texto}")

def esperar_motor_apagado(ser) -> bool:
    """Espera hasta recibir el mensaje de fin del motor"""
    print(f"  Esperando '{MENSAJE_FIN}'...")
    inicio = time.time()
    while time.time() - inicio < TIMEOUT_MOTOR:
        if ser.in_waiting > 0:
            linea = ser.readline().decode("utf-8", errors="ignore").strip()
            if linea:
                print(f"  [Arduino] Recibido: '{linea}'")
                if MENSAJE_FIN.lower() in linea.lower():
                    print("  → Señal de fin detectada")
                    return True
        time.sleep(0.04)
    print("  ⚠ Timeout: no llegó la señal de fin")
    return False

def grabar_un_movimiento(ser, velocidad: int, direccion: str, nombre_archivo: str):
    """
    direccion: "b" (derecha) o "a" (izquierda)
    """
    print(f"\n--- Velocidad {velocidad} | Dirección {direccion} | Archivo: {nombre_archivo} ---")

    # 1. Setear velocidad
    enviar_arduino(ser, f"v{velocidad}")
    time.sleep(0.3)

    # 2. Nombre del archivo
    set_nombre_archivo(nombre_archivo)
    time.sleep(0.2)

    # 3. Empezar a grabar
    print("  Iniciando grabación...")
    start_recording()
    time.sleep(0.4)

    # 4. Arrancar motor
    enviar_arduino(ser, direccion)

    # 5. Esperar fin
    ok = esperar_motor_apagado(ser)

    # 6. Pequeño margen y parar grabación
    time.sleep(ESPERA_EXTRA_FIN)
    print("  Deteniendo grabación...")
    stop_recording()

    if not ok:
        print("  ⚠ Atención: se detuvo por timeout")

def main():
    print("=" * 60)
    print("  AUTOMATIZACIÓN DE EXPERIMENTO - CÁMARA + MOTOR")
    print("=" * 60)
    print(f"Velocidades: {VELOCIDADES}")
    #print(f"Carpeta:     {CARPETA_VIDEOS}")
    print()

    # Abrir puerto serie
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=0.5)
        time.sleep(2.0)
        print(f"Puerto {ARDUINO_PORT} abierto correctamente\n")
    except Exception as e:
        print(f"ERROR abriendo puerto serie: {e}")
        sys.exit(1)

    # Configurar carpeta de DigiCamControl una sola vez
    #dcc(f'set session.folder "{CARPETA_VIDEOS}"')
    time.sleep(0.5)

    try:
        for i, vel in enumerate(VELOCIDADES, 1):
            print(f"\n{'='*60}")
            print(f"  VELOCIDAD {vel}  ({i}/{len(VELOCIDADES)})")
            print(f"{'='*60}")

            # ----- Movimiento a la DERECHA (b) -----
            nombre_der = f"{PREFIJO_NOMBRE}_{vel:03d}_ida"
            grabar_un_movimiento(ser, vel, "b", nombre_der)

            print(f"  Esperando {ESPERA_DESPUES_DERECHA}s antes del movimiento contrario...")
            time.sleep(ESPERA_DESPUES_DERECHA)

            # ----- Movimiento a la IZQUIERDA (a) -----
            nombre_izq = f"{PREFIJO_NOMBRE}_{vel:03d}_vuelta"
            grabar_un_movimiento(ser, vel, "a", nombre_izq)

            # Espera antes de pasar a la siguiente velocidad
            if i < len(VELOCIDADES):
                print(f"  Esperando {ESPERA_DESPUES_IZQUIERDA}s antes de la siguiente velocidad...")
                time.sleep(ESPERA_DESPUES_IZQUIERDA)

        print("\n" + "=" * 60)
        print("  EXPERIMENTO TERMINADO")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⚠ Interrumpido por el usuario (Ctrl+C)")
        stop_recording()
    finally:
        ser.close()
        print("Puerto serie cerrado.")

#%%
#if __name__ == "__main__":
main()

