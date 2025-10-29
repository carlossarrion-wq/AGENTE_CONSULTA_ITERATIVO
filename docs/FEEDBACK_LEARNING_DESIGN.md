# Sistema de Aprendizaje mediante Feedback - Diseño

## Pregunta del Usuario
¿Es posible que el agente aprenda recibiendo feedback sobre las respuestas?

## Respuesta: Sí, es totalmente posible

Existen varias estrategias para implementar aprendizaje mediante feedback en tu agente IA. A continuación, presento diferentes aproximaciones ordenadas de menor a mayor complejidad.

---

## 🎯 Estrategias de Implementación

### 1. **Feedback Explícito con Almacenamiento (Más Simple)**

#### Concepto
Después de cada respuesta, el usuario puede calificar la respuesta (👍/👎) y opcionalmente proporcionar comentarios.

#### Implementación
```python
# Después de mostrar la respuesta del LLM
feedback = input("¿Fue útil esta respuesta? (s/n/comentario): ")

if feedback.lower() in ['s', 'si', 'sí', 'yes']:
    rating = 'positive'
elif feedback.lower() in ['n', 'no']:
    rating = 'negative'
else:
    rating = 'neutral'
    comment = feedback

# Guardar en logs
feedback_data = {
    "session_id": session_id,
    "query": user_input,
    "response": llm_response,
    "rating": rating,
    "comment": comment,
    "timestamp": datetime.now().isoformat()
}
```

#### Uso del Feedback
1. **Análisis manual**: Revisar respuestas mal calificadas para mejorar system prompts
2. **Ejemplos few-shot**: Usar respuestas bien calificadas como ejemplos en el prompt
3. **Detección de patrones**: Identificar tipos de preguntas que generan feedback negativo

#### Ventajas
- ✅ Fácil de implementar
- ✅ No requiere reentrenamiento del modelo
- ✅ Mejora inmediata mediante ajuste de prompts
- ✅ Bajo costo

#### Desventajas
- ❌ No modifica el modelo base
- ❌ Requiere intervención manual para mejoras

---

### 2. **Feedback con Few-Shot Learning Dinámico (Recomendado)**

#### Concepto
Usar el feedback para construir dinámicamente ejemplos few-shot que se incluyen en el system prompt.

#### Arquitectura
```
User Query → Check Feedback DB → Add Similar Good Examples → LLM → Response
                                        ↓
                                  User Feedback
                                        ↓
                                  Update Feedback DB
```

#### Implementación

**Base de Datos de Feedback**
```python
class FeedbackDatabase:
    def __init__(self):
        self.feedback_file = "logs/feedback/feedback_db.json"
        self.positive_examples = []
        self.negative_examples = []
    
    def add_feedback(self, query, response, rating, comment=None):
        """Almacena feedback con embeddings para búsqueda semántica"""
        feedback_entry = {
            "query": query,
            "response": response,
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.now().isoformat(),
            "embedding": self._get_embedding(query)  # Para búsqueda semántica
        }
        
        if rating == 'positive':
            self.positive_examples.append(feedback_entry)
        else:
            self.negative_examples.append(feedback_entry)
        
        self._save_to_disk()
    
    def get_similar_positive_examples(self, query, top_k=3):
        """Obtiene ejemplos positivos similares a la query actual"""
        query_embedding = self._get_embedding(query)
        
        # Calcular similitud coseno con ejemplos positivos
        similarities = []
        for example in self.positive_examples:
            similarity = cosine_similarity(query_embedding, example['embedding'])
            similarities.append((similarity, example))
        
        # Retornar top_k más similares
        similarities.sort(reverse=True, key=lambda x: x[0])
        return [ex for _, ex in similarities[:top_k]]
```

**Integración en el Prompt**
```python
def build_enhanced_prompt(self, user_query, feedback_db):
    """Construye prompt con ejemplos de feedback positivo"""
    
    # Obtener ejemplos similares bien calificados
    similar_examples = feedback_db.get_similar_positive_examples(user_query, top_k=3)
    
    # Construir sección de ejemplos
    examples_section = "\n\n# EJEMPLOS DE RESPUESTAS EXITOSAS\n\n"
    for i, example in enumerate(similar_examples, 1):
        examples_section += f"""
Ejemplo {i}:
Usuario: {example['query']}
Respuesta exitosa: {example['response']}
---
"""
    
    # Agregar al system prompt
    enhanced_prompt = self.base_system_prompt + examples_section
    return enhanced_prompt
```

#### Ventajas
- ✅ Mejora continua automática
- ✅ Aprende de ejemplos reales
- ✅ No requiere reentrenamiento
- ✅ Contextualmente relevante (usa similitud semántica)
- ✅ Implementación moderada

#### Desventajas
- ❌ Requiere gestión de base de datos de feedback
- ❌ Aumenta tokens en el prompt (costo)

---

### 3. **Reinforcement Learning from Human Feedback (RLHF) - Avanzado**

#### Concepto
Entrenar un modelo de recompensa basado en feedback humano y usar RL para optimizar el modelo.

#### Proceso
1. **Recolección de Feedback**: Usuarios califican respuestas
2. **Entrenamiento de Reward Model**: Modelo que predice qué respuestas serán bien calificadas
3. **Optimización con PPO**: Ajustar el modelo usando Proximal Policy Optimization

#### Implementación (Conceptual)
```python
# 1. Recolectar pares (query, response, rating)
feedback_dataset = collect_feedback_over_time()

# 2. Entrenar reward model
reward_model = train_reward_model(feedback_dataset)

# 3. Usar RL para optimizar
optimized_model = ppo_training(
    base_model=llm,
    reward_model=reward_model,
    training_data=queries
)
```

