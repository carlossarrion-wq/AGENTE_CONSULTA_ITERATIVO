# Herramienta de Web Crawler - Diseño e Implementación

## Objetivo

Desarrollar una herramienta `tool_web_crawler` que permita al agente buscar información en internet cuando la base de conocimiento interna no sea suficiente.

## Casos de Uso

1. **Parches de MuleSoft**: Buscar parches recientes para problemas identificados
2. **Documentación actualizada**: Consultar documentación oficial más reciente
3. **Errores conocidos**: Buscar soluciones a errores específicos
4. **Versiones y releases**: Información sobre nuevas versiones
5. **Best practices**: Prácticas recomendadas actualizadas

---

## 📚 Librerías Python Disponibles (Open Source)

### 1. **Beautiful Soup 4** ⭐⭐⭐⭐⭐
**Mejor para**: Parsing de HTML/XML

```python
from bs4 import BeautifulSoup
import requests

# Ejemplo
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')
text = soup.get_text()
```

**Ventajas:**
- ✅ Muy popular y bien documentada
- ✅ Fácil de usar
- ✅ Excelente para extraer contenido estructurado
- ✅ Maneja HTML mal formado

**Desventajas:**
- ❌ No ejecuta JavaScript
- ❌ Requiere requests para descargar páginas

**Instalación:**
```bash
pip3 install beautifulsoup4 requests
```

---

### 2. **Scrapy** ⭐⭐⭐⭐
**Mejor para**: Web scraping a gran escala

```python
import scrapy

class MulesoftSpider(scrapy.Spider):
    name = 'mulesoft'
    start_urls = ['https://docs.mulesoft.com']
    
    def parse(self, response):
        for article in response.css('article'):
            yield {
                'title': article.css('h1::text').get(),
                'content': article.css('p::text').getall()
            }
```

**Ventajas:**
- ✅ Framework completo de scraping
- ✅ Manejo automático de robots.txt
- ✅ Soporte para crawling recursivo
- ✅ Muy eficiente

**Desventajas:**
- ❌ Más complejo de configurar
- ❌ Overkill para búsquedas simples
- ❌ No ejecuta JavaScript

**Instalación:**
```bash
pip3 install scrapy
```

---

### 3. **Selenium** ⭐⭐⭐⭐⭐
**Mejor para**: Sitios con JavaScript dinámico

```python
from selenium import webdriver
from selenium.webdriver.common.by import By

# Ejemplo
driver = webdriver.Chrome()
driver.get(url)
content = driver.find_element(By.TAG_NAME, 'body').text
driver.quit()
```

**Ventajas:**
- ✅ Ejecuta JavaScript
- ✅ Simula navegador real
- ✅ Puede interactuar con elementos (clicks, forms)
- ✅ Ideal para SPAs (Single Page Applications)

**Desventajas:**
- ❌ Más lento (navegador completo)
- ❌ Requiere driver del navegador
- ❌ Mayor consumo de recursos

**Instalación:**
```bash
pip3 install selenium webdriver-manager
```

---

### 4. **Playwright** ⭐⭐⭐⭐⭐
**Mejor para**: Automatización moderna de navegadores

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(url)
    content = page.content()
    browser.close()
```

**Ventajas:**
- ✅ Más rápido que Selenium
- ✅ Soporta múltiples navegadores
- ✅ API moderna y limpia
- ✅ Ejecuta JavaScript

**Desventajas:**
- ❌ Requiere instalación de navegadores
- ❌ Mayor complejidad

**Instalación:**
```bash
pip3 install playwright
playwright install chromium
```

---

### 5. **Requests-HTML** ⭐⭐⭐⭐
**Mejor para**: Balance entre simplicidad y JavaScript

```python
from requests_html import HTMLSession

session = HTMLSession()
r = session.get(url)
r.html.render()  # Ejecuta JavaScript
text = r.html.text
```

**Ventajas:**
- ✅ Sintaxis simple como requests
- ✅ Puede ejecutar JavaScript
- ✅ Parsing integrado
- ✅ Fácil de usar

**Desventajas:**
- ❌ Requiere Chromium instalado
- ❌ Menos control que Selenium/Playwright

**Instalación:**
```bash
pip3 install requests-html
```

---

### 6. **Trafilatura** ⭐⭐⭐⭐⭐
**Mejor para**: Extracción de contenido principal

```python
import trafilatura

