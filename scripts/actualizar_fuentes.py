# -*- coding: utf-8 -*-
"""Monitor de fuentes oficiales de la biblioteca.
Descarga cada fuente, extrae su texto, calcula una huella (hash)
y la compara con la última guardada. Si algo cambia, queda
registrado en data/estado_fuentes.json y data/informe_fuentes.md."""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# 1) Fuentes oficiales que vigilamos (nombre -> URL)
FUENTES = {
    "RGPD": "http://data.europa.eu/eli/reg/2016/679/oj",
    "LOPDGDD": "https://www.boe.es/eli/es/lo/2018-12-05/3",
    "DORA": "http://data.europa.eu/eli/reg/2022/2554/oj",
    "NIS2": "http://data.europa.eu/eli/dir/2022/2555/oj",
    "CRA": "http://data.europa.eu/eli/reg/2024/2847/oj",
    "ENS (RD 311/2022)": "https://www.boe.es/eli/es/rd/2022-05-03/311",
    "AEPD FAQ": "https://www.aepd.es/preguntas-frecuentes",
    "CCN-CERT FAQ": "https://www.ccn-cert.cni.es/es/sobre-nosotros/faq.html",
    "TISAX (ENX)": "https://enx.com/en-US/TISAX/",
}

RUTA_DATOS = Path("data")
RUTA_ESTADO = RUTA_DATOS / "estado_fuentes.json"
RUTA_INFORME = RUTA_DATOS / "informe_fuentes.md"


def texto_limpio(html):
    sopa = BeautifulSoup(html, "html.parser")
    for tag in sopa(["script", "style", "noscript"]):
        tag.decompose()
    return re.sub(r"\s+", " ", sopa.get_text(" ", strip=True))


def huella(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def descargar(url):
    r = requests.get(url, headers={"User-Agent": "biblioteca-monitor/1.0"}, timeout=60)
    r.raise_for_status()
    return r.text


def main():
    RUTA_DATOS.mkdir(parents=True, exist_ok=True)

    anterior = {}
    if RUTA_ESTADO.exists():
        anterior = json.loads(RUTA_ESTADO.read_text(encoding="utf-8"))

    nuevo, cambios, errores = {}, [], []

    for nombre, url in FUENTES.items():
        try:
            texto = texto_limpio(descargar(url))
            h = huella(texto)
            nuevo[nombre] = {"url": url, "huella": h, "longitud_texto": len(texto),
                             "consultado": datetime.now(timezone.utc).isoformat(), "estado": "OK"}
            if anterior.get(nombre, {}).get("huella") and anterior[nombre]["huella"] != h:
                cambios.append(nombre)
                nuevo[nombre]["cambio_detectado"] = True
        except Exception as exc:
            errores.append(f"{nombre}: {exc}")
            nuevo[nombre] = {"url": url, "estado": "ERROR", "error": str(exc),
                             "consultado": datetime.now(timezone.utc).isoformat()}

    RUTA_ESTADO.write_text(json.dumps(nuevo, ensure_ascii=False, indent=2), encoding="utf-8")

    lineas = ["# Informe de estado de las fuentes", "",
              f"_Generado el {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_", ""]
    lineas.append("## ⚠️ Cambios detectados en: " + ", ".join(cambios) if cambios
                  else "## ✅ Sin cambios de contenido desde la última revisión")
    lineas.append("")
    for nombre, info in nuevo.items():
        if info.get("estado") == "OK":
            marca = "🔄 CAMBIO" if info.get("cambio_detectado") else "✔"
            lineas.append(f"- {marca} **{nombre}** — {info['longitud_texto']} caracteres")
        else:
            lineas.append(f"- ❌ **{nombre}** — error al descargar: {info.get('error')}")

    RUTA_INFORME.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("Revisión completada. Cambios:", cambios or "ninguno", "| Errores:", errores or "ninguno")


if __name__ == "__main__":
    main()
