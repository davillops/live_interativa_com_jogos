@echo off
title Servidor do Overlay - GMod
cd /d "%~dp0overlay"
python -m http.server 8080