# Guía de Expresiones Regulares para el Sistema de Búsqueda Darwin

## 📋 Introducción

Esta guía especifica la nomenclatura y sintaxis correcta para utilizar expresiones regulares en la herramienta `regex_search.py` del sistema de consulta Darwin.

## 🔧 Arquitectura del Sistema

La herramienta de búsqueda regex utiliza un **sistema híbrido**:

1. **OpenSearch** (motor de búsqueda) - Usa sintaxis **Lucene regexp**
2. **Python** (procesamiento local) - Usa sintaxis **Python regex estándar**

## 📝 Tipos de Patrones Soportados

### 1. **Patrones Simples** (Recomendado)
**Detección automática**: Solo caracteres alfanuméricos y espacios
**Motor utilizado**: OpenSearch Wildcard Query

```bash
# ✅ FUNCIONA PERFECTAMENTE
python3 src/regex_search.py "NNSS"
python3 src/regex_search.py "Darwin"
python3 src/regex_search.py "4087"
```

### 2. **Patrones Complejos** (Limitaciones)
**Detección automática**: Contiene caracteres especiales regex
**Motor utilizado**: OpenSearch Regexp Query + Python regex

```bash
# ✅ FUNCIONA (emails)
python3 src/regex_search.py "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

# ❌ PROBLEMÁTICO (guiones)
python3 src/regex_search.py "DAR-[0-9]+"
python3 src/regex_search.py "NU_\d{2}"
```

## 🎯 Sintaxis Recomendada

### ✅ Patrones que SÍ Funcionan Bien

#### **Caracteres alfanuméricos**
```bash
python3 src/regex_search.py "[A-Z]+"           # Letras mayúsculas
python3 src/regex_search.py "[0-9]+"           # Números
python3 src/regex_search.py "[a-zA-Z0-9]+"     # Alfanuméricos
```

#### **Emails**
```bash
python3 src/regex_search.py "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
```

#### **Números con formato**
```bash
python3 src/regex_search.py "[0-9]{4}"         # Exactamente 4 dígitos
python3 src/regex_search.py "[0-9]{2,6}"       # Entre 2 y 6 dígitos
```

#### **Fechas**
```bash
python3 src/regex_search.py "[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}"  # DD/MM/YYYY
```

#### **IPs**
```bash
python3 src/regex_search.py "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"
```

### ❌ Patrones Problemáticos

#### **Guiones y guiones bajos**
```bash
# ❌ NO FUNCIONA BIEN
python3 src/regex_search.py "DAR-[0-9]+"
python3 src/regex_search.py "NU_\d{2}"

# ✅ ALTERNATIVA: Usar búsqueda léxica
python3 src/lexical_search.py "DAR-4087"
python3 src/lexical_search.py "NU_17"
```

#### **Metacaracteres complejos**
```bash
# ❌ PROBLEMÁTICO
python3 src/regex_search.py "\w+\-\d+"
python3 src/regex_search.py "\b[A-Z]{2,4}[-_]?\d{3,6}\b"
```

## 🔍 Alternativas Recomendadas por Tipo de Búsqueda

### **Para Patrones Específicos Conocidos**
```bash
# ✅ MEJOR OPCIÓN: Búsqueda léxica
python3 src/lexical_search.py "DAR-4087"
python3 src/lexical_search.py "NU_17"
python3 src/lexical_search.py "NNSS"
```

### **Para Conceptos y Significados**
```bash
# ✅ MEJOR OPCIÓN: Búsqueda semántica
python3 src/semantic_search.py "DAR 4087" --min-score 0.3
python3 src/semantic_search.py "módulos Darwin" --min-score 0.3
```

### **Para Patrones de Formato Simple**
```bash
# ✅ USAR: Regex con patrones simples
python3 src/regex_search.py "[0-9]+"
python3 src/regex_search.py "[A-Z]+"
python3 src/regex_search.py "DAR"  # Solo la parte alfabética
```

## 📚 Ejemplos Prácticos por Caso de Uso

### **Buscar Códigos de Proyecto**
```bash
# Para DAR-4087, NU_17, etc.
# ✅ RECOMENDADO
python3 src/lexical_search.py "DAR-4087"
python3 src/semantic_search.py "DAR 4087"

# ⚠️ ALTERNATIVA (solo parte numérica)
python3 src/regex_search.py "4087"
```

