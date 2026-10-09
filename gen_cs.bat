@echo off
cd /d C:\Users\Petty Cash sas\Documents\Mighty Pulse\backend
..\venv\Scripts\python.exe manage.py generate_curriculum education/curricula/computer_science_ol.json --chapter 1 --lesson 1 --fr > gen_cs.log 2>&1
..\venv\Scripts\python.exe manage.py generate_curriculum education/curricula/computer_science_ol.json --chapter 1 --lesson 2 --fr >> gen_cs.log 2>&1
echo [FIN] >> gen_cs.log
