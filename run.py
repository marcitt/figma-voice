import subprocess
import sys #gives access to the Python interpreter 
import time

# parent process run.py creates three seperate child subprocesses run in parallel
# these don't share memory - so IPC is required

def main():
    # start fastapi
    fastapi = subprocess.Popen(["uvicorn", "main:app", "--reload"])
    print(f"FastAPI started - PID {fastapi.pid}")
    
    # subprocess.Popen is non-blocking 
    # will immediately go to the next step before waiting for fastapi to initiate
    
    # wait for fastapi to start
    time.sleep(1)

    # start overlay
    overlay = subprocess.Popen(["python", "overlay.py"])
    print(f"Overlay started — PID {overlay.pid}")

    # start pipeline
    pipeline = subprocess.Popen(["python", "pipeline.py"])
    print(f"Pipeline started — PID {pipeline.pid}")

    try:
        fastapi.wait() # blocks the main process indefinitely in order to keep it alive
        overlay.wait()
        pipeline.wait()
        
        # when CMD+C is pressed all of the processes are terminated:
    except KeyboardInterrupt:
        print("Shutting down...")
        fastapi.terminate()
        overlay.terminate()
        pipeline.terminate()
        sys.exit(0) #exits with a status code of 0


if __name__ == "__main__":
    main()
