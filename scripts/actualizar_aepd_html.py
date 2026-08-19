# -*- coding: utf-8 -*-
"""Actualiza index.html añadiendo SOLO las nuevas FAQs de la AEPD.
Mantiene intacta toda la estructura existente del HTML."""

import json
import re
import sys
import time
import random
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

RAIZ = Path(__file__).resolve().parent.parent
HTML = RAIZ / "index.html"
DATA = RAIZ / "data"
FAqs_JSON = DATA / "aepd_faqs_extraidas.json"

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}


def extraer_faqs_aepd():
    """Extrae todas las FAQs de la AEPD organizadas por sección."""
    print(" Extrayendo FAQs de la AEPD...")
    
    url_base = "https://www.aepd.es/preguntas-frecuentes"
    
    try:
        response = requests.get(url_base, headers=UA, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"❌ Error al obtener página principal: {e}")
        return {}
    
    secciones = {}
    total_faqs = 0
    
    # Obtener todas las categorías
    enlaces_categorias = soup.find_all("a", href=re.compile(r"/preguntas-frecuentes/\d+-"))
    print(f" Encontradas {len(enlaces_categorias)} categorías")
    
    for idx_cat, cat in enumerate(enlaces_categorias, 1):
        nombre_cat = cat.get_text(strip=True)
        href_cat = cat.get("href", "")
        if not href_cat:
            continue
        
        url_cat = f"https://www.aepd.es{href_cat}" if href_cat.startswith("/") else href_cat
        
        try:
            time.sleep(random.uniform(1.0, 2.0))
            response_cat = requests.get(url_cat, headers=UA, timeout=30)
            soup_cat = BeautifulSoup(response_cat.text, "html.parser")
            
            faqs = []
            enlaces_faqs = soup_cat.find_all("a", href=re.compile(r"/FAQ-"))
            
            for idx_faq, enlace_faq in enumerate(enlaces_faqs, 1):
                pregunta = enlace_faq.get_text(strip=True)
                href_faq = enlace_faq.get("href", "")
                if not pregunta or not href_faq:
                    continue
                
                url_faq = f"https://www.aepd.es{href_faq}" if href_faq.startswith("/") else href_faq
                
                # Extraer respuesta
                try:
                    time.sleep(random.uniform(0.5, 1.5))
                    res_faq = requests.get(url_faq, headers=UA, timeout=15)
                    soup_faq = BeautifulSoup(res_faq.text, "html.parser")
                    
                    contenido = (
                        soup_faq.find("div", class_=re.compile(r"content|field-body|node-body")) or
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
                    
                    faqs.append({
                        "pregunta": pregunta,
                        "respuesta": respuesta,
                        "fuente": url_faq
                    })
                    
                    if idx_faq % 10 == 0:
                        print(f"   ️ {idx_faq}/{len(enlaces_faqs)}...")
                        
                except Exception as e:
                    print(f"   ⚠️ Error en FAQ: {str(e)[:50]}")
                    continue
            
            secciones[nombre_cat] = faqs
            total_faqs += len(faqs)
            print(f"   ✅ {nombre_cat}: {len(faqs)} FAQs")
            
        except Exception as e:
            print(f"   ❌ Error en categoría: {str(e)[:80]}")
            continue
    
    print(f"\n✅ Total: {total_faqs} FAQs extraídas")
    return secciones


def actualizar_html(nuevas_faqs):
    """Añade SOLO las nuevas FAQs al HTML existente."""
    if not HTML.exists():
        print("❌ index.html no existe")
        return False
    
    html_content = HTML.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_content, "html.parser")
    
    total_añadidas = 0
    total_omiti das = 0
    
    for nombre_seccion, faqs in nuevas_faqs.items():
        # Buscar la sección en el HTML por el número y título
        # Las secciones tienen formato: "00\nConceptos básicos..."
        seccion_encontrada = None
        
        # Buscar todas las secciones con clase "seccion"
        for seccion in soup.find_all("div", class_="seccion"):
            header = seccion.find("div", class_="seccion-header")
            if header:
                h2 = header.find("h2")
                if h2 and nombre_seccion in h2.get_text():
                    seccion_encontrada = seccion
                    break
        
        if not seccion_encontrada:
            print(f"   ⚠️ No encontrada: {nombre_seccion}")
            continue
        
        # Buscar el contenedor de FAQs
        content = seccion_encontrada.find("div", class_="seccion-content")
        if not content:
            continue
        
        # Obtener preguntas existentes
        preguntas_existentes = set()
        for faq_div in content.find_all("div", class_="faq"):
            pregunta_tag = faq_div.find("div", class_="faq-pregunta")
            if pregunta_tag:
                # Extraer solo el texto de la pregunta (sin el "+")
                texto = pregunta_tag.get_text(strip=True).replace("+", "").strip()
                preguntas_existentes.add(texto)
        
        # Añadir solo las nuevas FAQs
        for faq in faqs:
            if faq["pregunta"] not in preguntas_existentes:
                # Crear nuevo elemento FAQ con la misma estructura
                nuevo_faq = soup.new_tag("div", **{"class": "faq"})
                
                pregunta_tag = soup.new_tag("div", **{"class": "faq-pregunta"})
                pregunta_tag.string = faq["pregunta"]
                mas_tag = soup.new_tag("span")
                mas_tag.string = "+"
                pregunta_tag.append(mas_tag)
                
                respuesta_tag = soup.new_tag("div", **{"class": "faq-respuesta"})
                respuesta_tag.string = faq["respuesta"]
                
                # Añadir enlace a fuente
                fuente_tag = soup.new_tag("div", style="margin-top:.5rem;padding-top:.5rem;border-top:1px solid #f3f4f6")
                enlace_tag = soup.new_tag("a", href=faq["fuente"], target="_blank", style="font-size:.75rem;color:#2563eb;text-decoration:none")
                enlace_tag.string = "Ver en web de la AEPD ↗"
                fuente_tag.append(enlace_tag)
                respuesta_tag.append(fuente_tag)
                
                nuevo_faq.append(pregunta_tag)
                nuevo_faq.append(respuesta_tag)
                content.append(nuevo_faq)
                
                total_añadidas += 1
                print(f"    ➕ Añadida: {faq['pregunta'][:60]}...")
            else:
                total_omitidas += 1
    
    if total_añadidas > 0:
        # Actualizar fecha en el footer
        footer = soup.find("footer")
        if footer:
            small = footer.find("small")
            if small:
                small.string = f"Actualizado: {datetime.now().strftime('%B %Y')}"
        
        # Guardar HTML formateado
        HTML.write_text(str(soup), encoding="utf-8")
        print(f"\n✅ {total_añadidas} FAQs nuevas añadidas")
        print(f"   {total_omitidas} FAQs ya existentes (omitidas)")
        return True
    else:
        print(f"\n✅ No hay FAQs nuevas ({total_omitidas} verificadas)")
        return False


def main():
    DATA.mkdir(exist_ok=True)
    
    # Extraer FAQs actuales de la AEPD
    faqs_actuales = extraer_faqs_aepd()
    
    # Guardar JSON de respaldo
    FAqs_JSON.write_text(
        json.dumps(faqs_actuales, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    # Actualizar HTML solo si hay FAQs
    if faqs_actuales:
        actualizar_html(faqs_actuales)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