downloaded = trafilatura.fetch_url(url)
text = trafilatura.extract(downloaded)
```

**Ventajas:**
- ✅ Extrae solo contenido relevante (sin ads, menús, etc.)
- ✅ Muy rápido
- ✅ Detecta idioma automáticamente
- ✅ Ideal para artículos y documentación

**Desventajas:**
- ❌ No ejecuta JavaScript
- ❌ Menos control sobre el parsing

**Instalación:**
```bash
pip3 install trafilatura
```

---

### 7. **DuckDuckGo Search** ⭐⭐⭐⭐⭐
**Mejor para**: Búsquedas en internet sin API key

```python
from duckduckgo_search import DDGS

results = DDGS().text("mulesoft patch 4.5.0", max_results=5)
for r in results:
    print(r['title'], r['href'], r['body'])
```

**Ventajas:**
- ✅ No requiere API key
- ✅ Sin límites de rate
- ✅ Resultados de búsqueda instantáneos
- ✅ Muy fácil de usar

**Desventajas:**
- ❌ Solo búsquedas, no scraping
- ❌ Resultados limitados

**Instalación:**
```bash
pip3 install duckduckgo-search
```

---

### 8. **Newspaper3k** ⭐⭐⭐⭐
**Mejor para**: Extracción de artículos de noticias

```python
from newspaper import Article

article = Article(url)
article.download()
article.parse()
print(article.title)
print(article.text)
```

**Ventajas:**
- ✅ Especializado en artículos
- ✅ Extrae metadatos (autor, fecha, etc.)
- ✅ Limpia el contenido automáticamente

**Desventajas:**
- ❌ Limitado a artículos/noticias
- ❌ No ejecuta JavaScript

**Instalación:**
```bash
pip3 install newspaper3k
```

---

## 🎯 Recomendación para tu Caso

### **Estrategia Híbrida Recomendada**

```python
# 1. DuckDuckGo para búsqueda inicial
# 2. Trafilatura para extracción de contenido
# 3. Beautiful Soup como fallback
```

### Justificación

1. **DuckDuckGo Search**: 
   - Sin API key
   - Encuentra URLs relevantes rápidamente
   - Ideal para "buscar parches de mulesoft"

2. **Trafilatura**:
   - Extrae contenido limpio
   - Perfecto para documentación técnica
   - Muy rápido

3. **Beautiful Soup**:
   - Fallback si Trafilatura falla
   - Mayor control sobre parsing
   - Muy confiable

---

## 📋 Arquitectura de la Herramienta

```
tool_web_crawler
├── Fase 1: Búsqueda (DuckDuckGo)
│   └── Obtener URLs relevantes
│
├── Fase 2: Extracción (Trafilatura)
│   └── Extraer contenido de cada URL
│
├── Fase 3: Procesamiento
│   ├── Limpiar texto
│   ├── Resumir si es muy largo
│   └── Formatear para el LLM
│
└── Fase 4: Retorno
    └── Devolver contenido estructurado
```

---

## 🔧 Implementación Propuesta

### Estructura del Archivo

```python
# src/tools/tool_web_crawler.py

class WebCrawlerTool:
    """
    Herramienta para buscar información en internet
    """
    
    def __init__(self, max_results=3, max_content_length=2000):
        self.max_results = max_results
        self.max_content_length = max_content_length
    
    def search_and_extract(self, query: str) -> dict:
        """
        Busca en internet y extrae contenido relevante
        
        Args:
            query: Consulta de búsqueda
            
        Returns:
            dict con resultados estructurados
        """
        # 1. Buscar URLs
        urls = self._search_duckduckgo(query)
        
        # 2. Extraer contenido
        results = []
        for url in urls[:self.max_results]:
            content = self._extract_content(url)
            if content:
                results.append(content)
        
        # 3. Formatear resultados
        return self._format_results(results)
    
    def _search_duckduckgo(self, query: str) -> list:
        """Busca URLs usando DuckDuckGo"""
        from duckduckgo_search import DDGS
        
        results = DDGS().text(query, max_results=self.max_results)
        return [r['href'] for r in results]
    
    def _extract_content(self, url: str) -> dict:
        """Extrae contenido de una URL"""
        try:
            # Intentar con Trafilatura primero
            import trafilatura
            downloaded = trafilatura.fetch_url(url)
            text = trafilatura.extract(downloaded)
            
            if text:
                return {
                    'url': url,
                    'content': text[:self.max_content_length],
                    'method': 'trafilatura'
                }
        except:
            pass
        
        try:
            # Fallback a Beautiful Soup
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remover scripts y estilos
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            
            return {
                'url': url,
                'content': text[:self.max_content_length],
                'method': 'beautifulsoup'
            }
        except:
            return None
    
    def _format_results(self, results: list) -> dict:
        """Formatea resultados para el LLM"""
        formatted = {
            'success': len(results) > 0,
            'results_count': len(results),
            'sources': []
        }
        
        for i, result in enumerate(results, 1):
            formatted['sources'].append({
                'number': i,
                'url': result['url'],
                'content': result['content'],
                'extraction_method': result['method']
            })
        
        return formatted