### **Buscar Emails**
```bash
# ✅ FUNCIONA
python3 src/regex_search.py "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
```

### **Buscar Números de Versión**
```bash
# ✅ FUNCIONA
python3 src/regex_search.py "[0-9]+\.[0-9]+"
python3 src/regex_search.py "v[0-9]+\.[0-9]+"
```

### **Buscar Fechas**
```bash
# ✅ FUNCIONA
python3 src/regex_search.py "[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}"
```

### **Buscar Códigos Postales Españoles**
```bash
# ✅ FUNCIONA
python3 src/regex_search.py "[0-5][0-9]{4}"
```

## ⚙️ Parámetros Adicionales

### **Sensibilidad a Mayúsculas**
```bash
python3 src/regex_search.py "darwin" --case-sensitive
```

### **Filtrar por Tipo de Archivo**
```bash
python3 src/regex_search.py "[0-9]+" --file-types docx pdf
```

### **Controlar Contexto**
```bash
python3 src/regex_search.py "[0-9]+" --context-lines 5 --max-matches-per-file 10
```

### **Formato de Salida**
```bash
python3 src/regex_search.py "[0-9]+" --output json
python3 src/regex_search.py "[0-9]+" --output pretty
```

## 🚨 Limitaciones Importantes

### **Caracteres Problemáticos**
- **Guión** (`-`): Problemático en patrones complejos
- **Guión bajo** (`_`): Problemático con `\d` y otros metacaracteres
- **Barra invertida** (`\`): Diferencias entre Lucene y Python

### **Metacaracteres con Limitaciones**
- `\d` → Usar `[0-9]` en su lugar
- `\w` → Usar `[a-zA-Z0-9]` en su lugar
- `\s` → Usar ` ` (espacio literal) en su lugar

## 💡 Mejores Prácticas

### **1. Elegir la Herramienta Correcta**
- **Patrones exactos conocidos** → `lexical_search.py`
- **Conceptos y significados** → `semantic_search.py`
- **Patrones de formato simples** → `regex_search.py`

### **2. Simplificar Patrones**
```bash
# ❌ Complejo
python3 src/regex_search.py "\b[A-Z]{2,4}[-_]?\d{3,6}\b"

# ✅ Simple
python3 src/regex_search.py "[A-Z]+"
python3 src/regex_search.py "[0-9]+"
```

### **3. Usar Caracteres Literales**
```bash
# ✅ Preferir
python3 src/regex_search.py "[0-9]"

# ⚠️ Evitar
python3 src/regex_search.py "\d"
```

### **4. Probar Incrementalmente**
```bash
# 1. Probar partes por separado
python3 src/regex_search.py "DAR"
python3 src/regex_search.py "4087"

# 2. Si funciona, intentar combinado
python3 src/lexical_search.py "DAR-4087"
```

## 🔧 Solución de Problemas

### **Si no encuentra resultados:**
1. Probar con búsqueda léxica: `lexical_search.py`
2. Probar con búsqueda semántica: `semantic_search.py`
3. Simplificar el patrón regex
4. Buscar partes del patrón por separado

### **Si encuentra resultados pero no muestra contenido:**
- El sistema ahora maneja automáticamente las diferencias entre OpenSearch y Python
- Debería mostrar el contenido encontrado por OpenSearch

## 📞 Ejemplos de Comandos Completos

```bash
# Buscar emails con contexto
python3 src/regex_search.py "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" --context-lines 3 --output pretty

# Buscar números en documentos Word
python3 src/regex_search.py "[0-9]{4}" --file-types docx --max-matches-per-file 20

# Buscar códigos específicos (recomendado usar léxica)
python3 src/lexical_search.py "DAR-4087"

# Buscar conceptos relacionados
python3 src/semantic_search.py "códigos DAR proyecto" --min-score 0.3
```

---

**Nota**: Esta guía se basa en las limitaciones identificadas del sistema híbrido OpenSearch + Python. Para patrones complejos con guiones o guiones bajos, se recomienda usar las herramientas de búsqueda léxica o semántica.
