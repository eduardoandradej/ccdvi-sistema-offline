#!/usr/bin/env bash
# Verifica que o frontend compilado não referencia recursos externos (CDN, fontes, APIs).
set -euo pipefail
DIST="${1:-$(dirname "$0")/../frontend/dist}"
[ -d "$DIST" ] || { echo "Compile o frontend antes (npm run build)."; exit 1; }
# URLs absolutas http(s) em HTML/CSS/JS. Exceções: namespaces XML/SVG e URLs que aparecem apenas
# dentro de mensagens de erro/aviso das bibliotecas React e React Router (texto, nunca carregadas).
HITS="$(grep -rhoE "https?://[a-zA-Z0-9.-]+" "$DIST" | sort -u | grep -vE "www\.w3\.org|reactjs\.org|react\.dev|fb\.me|reactrouter\.com" || true)"
if [ -n "$HITS" ]; then echo "Referências externas encontradas:"; echo "$HITS"; exit 1; fi
echo "OK: nenhum recurso externo referenciado em $DIST"
