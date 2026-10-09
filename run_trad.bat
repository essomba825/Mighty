@echo off
cd /d C:\Users\Petty Cash sas\Documents\Mighty Pulse\backend
..\venv\Scripts\python.exe manage.py shell -c "exec(open('translate_lessons.py', encoding='utf-8').read())" > trad_out.txt 2> trad_err.txt
