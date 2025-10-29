# Sistema de Aprendizaje mediante Feedback - Soluciones Optimizadas

## Problema Identificado

**El usuario señala correctamente que:**
> "El problema es que en la estrategia de almacenar el feedback para luego generar ejemplos de respuestas valoradas positivamente en el few shot prompting, se incrementa significativamente el volumen del prompt de sistema, y tampoco puedes incluir todas las preguntas-respuestas que den información representativa al LLM"

## ✅ Soluciones Optimizadas

---

## 🎯 Estrategia 1: Resúmenes Comprimidos de Feedback (RECOMENDADA)

### Concepto
En lugar de incluir ejemplos completos, crear **resúmenes comprimidos** que capturen la esencia del conocimiento.

### Arquitectura

```
Feedback Positivo → Clustering → Resumen por Cluster → Prompt Compacto
     (1000s)           (10-20)        (200 tokens)       (2-3K tokens)
```

### Implementación

```python
class FeedbackCompressor:
    """Comprime feedback en resúmenes representativos"""
    
    def __init__(self, max_prompt_tokens=2000):
        self.max_prompt_tokens = max_prompt_tokens
        self.clusters = {}
    
    def compress_feedback(self, feedback_examples):
        """
        Agrupa feedback similar y crea resúmenes compactos
        
        Args:
            feedback_examples: Lista de ejemplos con feedback positivo
            
        Returns:
            String compacto con conocimiento destilado
        """
        # 1. Clustering semántico de queries similares
        clusters = self._cluster_similar_queries(feedback_examples)
        
        # 2. Para cada cluster, extraer patrones comunes
        compressed_knowledge = []
        
        for cluster_id, examples in clusters.items():
            # Identificar tema del cluster
            theme = self._identify_theme(examples)
            
            # Extraer patrones de respuestas exitosas
            patterns = self._extract_response_patterns(examples)
            
            # Crear resumen compacto
            summary = {
                'theme': theme,
                'key_points': patterns['key_points'][:3],  # Top 3
                'approach': patterns['common_approach'],
                'examples_count': len(examples)
            }
            
            compressed_knowledge.append(summary)
        
        # 3. Convertir a texto compacto
        return self._format_compressed_knowledge(compressed_knowledge)
    
    def _cluster_similar_queries(self, examples, n_clusters=10):
        """Agrupa queries similares usando embeddings"""
        from sklearn.cluster import KMeans
        
        # Obtener embeddings
        embeddings = [ex['embedding'] for ex in examples]
        
        # Clustering
        kmeans = KMeans(n_clusters=min(n_clusters, len(examples)))
        labels = kmeans.fit_predict(embeddings)
        
        # Agrupar por cluster
        clusters = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(examples[idx])
        
        return clusters
    
    def _extract_response_patterns(self, examples):
        """Extrae patrones comunes de respuestas exitosas"""
        # Usar LLM para extraer patrones
        examples_text = "\n\n".join([
            f"Q: {ex['query']}\nA: {ex['response']}"
            for ex in examples[:5]  # Solo top 5 del cluster
        ])
        
        extraction_prompt = f"""
Analiza estas respuestas exitosas y extrae:
1. Los 3 puntos clave más importantes
2. El enfoque común usado
3. Qué hace que estas respuestas sean buenas

Respuestas:
{examples_text}

Responde en formato JSON compacto.
"""
        
        # Llamar a LLM para extraer patrones
        patterns = self._call_llm_for_extraction(extraction_prompt)
        return patterns
    
    def _format_compressed_knowledge(self, compressed_knowledge):
        """Formatea conocimiento comprimido para el prompt"""
        
        formatted = "\n# CONOCIMIENTO DE FEEDBACK POSITIVO\n\n"
        
        for i, knowledge in enumerate(compressed_knowledge, 1):
            formatted += f"{i}. **{knowledge['theme']}** ({knowledge['examples_count']} ejemplos)\n"
            formatted += f"   Enfoque: {knowledge['approach']}\n"
            formatted += f"   Puntos clave:\n"
            for point in knowledge['key_points']:
                formatted += f"   - {point}\n"
            formatted += "\n"
        
        return formatted
```

