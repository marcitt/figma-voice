import subprocess
import sys
import time


def main():
    # start fastapi
    fastapi = subprocess.Popen(["uvicorn", "main:app", "--reload"])
    print(f"FastAPI started — PID {fastapi.pid}")

    # wait for fastapi to start
    time.sleep(1)

    # start overlay
    overlay = subprocess.Popen(["python", "overlay.py"])
    print(f"Overlay started — PID {overlay.pid}")

    try:
        fastapi.wait()
        overlay.wait()
    except KeyboardInterrupt:
        print("Shutting down...")
        fastapi.terminate()
        overlay.terminate()
        sys.exit(0)


if __name__ == "__main__":
    main()
