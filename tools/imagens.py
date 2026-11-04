# Modelo Imagens (#015b): janela no topo com imagens trocando com a fala + legenda karaokê no peito.
# Render HDR (HLG/BT.2020) como gravado: só os gráficos são convertidos de sRGB para HLG.
# Uso: python3 -I imagens.py $S <modo> [args]   modos: info | faces | frames t1 t2 ... | sheet | preview out ss dur | full out
# Arquivos em $S: raw/words.json, raw/cuts.json, raw/base_hdr.mp4, raw/faces.json, raw/mix.m4a (voz + whoosh),
#                 fonts/, imgs/<arquivo>.jpg e plano.json (configuração do vídeo).
import json, sys, math, subprocess, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = sys.argv[1]; MODE = sys.argv[2]; ARGS = sys.argv[3:]
W, H, FPS = 1080, 1920, 30
F = f"{S}/fonts"
GRAF = (55, 52, 53); TURQ = (40, 212, 206); WHITE = (255, 255, 255); RED = (229, 72, 77); BLACK = (20, 18, 19)
LIB = "/usr/share/fonts/truetype/liberation"
_fc = {}
def font(name, size):
    k = (name, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype({"anton": f"{F}/Anton-Regular.ttf", "cb": f"{F}/Carlito-Bold.ttf",
                                     "ab": f"{LIB}/LiberationSans-Bold.ttf"}[name], size)
    return _fc[k]

P = json.load(open(f"{S}/plano.json"))
# P: {"win": [x, y, w, h], "imgs": [[word_idx, file, focus_y(0-1)], ...], "win_end": word_idx,
#     "repl": {idx: "palavra"}, "abertura": {"linhas": [[texto, "branco"|"turq"|"verm"], ...], "fim": word_idx},
#     "cta": {"texto": "...", "ini": word_idx}, "capy": 1440}

# ---------------- tempo ----------------
Wd = json.load(open(f"{S}/raw/words.json"))
CUT = json.load(open(f"{S}/raw/cuts.json")); SEGS = CUT["segs"]; KEEP = CUT["keep"]
K = CUT.get("k", 1.0); SDR = P.get("sdr", False)
DUR = SEGS[-1]["out0"] + (SEGS[-1]["in1"] - SEGS[-1]["in0"]) / K
def m(t):
    for s in SEGS:
        if s["in0"] - 1e-6 <= t <= s["in1"] + 1e-6: return s["out0"] + (t - s["in0"]) / K
    for s in SEGS:
        if t < s["in0"]: return s["out0"]
    return DUR
def T(i): return m(Wd[i]["s"])
def E(i): return m(Wd[i]["e"])
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else (1.0 if t >= t0 else 0.0)

# ---------------- legenda karaokê (padrão) ----------------
REPL = {int(k): v for k, v in P.get("repl", {}).items()}
cap = [{"w": REPL.get(i, Wd[i]["w"]), "s": T(i), "e": E(i), "i": i} for i in KEEP if REPL.get(i, Wd[i]["w"]) != ""]
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
CAPY = P.get("capy", 1440)
FACES = json.load(open(f"{S}/raw/faces.json")) if os.path.exists(f"{S}/raw/faces.json") else []
def chin_max(t0, t1):
    c = [y + 1.08 * h for t, x, y, w, h in FACES if x is not None and y > 500 and t0 - 0.1 <= t <= t1 + 0.1]
    return max(c) if c else 0
def hair_min(t0, t1):
    c = [y - 0.24 * h for t, x, y, w, h in FACES if x is not None and y > 500 and t0 - 0.1 <= t <= t1 + 0.1]
    return min(c) if c else H
# legenda no peito; quando ele se inclina, desce junto (até 1560, acima do rodapé do Reels)
GY = {gi: int(clamp(chin_max(cap[g[0]]["s"], cap[g[-1]]["e"] + 0.6) - 10, CAPY, 1560)) for gi, g in enumerate(groups)}
def caption_at(t):
    for gi, g in enumerate(groups):
        s = cap[g[0]]["s"]; nxt = cap[groups[gi + 1][0]]["s"] if gi + 1 < len(groups) else DUR
        end = min(nxt, cap[g[-1]]["e"] + 0.6)
        if s - 0.03 <= t < end:
            hi = g[0]
            for j in g:
                if cap[j]["s"] - 0.03 <= t: hi = j
            return caption_img(gi, hi), GY[gi]
    return None

# ---------------- conversão sRGB -> HLG (só gráficos) ----------------
M = np.array([[0.6274, 0.3293, 0.0433], [0.0691, 0.9195, 0.0114], [0.0164, 0.0880, 0.8956]])
lin = np.array([((v / 255) / 12.92 if v / 255 <= 0.04045 else (((v / 255) + 0.055) / 1.055) ** 2.4) for v in range(256)])
a_, b_, c_ = 0.17883277, 0.28466892, 0.55991073
def hlg(E_):
    E_ = np.clip(E_, 0, 1)
    return np.where(E_ <= 1 / 12, np.sqrt(3 * E_), a_ * np.log(np.maximum(12 * E_ - b_, 1e-6)) + c_)
def to_hlg(rgb8):
    if SDR: return rgb8.astype(np.float32) * 257
    return (hlg(lin[rgb8] @ M.T * 0.2647) * 65535).astype(np.float32)

class Layer:
    """Gráfico pré-convertido para HLG: posição, cor HLG e alfa (calculados uma vez)."""
    def __init__(self, im, x, y):
        a = np.asarray(im)
        ys, xs = np.nonzero(a[..., 3] > 0)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        sub = a[y0:y1, x0:x1]
        self.x, self.y = x + x0, y + y0
        self.al = sub[..., 3:4].astype(np.float32) / 255; self.rgb = to_hlg(sub[..., :3])
        self.im = im; self.px, self.py = x, y
    def draw(self, fr, alpha=1.0):
        h, w = self.rgb.shape[:2]
        x0, y0 = max(0, self.x), max(0, self.y); x1, y1 = min(W, self.x + w), min(H, self.y + h)
        if x1 <= x0 or y1 <= y0: return
        sx, sy = x0 - self.x, y0 - self.y
        al = self.al[sy:sy + y1 - y0, sx:sx + x1 - x0] * alpha
        fr[y0:y1, x0:x1] = fr[y0:y1, x0:x1] * (1 - al) + self.rgb[sy:sy + y1 - y0, sx:sx + x1 - x0] * al

def draw_rgba(fr, im, x, y):
    a = np.asarray(im)
    if not (a[..., 3] > 0).any(): return
    ys, xs = np.nonzero(a[..., 3] > 0); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    sub = a[y0:y1, x0:x1]; al = sub[..., 3:4].astype(np.float32) / 255
    X, Y = x + x0, y + y0; hh, ww = sub.shape[:2]
    fr[Y:Y + hh, X:X + ww] = fr[Y:Y + hh, X:X + ww] * (1 - al) + to_hlg(sub[..., :3]) * al

# ---------------- janela de imagens ----------------
WX, WY, WW, WH = P["win"]; RAD = 28; SHB = 24; PAD = SHB * 2
def window_img(path, fy=0.5, WW=WW, WH=WH):
    src = Image.open(path).convert("RGB")
    r = max(WW / src.width, WH / src.height)
    im = src.resize((math.ceil(src.width * r), math.ceil(src.height * r)), Image.LANCZOS)
    ox = (im.width - WW) // 2; oy = int(clamp(fy) * (im.height - WH))
    im = im.crop((ox, oy, ox + WW, oy + WH)).convert("RGBA")
    mk = Image.new("L", (WW * 2, WH * 2), 0); ImageDraw.Draw(mk).rounded_rectangle([0, 0, WW * 2 - 1, WH * 2 - 1], radius=RAD * 2, fill=255)
    im.putalpha(mk.resize((WW, WH), Image.LANCZOS))
    out = Image.new("RGBA", (WW + PAD * 2, WH + PAD * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0)); blk = Image.new("RGBA", (WW, WH), (0, 0, 0, 0))
    blk.putalpha(im.getchannel("A").point(lambda v: int(v * 0.45))); sh.paste(blk, (PAD, PAD + 8))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(SHB))); out.alpha_composite(im, (PAD, PAD))
    return out