### Ejemplo de Salida Comprimida

**Antes (3000+ tokens):**
```
Ejemplo 1:
Usuario: ¿Cómo crear un contrato en Darwin?
Respuesta: Para crear un contrato en Darwin, primero debes...
[500 tokens]

Ejemplo 2:
Usuario: ¿Cuál es el proceso para generar contratos?
Respuesta: El proceso de generación de contratos implica...
[500 tokens]

[... 5 ejemplos más ...]
```

**Después (300 tokens):**
```
# CONOCIMIENTO DE FEEDBACK POSITIVO

1. **Creación de Contratos** (15 ejemplos)
   Enfoque: Paso a paso con validaciones
   Puntos clave:
   - Siempre mencionar requisitos previos
   - Incluir capturas de pantalla o referencias
   - Advertir sobre errores comunes

2. **Consultas Técnicas** (12 ejemplos)
   Enfoque: Explicación técnica + ejemplo práctico
   Puntos clave:
   - Usar terminología correcta del sistema
   - Proporcionar código/configuración cuando aplique
   - Mencionar documentación relevante
```

### Ventajas
- ✅ **Reducción drástica de tokens**: 90% menos
- ✅ **Mantiene conocimiento esencial**: Patrones clave preservados
- ✅ **Escalable**: Puede procesar miles de ejemplos
- ✅ **Actualizable**: Fácil regenerar resúmenes

### Desventajas
- ⚠️ Requiere procesamiento periódico (batch)
- ⚠️ Pierde detalles específicos

---

## 🎯 Estrategia 2: Retrieval-Augmented Generation (RAG) con Feedback

### Concepto
No incluir ejemplos en el prompt. En su lugar, usar **RAG** para recuperar solo el conocimiento más relevante en tiempo real.

### Arquitectura

```
User Query → Embedding → Search Feedback DB → Top-3 Relevant → Inject in Prompt
                              ↓
                    (Vector Database)
                    - 1000s of examples
                    - Indexed by embedding
```

### Implementación

```python
class FeedbackRAG:
    """RAG system para feedback"""
    
    def __init__(self, opensearch_client):
        self.opensearch = opensearch_client
        self.feedback_index = "feedback_knowledge"
    
    def get_relevant_feedback(self, query, top_k=3, max_tokens=500):
        """
        Recupera feedback más relevante para la query
        
        Args:
            query: Query del usuario
            top_k: Número de ejemplos a recuperar
            max_tokens: Máximo de tokens a incluir
            
        Returns:
            String con feedback relevante comprimido
        """
        # 1. Buscar ejemplos similares en OpenSearch
        similar_examples = self._search_similar_feedback(query, top_k=top_k*2)
        
        # 2. Filtrar por calidad (rating, recency)
        filtered = self._filter_by_quality(similar_examples)
        
        # 3. Comprimir para caber en max_tokens
        compressed = self._compress_to_fit(filtered[:top_k], max_tokens)
        
        return compressed
    
    def _search_similar_feedback(self, query, top_k=6):
        """Busca feedback similar usando búsqueda semántica"""
        
        # Obtener embedding de la query
        query_embedding = self._get_embedding(query)
        
        # Buscar en OpenSearch
        search_body = {
            "size": top_k,
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": query_embedding}
                    }
                }
            },
            "_source": ["query", "response", "rating", "timestamp"]
        }
        
        results = self.opensearch.search(
            index=self.feedback_index,
            body=search_body
        )
        
        return [hit['_source'] for hit in results['hits']['hits']]
    
    def _filter_by_quality(self, examples):
        """Filtra ejemplos por calidad y recencia"""
        from datetime import datetime, timedelta
        
        filtered = []
        recent_threshold = datetime.now() - timedelta(days=30)
        
        for ex in examples:
            # Solo feedback positivo
            if ex['rating'] != 'positive':
                continue
            
            # Preferir ejemplos recientes
            timestamp = datetime.fromisoformat(ex['timestamp'])
            recency_score = 1.0 if timestamp > recent_threshold else 0.5
            
            ex['quality_score'] = recency_score
            filtered.append(ex)
        
        # Ordenar por calidad
        filtered.sort(key=lambda x: x['quality_score'], reverse=True)
        return filtered
    
    def _compress_to_fit(self, examples, max_tokens):
        """Comprime ejemplos para caber en límite de tokens"""
        
        compressed = "# EJEMPLOS RELEVANTES DE FEEDBACK POSITIVO\n\n"
        current_tokens = 0
        
        for i, ex in enumerate(examples, 1):
            # Truncar respuesta si es muy larga
            response = ex['response']
            if len(response) > 200:
                response = response[:200] + "..."
            
            example_text = f"{i}. Q: {ex['query']}\n   A: {response}\n\n"
            example_tokens = len(example_text.split())
            
            if current_tokens + example_tokens > max_tokens:
                break
            
            compressed += example_text
            current_tokens += example_tokens
        
        return compressed
```

