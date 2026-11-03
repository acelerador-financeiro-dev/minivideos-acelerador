#!/usr/bin/env python3
"""Busca e baixa imagens para o modelo Imagens (roda no GitHub Actions).

Pedido: imagens/pedidos/NNN.txt, uma linha por imagem:
    nome<TAB>termos de busca em ingles          -> busca nos bancos, baixa ate 3 opcoes (nome_a.jpg, nome_b.jpg...)
    nome<TAB>url:https://...                    -> baixa direto (nome_a.jpg)
Linhas vazias e com # sao ignoradas.

    nome<TAB>arte:termos                         -> obra/ilustracao antiga (Wikimedia Commons, depois Openverse)
Fotos: Pexels (se PEXELS_KEY), Unsplash (se UNSPLASH_KEY), depois Openverse (sem chave, qualidade fraca).
Saida: imagens/NNN/*.jpg (lado maior 1400), imagens/NNN/creditos.tsv, imagens/NNN/falhas.txt, imagens/NNN/.ok
"""
import io, json, os, sys, time, urllib.parse, urllib.request
from PIL import Image

UA = "minivideos-acelerador/1.0 (github.com/acelerador-financeiro-dev/minivideos-acelerador)"
OPCOES = int(os.environ.get("OPCOES", "3"))


def get(url, headers=None, raw=False):
    h = {"User-Agent": UA}
    h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60) as r:
        data = r.read()
    return data if raw else json.loads(data)


def pexels(q):
    k = os.environ.get("PEXELS_KEY")
    if not k:
        return []
    d = get("https://api.pexels.com/v1/search?" + urllib.parse.urlencode({"query": q, "per_page": OPCOES + 2, "orientation": "landscape"}),
            {"Authorization": k})
    return [(p["src"]["large2x"], "Pexels", p.get("photographer", ""), "Pexels License", p["url"]) for p in d.get("photos", [])]


def unsplash(q):
    k = os.environ.get("UNSPLASH_KEY")
    if not k:
        return []
    d = get("https://api.unsplash.com/search/photos?" + urllib.parse.urlencode({"query": q, "per_page": OPCOES + 2, "orientation": "landscape", "content_filter": "high"}),
            {"Authorization": "Client-ID " + k})
    return [(p["urls"]["regular"], "Unsplash", p["user"]["name"], "Unsplash License", p["links"]["html"]) for p in d.get("results", [])]


def openverse(q):
    d = get("https://api.openverse.org/v1/images/?" + urllib.parse.urlencode(
        {"q": q, "license_type": "commercial,modification", "page_size": OPCOES + 3, "mature": "false"}))
    return [(r["url"], "Openverse/" + (r.get("source") or ""), r.get("creator") or "", (r.get("license") or "") + " " + (r.get("license_version") or ""), r.get("foreign_landing_url") or "")
            for r in d.get("results", [])]


def commons(q):
    d = get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": OPCOES + 3,
        "gsrsearch": q + " filetype:bitmap", "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 1400}))
    out = []
    for p in (d.get("query", {}).get("pages", {}) or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {})
        out.append((ii.get("thumburl") or ii.get("url"), "Wikimedia Commons",
                    (md.get("Artist", {}).get("value") or "")[:80], md.get("LicenseShortName", {}).get("value", ""), ii.get("descriptionurl", "")))
    return out


def salvar(url, destino):
    data = get(url, raw=True)
    im = Image.open(io.BytesIO(data))
    im = im.convert("RGB")
    im.thumbnail((1400, 1400), Image.LANCZOS)
    if min(im.size) < 300:
        raise ValueError("imagem pequena demais")
    im.save(destino, "JPEG", quality=92)


def main():
    for ped in sorted(os.listdir("imagens/pedidos")):
        if not ped.endswith(".txt"):
            continue
        n = ped[:-4]
        d = os.path.join("imagens", n)
        if os.path.exists(os.path.join(d, ".ok")):
            continue
        os.makedirs(d, exist_ok=True)
        cred = open(os.path.join(d, "creditos.tsv"), "a")
        falhas = open(os.path.join(d, "falhas.txt"), "a")
        for linha in open(os.path.join("imagens/pedidos", ped), encoding="utf-8"):
            linha = linha.rstrip("\n")
            if not linha.strip() or linha.startswith("#") or "\t" not in linha:
                continue
            nome, q = [x.strip() for x in linha.split("\t", 1)]
            if q.startswith("url:"):
                cands = [(q[4:], "direto", "", "", q[4:])]
            else:
                cands = []
                # "arte: ..." = obra/ilustracao antiga (Wikimedia primeiro); o resto = foto (Pexels, Unsplash, Openverse)
                if q.startswith("arte:"):
                    q = q[5:].strip(); bancos = (commons, openverse)
                else:
                    bancos = (pexels, unsplash, openverse)
                for f in bancos:
                    try:
                        cands += f(q)
                    except Exception as e:
                        print(f"[{nome}] {f.__name__}: {e}")
                    if len(cands) >= OPCOES * 2:
                        break
            ok = 0
            for url, banco, autor, lic, pagina in cands:
                if ok >= (1 if q.startswith("url:") else OPCOES) or not url:
                    break
                arq = f"{nome}_{'abcdefgh'[ok]}.jpg"
                try:
                    salvar(url, os.path.join(d, arq))
                    cred.write("\t".join([arq, banco, autor.replace("\t", " "), lic, pagina]) + "\n")
                    ok += 1
                except Exception as e:
                    print(f"[{nome}] falhou {url}: {e}")
                time.sleep(0.3)
            if ok == 0:
                falhas.write(linha + "\n")
            print(f"{nome}: {ok} opcoes")
        cred.close(); falhas.close()
        open(os.path.join(d, ".ok"), "w").close()


if __name__ == "__main__":
    main()
