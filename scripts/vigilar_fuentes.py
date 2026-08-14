# -*- coding: utf-8 -*-
"""Vigilancia de fuentes oficiales.
Compara el contenido actual de cada fuente con el último estado guardado
y genera data/cambios_detectados.md si detecta modificaciones."""
import hashlib, json, sys, time
from datetime import datetime, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
ESTADO = DATA / "estado_fuentes.json"
CAMBIOS = DATA / "cambios_detectados.md"
FUENTES = RAIZ / "fuentes.json"
UA = "Mozilla/5.0 (compatible; biblioteca-vigilante/1.1)"
TIMEOUT = 60
REINTENTOS = 3

def descargar(url):
    ultimo = None
    for _ in range(REINTENTOS):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
            r.raise_for_status()
            return r.text
        except Exception as e:
            ultimo = e
            time.sleep(2)
    raise ultimo

def texto_html(html):
    sopa = BeautifulSoup(html, "html.parser")
    for tag in sopa(["script", "style", "noscript", "nav", "footer"]):
        tag.decompose()
    return " ".join(sopa.get_text(" ", strip=True).split())

def huella(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()

def main():
    DATA.mkdir(exist_ok=True)
    fuentes = json.loads(FUENTES.read_text(encoding="utf-8"))["fuentes"]
    previo = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}
    nuevo, cambios, errores = {}, [], []

    for f in fuentes:
        fid = f["id"]
        try:
            txt = texto_html(descargar(f["url"]))
            h = huella(txt)
            nuevo[fid] = {"url": f["url"], "categoria": f.get("categoria", ""),
                          "hash": h, "longitud": len(txt), "estado": "ok",
                          "fecha": datetime.now(timezone.utc).isoformat()}
            if fid in previo and previo[fid].get("hash") != h:
                cambios.append(f)
        except Exception as e:
            errores.append({"nombre": f["nombre"], "error": str(e),
                            "categoria": f.get("categoria", "")})
            nuevo[fid] = {"url": f["url"], "categoria": f.get("categoria", ""),
                          "estado": "error", "error": str(e),
                          "fecha": datetime.now(timezone.utc).isoformat()}

    ESTADO.write_text(json.dumps(nuevo, ensure_ascii=False, indent=2), encoding="utf-8")

    if cambios:
        cats = {}
        for c in cambios:
            cats.setdefault(c.get("categoria", "Otras"), []).append(c)
        lineas = ["# Cambio detectado en fuentes oficiales", "",
                  f"Fecha: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC", "",
                  "Se han detectado modificaciones; revisa la biblioteca y actualiza las secciones afectadas:", ""]
        for cat, lista in cats.items():
            lineas.append(f"## {cat}")
            lineas.append("")
            for c in lista:
                lineas.append(f"- **{c['nombre']}** — {c['url']}")
            lineas.append("")
        if errores:
            lineas.append("## Fuentes con error en esta revisión")
            lineas.append("")
            for e in errores:
                lineas.append(f"- {e['categoria']} · {e['nombre']}: `{e['error'][:120]}`")
        CAMBIOS.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        print(f"Fuentes revisadas: {len(fuentes)} | cambios: {len(cambios)} | errores: {len(errores)}")
    else:
        if CAMBIOS.exists():
            CAMBIOS.unlink()
        print(f"Fuentes revisadas: {len(fuentes)} | sin cambios | errores: {len(errores)}")

    for e in errores:
        print(f"ERROR: {e['categoria']} · {e['nombre']} -> {e['error']}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