### Integración en el Flujo

```python
# En llm_communication.py

def send_request_with_feedback(self, user_query):
    """Envía request con feedback relevante inyectado"""
    
    # 1. Recuperar feedback relevante (solo 500 tokens)
    relevant_feedback = self.feedback_rag.get_relevant_feedback(
        query=user_query,
        top_k=3,
        max_tokens=500
    )
    
    # 2. Construir prompt con feedback
    enhanced_prompt = f"""
{self.base_system_prompt}

{relevant_feedback}

Usa el conocimiento de los ejemplos anteriores para mejorar tu respuesta.
"""
    
    # 3. Enviar request
    return self._send_to_bedrock(enhanced_prompt, user_query)
```

### Ventajas
- ✅ **Tokens controlados**: Siempre < 500 tokens
- ✅ **Altamente relevante**: Solo ejemplos similares
- ✅ **Escalable infinitamente**: DB puede crecer sin límite
- ✅ **Tiempo real**: No requiere procesamiento batch

### Desventajas
- ⚠️ Requiere OpenSearch configurado
- ⚠️ Latencia adicional de búsqueda (~50-100ms)

---

## 🎯 Estrategia 3: Feedback como Reglas de Negocio

### Concepto
Convertir feedback en **reglas explícitas** en lugar de ejemplos.

### Implementación

```python
class FeedbackRulesExtractor:
    """Extrae reglas de negocio del feedback"""
    
    def extract_rules_from_feedback(self, feedback_examples):
        """
        Analiza feedback y extrae reglas generales
        
        Returns:
            Lista de reglas en formato compacto
        """
        # Agrupar por tipo de query
        query_types = self._categorize_queries(feedback_examples)
        
        rules = []
        
        for query_type, examples in query_types.items():
            # Analizar qué hace que las respuestas sean buenas
            positive = [ex for ex in examples if ex['rating'] == 'positive']
            negative = [ex for ex in examples if ex['rating'] == 'negative']
            
            # Extraer reglas
            rule = self._extract_rule(query_type, positive, negative)
            rules.append(rule)
        
        return rules
    
    def _extract_rule(self, query_type, positive, negative):
        """Extrae regla de un tipo de query"""
        
        # Usar LLM para analizar patrones
        analysis_prompt = f"""
Analiza estos ejemplos de respuestas para queries sobre "{query_type}":

RESPUESTAS EXITOSAS (rating positivo):
{self._format_examples(positive[:3])}

RESPUESTAS FALLIDAS (rating negativo):
{self._format_examples(negative[:3])}

Extrae UNA regla general que explique qué hace que las respuestas sean exitosas.
Formato: "Para queries sobre {query_type}, SIEMPRE [acción] y NUNCA [acción]"
"""
        
        rule = self._call_llm(analysis_prompt)
        return {
            'query_type': query_type,
            'rule': rule,
            'confidence': len(positive) / (len(positive) + len(negative))
        }
    
    def format_rules_for_prompt(self, rules):
        """Formatea reglas para incluir en prompt"""
        
        formatted = "\n# REGLAS APRENDIDAS DE FEEDBACK\n\n"
        
        for rule in sorted(rules, key=lambda x: x['confidence'], reverse=True):
            if rule['confidence'] > 0.7:  # Solo reglas con alta confianza
                formatted += f"- {rule['rule']}\n"
        
        return formatted
```