IMGS = sorted(P["imgs"], key=lambda r: r[0])
SHOW = []  # (t0, t1, arquivo, foco)
WIN_END = T(P["win_end"]) - 0.05
for k, r in enumerate(IMGS):
    t0 = 0.0 if k == 0 else T(r[0]) - 0.04
    t1 = (T(IMGS[k + 1][0]) - 0.04) if k + 1 < len(IMGS) else WIN_END
    # se ele se inclina e o cabelo sobe até a janela, a janela daquele trecho encolhe (presa no topo)
    hm = hair_min(t0, t1); sc = 1.0 if hm >= WY + WH + 8 else clamp((hm - 8 - WY) / WH, 0.6, 1.0)
    SHOW.append((t0, t1, r[1], r[2] if len(r) > 2 else 0.5, sc))
_wl = {}
def win_layer(k):
    if k not in _wl:
        if len(_wl) > 6: _wl.pop(next(iter(_wl)))
        sc = SHOW[k][4]; ww, wh = int(WW * sc), int(WH * sc)
        _wl[k] = Layer(window_img(f"{S}/imgs/{SHOW[k][2]}", SHOW[k][3], ww, wh), int(540 - ww / 2) - PAD, WY - PAD)
    return _wl[k]
def win_at(t):
    for k, (t0, t1, *_r) in enumerate(SHOW):
        if t0 <= t < t1: return k
    return None

