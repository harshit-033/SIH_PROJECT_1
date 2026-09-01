import socket
import sys
import uvicorn

def get_lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def main():
    lan_ip = get_lan_ip()
    port = 8000
    
    print("=" * 70)
    print("  SIH LOCAL AI WORKBENCH - MULTI-CLIENT SERVER")
    print("=" * 70)
    print(f"[*] Local Host URL   : http://localhost:{port}")
    print(f"[*] LAN Network URL  : http://{lan_ip}:{port}")
    print(f"[*] API Documentation: http://localhost:{port}/docs")
    print("-" * 70)
    print("Default Credentials:")
    print("  Admin User: admin / admin123")
    print("  Client 1  : user1 / pass123")
    print("  Client 2  : user2 / pass123")
    print("=" * 70)
    
    uvicorn.run("server.main:app", host="0.0.0.0", port=port, log_level="info")

if __name__ == '__main__':
    main()
