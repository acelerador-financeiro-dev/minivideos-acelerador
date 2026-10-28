import json, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
S = sys.argv[1]
os.chdir(S)
ANTON = 'fonts/Anton-Regular.ttf'; CARB = 'fonts/Carlito-Bold.ttf'
CR = '/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf'
TQ = (40, 212, 206); RED = (229, 72, 77); YEL = (255, 204, 0); WHITE = (255, 255, 255); INK = (20, 24, 30); GRAY = (95, 102, 112)
DUR = 131.51
H = 700  # faixa de cima (y 0..700); cabelo mínimo medido 722

def F(p, s): return ImageFont.truetype(p, s)

def shadow_text(d, xy, txt, font, fill, anchor='ma', stroke=6):
    d.text(xy, txt, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0))

def wrap(d, txt, font, maxw):
    out, cur = [], ''
    for w in txt.split():
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: out.append(cur); cur = w
    out.append(cur); return out

def card(im, y0, h, header, title, big=None, bigcol=RED, sub=None, w=900):
    x0 = (1080 - w) // 2
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
    ds.rounded_rectangle([x0 + 6, y0 + 10, x0 + w + 6, y0 + h + 10], 28, fill=(0, 0, 0, 110))
    im.alpha_composite(sh)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 28, fill=WHITE)
    d.rounded_rectangle([x0, y0, x0 + 14, y0 + h], 7, fill=TQ)
    y = y0 + 26
    d.text((x0 + 44, y), header, font=F(CARB, 30), fill=GRAY); y += 46
    ft = F(CARB, 42)
    for ln in (wrap(d, title, ft, w - 88) if title else []):
        d.text((x0 + 44, y), ln, font=ft, fill=INK); y += 50
    if big:
        y += 8
        fb = F(ANTON, 104)
        d.text((x0 + 44, y), big, font=fb, fill=bigcol)
        bw = d.textlength(big, font=fb)
        if sub:
            fs = F(CARB, 38)
            lines = wrap(d, sub, fs, w - 88 - bw - 30)
            yy = y + 20
            for ln in lines:
                d.text((x0 + 44 + bw + 26, yy), ln, font=fs, fill=INK); yy += 44
    elif sub:
        y += 6
        for ln in wrap(d, sub, F(CR, 34), w - 88):
            d.text((x0 + 44, y), ln, font=F(CR, 34), fill=GRAY); y += 40

def pill(im, y, txt, icon, col, w=None):
    d = ImageDraw.Draw(im); f = F(ANTON, 52)
    tw = d.textlength(txt, font=f); w = w or int(tw + 150)
    x0 = (1080 - w) // 2
    d.rounded_rectangle([x0 + 5, y + 8, x0 + w + 5, y + 98], 45, fill=(0, 0, 0, 120))
    d.rounded_rectangle([x0, y, x0 + w, y + 90], 45, fill=(255, 255, 255, 255), outline=col, width=6)
    cx, cy = x0 + 52, y + 45
    d.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=col)
    if icon == '!':
        d.text((cx, cy), '!', font=F(ANTON, 44), fill=WHITE, anchor='mm')
    else:
        d.line([(cx - 13, cy + 1), (cx - 3, cy + 12), (cx + 15, cy - 11)], fill=WHITE, width=7)
    d.text((x0 + 98, y + 45), txt, font=f, fill=(20, 18, 19), anchor='lm')

def soft(im, draw_fn, blur=12, off=5, alpha=170):
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); draw_fn(ImageDraw.Draw(lay))
    a = lay.getchannel('A').point(lambda v: int(v * alpha / 255))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 255)); sh.putalpha(a)
    sh = sh.transform(im.size, Image.AFFINE, (1, 0, 0, 0, 1, -off)).filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(sh); im.alpha_composite(lay)