```

---

## 📦 Dependencias Necesarias

```txt
# Añadir a requirements.txt
duckduckgo-search>=4.0.0
trafilatura>=1.6.0
beautifulsoup4>=4.12.0
requests>=2.31.0
lxml>=4.9.0
```

---

## 🔒 Consideraciones de Seguridad

1. **Rate Limiting**: Limitar número de requests por minuto
2. **Timeout**: Establecer timeout en requests (10s)
3. **User-Agent**: Usar user-agent apropiado
4. **Robots.txt**: Respetar robots.txt (opcional)
5. **Sanitización**: Limpiar contenido extraído
6. **Validación de URLs**: Verificar URLs antes de acceder

---

## 🎯 Integración con el Agente

### En tool_executor.py

```python
from tools.tool_web_crawler import WebCrawlerTool

class ToolType(Enum):
    SEMANTIC_SEARCH = "semantic_search"
    LEXICAL_SEARCH = "lexical_search"
    REGEX_SEARCH = "regex_search"
    GET_FILE_CONTENT = "get_file_content"
    WEB_CRAWLER = "web_crawler"  # NUEVO
```

### En system_prompt

```markdown
## web_crawler
Busca información en internet cuando la base de conocimiento interna no es suficiente.

**Cuándo usar:**
- Información sobre parches o versiones recientes
- Documentación actualizada no disponible internamente
- Soluciones a errores específicos
- Best practices actualizadas

**Parámetros:**
- query (requerido): Consulta de búsqueda específica

**Ejemplo:**
<use_tool>
<tool_name>web_crawler</tool_name>
<parameters>
{
  "query": "mulesoft runtime 4.5.0 patch security vulnerability"
}
</parameters>
</use_tool>

**IMPORTANTE:** Usa esta herramienta solo cuando:
1. La información no está en la base de conocimiento
2. Se necesita información muy reciente
3. El usuario pregunta explícitamente por información actualizada
```

---

## 📊 Ejemplo de Uso

### Input del Usuario
```
"¿Hay algún parche reciente de MuleSoft 4.5.0 que solucione problemas de seguridad?"
```

### Herramienta Ejecutada
```xml
<use_tool>
<tool_name>web_crawler</tool_name>
<parameters>
{
  "query": "mulesoft 4.5.0 security patch 2024"
}
</parameters>
</use_tool>
```

### Output de la Herramienta
```json
{
  "success": true,
  "results_count": 3,
  "sources": [
    {
      "number": 1,
      "url": "https://docs.mulesoft.com/release-notes/...",
      "content": "MuleSoft Runtime 4.5.0 Patch 2 addresses critical security vulnerabilities...",
      "extraction_method": "trafilatura"
    },
    {
      "number": 2,
      "url": "https://help.mulesoft.com/...",
      "content": "Security Advisory: CVE-2024-XXXX affects MuleSoft Runtime 4.5.0...",
      "extraction_method": "trafilatura"
    }
  ]
}
```

---

## 🚀 Plan de Implementación

### Fase 1: Implementación Básica (2-3 horas)
- [ ] Crear tool_web_crawler.py
- [ ] Implementar búsqueda con DuckDuckGo
- [ ] Implementar extracción con Trafilatura
- [ ] Añadir fallback con Beautiful Soup
- [ ] Testing básico

### Fase 2: Integración (1-2 horas)
- [ ] Añadir a ToolType enum
- [ ] Integrar en tool_executor.py
- [ ] Actualizar system_prompt
- [ ] Testing de integración

### Fase 3: Optimizaciones (1-2 horas)
- [ ] Añadir rate limiting
- [ ] Implementar caché de resultados
- [ ] Mejorar formateo de resultados
- [ ] Añadir métricas

### Fase 4: Documentación y Testing (1 hora)
- [ ] Documentar uso
- [ ] Crear ejemplos
- [ ] Testing end-to-end
- [ ] Actualizar README

---

## ✅ Conclusión

**Recomendación Final:**
- **DuckDuckGo Search**: Para búsquedas (sin API key)
- **Trafilatura**: Para extracción de contenido
- **Beautiful Soup**: Como fallback

Esta combinación proporciona:
- ✅ Sin costos (no requiere API keys)
- ✅ Rápido y eficiente
- ✅ Contenido limpio y relevante
- ✅ Fácil de mantener

¿Te gustaría que implemente esta herramienta ahora?
