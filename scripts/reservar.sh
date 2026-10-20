#!/usr/bin/env bash
# Reserva o próximo número de vídeo (#NNN) de forma atômica entre chats paralelos.
# Uso: scripts/reservar.sh "<hora do pedido AAAA-MM-DD HH:MM>" <bytes do bruto>
# Saídas: "NUMERO=NNN" (reservado) | "DUPLICADO=NNN" (esse bruto já tem número) | código 1 (falhou).
# Funciona porque o push na main só passa se ninguém tiver reservado antes; se perder a corrida,
# busca de novo e tenta o número seguinte.
set -u
cd "$(dirname "$0")/.."
pedido="$1"; bytes="$2"
for try in $(seq 1 10); do
  git fetch -q --depth 1 origin main && git reset -q --hard origin/main || { sleep 2; continue; }
  dup=$(grep -l "^bruto_bytes=$bytes$" reservas/*.txt 2>/dev/null | head -1)
  if [ -n "$dup" ]; then echo "DUPLICADO=$(basename "$dup" .txt)"; exit 0; fi
  last=$(ls reservas | sed -n 's/^\([0-9][0-9][0-9]\)\.txt$/\1/p' | sort -n | tail -1)
  n=$(printf %03d $((10#${last:-0} + 1)))
  printf 'numero=%s\npedido=%s\nbruto_bytes=%s\ntema=\nstatus=em edição\nreservado_utc=%s\n' \
    "$n" "$pedido" "$bytes" "$(date -u +%FT%TZ)" > "reservas/$n.txt"
  git add --sparse "reservas/$n.txt" 2>/dev/null || git add "reservas/$n.txt"
  git -c user.name=Claude -c user.email=noreply@anthropic.com commit -q -m "Reserva #$n"
  if git push -q origin HEAD:main 2>/dev/null; then echo "NUMERO=$n"; exit 0; fi
  sleep $((RANDOM % 3 + 1))
done
echo "Falhou ao reservar" >&2; exit 1