LSB = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
def faixa(im, y, lines, size=56, hl=None, hlcol=None):
    """Faixa estilo Instagram por linha: fundo branco e texto preto; a linha de destaque
    ganha caixa colorida (turquesa com texto grafite, ou vermelha com texto branco)."""
    hlcol = hlcol or TQ
    f = F(LSB, size); lh = int(size * 1.22) + 10
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for i, l in enumerate(lines):
        tw = d.textlength(l, font=f); w = int(tw + 48); x0 = (1080 - w) // 2; yy = y + i * lh
        bg = hlcol if hl == i else WHITE
        fg = WHITE if (hl == i and hlcol == RED) else (55, 52, 53) if hl == i else (0, 0, 0)
        d.rounded_rectangle([x0, yy, x0 + w, yy + lh - 4], 18, fill=bg + (255,))
        d.text((540, yy + (lh - 4) / 2), l, font=f, fill=fg, anchor='mm')
    a = lay.getchannel('A').point(lambda v: int(v * 0.55))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 255)); sh.putalpha(a)
    sh = sh.transform(im.size, Image.AFFINE, (1, 0, 0, 0, 1, -6)).filter(ImageFilter.GaussianBlur(10))
    im.alpha_composite(sh); im.alpha_composite(lay)
    return y + lh * len(lines)

def title(im):
    faixa(im, 175, ['Metade dos brasileiros', 'já caiu em golpe.'], size=62, hl=1, hlcol=RED)

def big2(im, y, l1, l2, c2=TQ, s=78):
    faixa(im, y, [l1] + ([l2] if l2 else []), size=54, hl=1 if (l2 and c2 != WHITE) else None)

# estados da faixa de cima: (início, função)
def st_title(im): title(im)
def st_title_cardA(im):
    title(im)
    card(im, 372, 232, 'INFOMONEY · MAR/2025 · DADOS SERASA EXPERIAN',
         None, big='51%', sub='dos brasileiros sofreram fraude em 2024')
def st_cardA(im):
    card(im, 190, 335, 'INFOMONEY · MAR/2025 · DADOS SERASA EXPERIAN',
         'Metade dos brasileiros foi vítima de fraude em 2024', big='51%', sub='dos brasileiros sofreram fraude em 2024')
def st_cardB(im):
    card(im, 170, 420, 'SERASA EXPERIAN · 26/08/2026',
         'Brasil registra quase 3 milhões de tentativas de fraude de identidade no 1º semestre',
         big='2.860.957', sub='tentativas de jan. a jun. de 2026')
def st_cardCVM(im):
    card(im, 170, 400, 'CVM · PORTAL DO INVESTIDOR · 01/07/2025',
         'Em um teste da CVM, quase metade dos participantes cairia em golpe de investimentos. Será que você também?',
         sub='Corretora falsa criada pela CVM e pela ANBIMA, para fins educativos')
def st_cardC(im):
    card(im, 170, 330, 'ANBIMA · 15/05/2024 · EXPERIMENTO COM A CVM',
         'Quase metade das pessoas que acessaram site de falsa corretora cairia em golpe financeiro',
         sub='Site fictício ficou 4 meses no ar · 104 mil visitantes únicos')
def st_cardC2(im):
    card(im, 170, 425, 'CVM · PORTAL DO INVESTIDOR · 01/07/2025',
         'Teste com corretora falsa: mesmo com sinais claros de golpe...',
         big='48%', sub='dos visitantes demonstraram intenção de investir')
FL = ['ROBÔ QUE RENDE DORMINDO', 'RENTABILIDADE ABSURDA SEM RISCO', 'FÓRMULA SECRETA']
def st_flags(n):
    def f(im):
        for i in range(n): pill(im, 190 + i * 118, FL[i], '!', RED, w=900)
    return f
def st_atalho(n):
    def f(im):
        big2(im, 190, 'Enquanto você procura o atalho...', None)
        if n > 1: big2(im, 330, 'alguém fica rico', 'vendendo esse atalho pra você.', c2=TQ)
    return f
CK = ['GANHAR MAIS', 'GASTAR MENOS DO QUE GANHA', 'INVESTIR']
def st_checks(n):
    def f(im):
        for i in range(n): pill(im, 190 + i * 118, CK[i], 'v', TQ, w=900)
    return f
