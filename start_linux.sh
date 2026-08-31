#!/usr/bin/env bash
# Script de arranque para Linux — Estudio Deco
# Permite editar la plantilla y enviar tickets de prueba a la impresora en Linux

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ -f "$DIR/.venv/bin/python3" ]; then
    PYTHON="$DIR/.venv/bin/python3"
else
    PYTHON="python3"
fi

echo "=============================================="
echo "  🖨️ Estudio Deco — Previsualización e Impresión (Linux)"
echo "=============================================="
echo "  Servidor de prueba: http://localhost:8765"
echo "  Plantilla: config/ticket_template.json"
echo "  Usando Python: $PYTHON"
echo "=============================================="
echo ""

"$PYTHON" ticket_editor_linux.py
