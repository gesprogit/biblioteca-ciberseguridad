# -*- coding: utf-8 -*-
"""Scraper de FAQs de la AEPD.
Extrae automáticamente todas las categorías, preguntas y respuestas completas."""

import json
import re
import time
import random
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
SALIDA = DATA / "aepd_contenido.json"

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}


def extraer_aepd():
    print("🔍 Iniciando extracción de FAQs de la AEPD...")
    DATA.mkdir(exist_ok=True)
    
    url_base = "https://www.aepd.es/preguntas-frecuentes"
    
    try:
        response = requests.get(url_base, headers=UA, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"❌ Error al obtener página principal: {e}")
        return
    
    categorias_data = []
    
    # 1. Obtener todas las categorías
    enlaces_categorias = soup.find_all("a", href=re.compile(r"/preguntas-frecuentes/\d+-"))
    print(f"📂 Encontradas {len(enlaces_categorias)} categorías")
    
    for idx_cat, cat in enumerate(enlaces_categorias, 1):
        nombre_cat = cat.get_text(strip=True)
        href_cat = cat.get("href", "")
        if not href_cat:
            continue
        
        url_cat = f"https://www.aepd.es{href_cat}" if href_cat.startswith("/") else href_cat
        print(f"\n[{idx_cat}/{len(enlaces_categorias)}] 📂 {nombre_cat}")
        
        try:
            time.sleep(random.uniform(1.0, 2.0))
            response_cat = requests.get(url_cat, headers=UA, timeout=30)
            response_cat.raise_for_status()
            soup_cat = BeautifulSoup(response_cat.text, "html.parser")
            
            faqs_categoria = []
            enlaces_faqs = soup_cat.find_all("a", href=re.compile(r"/FAQ-"))
            
            for idx_faq, enlace_faq in enumerate(enlaces_faqs, 1):
                pregunta = enlace_faq.get_text(strip=True)
                href_faq = enlace_faq.get("href", "")
                if not pregunta or not href_faq:
                    continue
                
                url_faq = f"https://www.aepd.es{href_faq}" if href_faq.startswith("/") else href_faq
                
                # 2. Obtener respuesta completa
                try:
                    time.sleep(random.uniform(0.5, 1.5))
                    res_faq = requests.get(url_faq, headers=UA, timeout=15)
                    res_faq.raise_for_status()
                    soup_faq = BeautifulSoup(res_faq.text, "html.parser")
                    
                    # Buscar el contenido de la respuesta
                    contenido = (
                        soup_faq.find("div", class_=re.compile(r"content|field-body|node-body|respuesta")) or
                        soup_faq.find("main") or
                        soup_faq.find("article")
                    )
                    
                    if contenido:
                        parrafos = contenido.find_all("p")
                        respuesta = "\n\n".join([
                            p.get_text(strip=True) 
                            for p in parrafos 
                            if len(p.get_text(strip=True)) > 20
                        ])
                        if len(respuesta) < 50:
                            respuesta = contenido.get_text(strip=True)
                    else:
                        respuesta = "Consulta la respuesta completa en la fuente oficial."
                    
                    faqs_categoria.append({
                        "pregunta": pregunta,
                        "respuesta": respuesta,
                        "fuente": url_faq
                    })
                    
                    if idx_faq % 10 == 0:
                        print(f"   ⏱️ {idx_faq}/{len(enlaces_faqs)} FAQs procesadas...")
                        
                except Exception as e:
                    print(f"   ⚠️ Error en FAQ: {str(e)[:50]}")
                    continue
            
            categorias_data.append({
                "id": f"cat-{idx_cat:02d}",
                "titulo": nombre_cat,
                "faqs": faqs_categoria
            })
            print(f"   ✅ {len(faqs_categoria)} FAQs extraídas")
            
        except Exception as e:
            print(f"   ❌ Error en categoría: {str(e)[:80]}")
            continue
    
    # Guardar resultado
    resultado = {
        "ultima_actualizacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "total_categorias": len(categorias_data),
        "total_faqs": sum(len(c["faqs"]) for c in categorias_data),
        "categorias": categorias_data
    }
    
    SALIDA.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    print(f"\n✅ Extracción AEPD completada:")
    print(f"   📊 {resultado['total_categorias']} categorías")
    print(f"   📝 {resultado['total_faqs']} FAQs totales")
    print(f"   💾 Guardado en: {SALIDA}")


if __name__ == "__main__":
    extraer_aepd()
