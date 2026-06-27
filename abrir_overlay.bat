@echo off
title Servidor do Overlay
echo ============================================
echo  Overlay disponivel em:
echo    http://localhost:8080/painel.html
echo    http://localhost:8080/painel_hytale.html
echo.
echo  Cole o endereco na fonte do
echo  TikTok Live Studio. Deixe esta janela
echo  aberta durante a live.
echo ============================================
cd /d "%~dp0overlay"
python -m http.server 8080