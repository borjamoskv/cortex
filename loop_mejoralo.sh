#!/bin/bash
# loop_mejoralo.sh - SOVEREIGN OUROBOROS LOOP
# Este proceso ejecuta MEJORAlo de forma recursiva e infinita.
# Detenlo con Ctrl+C cuando alcances el 130/100.

echo "☠️ Iniciando Bucle Infinito de MEJORAlo (Ouroboros)..."
echo "Presiona Ctrl+C para abortar el bucle."
echo ""

while true; do
    echo "============================================================"
    echo "⚡ [$(date '+%H:%M:%S')] EJECUTANDO MEJORAlo"
    echo "============================================================"
    
    # 1. Ejecutamos el CLI de MEJORAlo
    # Nota: Aquí invocas el sub-comando de python o tu workflow favorito.
    # Por defecto apuntamos a cortex.cli mejoralo scan,
    # pero puedes cambiar a 'cortex.cli mejoralo ship' según convenga.
    cd ~/cortex && .venv/bin/python -m cortex.cli mejoralo scan cortex .    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo "⚠️ MEJORAlo detectó un error o se abortó manualmente (Exit: $EXIT_CODE)."
        echo "⏳ Pausando 30 segundos antes de reintentar para no saturar el enjambre..."
        sleep 30
    else
        echo "✅ MEJORAlo terminó exitosamente esta ola."
        echo "⏳ Respirando 30 minutos antes de la siguiente fase evolutiva..."
        sleep 1800
    fi
done
