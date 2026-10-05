@echo off
echo Building LoLPing.exe...
pip install -r windows\requirements.txt
pyinstaller --onefile --windowed --name LoLPing --icon Resources\Icons\ping.png --add-data "Resources;Resources" --paths windows windows\main.py
echo.
echo Done! Output: dist\LoLPing.exe
