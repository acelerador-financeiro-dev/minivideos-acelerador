import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
S = sys.argv[1]
LIB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
ANT = sys.argv[2] if len(sys.argv) > 2 else "/home/claude/node_modules/@fontsource/anton/files/anton-latin-400-normal.woff"  # uso: titulo_cartao.py PASTA [anton.woff]
TURQ = (40, 212, 206); RED = (229, 72, 77); YEL = (255, 214, 10); GRA = (24, 26, 30)

def shadow(layer, r=16, a=120, off=(0, 8)):
    alpha = layer.split()[3].point(lambda v: v * a // 255)
    blk = Image.new("RGBA", layer.size, (0, 0, 0, 255)); blk.putalpha(alpha)
    blk = blk.filter(ImageFilter.GaussianBlur(r))
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0)); out.alpha_composite(blk, off); out.alpha_composite(layer)
    return out

L = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
card = Image.new("RGBA", (800, 320), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
d.rounded_rectangle((0, 0, 799, 319), 40, fill=TURQ)
d.rounded_rectangle((50, 46, 150, 116), 14, fill=YEL)
f1 = ImageFont.truetype(LIB, 46); f2 = ImageFont.truetype(ANT, 92)
d.text((180, 56), "ENSINANDO", font=f1, fill=GRA)
d.text((50, 140), "CARTÃO DE CRÉDITO", font=f2, fill=(255, 255, 255), stroke_width=4, stroke_fill=GRA)
card = card.rotate(-4, expand=True, resample=Image.BICUBIC)
L.alpha_composite(card, ((1080 - card.width) // 2, 210))
tag = Image.new("RGBA", (660, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(tag)
d.rounded_rectangle((0, 0, 659, 119), 60, fill=RED)
f3 = ImageFont.truetype(LIB, 56); t = "PRO NENÉM DE 3 ANOS"
b = d.textbbox((0, 0), t, font=f3)
d.text(((660 - (b[2] - b[0])) // 2 - b[0], (120 - (b[3] - b[1])) // 2 - b[1]), t, font=f3, fill=(255, 255, 255))
tag = tag.rotate(5, expand=True, resample=Image.BICUBIC)
L.alpha_composite(tag, (330, 515))
L = shadow(L)
L.save(S + "/titulo_srgb.png")
print("bbox", L.getbbox())

# sRGB -> sinal HLG BT.2020 (branco = branco de referência HLG, sinal 0.75)
a = np.asarray(L).astype(np.float64) / 255.0
rgb, al = a[..., :3], a[..., 3:]
lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
M = np.array([[0.6274, 0.3293, 0.0433], [0.0691, 0.9195, 0.0114], [0.0164, 0.0880, 0.8956]])
lin = np.clip(lin @ M.T, 0, 1) * 0.2647
A, B, C = 0.17883277, 0.28466892, 0.55991073
hlg = np.where(lin <= 1 / 12, np.sqrt(3 * lin), A * np.log(np.maximum(12 * lin - B, 1e-9)) + C)
out = np.concatenate([np.clip(hlg, 0, 1), al], -1)
# grava PNG 16 bits RGBA via ffmpeg-friendly raw
(out * 65535).round().astype("<u2").tofile(S + "/titulo_hlg.rgba64le")
