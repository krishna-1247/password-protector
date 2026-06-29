@echo off
cd /d "c:\Users\gopikrishna.m\Documents\password_protector\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
