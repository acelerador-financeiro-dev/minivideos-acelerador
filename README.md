# Mini vídeos — Acelerador Financeiro

Vídeos finais (1080x1920) publicados como anexos de release. O Metricool busca cada vídeo pelo link do anexo para agendar no Reels, Shorts e TikTok.

## Numeração dos vídeos (chats em paralelo)
Cada chat de edição reserva o número **antes de qualquer outra coisa**: `scripts/reservar.sh "<hora do pedido>" <bytes do bruto>`.
O primeiro push ganha o número; quem perder a corrida pega o seguinte. A pasta `reservas/` tem um arquivo por número
(hora do pedido, tamanho do bruto, tema, status). O mesmo bruto (mesmo tamanho em bytes) devolve `DUPLICADO=NNN`.
