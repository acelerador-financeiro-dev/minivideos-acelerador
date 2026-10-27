# #014 — gráficos + modo "fundo verde" (ele recortado na frente das tabelas). Render HDR (HLG/BT.2020) como gravado.
import json, sys, math, subprocess, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = sys.argv[1]; MODE = sys.argv[2]; ARGS = sys.argv[3:]
W, H, FPS = 1080, 1920, 30
F = f"{S}/fonts"
GRAF = (55, 52, 53); TURQ = (40, 212, 206); LAV = (187, 187, 223); WHITE = (255, 255, 255)
RED = (229, 72, 77); YEL = (255, 241, 76); BLACK = (20, 18, 19)
LIB = "/usr/share/fonts/truetype/liberation"
_fc = {}
def font(name, size):
    k = (name, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype({"anton": f"{F}/Anton-Regular.ttf", "cb": f"{F}/Carlito-Bold.ttf", "cr": f"{F}/Carlito-Regular.ttf",
                                     "ar": f"{LIB}/LiberationSans-Regular.ttf", "ab": f"{LIB}/LiberationSans-Bold.ttf"}[name], size)
    return _fc[k]

# ---------------- timing ----------------
Wd = json.load(open(f"{S}/raw/words.json"))
CUT = json.load(open(f"{S}/raw/cuts.json")); SEGS = CUT["segs"]; KEEP = CUT["keep"]
DUR = SEGS[-1]["out0"] + SEGS[-1]["in1"] - SEGS[-1]["in0"]
def m(t):
    for s in SEGS:
        if s["in0"] - 1e-6 <= t <= s["in1"] + 1e-6: return s["out0"] + t - s["in0"]
    for s in SEGS:
        if t < s["in0"]: return s["out0"]
    return DUR
def T(i): return m(Wd[i]["s"])
def E(i): return m(Wd[i]["e"])

# ---------------- legenda karaokê ----------------
REPL = {108: "gastos", 145: "de saúde.", 210: "janta", 272: "encargos,", 316: "retrasado", 532: "morre",
        609: "lazer,", 652: "20, com 5,", 669: "acima", 650: "da", 102: "ó.", 685: "Estou"}
MERGE_INTO = {}
cap = []
for i in KEEP:
    if i in MERGE_INTO: cap[-1]["e"] = E(i); continue
    cap.append({"w": REPL.get(i, Wd[i]["w"]), "s": T(i), "e": E(i), "i": i})
groups = []; g = []
for k, w in enumerate(cap):
    g.append(k); txt = " ".join(cap[j]["w"] for j in g)
    nxt = cap[k + 1] if k + 1 < len(cap) else None
    if (nxt is None or w["w"][-1] in ".,?!" or len(g) >= 3 or len(txt + " " + nxt["w"]) > 19 or (nxt["s"] - w["e"]) > 0.3):
        groups.append(g); g = []
_capcache = {}
def caption_img(gi, hi):
    key = (gi, hi)
    if key in _capcache: return _capcache[key]
    f = font("cb", 64); words = [cap[j]["w"] for j in groups[gi]]
    sp = f.getlength(" "); widths = [f.getlength(w) for w in words]
    tw = int(sum(widths) + sp * (len(words) - 1)) + 40
    sh = Image.new("RGBA", (tw, 110), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh); x = 20
    for k, w in enumerate(words): ds.text((x, 22), w, font=f, fill=(0, 0, 0, 200)); x += widths[k] + sp
    sh = sh.filter(ImageFilter.GaussianBlur(5))
    out = Image.new("RGBA", sh.size, (0, 0, 0, 0)); out.alpha_composite(sh); d = ImageDraw.Draw(out); x = 20
    for k, w in enumerate(words):
        col = TURQ if groups[gi][k] == hi else WHITE
        d.text((x, 18), w, font=f, fill=col + (255,), stroke_width=3, stroke_fill=BLACK + (255,)); x += widths[k] + sp
    _capcache[key] = out; return out
def caption_at(t):
    for gi, g in enumerate(groups):
        s = cap[g[0]]["s"]; nxt = cap[groups[gi + 1][0]]["s"] if gi + 1 < len(groups) else DUR
        end = min(nxt, cap[g[-1]]["e"] + 0.6)
        if s - 0.03 <= t < end:
            hi = g[0]
            for j in g:
                if cap[j]["s"] - 0.03 <= t: hi = j
            return caption_img(gi, hi), GY.get(gi, 1440) if "GY" in globals() else 1440
    return None

# ---------------- helpers ----------------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else (1.0 if t >= t0 else 0.0)
def eo(x): return 1 - (1 - x) ** 3
def eback(x):
    c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def with_alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a))); return im