### Ejemplo de Reglas Extraídas

```
# REGLAS APRENDIDAS DE FEEDBACK

- Para queries sobre creación de contratos, SIEMPRE mencionar requisitos previos y NUNCA asumir que el usuario conoce el proceso completo

- Para queries técnicas sobre APIs, SIEMPRE incluir ejemplos de código y NUNCA dar solo explicaciones teóricas

- Para queries sobre errores, SIEMPRE proporcionar pasos de troubleshooting y NUNCA limitarse a describir el error

- Para queries sobre configuración, SIEMPRE verificar la versión del sistema y NUNCA dar instrucciones genéricas
```

### Ventajas
- ✅ **Extremadamente compacto**: 10-20 reglas = 200-300 tokens
- ✅ **Generalizable**: Aplica a muchas queries
- ✅ **Fácil de mantener**: Reglas legibles por humanos
- ✅ **Acumulativo**: Nuevas reglas se agregan sin crecer mucho

### Desventajas
- ⚠️ Pierde especificidad de ejemplos
- ⚠️ Requiere análisis periódico para extraer reglas

---

## 🎯 Estrategia 4: Modelo de Recompensa Ligero

### Concepto
Entrenar un **modelo pequeño** que prediga si una respuesta será bien calificada, y usarlo para **reranking** o **validación**.

### Arquitectura

```
LLM Response → Reward Model → Score → [If low] → Regenerate
                                    → [If high] → Return
```

### Implementación

```python
class LightweightRewardModel:
    """Modelo ligero para predecir calidad de respuestas"""
    
    def __init__(self):
        # Modelo pequeño (DistilBERT, ~60MB)
        from transformers import AutoModelForSequenceClassification
        self.model = AutoModelForSequenceClassification.from_pretrained(
            "distilbert-base-uncased",
            num_labels=1
        )
    
    def train_on_feedback(self, feedback_examples):
        """Entrena modelo con feedback acumulado"""
        
        # Preparar datos
        X = []  # (query, response) pairs
        y = []  # ratings (0-1)
        
        for ex in feedback_examples:
            text = f"Query: {ex['query']}\nResponse: {ex['response']}"
            X.append(text)
            y.append(1.0 if ex['rating'] == 'positive' else 0.0)
        
        # Entrenar
        self._train(X, y)
    
    def predict_quality(self, query, response):
        """Predice calidad de una respuesta (0-1)"""
        text = f"Query: {query}\nResponse: {response}"
        score = self.model.predict([text])[0]
        return score
    
    def should_regenerate(self, query, response, threshold=0.6):
        """Decide si regenerar respuesta basado en score"""
        score = self.predict_quality(query, response)
        return score < threshold
```

### Uso en el Flujo

```python
# En chat_interface.py

def process_with_quality_check(self, user_query):
    """Procesa query con validación de calidad"""
    
    max_attempts = 2
    
    for attempt in range(max_attempts):
        # Generar respuesta
        response = self.llm_comm.send_request(user_query)
        
        # Validar calidad
        quality_score = self.reward_model.predict_quality(
            user_query,
            response.content
        )
        
        if quality_score > 0.7:
            # Respuesta de buena calidad
            return response
        
        # Regenerar con instrucciones adicionales
        user_query = f"{user_query}\n\n[NOTA: Respuesta anterior tuvo score bajo. Mejora: ser más específico y detallado]"
    
    # Retornar última respuesta
    return response
```