# ---------------- frase de abertura (faixa branca do Instagram, regra 19) ----------------
AB = P.get("abertura")
def make_abertura():
    lines = AB["linhas"]; f0 = font("ab", 58); out = []; y = 0
    for txt, kind in lines:
        bg, fg = {"branco": (WHITE, BLACK), "turq": (TURQ, GRAF), "verm": (RED, WHITE)}[kind]
        w = int(f0.getlength(txt)) + 56; h = 88
        im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=26, fill=bg)
        f2 = ImageFont.truetype(f0.path, f0.size * 2); bb = f2.getbbox(txt)
        d.text((56, (h * 2 - (bb[3] + bb[1])) / 2), txt, font=f2, fill=fg)
        out.append((im.resize((w, h), Image.LANCZOS), y)); y += h - 4
    tw = max(i.width for i, _ in out) + 40; th = y + 40
    can = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    for i, yy in out: can.alpha_composite(i, ((tw - i.width) // 2, yy + 20))
    sh = Image.new("RGBA", can.size, (0, 0, 0, 0)); blk = Image.new("RGBA", can.size, (0, 0, 0, 0))
    blk.putalpha(can.getchannel("A").point(lambda v: int(v * 0.35))); sh.paste(blk, (0, 6))
    fin = Image.new("RGBA", can.size, (0, 0, 0, 0)); fin.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10))); fin.alpha_composite(can)
    return fin
AB_L = None; AB_END = 0
if AB:
    _ab = make_abertura(); AB_END = E(AB["fim"]) + 0.15
    # encostada na borda de baixo da janela, por cima dela
    AB_L = Layer(_ab, int(540 - _ab.width / 2), int(WY + WH - _ab.height + 26))