def scaled(im, s):
    if abs(s - 1) < 0.01: return im
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
def shadowed(im, blur=14, off=6, alpha=150):
    pad = blur * 2
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    blk = Image.new("RGBA", im.size, (0, 0, 0, 255)); blk.putalpha(im.getchannel("A").point(lambda v: int(v * alpha / 255)))
    sh.paste(blk, (pad, pad + off)); sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(sh); out.alpha_composite(im, (pad, pad)); return out, pad

def pill(text, bg, fg, fnt, padx=30, h=78):
    w = int(fnt.getlength(text) + padx * 2); im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=h, fill=bg)
    f2 = ImageFont.truetype(fnt.path, fnt.size * 2); bb = f2.getbbox(text)
    d.text((padx * 2, (h * 2 - (bb[3] + bb[1])) / 2), text, font=f2, fill=fg)
    return im.resize((w, h), Image.LANCZOS)

def make_title():
    SS = 2; f1 = font("anton", 96 * SS)
    l1 = "GANHO R$ 30 MIL POR MÊS"; l2 = "E SÓ FAÇO O BÁSICO"
    w1, w2 = f1.getlength(l1), f1.getlength(l2); Wt = int(max(w1, w2)) + 40 * SS; Ht = 250 * SS
    im = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.text(((Wt - w1) / 2, 0), l1, font=f1, fill=WHITE, stroke_width=3 * SS, stroke_fill=BLACK)
    d.text(((Wt - w2) / 2, 122 * SS), l2, font=f1, fill=TURQ, stroke_width=3 * SS, stroke_fill=BLACK)
    im = im.resize((Wt // SS, Ht // SS), Image.LANCZOS)
    if im.width > 980: im = im.resize((980, int(im.height * 980 / im.width)), Image.LANCZOS)
    return shadowed(im, 12, 5, 170)
TITLE = make_title()

CTA_A, CTA_B = "CONCORDO", "DISCORDO"
def make_cta():
    f1 = font("cb", 50); f2 = font("anton", 50); fo = font("cb", 44)
    bw1 = int(f2.getlength(CTA_A) + 40); bw2 = int(f2.getlength(CTA_B) + 40); ow = int(fo.getlength("ou") + 28)
    w1 = f1.getlength("Comenta:"); Wc = int(w1 + 16 + bw1 + ow + bw2) + 10; Hc = 88
    SS = 2; im = Image.new("RGBA", (Wc * SS, Hc * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    F1 = ImageFont.truetype(f1.path, 50 * SS); F2 = ImageFont.truetype(f2.path, 50 * SS); FO = ImageFont.truetype(fo.path, 44 * SS)
    d.text((0, 44 * SS // 2 + 10), "Comenta:", font=F1, fill=WHITE, stroke_width=4, stroke_fill=BLACK)
    x = int((w1 + 16) * SS)
    for k, (word, bw) in enumerate([(CTA_A, bw1), (CTA_B, bw2)]):
        d.rounded_rectangle([x, 6, x + bw * SS, Hc * SS - 6], radius=18, fill=TURQ)
        bb = F2.getbbox(word); d.text((x + 20 * SS, (Hc * SS - (bb[3] + bb[1])) / 2), word, font=F2, fill=GRAF)
        x += bw * SS
        if k == 0:
            d.text((x + 14 * SS, 44 * SS // 2 + 14), "ou", font=FO, fill=WHITE, stroke_width=4, stroke_fill=BLACK); x += ow * SS
    im = im.resize((Wc, Hc), Image.LANCZOS)
    if im.width > 960: im = im.resize((960, int(im.height * 960 / im.width)), Image.LANCZOS)
    return shadowed(im, 10, 5, 150)
CTA = make_cta()
FAMILIA = shadowed(pill("CASAL + 2 FILHOS", WHITE, GRAF, font("anton", 50)), 10, 5, 140)
RENDA = shadowed(pill("R$ 30 MIL POR MÊS", TURQ, GRAF, font("anton", 50)), 10, 5, 140)

# ---------------- tabelas (réplica fiel da planilha dele, em tamanho legível) ----------------
TAB_A = ("MAIORES GASTOS", [("Condomínio", "R$ 2.200,00"), ("Saúde em geral", "R$ 6.000,00"), ("Supermercado e alimentação", "R$ 5.000,00"),
                            ("Doméstica", "R$ 3.700,00"), ("Imobilizado", "R$ 4.000,00")], "R$ 20.900,00")
TAB_B = ("GASTOS FUTUROS NECESSÁRIOS", [("Escolinhas", "R$ 3.000,00"), ("Esportes filhos", "R$ 1.500,00"),
                                        ("Roupas/alimentos extras etc filhos", "R$ 1.000,00")], "R$ 5.500,00")
TAB_C = ("COISAS QUE NÃO ESTAMOS FAZENDO/MÊS", [("Viagens", "R$ 5.000,00"), ("Lazer", "R$ 1.000,00"), ("Estética", "R$ 2.000,00"),
                                                ("Educação", "R$ 3.000,00"), ("Vestuário", "R$ 1.500,00"), ("Manutenções Casa", "R$ 5.000,00"),
                                                ("Investimentos", "R$ 5.000,00")], "R$ 22.500,00")
TAB_S = ("A CONTA COMPLETA", [("Maiores gastos", "R$ 20.900,00"), ("Gastos futuros necessários", "R$ 5.500,00"),
                              ("Coisas que não estamos fazendo", "R$ 22.500,00")], "R$ 48.900,00")
TX, TY, TWD = 40, 168, 1000

def table_img(tab, rowh, fsz, active, shown, total_on, total_lbl=""):
    """active: índice da linha destacada (-1 nenhum, 99 total); shown: quantas linhas visíveis (as outras ficam claras)."""
    SS = 2; head, rows, total = tab; n = len(rows) + 2
    Wt = TWD * SS; Ht = (rowh * n + 12) * SS
    im = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    B = 6 * SS; d.rectangle([0, 0, Wt - 1, Ht - 1], fill=BLACK)
    x0, y0, x1, y1 = B, B, Wt - B, Ht - B
    d.rectangle([x0, y0, x1, y1], fill=WHITE)
    rh = (y1 - y0) / n
    fh = font("ab", int(fsz * 0.92) * SS); fr = font("ar", fsz * SS); fb = font("ab", fsz * SS)
    d.rectangle([x0, y0, x1, y0 + rh], fill=YEL)
    if fh.getlength(head) > (x1 - x0) - 40 * SS: fh = font("ab", int(fsz * 0.80) * SS)
    d.text((x0 + 18 * SS, y0 + rh / 2), head, font=fh, fill=BLACK, anchor="lm")
    for k, (lb, val) in enumerate(rows):
        ry = y0 + rh * (k + 1)
        vis = k < shown
        if k == active:
            d.rectangle([x0, ry, x1, ry + rh], fill=(40, 212, 206, 255))
        col = BLACK if vis else (205, 204, 208)
        d.line([(x0, ry), (x1, ry)], fill=(210, 210, 214), width=2 * SS)
        flb = fr
        if fr.getlength(lb) > (x1 - x0) * 0.66: flb = font("ar", int(fsz * 0.82) * SS)
        d.text((x0 + 18 * SS, ry + rh / 2), lb, font=flb, fill=col, anchor="lm")
        d.text((x1 - 18 * SS, ry + rh / 2), val, font=fb if k == active else fr, fill=col, anchor="rm")
    ry = y0 + rh * (len(rows) + 1)
    d.line([(x0, ry), (x1, ry)], fill=(210, 210, 214), width=2 * SS)
    tcol = BLACK if total_on else (205, 204, 208)
    if total_on and active == 99: d.rectangle([x0, ry, x1, ry + rh], fill=YEL)
    if total_lbl: d.text((x0 + 18 * SS, ry + rh / 2), total_lbl, font=fb, fill=tcol, anchor="lm")
    d.text((x1 - 18 * SS, ry + rh / 2), total, font=fb, fill=tcol, anchor="rm")
    return im.resize((Wt // SS, Ht // SS), Image.LANCZOS)

# linhas: (tabela, rowh, fonte, t_in, t_out, [(t, ativo, mostradas, total_on)])
SPLIT652 = T(652) + (E(652) - T(652)) * 0.55
SHOWS = [
    (TAB_A, 74, 44, T(100), T(395) - 0.05, [(T(100), -1, 5, False), (T(114), 0, 5, False), (T(143), 1, 5, False), (T(185), 2, 5, False),
                                         (T(246), 3, 5, False), (T(294), 4, 5, False), (T(380), 99, 5, True)]),
    (TAB_B, 82, 46, T(395), T(566) - 0.05, [(T(395), -1, 3, False), (T(417), 0, 3, False), (T(503), 1, 3, False), (T(535), 2, 3, False),
                                         (T(566) - 0.6, 99, 3, True)]),
    (TAB_C, 58, 38, T(566), T(645) - 0.05, [(T(566), -1, 7, False), (T(584), 0, 7, False), (T(608), 1, 7, False), (T(610), 2, 7, False),
                                         (T(625), -1, 7, False), (T(636), 99, 7, True)]),
    (TAB_S, 80, 44, T(645), E(684) + 0.1, [(T(645), -1, 0, False), (T(651), 0, 1, False), (SPLIT652, 1, 2, False), (T(654), 2, 3, False),
                                         (T(672), 99, 3, True)]),
]
_tc = {}
def table_at(t):
    for tab, rowh, fsz, ti, to, steps in SHOWS:
        if ti - 0.01 <= t < to + 0.25:
            st = steps[0]
            for s in steps:
                if t >= s[0] - 0.03: st = s
            key = (tab[0], st[1], st[2], st[3])
            if key not in _tc: _tc[key] = table_img(tab, rowh, fsz, st[1], st[2], st[3], "TOTAL" if tab is TAB_S else "")
            pin = eo(prog(t, ti, 0.3)); pout = prog(t, to, 0.22)
            return _tc[key], pin * (1 - pout), -40 * (1 - pin) - 20 * pout
    return None
# selo extra na tela da soma: precisaria x ganha
NEED = shadowed(pill("PRECISARIA DE R$ 48,9 MIL", RED, WHITE, font("anton", 44), h=74, padx=24), 10, 5, 150)
NEED2 = shadowed(pill("GANHO R$ 30 MIL", TURQ, GRAF, font("anton", 44), h=74, padx=24), 10, 5, 150)

# modo planilha (fundo trocado): de quando a tabela entra até a soma final
GS_IN, GS_OUT = T(100) - 0.15, E(684) + 0.1
def gs_alpha(t): return prog(t, GS_IN, 0.35) * (1 - prog(t, GS_OUT, 0.35))
def make_bg():
    im = Image.new("RGB", (W, H), GRAF); d = ImageDraw.Draw(im)
    for y in range(H):  # leve degradê
        v = 1 - y / H * 0.35
        d.line([(0, y), (W, y)], fill=(int(55 * v + 10 * (1 - v)), int(52 * v + 10 * (1 - v)), int(53 * v + 10 * (1 - v))))
    for x in range(0, W, 120): d.line([(x, 0), (x, H)], fill=(70, 67, 68), width=2)
    for y in range(0, H, 60): d.line([(0, y), (W, y)], fill=(70, 67, 68), width=2)
    glow = Image.new("L", (W, H), 0); ImageDraw.Draw(glow).ellipse([-200, -300, W + 200, 900], fill=60)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    im = Image.composite(Image.new("RGB", (W, H), TURQ), im, glow)
    return np.asarray(im)
BG8 = make_bg()

# ---------------- selos e título no modo normal (faixa de cima, acima do cabelo) ----------------
TOPY = 470
BADGES = [
    (FAMILIA, 540, TOPY, T(57), E(71) + 0.2),
    (CTA, 540, TOPY, T(72), E(99) - 0.2),
    (CTA, 540, TOPY, T(685), DUR + 1),
]
TITLE_OUT = E(52) + 0.2

# zoom: alterna por trecho só fora do modo planilha, e desliga onde o queixo desceria demais
FACES = json.load(open(f"{S}/raw/faces.json")) if os.path.exists(f"{S}/raw/faces.json") else []
def zbox(z):
    cw, ch = W / z, H / z; cx, cy = 0.52 * W, 0.47 * H
    return clamp(cx - cw / 2, 0, W - cw), clamp(cy - ch / 2, 0, H - ch)
def chin_of(y, h): return y + 1.08 * h
SAFEZ = []
for sgi, sg in enumerate(SEGS):
    a0 = sg["out0"]; a1 = a0 + sg["in1"] - sg["in0"]; z = sg["zoom"]
    if z != 1.0:
        _, y0 = zbox(z)
        for t, x, y, w, h in FACES:
            if x is not None and y > 500 and a0 <= t < a1 and (chin_of(y, h) - y0) * z > 1490: z = 1.0; break
    SAFEZ.append(z)
def zoom_at(t):
    if GS_IN - 0.4 <= t <= GS_OUT + 0.4: return 1.0
    for k, s_ in enumerate(SEGS):
        if s_["out0"] - 1e-6 <= t < s_["out0"] + s_["in1"] - s_["in0"]: return SAFEZ[k]
    return 1.0
# legenda: no peito; num grupo em que ele se inclina, desce junto (até 1560, acima do rodapé do Reels)
def chin_at_range(t0, t1):
    mx = 0
    for t, x, y, w, h in FACES:
        if x is None or y < 500 or not (t0 - 0.1 <= t <= t1 + 0.1): continue
        c = chin_of(y, h); z = zoom_at(t)
        if z != 1.0:
            _, y0 = zbox(z); c = (c - y0) * z
        mx = max(mx, c)
    return mx
GY = {}
for gi, g in enumerate(groups):
    t0 = cap[g[0]]["s"]; t1 = cap[g[-1]]["e"] + 0.6
    GY[gi] = int(clamp(chin_at_range(t0, t1) - 10, 1440, 1560))
CAPY = 1440
def overlay_parts(t):
    """back: atrás da pessoa (tabela); front: na frente (título, selos, legenda)."""
    back = Image.new("RGBA", (W, H), (0, 0, 0, 0)); front = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if t < TITLE_OUT + 0.3:
        a = prog(t, 0, 0.2) * (1 - prog(t, TITLE_OUT, 0.25)); s = 0.94 + 0.06 * eo(prog(t, 0, 0.3))
        if a > 0:
            im, pad = TITLE; im = with_alpha(scaled(im, s), a)
            front.alpha_composite(im, (int(540 - im.width / 2), int(TOPY - im.height / 2)))
    ta = table_at(t)
    if ta:
        im, a, dy = ta
        if a > 0: back.alpha_composite(with_alpha(im, a), (TX, int(TY + dy)))
    if T(672) <= t < GS_OUT + 0.3:
        tab = [x for x in SHOWS if x[0] is TAB_S][0]; cy = TY + tab[1] * 5 + 12 + 58
        wa, wb = NEED2[0].width - 2 * NEED2[1], NEED[0].width - 2 * NEED[1]; x0 = 540 - (wa + 20 + wb) / 2
        for (img, pad), tt, x in [(NEED2, T(672), x0), (NEED, T(674), x0 + wa + 20)]:
            p = prog(t, tt, 0.3); a = min(1, p * 2.5) * (1 - prog(t, GS_OUT, 0.2))
            if a > 0:
                im = with_alpha(scaled(img, eback(p)), a); w0 = img.width - 2 * pad
                back.alpha_composite(im, (int(x + w0 / 2 - im.width / 2), int(cy - im.height / 2)))
    for (img, pad), bx, by, ti, to in BADGES:
        if ti - 0.01 <= t < to + 0.2:
            p = prog(t, ti, 0.3); po = prog(t, to, 0.18)
            a = min(1, p * 2.5) * (1 - po); s = eback(p) * (1 - 0.1 * po)
            if a <= 0: continue
            im = with_alpha(scaled(img, s), a)
            front.alpha_composite(im, (int(bx - im.width / 2), int(by - im.height / 2)))
    ci = caption_at(t)
    if ci is not None: front.alpha_composite(ci[0], (int(540 - ci[0].width / 2), ci[1]))
    return back, front

# ---------------- conversão sRGB -> HLG (só gráficos) ----------------
M = np.array([[0.6274, 0.3293, 0.0433], [0.0691, 0.9195, 0.0114], [0.0164, 0.0880, 0.8956]])
lin = np.array([((v / 255) / 12.92 if v / 255 <= 0.04045 else (((v / 255) + 0.055) / 1.055) ** 2.4) for v in range(256)])
a_, b_, c_ = 0.17883277, 0.28466892, 0.55991073
def hlg(E_):
    E_ = np.clip(E_, 0, 1)
    return np.where(E_ <= 1 / 12, np.sqrt(3 * E_), a_ * np.log(np.maximum(12 * E_ - b_, 1e-6)) + c_)
LUT = None
def to_hlg(rgb8):
    return (hlg(lin[rgb8] @ M.T * 0.2647) * 65535).astype(np.float32)
BG_H = None

# máscaras da pessoa (320x320 por quadro, calculadas a cada 2 quadros)
MASKF = f"{S}/raw/masks.npy"
MK = None; MK0 = 0
def mask_at(n):
    global MK, MK0
    if MK is None:
        MK = np.load(MASKF, mmap_mode="r"); MK0 = int(open(f"{S}/raw/masks.start").read())
    k = (n - MK0) / 2.0; i0 = int(math.floor(k)); fr_ = k - i0
    i0 = max(0, min(len(MK) - 1, i0)); i1 = min(len(MK) - 1, i0 + 1)
    mk = MK[i0].astype(np.float32) * (1 - fr_) + MK[i1].astype(np.float32) * fr_
    return mk

def blend(dst, src, al):
    return dst * (1 - al) + src * al

def comp_region(fr, ov):
    a = ov[..., 3]
    if not (a > 0).any(): return fr
    ys, xs = np.nonzero(a > 0); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    sub = ov[y0:y1, x0:x1]; al = sub[..., 3:4].astype(np.float32) / 255
    fr = fr.copy(); fr[y0:y1, x0:x1] = blend(fr[y0:y1, x0:x1], to_hlg(sub[..., :3]), al)
    return fr

def frame_hdr(fr, n, cv2):
    global BG_H
    t = n / FPS
    z = zoom_at(t)
    fr = fr.astype(np.float32)
    if z != 1.0:
        x0, y0 = zbox(z); cw, ch = W / z, H / z
        crop = fr[int(round(y0)):int(round(y0 + ch)), int(round(x0)):int(round(x0 + cw))]
        fr = cv2.resize(crop, (W, H), interpolation=cv2.INTER_LINEAR)
    back, front = overlay_parts(t)
    ga = gs_alpha(t)
    if ga > 0:
        # fundo original (parede dele); a tabela fica na parede, atrás da cabeça/mão dele quando se cruzam
        bk = np.asarray(back); a = bk[..., 3]
        if (a > 0).any():
            ys, xs = np.nonzero(a > 0); y0, y1 = max(0, ys.min() - 4), min(H, ys.max() + 5)
            mk = cv2.resize(mask_at(n), (W, H), interpolation=cv2.INTER_CUBIC)[y0:y1]
            mk = np.clip((mk / 255 - 0.08) / 0.84, 0, 1)
            mk = cv2.GaussianBlur(mk, (0, 0), 1.6)[..., None] * ga
            sub = fr[y0:y1]; bgs = comp_region(sub, bk[y0:y1])
            fr = fr.copy(); fr[y0:y1] = blend(bgs, sub, mk)
    else:
        fr = comp_region(fr, np.asarray(back))
    fr = comp_region(fr, np.asarray(front))
    return np.clip(fr + 0.5, 0, 65535).astype(np.uint16)

BASE = f"{S}/raw/base_hdr.mp4"
def reader(ss=None, dur=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", f"{ss:.3f}"] if ss is not None else []) + ["-i", BASE] + (["-t", f"{dur:.3f}"] if dur else []) + \
        ["-vf", "scale=in_color_matrix=bt2020:in_range=tv,format=rgb48le", "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE)
def writer(out, ss=None, dur=None, crf="21"):
    aud = (["-ss", f"{ss:.3f}"] if ss is not None else []) + ["-i", BASE] + (["-t", f"{dur:.3f}"] if dur else [])
    return subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb48le", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"] + aud +
        ["-map", "0:v", "-map", "1:a", "-vf", "scale=out_color_matrix=bt2020:out_range=tv,format=yuv420p10le",
         "-c:v", "libx265", "-preset", "fast", "-crf", crf, "-tag:v", "hvc1",
         "-x265-params", "log-level=error:colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited:vbv-maxrate=8000:vbv-bufsize=16000",
         "-colorspace", "bt2020nc", "-color_primaries", "bt2020", "-color_trc", "arib-std-b67",
         "-c:a", "copy", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)

def run(out, ss=None, dur=None, only=None):
    sys.path.insert(0, S + "/cv4"); import cv2
    rd = reader(ss, dur); wr = writer(out, ss, dur) if out else None
    n0 = int(round((ss or 0) * FPS)); n = 0; fs = W * H * 6
    while True:
        buf = rd.stdout.read(fs)
        if len(buf) < fs: break
        fr = np.frombuffer(buf, np.uint16).reshape(H, W, 3)
        o = frame_hdr(fr, n0 + n, cv2)
        if wr: wr.stdin.write(o.tobytes())
        if only is not None: only(o, n0 + n)
        n += 1
        if n % 300 == 0: print("frame", n, flush=True)
    if wr: wr.stdin.close(); wr.wait()
    print("DONE", n, flush=True)

def hlg_to_srgb(o):
    # só para conferência (folhas de contato): HLG -> linear -> sRGB aproximado
    E_ = o.astype(np.float32) / 65535
    L = np.where(E_ <= 0.5, E_ ** 2 / 3, (np.exp((E_ - c_) / a_) + b_) / 12)
    L = L / 0.2647
    Mi = np.linalg.inv(M); L = np.clip(L @ Mi.T, 0, 1)
    s = np.where(L <= 0.0031308, L * 12.92, 1.055 * L ** (1 / 2.4) - 0.055)
    return (np.clip(s, 0, 1) * 255).astype(np.uint8)

if MODE == "frames":
    os.makedirs(f"{S}/check", exist_ok=True)
    for t in [float(x) for x in ARGS]:
        def save(o, n, t=t): Image.fromarray(hlg_to_srgb(o)).resize((360, 640)).save(f"{S}/check/c_{t:07.2f}.jpg", quality=80)
        run(None, t, 1 / FPS, save)
elif MODE == "info":
    print("DUR", DUR, "groups", len(groups), "GS", round(GS_IN, 2), round(GS_OUT, 2), "TITLE_OUT", round(TITLE_OUT, 2))
    for tab, rowh, fsz, ti, to, steps in SHOWS: print(tab[0], round(ti, 2), round(to, 2), "bottom", TY + rowh * (len(tab[1]) + 2) + 12)
    for gi, g in enumerate(groups): print(f'{cap[g[0]]["s"]:6.2f}', " ".join(cap[j]["w"] for j in g))
elif MODE == "faces":
    fc = json.load(open(f"{S}/raw/faces.json")); bad = []
    for t, x, y, w, h in fc:
        if x is None or y < 500: continue
        hair = y - 0.24 * h; chin = chin_of(y, h)
        z = zoom_at(t)
        if z != 1.0:
            _, y0 = zbox(z); hair = (hair - y0) * z; chin = (chin - y0) * z
        eyes = y + 0.36 * h; mouth_b = y + h * 0.95
        if gs_alpha(t) > 0.5:
            ta = table_at(t)  # tabela atrás dele: pode encostar no cabelo; não pode cobrir mais que 1 linha
            if ta and TY + ta[0].height > hair + 70: bad.append((t, "tabela atrás do cabelo", int(hair)))
        if t < TITLE_OUT and TOPY + TITLE[0].height / 2 - TITLE[1] > hair: bad.append((t, "titulo", int(hair)))
        for (img, pad), bx, by, ti, to in BADGES:
            if ti <= t < to and by + img.height / 2 - pad > hair: bad.append((t, "selo", int(hair)))
        ci = caption_at(t)
        if ci is not None and ci[1] + 18 < chin: bad.append((t, "legenda", int(chin), ci[1]))
    print("SEM CONFLITOS" if not bad else bad[:60], len(bad))
elif MODE == "preview":
    run(ARGS[0], float(ARGS[1]), float(ARGS[2]))
elif MODE == "full":
    run(ARGS[0])
