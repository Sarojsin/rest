"""Standalone entry point for the FCM outbox worker.

    backend\\venv\\Scripts\\python.exe backend\\run_fcm_worker.py
"""
from app.workers.fcm_outbox import main

main()
