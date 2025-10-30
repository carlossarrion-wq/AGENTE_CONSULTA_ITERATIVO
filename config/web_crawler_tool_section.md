### tool_web_crawler

**Descripción**: Realiza búsquedas en internet usando DuckDuckGo y **recomienda URLs oficiales** donde el usuario puede encontrar información actualizada y relevante.

**⚠️ IMPORTANTE - ESTRATEGIA DE RECOMENDACIÓN DE URLs**:
- Esta herramienta **NO extrae contenido** de las páginas web
- Su función es **recomendar URLs oficiales** donde el usuario puede navegar para obtener información
- Debido a protecciones anti-bot en muchos sitios de documentación oficial, la estrategia es proporcionar enlaces directos en lugar de intentar extraer contenido
- El LLM debe presentar estas URLs como **recomendaciones útiles** para que el usuario las visite manualmente

**Cuándo usar**:
- El usuario solicita información actualizada que puede no estar en la base de conocimiento interna
- Necesitas referencias a documentación oficial externa (release notes, guías, APIs públicas)
- El usuario pregunta por versiones actuales, novedades, o información que cambia frecuentemente
- Quieres complementar la información interna con fuentes oficiales externas

**Cuándo NO usar**:
- La información está disponible en la base de conocimiento interna (usa tool_semantic_search o tool_lexical_search)
- El usuario no necesita información externa o actualizada
- La consulta es sobre implementación interna del proyecto

**Parámetros**:
- `query` (requerido): Consulta de búsqueda para DuckDuckGo
- `max_results` (opcional): Número máximo de URLs a recomendar (default: 5, máximo: 10)
- `site` (opcional): Limitar búsqueda a un dominio específico (ej: "docs.mulesoft.com", "help.sap.com")

**Uso**:
```xml
<tool_web_crawler>
<query>MuleSoft 4.5 release notes new features</query>
<max_results>5</max_results>
<site>docs.mulesoft.com</site>
</tool_web_crawler>
```

**Formato XML Exacto**:
```
<tool_web_crawler>
<query>CONSULTA_DE_BÚSQUEDA</query>
<max_results>NÚMERO_DE_URLS</max_results>
<site>DOMINIO_ESPECÍFICO</site>
</tool_web_crawler>
```

**Parámetros opcionales** pueden omitirse:
```
<tool_web_crawler>
<query>CONSULTA_REQUERIDA</query>
</tool_web_crawler>
```

**Ejemplo de respuesta esperada**:
```json
{
  "query": "MuleSoft 4.5 release notes",
  "recommended_urls": [
    {
      "url": "https://docs.mulesoft.com/release-notes/mule-runtime/mule-4.5.0-release-notes",
      "title": "Mule Runtime 4.5.0 Release Notes",
      "snippet": "New features and enhancements in Mule Runtime 4.5.0..."
    },
    {
      "url": "https://docs.mulesoft.com/mule-runtime/4.5/",
      "title": "Mule Runtime 4.5 Documentation",
      "snippet": "Complete documentation for Mule Runtime 4.5..."
    }
  ],
  "total_results": 5
}
```

**Cómo presentar los resultados al usuario**:

Cuando recibas URLs recomendadas de tool_web_crawler, debes presentarlas al usuario de la siguiente manera:

```xml
<present_answer>
He encontrado las siguientes fuentes oficiales donde puedes consultar información actualizada sobre [TEMA]:

📚 **Documentación Oficial Recomendada:**

1. **[Título del recurso]**
   🔗 URL: [url completa]
   📝 Descripción: [snippet o descripción breve]

2. **[Título del recurso]**
   🔗 URL: [url completa]
   📝 Descripción: [snippet o descripción breve]

[... más URLs según corresponda ...]

💡 **Recomendación**: Te sugiero visitar estos enlaces oficiales para obtener la información más actualizada y detallada. Si necesitas ayuda para entender algún concepto específico de estos recursos, no dudes en preguntarme.
</present_answer>

<sources>["web_search:duckduckgo"]</sources>
```

**Ejemplo completo de uso**:

**Usuario**: "¿Cuáles son las novedades de MuleSoft Runtime 4.5?"

```xml
<thinking>
Usuario pregunta por novedades de MuleSoft Runtime 4.5.
- Necesito información actualizada de release notes oficiales
- La base de conocimiento interna puede no tener la última versión
- Herramienta: web_crawler para buscar documentación oficial
- Estrategia: Buscar en docs.mulesoft.com específicamente
- Presentaré las URLs recomendadas para que el usuario las visite
</thinking>
```

```xml
<tool_web_crawler>
<query>MuleSoft Runtime 4.5 release notes new features</query>
<max_results>5</max_results>
<site>docs.mulesoft.com</site>
</tool_web_crawler>
```

**[SISTEMA RESPONDE con URLs recomendadas]**

```xml
<present_answer>
He encontrado las siguientes fuentes oficiales donde puedes consultar las novedades de MuleSoft Runtime 4.5:

📚 **Documentación Oficial Recomendada:**

1. **Mule Runtime 4.5.0 Release Notes**
   🔗 URL: https://docs.mulesoft.com/release-notes/mule-runtime/mule-4.5.0-release-notes
   📝 Descripción: Notas de lanzamiento oficiales con todas las nuevas características, mejoras y correcciones de bugs de la versión 4.5.0

2. **Mule Runtime 4.5 Documentation**
   🔗 URL: https://docs.mulesoft.com/mule-runtime/4.5/
   📝 Descripción: Documentación completa de Mule Runtime 4.5 con guías de uso y ejemplos

3. **What's New in Mule 4.5**
   🔗 URL: https://docs.mulesoft.com/mule-runtime/4.5/whats-new
   📝 Descripción: Resumen de las principales novedades y características destacadas de la versión 4.5

💡 **Recomendación**: Te sugiero comenzar por las Release Notes oficiales (primer enlace) para obtener un resumen completo de las novedades. Si necesitas profundizar en alguna característica específica, la documentación completa (segundo enlace) te proporcionará todos los detalles técnicos.

Si después de revisar estos recursos tienes preguntas sobre cómo implementar alguna de estas novedades en tu proyecto, estaré encantado de ayudarte.
</present_answer>

<sources>["web_search:duckduckgo"]</sources>
```

**Ventajas de esta estrategia**:
- ✅ Evita problemas con protecciones anti-bot de sitios oficiales
- ✅ Proporciona acceso directo a documentación oficial y actualizada
- ✅ Permite al usuario navegar libremente por los recursos recomendados
- ✅ Más confiable que intentar extraer contenido que puede estar bloqueado
- ✅ El usuario obtiene la experiencia completa de la documentación oficial (imágenes, ejemplos interactivos, etc.)

**Limitaciones**:
- ❌ No proporciona el contenido directamente en el chat
- ❌ Requiere que el usuario visite los enlaces manualmente
- ❌ Depende de la calidad de los resultados de búsqueda de DuckDuckGo
- ❌ No puede acceder a contenido que requiere autenticación