### Ventajas
- ✅ **Sin tokens adicionales**: No modifica el prompt
- ✅ **Validación automática**: Detecta respuestas pobres
- ✅ **Mejora continua**: Se entrena con nuevo feedback
- ✅ **Rápido**: Inferencia < 50ms

### Desventajas
- ⚠️ Requiere entrenamiento inicial
- ⚠️ Necesita actualización periódica
- ⚠️ Infraestructura adicional

---

## 📊 Comparación de Estrategias

| Estrategia | Tokens Añadidos | Escalabilidad | Complejidad | Efectividad |
|------------|----------------|---------------|-------------|-------------|
| **Resúmenes Comprimidos** | 300-500 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **RAG con Feedback** | 300-500 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Reglas de Negocio** | 200-300 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Reward Model** | 0 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 🎯 Recomendación Final: Estrategia Híbrida

### Combinación Óptima

```
1. RAG con Feedback (tiempo real, 300 tokens)
   ↓
2. Reglas de Negocio (estáticas, 200 tokens)
   ↓
3. Reward Model (validación, 0 tokens)
```

### Total: ~500 tokens adicionales, máxima efectividad

### Implementación

```python
class OptimizedFeedbackSystem:
    """Sistema híbrido optimizado"""
    
    def __init__(self):
        self.rag = FeedbackRAG()
        self.rules = FeedbackRulesExtractor()
        self.reward_model = LightweightRewardModel()
    
    def enhance_prompt(self, user_query):
        """Construye prompt optimizado con feedback"""
        
        # 1. RAG: Ejemplos relevantes (300 tokens)
        relevant_examples = self.rag.get_relevant_feedback(
            user_query,
            max_tokens=300
        )
        
        # 2. Reglas: Conocimiento general (200 tokens)
        business_rules = self.rules.get_applicable_rules(
            user_query,
            max_tokens=200
        )
        
        # 3. Construir prompt
        enhanced_prompt = f"""
{self.base_system_prompt}

{business_rules}

{relevant_examples}
"""
        
        return enhanced_prompt
    
    def process_with_validation(self, user_query):
        """Procesa con validación de calidad"""
        
        # Generar respuesta con prompt mejorado
        enhanced_prompt = self.enhance_prompt(user_query)
        response = self.llm.generate(enhanced_prompt, user_query)
        
        # Validar con reward model
        quality_score = self.reward_model.predict_quality(
            user_query,
            response
        )
        
        if quality_score < 0.6:
            # Regenerar con feedback
            response = self.llm.generate(
                enhanced_prompt + "\n[Nota: Sé más específico y detallado]",
                user_query
            )
        
        return response, quality_score
```

---

## 🚀 Plan de Implementación Recomendado

### Fase 1: RAG con Feedback (Semana 1)
- [ ] Indexar feedback en OpenSearch
- [ ] Implementar búsqueda semántica
- [ ] Integrar en flujo de prompts
- [ ] Limitar a 300 tokens

### Fase 2: Reglas de Negocio (Semana 2)
- [ ] Analizar feedback acumulado
- [ ] Extraer reglas con LLM
- [ ] Formatear para prompt (200 tokens)
- [ ] Actualización semanal automática

### Fase 3: Reward Model (Semana 3-4)
- [ ] Entrenar modelo inicial
- [ ] Implementar validación
- [ ] Configurar reentrenamiento automático
- [ ] Métricas de calidad

---

## ✅ Conclusión

**La solución óptima es RAG + Reglas**, que proporciona:
- ✅ Solo 500 tokens adicionales (controlado)
- ✅ Altamente relevante y contextual
- ✅ Escalable a millones de ejemplos
- ✅ Mejora continua automática
- ✅ Sin reentrenamiento del modelo base

¿Te gustaría que implemente esta solución híbrida?