def st_metodo(n):
    def f(im):
        big2(im, 190, 'Não é milagre.', 'Não é sorte.', c2=WHITE)
        if n > 1: big2(im, 395, 'É método, conhecimento', 'e consistência.', c2=TQ)
    return f
def st_cta(n):
    def f(im):
        big2(im, 190, 'Quer construir patrimônio', 'de verdade?', c2=TQ)
        if n > 1: pill(im, 400, 'SEGUE O PERFIL', 'v', TQ, w=640)
    return f
def st_none(im): pass

STATES = [
    (0.0, st_title), (7.2, st_title_cardA), (10.0, st_cardA), (15.4, st_cardB), (23.7, st_none),
    (26.6, st_cardCVM), (31.9, st_cardC), (39.3, st_cardC2), (47.0, st_none),
    (57.9, st_flags(1)), (62.2, st_flags(2)), (65.1, st_flags(3)), (68.5, st_none),
    (69.7, st_atalho(1)), (72.8, st_atalho(2)), (82.0, st_none),
    (85.4, st_checks(1)), (99.9, st_checks(2)), (102.8, st_checks(3)), (107.3, st_metodo(1)), (109.8, st_metodo(2)),
    (112.0, st_cta(1)), (120.3, st_cta(2)), (DUR, None),
]
os.makedirs('ov', exist_ok=True)
lines = []
for i in range(len(STATES) - 1):
    t0, fn = STATES[i]; t1 = STATES[i + 1][0]
    im = Image.new('RGBA', (1080, H), (0, 0, 0, 0)); fn(im)
    p = f'ov/s{i:02d}.png'; im.save(p)
    lines += [f"file '{os.path.abspath(p)}'", f'duration {t1 - t0:.3f}']
lines.append(f"file '{os.path.abspath(p)}'")
open('ov.txt', 'w').write('\n'.join(lines) + '\n')

# ---------- legenda karaokê (ASS) na faixa de cima, logo acima do cabelo ----------
W = json.load(open('words.json'))
FIX = {38: 'foram', 39: 'vítimas', 89: 'CVM', 90: 'e Anbima', 125: '48%', 126: None, 130: 'visitaram',
       188: 'enquanto', 189: None, 277: 'construir', 278: None, 279: None, 267: 'doido,'}
words = []
for i, w in enumerate(W):
    t = FIX.get(i, w['w'])
    if t is None: continue
    words.append({'w': t, 't': w['t']})
for i, w in enumerate(words):
    w['e'] = words[i + 1]['t'] if i + 1 < len(words) else DUR
    w['e'] = min(w['e'], w['t'] + 1.0)
chunks, cur = [], []
for w in words:
    cur.append(w)
    txt = ' '.join(x['w'] for x in cur)
    if len(cur) >= 4 or len(txt) >= 20 or w['w'][-1] in '.,?!':
        chunks.append(cur); cur = []
if cur: chunks.append(cur)

def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'
def clean(s): return s.strip(',.').upper() if False else s
ass = ['[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1080', 'PlayResY: 1920', 'WrapStyle: 2', '',
       '[V4+ Styles]',
       'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
       'Style: Leg,Carlito,66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,0,0,1,6,3,8,60,60,622,1',
       '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
TQASS = '&H00B4C418&'
for ch in chunks:
    for j, w in enumerate(ch):
        t0 = w['t']; t1 = ch[j + 1]['t'] if j + 1 < len(ch) else w['e']
        parts = []
        for k, x in enumerate(ch):
            s = x['w']
            parts.append('{\\c' + TQASS + '}' + s + '{\\c&H00FFFFFF&}' if k == j else s)
        ass.append(f'Dialogue: 0,{ts(t0)},{ts(t1)},Leg,,0,0,0,,' + ' '.join(parts))
open('leg.ass', 'w').write('\n'.join(ass) + '\n')
print(len(STATES) - 1, 'estados;', len(chunks), 'frases')
