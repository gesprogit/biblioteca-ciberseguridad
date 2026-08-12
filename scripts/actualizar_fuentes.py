# -*- coding: utf-8 -*-
"""Biblioteca de Conceptos · app de mantenimiento v2.
Modo vigilar  : python scripts/actualizar_fuentes.py            -> huellas + informe
Modo regenerar: python scripts/actualizar_fuentes.py regenerar  -> reescribe bloques <!--GEN--> de index.html"""
import hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "fuentes.json"
DATA = RAIZ / "data"
ESTADO = DATA / "estado_fuentes.json"
INFORME = DATA / "informe_fuentes.md"
HTML = RAIZ / "index.html"
UA = {"User-Agent": "biblioteca-conceptos-monitor/2.0"}

def norm(t): return re.sub(r"\s+", " ", t or "").strip().lower()
def huella(t): return hashlib.sha256(t.encode("utf-8")).hexdigest()

def extraer(f):
    r = requests.get(f["url"], headers=UA, timeout=60)
    r.raise_for_status()
    sopa = BeautifulSoup(r.text, "html.parser")
    for tag in sopa(["script", "style", "noscript"]): tag.decompose()
    nodo = sopa.select_one(f.get("selector", "body")) or sopa.body
    return norm(nodo.get_text(" "))

def vigilar():
    cfg = json.loads(FUENTES.read_text(encoding="utf-8"))
    DATA.mkdir(exist_ok=True)
    previo = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}
    nuevo, cambios = {}, []
    lineas = ["# Informe de vigilancia de fuentes", "",
              f"_Generado: {datetime.now(timezone.utc).isoformat()}_", ""]
    for f in cfg["fuentes"]:
        try:
            texto = extraer(f); h = huella(texto)
            nuevo[f["id"]] = {"url": f["url"], "huella": h, "chars": len(texto),
                              "estado": "OK", "fecha": datetime.now(timezone.utc).isoformat()}
            if previo.get(f["id"], {}).get("huella") not in (None, h):
                cambios.append(f["nombre"])
                lineas.append(f"- 🔄 CAMBIO · {f['nombre']} ({f['url']})")
        except Exception as e:
            nuevo[f["id"]] = {"url": f["url"], "estado": "ERROR", "error": str(e),
                              "fecha": datetime.now(timezone.utc).isoformat()}
            lineas.append(f"- ❌ ERROR · {f['nombre']}: {e}")
    if not cambios:
        lineas.append("- ✅ Sin cambios de contenido desde la última revisión.")
    ESTADO.write_text(json.dumps(nuevo, ensure_ascii=False, indent=2), encoding="utf-8")
    INFORME.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("Vigilancia OK · cambios:", cambios or "ninguno")
    return bool(cambios)

def regenerar():
    """Sincroniza los bloques <!--GEN:fecha:ID--> de index.html con el estado real."""
    if not HTML.exists():
        print("index.html no existe; nada que regenerar."); return
    estado = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}
    cfg = json.loads(FUENTES.read_text(encoding="utf-8"))
    nombre_por_id = {f["id"]: f["nombre"] for f in cfg["fuentes"]}
    html = HTML.read_text(encoding="utf-8")
    def repl(m):
        fid = m.group(1)
        e = estado.get(fid, {})
        fecha = (e.get("fecha") or "")[:10] or "s/e"
        txt = f"{nombre_por_id.get(fid, fid)} · revisado {fecha} · {e.get('estado','—')}"
        return f"<!--GEN:fecha:{fid}-->{txt}<!--/GEN-->"
    html2, n = re.subn(r"<!--GEN:fecha:([\w-]+)-->(.*?)<!--/GEN-->", repl, html, flags=re.S)
    HTML.write_text(html2, encoding="utf-8")
    print(f"Regeneración OK · {n} bloques sincronizados")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "regenerar":
        vigilar(); regenerar()
    else:
        vigilar()
