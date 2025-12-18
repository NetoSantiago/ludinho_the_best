import os, sys, time, threading
from pathlib import Path
from pyngrok import ngrok, conf
import uvicorn

PORT = int(os.getenv("PORT", "8000"))
AUTHTOKEN = os.getenv("NGROK_AUTHTOKEN")

# Garante que o script rode a partir da raiz do projeto (pasta pai de /scripts)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def run_uvicorn():
    # Importa o módulo 'server' direto daqui (agora no cwd correto)
    try:
        import server  # precisa existir server.py na raiz com app = FastAPI(...)
    except Exception as e:
        print("ERRO: não consegui importar o módulo 'server'.")
        print(f"Dica: confira se existe {PROJECT_ROOT/'server.py'} e se há 'app = FastAPI(...)' nele.")
        raise
    # Usa o objeto app diretamente (evita import por string e problemas de path)
    uvicorn.run(app=server.app, host="0.0.0.0", port=PORT, reload=False)

def main():
    if AUTHTOKEN:
        conf.get_default().auth_token = AUTHTOKEN
    else:
        print("[WARN] NGROK_AUTHTOKEN não definido — o túnel pode não subir.")

    t = threading.Thread(target=run_uvicorn, daemon=True)
    t.start()
    time.sleep(1.5)  # dá tempo do server subir

    public_url = ngrok.connect(addr=PORT, proto="http").public_url
    os.environ["PUBLIC_WEBHOOK_URL"] = public_url
    print(f"[OK] Webhook público via ngrok: {public_url}/webhook")

    WA_BASE_URL = os.getenv("WA_BASE_URL", "http://localhost:21465")
    WA_SESSION  = os.getenv("WA_SESSION", "ludolovers")
    WA_BEARER   = os.getenv("WA_BEARER", "")

    if WA_BEARER:
        print("\nComando sugerido para iniciar sessão no WPPConnect:")
        print(f'curl -X POST --location "{WA_BASE_URL}/api/{WA_SESSION}/start-session" \\')
        print(f"  -H 'Authorization: Bearer {WA_BEARER}' \\")
        print('  -H "Content-Type: application/json" \\')
        print(f"  -d '{{\"webhook\":\"{public_url}/webhook\",\"waitQrCode\": true}}'")
    else:
        print("\n[INFO] Defina WA_BEARER no .env para ver o curl sugerido.")

    print("\nPressione Ctrl+C para encerrar.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Encerrando túnel...")
        ngrok.kill()

if __name__ == "__main__":
    main()
