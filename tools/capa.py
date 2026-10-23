"""Gera a capa 1080x1920 de um Reel: frame do vídeo + título grande (Anton) no topo + selo de CTA embaixo.
Uso: python3 capa.py frame.png saida.jpg "LINHA 1|LINHA 2|..." "LINHA_DESTACADA" "COMENTA: MAPA" [y_centro_do_selo] [topo|base]
(layout "base" quando o rosto está alto no quadro: título no peito, selo do CTA no alto, y_centro≈230)
(o selo do CTA fica centrado em y para cobrir a legenda queimada; medir a altura da legenda no frame)
- Título fica na faixa y≈250–700 (dentro do recorte 3:4 do grid do Instagram, acima do rosto).
- Faixa de baixo escurecida cobre a legenda queimada; o CTA fica dentro do recorte 3:4.
"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ANTON = "/home/claude/node_modules/@fontsource/anton/files/anton-latin-400-normal.woff"
TURQ = (40, 212, 206)
INK = (55, 52, 53)
W, H = 1080, 1920


def gradient(h, top_alpha, bottom_alpha):
    g = Image.new("L", (1, h))
    for y in range(h):
        g.putpixel((0, y), int(top_alpha + (bottom_alpha - top_alpha) * y / max(1, h - 1)))
    return g.resize((W, h))


def fit_font(draw, text, max_w, start, minimum=60):
    size = start
    while size > minimum:
        f = ImageFont.truetype(ANTON, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return ImageFont.truetype(ANTON, minimum)


def main(frame, out, lines, highlight, cta, cy=1360, layout="topo"):
    img = Image.open(frame).convert("RGB").resize((W, H))
    dark = Image.new("RGB", (W, H), (12, 11, 12))
    if layout == "topo":
        # topo: painel escuro sólido cobre os cards queimados; esmaece até o fundo, acima da cabeça
        panel = Image.new("L", (W, 700), 0)
        for yy in range(700):
            a = 250 if yy < 560 else int(250 * (1 - (yy - 560) / 140))
            ImageDraw.Draw(panel).line((0, yy, W, yy), fill=a)
        img.paste(Image.new("RGB", (W, 700), (22, 20, 21)), (0, 0), panel)
        base = gradient(620, 0, 235)
        img.paste(dark.crop((0, 0, W, 620)), (0, H - 620), base)
    else:
        # base: rosto alto no quadro -> título vai no peito, sobre um painel escuro que cobre legenda e selos queimados
        panel = Image.new("L", (W, 820), 0)
        for yy in range(820):
            a = int(248 * yy / 120) if yy < 120 else 248
            ImageDraw.Draw(panel).line((0, yy, W, yy), fill=a)
        img.paste(Image.new("RGB", (W, 820), (22, 20, 21)), (0, H - 820), panel)
        top = gradient(360, 200, 0)
        img.paste(dark.crop((0, 0, W, 360)), (0, 0), top)

    d = ImageDraw.Draw(img)
    y = 250 if layout == "topo" else 1230
    for i, line in enumerate(lines):
        start = 150 if i == 0 else 100
        f = fit_font(d, line, W - 140, start)
        tw = d.textlength(line, font=f)
        x = (W - tw) / 2
        bbox = d.textbbox((x, y), line, font=f)
        if highlight and highlight in line:
            pad = 18
            d.rounded_rectangle((bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad), radius=18, fill=TURQ)
            d.text((x, y), line, font=f, fill=INK)
        else:
            # sombra suave
            sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(sh).text((x + 4, y + 6), line, font=f, fill=(0, 0, 0, 170))
            img.paste(sh.filter(ImageFilter.GaussianBlur(6)), (0, 0), sh.filter(ImageFilter.GaussianBlur(6)))
            d = ImageDraw.Draw(img)
            d.text((x, y), line, font=f, fill=(255, 255, 255))
        y = bbox[3] + (34 if highlight and highlight in line else 22)

    if cta:
        # selo do CTA em cima da legenda queimada (faixa do peito, y≈1300–1430)
        f = ImageFont.truetype(ANTON, 76)
        tw = d.textlength(cta, font=f)
        bw = max(tw + 90, 640)
        x0 = (W - bw) / 2
        d.rounded_rectangle((x0, cy - 70, x0 + bw, cy + 70), radius=70, fill=TURQ)
        bb = d.textbbox((0, 0), cta, font=f)
        d.text(((W - tw) / 2, cy - (bb[1] + bb[3]) / 2), cta, font=f, fill=INK)
        tag = __import__("os").environ.get("CAPA_TAG", "ACELERADOR FINANCEIRO")  # CAPA_TAG="" no @karam.cesar
        ft = ImageFont.truetype(ANTON, 44)
        if tag: d.text(((W - d.textlength(tag, font=ft)) / 2, cy + 110 if layout == "topo" else cy - 150), tag, font=ft, fill=(240, 240, 244))
    img.save(out, "JPEG", quality=92)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3].split("|"), sys.argv[4], sys.argv[5], int(sys.argv[6]) if len(sys.argv) > 6 else 1360, sys.argv[7] if len(sys.argv) > 7 else "topo")
