@echo off
title Servidor do Overlay - Live Caos
echo ============================================
echo  Overlay disponivel em:
echo    http://localhost:8080/painel.html
echo.
echo  Cole esse endereco na fonte LINK do
echo  TikTok Live Studio. Deixe esta janela
echo  aberta durante a live.
echo ============================================
cd /d "%~dp0overlay"
python -m http.server 8080
