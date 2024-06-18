import subprocess
import signal
import sys
import os

# Ensure the virtual environment is used
venv_python = os.path.join('venv', 'Scripts', 'python.exe')

# Start the Flask app
flask_process = subprocess.Popen([venv_python, "combinedapp.py"])

# Start the Celery worker
celery_process = subprocess.Popen([venv_python, "-m", "celery", "-A", "make_celery.celery_app", "worker", "--loglevel=info"])

def signal_handler(sig, frame):
    print("Terminating processes...")
    flask_process.terminate()
    celery_process.terminate()
    flask_process.wait()
    celery_process.wait()
    print("Processes terminated.")
    sys.exit(0)

# Register signal handler for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Wait for both processes to complete
flask_process.wait()
celery_process.wait()