# ---------------- CTA final (o que ele pede no vídeo) ----------------
CT = P.get("cta"); CTA_L = None; CTA_T = DUR + 1
if CT:
    f = font("anton", 54); txt = CT["texto"]; w = int(f.getlength(txt)) + 70; h = 96
    im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=h, fill=TURQ)
    f2 = ImageFont.truetype(f.path, f.size * 2); bb = f2.getbbox(txt); d.text((70, (h * 2 - (bb[3] + bb[1])) / 2), txt, font=f2, fill=GRAF)
    im = im.resize((w, h), Image.LANCZOS)
    if im.width > 960: im = im.resize((960, int(h * 960 / w)), Image.LANCZOS)
    can = Image.new("RGBA", (im.width + 40, im.height + 40), (0, 0, 0, 0)); blk = Image.new("RGBA", can.size, (0, 0, 0, 0))
    blk.paste(Image.new("RGBA", im.size, (0, 0, 0, 110)), (20, 26), im); can.alpha_composite(blk.filter(ImageFilter.GaussianBlur(10))); can.alpha_composite(im, (20, 20))
    CTA_L = Layer(can, int(540 - can.width / 2), P["cta"].get("y", 430) - can.height // 2); CTA_T = T(CT["ini"])

# ---------------- quadro ----------------
def frame_hdr(fr, n):
    t = n / FPS; fr = fr.astype(np.float32)
    k = win_at(t)
    if k is not None: win_layer(k).draw(fr)
    if AB_L is not None and t < AB_END: AB_L.draw(fr, prog(t, 0, 0.15) * (1 - prog(t, AB_END - 0.2, 0.2)))
    if CTA_L is not None and t >= CTA_T: CTA_L.draw(fr, prog(t, CTA_T, 0.25))
    ci = caption_at(t)
    if ci is not None: draw_rgba(fr, ci[0], int(540 - ci[0].width / 2), ci[1])
    return np.clip(fr + 0.5, 0, 65535).astype(np.uint16)

BASE = f"{S}/raw/base.mkv" if SDR else f"{S}/raw/base_hdr.mp4"; AUD = f"{S}/raw/mix.m4a" if os.path.exists(f"{S}/raw/mix.m4a") else BASE
def reader(ss=None, dur=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", f"{ss:.3f}"] if ss is not None else []) + ["-i", BASE] + (["-t", f"{dur:.3f}"] if dur else []) + \
        ["-vf", ("scale=in_color_matrix=bt709:in_range=tv,format=rgb48le" if SDR else "scale=in_color_matrix=bt2020:in_range=tv,format=rgb48le"), "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE)
VOUT_HDR = ["-vf", "scale=out_color_matrix=bt2020:out_range=tv,format=yuv420p10le", "-c:v", "libx265", "-preset", "fast", "-crf", "21", "-tag:v", "hvc1",
         "-x265-params", "log-level=error:colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited:vbv-maxrate=8000:vbv-bufsize=16000",
         "-colorspace", "bt2020nc", "-color_primaries", "bt2020", "-color_trc", "arib-std-b67"]
VOUT_SDR = ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx265", "-preset", os.environ.get("XPRESET", "fast"), "-crf", os.environ.get("XCRF", "20"), "-tag:v", "hvc1",
         "-x265-params", "log-level=error:colorprim=bt709:transfer=bt709:colormatrix=bt709:range=limited:vbv-maxrate=9000:vbv-bufsize=18000",
         "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
def writer(out, ss=None, dur=None, crf="21"):
    aud = (["-ss", f"{ss:.3f}"] if ss is not None else []) + ["-i", AUD] + (["-t", f"{dur:.3f}"] if dur else [])
    return subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb48le", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"] + aud +
        ["-map", "0:v", "-map", "1:a"] + (VOUT_SDR if SDR else VOUT_HDR) + [
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
def run(out, ss=None, dur=None, only=None):
    rd = reader(ss, dur); wr = writer(out, ss, dur) if out else None
    n0 = int(round((ss or 0) * FPS)); n = 0; fs = W * H * 6
    while True:
        buf = rd.stdout.read(fs)
        if len(buf) < fs: break
        o = frame_hdr(np.frombuffer(buf, np.uint16).reshape(H, W, 3), n0 + n)
        if wr: wr.stdin.write(o.tobytes())
        if only is not None: only(o, n0 + n)
        n += 1
        if n % 300 == 0: print("frame", n, flush=True)
    if wr: wr.stdin.close(); wr.wait()
    print("DONE", n, flush=True)
def hlg_to_srgb(o):
    if SDR: return (o.astype(np.float32) / 257).clip(0, 255).astype(np.uint8)
    E_ = o.astype(np.float32) / 65535
    L = np.where(E_ <= 0.5, E_ ** 2 / 3, (np.exp((E_ - c_) / a_) + b_) / 12) / 0.2647
    L = np.clip(L @ np.linalg.inv(M).T, 0, 1)
    return (np.clip(np.where(L <= 0.0031308, L * 12.92, 1.055 * L ** (1 / 2.4) - 0.055), 0, 1) * 255).astype(np.uint8)

if MODE == "frames":
    os.makedirs(f"{S}/check", exist_ok=True)
    for t in [float(x) for x in ARGS]:
        def save(o, n, t=t): Image.fromarray(hlg_to_srgb(o)).resize((270, 480)).save(f"{S}/check/c_{t:07.2f}.jpg", quality=80)
        run(None, t, 1 / FPS, save)
elif MODE == "info":
    print("DUR", round(DUR, 2), "imgs", len(SHOW), "janela até", round(WIN_END, 2), "abertura até", round(AB_END, 2), "CTA", round(CTA_T, 2))
    for t0, t1, f, _, sc in SHOW: print(f"{t0:6.2f} {t1 - t0:4.2f} {f}" + (f"  escala {sc:.2f}" if sc < 1 else ""))
elif MODE == "faces":
    fc = json.load(open(f"{S}/raw/faces.json")); bad = []
    for t, x, y, w, h in fc:
        if x is None or y < 500: continue
        hair = y - 0.24 * h; chin = y + 1.08 * h
        k = win_at(t)
        if k is not None and WY + WH * SHOW[k][4] > hair: bad.append((t, "janela", int(hair)))
        if AB_L is not None and t < AB_END and AB_L.y + AB_L.rgb.shape[0] > hair: bad.append((t, "abertura", int(hair)))
        if CTA_L is not None and t >= CTA_T and CTA_L.y + CTA_L.rgb.shape[0] > hair: bad.append((t, "cta", int(hair)))
        ci = caption_at(t)
        if ci is not None and ci[1] + 18 < chin: bad.append((t, "legenda", int(chin)))
    print("SEM CONFLITOS" if not bad else bad[:40], len(bad))
elif MODE == "preview":
    run(ARGS[0], float(ARGS[1]), float(ARGS[2]))
elif MODE == "full":
    run(ARGS[0])