#### Ventajas
- ✅ Verdadero aprendizaje del modelo
- ✅ Mejora continua y automática
- ✅ Adaptación específica a tu dominio

#### Desventajas
- ❌ Muy complejo de implementar
- ❌ Requiere infraestructura de ML
- ❌ Alto costo computacional
- ❌ Necesita gran cantidad de feedback
- ❌ No aplicable a modelos propietarios (Bedrock)

---

### 4. **Fine-Tuning con Feedback (Intermedio-Avanzado)**

#### Concepto
Usar feedback acumulado para crear dataset de fine-tuning y ajustar el modelo.

#### Proceso
```python
# 1. Acumular feedback positivo
positive_examples = [
    {"query": "...", "response": "...", "rating": "positive"},
    # ... más ejemplos
]

# 2. Convertir a formato de fine-tuning
training_data = []
for example in positive_examples:
    training_data.append({
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": example['query']},
            {"role": "assistant", "content": example['response']}
        ]
    })

# 3. Fine-tune (si el modelo lo permite)
fine_tuned_model = bedrock.create_fine_tuning_job(
    base_model="anthropic.claude-3-sonnet",
    training_data=training_data
)
```

#### Ventajas
- ✅ Modelo adaptado a tu dominio
- ✅ Mejora permanente
- ✅ Reduce necesidad de prompts largos

#### Desventajas
- ❌ No todos los modelos permiten fine-tuning
- ❌ Bedrock tiene limitaciones de fine-tuning
- ❌ Costo de entrenamiento
- ❌ Requiere cantidad significativa de datos

---

## 🎯 Recomendación para tu Caso

### **Estrategia Híbrida: Feedback + Few-Shot Dinámico**

Te recomiendo implementar la **Estrategia 2** (Few-Shot Learning Dinámico) porque:

1. **Es práctica y efectiva**: Mejora inmediata sin reentrenar
2. **Bajo costo**: Solo aumenta tokens en el prompt
3. **Funciona con Bedrock**: No requiere acceso al modelo
4. **Escalable**: Puedes empezar simple y evolucionar
5. **Medible**: Puedes ver mejoras en métricas de satisfacción

### Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Feedback Database                               │
│  • Buscar ejemplos similares positivos                       │
│  • Extraer top-3 respuestas exitosas                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           Enhanced System Prompt                             │
│  • System prompt base                                        │
│  • + Ejemplos de feedback positivo                           │
│  • + Contexto de qué evitar (feedback negativo)             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  LLM (Bedrock)                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   Response                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              User Feedback                                   │
│  • Rating: 👍 / 👎                                           │
│  • Optional comment                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Update Feedback Database                             │
│  • Store with embeddings                                     │
│  • Update statistics                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Plan de Implementación

### Fase 1: Infraestructura Básica (1-2 días)
- [ ] Crear módulo `feedback_manager.py`
- [ ] Implementar captura de feedback en chat_interface
- [ ] Crear estructura de almacenamiento en logs/feedback/
- [ ] Añadir comandos: `feedback`, `ver_feedback`

### Fase 2: Base de Datos de Feedback (2-3 días)
- [ ] Implementar FeedbackDatabase class
- [ ] Integrar con OpenSearch para embeddings
- [ ] Crear búsqueda semántica de ejemplos similares
- [ ] Implementar persistencia en JSON/SQLite

### Fase 3: Few-Shot Dinámico (2-3 días)
- [ ] Modificar prompt builder para incluir ejemplos
- [ ] Implementar selección de top-k ejemplos similares
- [ ] Añadir lógica de "qué evitar" con feedback negativo
- [ ] Optimizar tamaño de prompt (limitar ejemplos)

### Fase 4: Analytics y Mejora Continua (1-2 días)
- [ ] Dashboard de métricas de feedback
- [ ] Análisis de patrones en feedback negativo
- [ ] Alertas para respuestas consistentemente mal calificadas
- [ ] Exportar datos para análisis manual

### Fase 5: Optimizaciones (Opcional)
- [ ] Cache de embeddings para performance
- [ ] Clustering de queries similares
- [ ] A/B testing de diferentes estrategias de few-shot
- [ ] Integración con sistema de métricas existente

---

## 💡 Ejemplo de Uso

```bash
# Usuario inicia sesión
python3 src/agent/main.py --app darwin --username darwin_001

# Usuario hace pregunta
👤 Tú: ¿Cómo crear un contrato en Darwin?

# Agente busca ejemplos similares bien calificados
[Sistema busca en feedback DB...]
[Encuentra 3 ejemplos similares con rating positivo]
[Construye prompt con estos ejemplos]

# Agente responde
🤖 Asistente: Para crear un contrato en Darwin...

# Usuario da feedback
¿Fue útil esta respuesta? (👍/👎/comentario): 👍

# Sistema almacena feedback
✅ Feedback registrado. ¡Gracias!

# Próxima vez que alguien pregunte algo similar
# El sistema usará esta respuesta como ejemplo
```

---

## 📊 Métricas de Éxito

1. **Tasa de Feedback Positivo**: % de respuestas con 👍
2. **Mejora Temporal**: Comparar feedback antes/después de implementación
3. **Reducción de Iteraciones**: Menos uso de herramientas por query
4. **Satisfacción del Usuario**: Encuestas periódicas
5. **Cobertura de Ejemplos**: % de queries con ejemplos similares disponibles

---

## 🚀 Próximos Pasos

¿Te gustaría que implemente esta solución? Puedo:

1. **Implementar Fase 1**: Sistema básico de captura de feedback
2. **Implementar Fase 2**: Base de datos con búsqueda semántica
3. **Implementar Fase 3**: Few-shot learning dinámico
4. **Crear prototipo completo**: Todas las fases integradas

¿Por cuál fase te gustaría empezar?
