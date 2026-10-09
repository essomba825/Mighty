@echo off
cd /d C:\Users\Petty Cash sas\Documents\Mighty Pulse\backend
..\venv\Scripts\python.exe manage.py generate_curriculum education/curricula/mathematics_ol.json --chapter 1 --lesson 2 --fr > gen_pilot.log 2>&1
..\venv\Scripts\python.exe manage.py generate_curriculum education/curricula/mathematics_ol.json --chapter 1 --lesson 3 --fr >> gen_pilot.log 2>&1
..\venv\Scripts\python.exe manage.py generate_curriculum education/curricula/mathematics_ol.json --chapter 2 --lesson 2 --fr >> gen_pilot.log 2>&1
echo [FIN] >> gen_pilot.log
