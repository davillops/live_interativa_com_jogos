@echo off
title Servidor do Overlay - Hytale
cd /d "%~dp0overlay"
python -m http.server 8081