# Cálculo de Valores del CohortReportCSV - Guía Detallada

Este documento explica paso a paso cómo se calcula cada valor que aparece en el CSV generado por el endpoint `AcademyCohortReportCSVView`.

**Endpoint:** `GET /v1/admissions/academy/{academy_id}/cohort/{cohort_id}/report.csv`

---

## 📋 Columnas del CSV

El CSV contiene las siguientes columnas (en este orden):

1. `course_name` - Nombre del cohort
2. `student_full_name` - Nombre completo del estudiante
3. `student_email` - Email del estudiante
4. `enrollment_date` - Fecha de inscripción
5. `student_start_date` - Fecha en que el estudiante comenzó
6. `status` - Estado del estudiante
7. `progress_percentage` - Porcentaje de progreso (0-100, entero redondeado)
8. `completion_date` - Fecha de finalización
9. `certificate_url` - URL del certificado
10. `comments` - Comentarios adicionales

---

## 🔄 Flujo de Cálculo (Resumen Ejecutivo)

**Concepto Clave**: El progreso se calcula comparando lo que el estudiante ha completado vs. lo que está en el **syllabus actual** del cohort. Solo se cuentan tareas que están en el syllabus actual.

**Flujo Simplificado**:
```
1. Obtener enrollments del cohort
   ↓
2. Extraer slugs del syllabus ACTUAL (lecciones, ejercicios, proyectos)
   ⚠️ IMPORTANTE: Solo cuenta tareas que están en el syllabus actual
   ↓
3. Consultar qué ha completado cada estudiante (Task + history_log)
   ↓
4. Filtrar: solo lo que está en el syllabus actual
   ↓
5. Calcular progreso = (completadas / total) * 100
```

**Nota sobre "Cache"**: `_extract_syllabus_slugs` no es una cache persistente. Es un diccionario en memoria que se crea **cada vez** que se ejecuta el reporte. Se ejecuta una vez al inicio y contiene los slugs del syllabus actual del cohort.

---

## 🔄 Flujo de Cálculo (Detalle por Fase)

### Fase 1: Preparación de Datos Base

#### Paso 1.1: Obtener Enrollments del Cohort

**Función:** `_get_enrollments_for_academy_student_progress_report(academy, cohort=None)`

**Ubicación:** `breathecode/admissions/actions.py` línea 333

**Qué hace:**
- Obtiene los `CohortUser` de la academia con rol `STUDENT`
- **Acepta parámetro `cohort` opcional** - si se especifica, filtra directamente en la query
- Hace `select_related` para optimizar queries (user, cohort, syllabus_version)
- Hace `prefetch_related` para micro_cohorts

**Query SQL equivalente:**
```sql
-- Si cohort es None (reporte de toda la academia):
SELECT * FROM admissions_cohortuser
WHERE cohort__academy_id = {academy_id}
  AND role = 'STUDENT'
ORDER BY cohort_id, created_at

-- Si cohort se especifica (reporte de cohort específico):
SELECT * FROM admissions_cohortuser
WHERE cohort__academy_id = {academy_id}
  AND role = 'STUDENT'
  AND cohort_id = {cohort_id}  -- ✅ Filtrado optimizado en la query
ORDER BY cohort_id, created_at
```

**✅ Optimización:**
El filtrado por cohort se hace **directamente en la query** cuando se especifica el parámetro, evitando cargar enrollments innecesarios de otros cohorts. Esto mejora significativamente el rendimiento cuando se genera un reporte para un cohort específico.

**Código:**
```python
def _get_enrollments_for_academy_student_progress_report(academy, cohort: Optional[Cohort] = None):
    queryset = (
        CohortUser.objects.filter(cohort__academy=academy, role="STUDENT")
        .select_related("user", "cohort", "cohort__syllabus_version", "cohort__syllabus_version__syllabus")
        .prefetch_related("cohort__micro_cohorts")
        .order_by("cohort_id", "created_at")
    )
    if cohort is not None:
        queryset = queryset.filter(cohort=cohort)
    return queryset
```

**Resultado:** Lista de objetos `CohortUser` con sus relaciones cargadas (filtrados por cohort si se especifica)

---

#### Paso 1.2: Extraer IDs Únicos

**Código:**
```python
enrollments = list(enrollments_qs)
user_ids = list({cu.user_id for cu in enrollments})
cohort_ids = list({cu.cohort_id for cu in enrollments})
cohorts_by_id = {cu.cohort_id: cu.cohort for cu in enrollments if cu.cohort is not None}
```

**Qué hace:**
- Convierte el queryset a lista
- Extrae todos los `user_id` únicos
- Extrae todos los `cohort_id` únicos
- Crea un diccionario para acceso rápido a cohorts por ID

**Resultado:**
- `user_ids`: `[1, 2, 3, ...]`
- `cohort_ids`: `[10]` (solo el cohort especificado)
- `cohorts_by_id`: `{10: <Cohort object>}`

---

### Fase 2: Extracción de Slugs del Syllabus

#### Paso 2.1: Extraer Slugs del Syllabus Actual

**Función:** `_extract_syllabus_slugs(cohorts)`

**Ubicación:** `breathecode/admissions/actions.py` línea 345

**⚠️ IMPORTANTE**: Esta función NO es una cache persistente. Se ejecuta **cada vez** que se genera el reporte y crea un diccionario en memoria con los slugs del syllabus **actual** del cohort.

**Qué hace:**
Para cada cohort, extrae del `syllabus_version.json` **actual**:

1. **Slugs de lecciones** - Usa `get_assets_from_syllabus()` con `task_types=["LESSON"]`
2. **Slugs de ejercicios** - Usa `get_assets_from_syllabus()` con `task_types=["EXERCISE"]`
3. **Slugs de proyectos obligatorios** - Usa `get_assets_from_syllabus()` con `task_types=["PROJECT"]` y `only_mandatory=True`
4. **Total de lecciones** - Cuenta cuántas lecciones hay
5. **Flag de proyectos obligatorios** - Indica si el cohort tiene proyectos obligatorios

**Estructura del Syllabus:**
El syllabus es un JSON con estructura:
```json
{
  "days": [
    {
      "id": 1,
      "label": "Day 1",
      "lessons": [
        {"slug": "learn-react-hooks", "type": "LESSON"},
        {"slug": "react-hooks-practice", "type": "EXERCISE"}
      ],
      "projects": [
        {"slug": "todo-app", "type": "PROJECT", "mandatory": true}
      ]
    }
  ]
}
```

**Resultado:**
```python
lesson_slugs_by_cohort = {
    10: {"learn-react-hooks", "learn-react-components", ...}  # set[str] - no duplicados
}
exercise_slugs_by_cohort = {
    10: {"react-hooks-practice", "react-state-practice", ...}  # set[str] - no duplicados
}
total_lessons_by_cohort = {
    10: 45  # int - cantidad total
}
mandatory_project_slugs_by_cohort = {
    10: {"todo-app", "blog-app", ...}  # set[str] - no duplicados
}
has_mandatory_projects_by_cohort = {
    10: True  # bool
}
```

**¿Por qué `set` en lugar de `list`?**
- ✅ **Elimina duplicados automáticamente** - Si el syllabus tiene slugs duplicados, solo se cuenta una vez
- ✅ **Intersección eficiente** - Se usa el operador `&` para encontrar slugs comunes (línea 774, 780)
- ✅ **Búsqueda O(1)** - Verificar si un slug está en el set es más rápido que en una lista
- ✅ **Operaciones eficientes** - `.update()`, `.add()` son más rápidos que con listas

---

### Fase 3: Análisis del History Log

#### Paso 3.1: Extraer Task IDs del History Log

**Función:** `_get_delivered_task_ids_from_history_log(enrollments, task_type="EXERCISE")`

**Ubicación:** `breathecode/admissions/actions.py` línea 391

**Qué hace:**
Analiza el campo `history_log` (JSONField) de cada `CohortUser` para extraer:

1. **IDs de tareas entregadas** - Del array `delivered_assignments` filtradas por `task_type` (por defecto "EXERCISE")
2. **Flag de inicio** - Si tiene `delivered_assignments` o `pending_assignments`, el estudiante ha comenzado

**Parámetros:**
- `enrollments`: Lista de CohortUser
- `task_type`: Tipo de tarea a extraer ("EXERCISE", "LESSON", "PROJECT", etc.) - Por defecto "EXERCISE"

**Nota:** Esta función es genérica y reutilizable. Se puede usar para extraer cualquier tipo de tarea del history_log.

**Estructura del History Log:**
```json
{
  "delivered_assignments": [
    {"id": 123, "type": "EXERCISE"},
    {"id": 124, "type": "LESSON"}
  ],
  "pending_assignments": [...]
}
```

**Resultado:**
```python
delivered_exercise_task_ids_by_pair = {
    (user_id=1, cohort_id=10): [123, 125, 127],
    (user_id=2, cohort_id=10): [124, 126]
}
started_by_pair = {
    (user_id=1, cohort_id=10): True,
    (user_id=2, cohort_id=10): True
}
```

**Nota:** El `history_log` es un campo legacy. Se usa como fallback si no hay datos en la tabla `Task`.

---

### Fase 4: Consulta de Tareas Entregadas

#### Paso 4.1: Obtener Detalles de Tareas por ID

**Función:** `_get_delivered_tasks_by_id(task_ids, user_ids, cohort_ids)`

**Ubicación:** `breathecode/admissions/actions.py` línea 412

**Qué hace:**
Hace una sola query a la tabla `Task` para obtener los detalles de todas las tareas entregadas encontradas en el history_log.

**Query SQL equivalente:**
```sql
SELECT id, user_id, cohort_id, task_type, associated_slug
FROM assignments_task
WHERE id IN (123, 124, 125, ...)
  AND user_id IN (1, 2, 3, ...)
  AND cohort_id IN (10)
```

**Resultado:**
```python
delivered_tasks_by_id = {
    123: {
        "id": 123,
        "user_id": 1,
        "cohort_id": 10,
        "task_type": "EXERCISE",
        "associated_slug": "react-hooks-practice"
    },
    ...
}
```

---

#### Paso 4.2: Mapear Task IDs a Slugs de Ejercicios

**Función:** `_get_delivered_exercise_slugs(...)`

**Ubicación:** `breathecode/admissions/actions.py` línea 425

**Qué hace:**
- Toma los task_ids del history_log
- Los mapea a slugs usando `delivered_tasks_by_id`
- Filtra solo los slugs que están en el syllabus del cohort

**Lógica:**
```python
for pair, task_ids in delivered_exercise_task_ids_by_pair.items():
    user_id, cohort_id = pair
    syllabus_slugs = exercise_slugs_by_cohort[cohort_id]
    
    for task_id in task_ids:
        task = delivered_tasks_by_id[task_id]
        if task["associated_slug"] in syllabus_slugs:
            slugs.add(task["associated_slug"])
```

**Resultado:**
```python
delivered_exercise_slugs_by_pair = {
    (user_id=1, cohort_id=10): {"react-hooks-practice", "react-state-practice"},
    (user_id=2, cohort_id=10): {"react-hooks-practice"}
}
```

---

### Fase 5: Cálculo de Lecciones Completadas

#### Paso 5.1: Obtener Lecciones Completadas

**Función:** `_get_completed_lesson_slugs(user_ids, cohort_ids, lesson_slugs_by_cohort)`

**Ubicación:** `breathecode/admissions/actions.py` línea 452

**Qué hace:**
Consulta la tabla `Task` para encontrar todas las lecciones que el estudiante ha completado.

**⚠️ FILTRO IMPORTANTE**: Solo cuenta lecciones cuyo `associated_slug` está en `lesson_slugs_by_cohort` (syllabus actual). Si una lección fue completada pero ya no está en el syllabus actual, **NO se cuenta**.

**Query SQL equivalente:**
```sql
SELECT user_id, cohort_id, associated_slug
FROM assignments_task
WHERE user_id IN (1, 2, 3, ...)
  AND cohort_id IN (10)
  AND task_type = 'LESSON'
  AND task_status = 'DONE'
  AND associated_slug IN ('learn-react-hooks', 'learn-react-components', ...)
```

**Criterios de "completada":**
- `task_type = "LESSON"`
- `task_status = "DONE"` (también se acepta "APPROVED" en algunos casos)

**Resultado:**
```python
lesson_done_slugs_by_pair = {
    (user_id=1, cohort_id=10): {"learn-react-hooks", "learn-react-components", ...},
    (user_id=2, cohort_id=10): {"learn-react-hooks"}
}
```

---

### Fase 6: Cálculo de Fecha de Inicio

#### Paso 6.1: Obtener Fecha de Inicio del Estudiante

**Función:** `_get_student_start_dates(user_ids, cohort_ids, lesson_slugs_by_cohort, exercise_slugs_by_cohort)`

**Ubicación:** `breathecode/admissions/actions.py` línea 478

**Qué hace:**
Encuentra la fecha más temprana en que el estudiante comenzó cualquier actividad (lección o ejercicio).

**Query SQL equivalente:**
```sql
SELECT 
    user_id, 
    cohort_id,
    MIN(COALESCE(opened_at, delivered_at, created_at)) as started_at
FROM assignments_task
WHERE user_id IN (1, 2, 3, ...)
  AND cohort_id IN (10)
  AND associated_slug IN (todos_los_slugs_del_syllabus)
  AND task_type IN ('LESSON', 'EXERCISE')
GROUP BY user_id, cohort_id
```

**Lógica de fecha:**
- Usa `opened_at` si existe
- Si no, usa `delivered_at`
- Si no, usa `created_at`
- Toma el mínimo (fecha más temprana)

**Resultado:**
```python
started_at_by_pair = {
    (user_id=1, cohort_id=10): datetime(2024-01-15 10:30:00),
    (user_id=2, cohort_id=10): datetime(2024-01-16 14:20:00)
}
```

---

### Fase 7: Cálculo de Ejercicios Completados

#### Paso 7.1: Obtener Ejercicios Completados

**Función:** `_get_completed_exercise_slugs(...)`

**Ubicación:** `breathecode/admissions/actions.py` línea 533

**Qué hace:**
Determina qué ejercicios están completados usando **tres fuentes de datos** (en orden de prioridad):

#### 7.1.1: Telemetría (Prioridad 1)

Consulta tareas con telemetría y verifica si `completion_rate == 100%`:

**Query:**
```sql
SELECT user_id, cohort_id, associated_slug, telemetry__telemetry
FROM assignments_task
WHERE user_id IN (1, 2, 3, ...)
  AND cohort_id IN (10)
  AND task_type = 'EXERCISE'
  AND associated_slug IN (todos_los_slugs_de_ejercicios)
  AND telemetry__telemetry IS NOT NULL
```

**Lógica de telemetría:**
La función `_telemetry_to_steps(telemetry)` extrae:
- `total_steps` del campo `global_metrics.total_steps`
- `completed_steps` calculado de `completion_rate` o `steps_not_completed`

Si `completed_steps >= total_steps`, el ejercicio está completado.

**Estructura de telemetría:**
```json
{
  "global_metrics": {
    "total_steps": 10,
    "completion_rate": 100.0,
    "steps_not_completed": 0
  }
}
```

#### 7.1.2: Task Status DONE (Prioridad 2)

Consulta tareas con `task_status = "DONE"`:

**Query:**
```sql
SELECT user_id, cohort_id, associated_slug
FROM assignments_task
WHERE user_id IN (1, 2, 3, ...)
  AND cohort_id IN (10)
  AND task_type = 'EXERCISE'
  AND task_status = 'DONE'
  AND associated_slug IN (todos_los_slugs_de_ejercicios)
```

#### 7.1.3: History Log (Prioridad 3 - Fallback)

Usa los slugs obtenidos del history_log (ya calculados en Paso 4.2).

**Resultado:**
```python
completed_exercise_slugs_by_pair = {
    (user_id=1, cohort_id=10): {"react-hooks-practice", "react-state-practice", "react-forms-practice"},
    (user_id=2, cohort_id=10): {"react-hooks-practice"}
}
```

**Nota:** Se combinan las tres fuentes (unión de sets), por lo que si un ejercicio está completado según cualquiera de las tres fuentes, se considera completado.

---

### Fase 8: Cálculo de Certificados

#### Paso 8.1: Obtener Certificados

**Función:** `_get_cert_by_pair(academy, user_ids, cohort_ids)`

**Ubicación:** `breathecode/admissions/actions.py` línea 601

**Qué hace:**
Consulta la tabla `UserSpecialty` para encontrar certificados emitidos.

**Query SQL equivalente:**
```sql
SELECT user_id, cohort_id, token, issued_at, preview_url, status
FROM certificate_userspecialty
WHERE user_id IN (1, 2, 3, ...)
  AND cohort_id IN (10)
  AND academy_id = {academy_id}
  AND status != 'ERROR'
```

**Resultado:**
```python
cert_by_pair = {
    (user_id=1, cohort_id=10): {
        "token": "abc123xyz",
        "issued_at": datetime(2024-03-01),
        "preview_url": "https://...",
        "status": "PERSISTED"
    }
}
```

---

### Fase 9: Cálculo de Proyectos Obligatorios Aprobados

#### Paso 9.1: Obtener Proyectos Obligatorios Aprobados

**Función:** `_get_approved_mandatory_project_slugs_by_pair(...)`

**Ubicación:** `breathecode/admissions/actions.py` línea 610

**Qué hace:**
Consulta la tabla `Task` para encontrar proyectos obligatorios que han sido aprobados.

**Query SQL equivalente:**
```sql
SELECT user_id, cohort_id, associated_slug
FROM assignments_task
WHERE user_id IN (1, 2, 3, ...)
  AND cohort_id IN (10)
  AND task_type = 'PROJECT'
  AND associated_slug IN (slugs_de_proyectos_obligatorios)
  AND revision_status IN ('APPROVED', 'IGNORED')
```

**Criterios:**
- `task_type = "PROJECT"`
- `associated_slug` debe estar en `mandatory_project_slugs_by_cohort`
- `revision_status = "APPROVED"` o `"IGNORED"`

**Resultado:**
```python
approved_mandatory_project_slugs_by_pair = {
    (user_id=1, cohort_id=10): {"todo-app", "blog-app"},
    (user_id=2, cohort_id=10): {"todo-app"}
}
```

---

### Fase 10: Cálculo de Fecha de Finalización

#### Paso 10.1: Obtener Fecha de Finalización

**Función:** `_get_completion_date_by_pair(...)`

**Ubicación:** `breathecode/admissions/actions.py` línea 638

**Qué hace:**
Encuentra la fecha más reciente en que el estudiante completó todas las unidades (lecciones y ejercicios).

**Query SQL equivalente:**
```sql
SELECT 
    user_id, 
    cohort_id,
    MAX(updated_at) as completion_date
FROM assignments_task
WHERE user_id IN (1, 2, 3, ...)
  AND cohort_id IN (10)
  AND task_type IN ('LESSON', 'EXERCISE')
  AND task_status = 'DONE'
  AND associated_slug IN (todos_los_slugs_del_syllabus)
GROUP BY user_id, cohort_id
```

**Lógica:**
- Solo cuenta tareas con `task_status = "DONE"`
- Toma el `MAX(updated_at)` - la fecha más reciente de finalización
- Solo se calcula si el progreso es >= 100%

**Resultado:**
```python
completion_date_by_pair = {
    (user_id=1, cohort_id=10): datetime(2024-03-01 15:30:00),
    (user_id=2, cohort_id=10): None  # No ha completado
}
```

---

### Fase 11: Cálculo Final por Estudiante

#### Paso 11.1: Función Interna `_get_units_for()`

**Ubicación:** `breathecode/admissions/actions.py` línea 757 (dentro de `academy_student_progress_report_rows`)

**Qué hace:**
Calcula el total de unidades y unidades completadas para un estudiante específico.

**Código:**
```python
def _get_units_for(user_id: int, cohort_id: int) -> tuple[int, int]:
    # Total de lecciones del syllabus
    total_lessons = int(total_lessons_by_cohort.get(cohort_id, 0))
    
    # Lecciones completadas (intersección entre completadas y del syllabus)
    completed_lessons = len(
        (lesson_done_slugs_by_pair.get((user_id, cohort_id), set()) or set())
        & (lesson_slugs_by_cohort.get(cohort_id, set()) or set())
    )
    
    # Total de ejercicios del syllabus
    total_exercises = len(exercise_slugs_by_cohort.get(cohort_id, set()))
    
    # Ejercicios completados (intersección entre completados y del syllabus)
    completed_exercises = len(
        (completed_exercise_slugs_by_pair.get((user_id, cohort_id), set()) or set())
        & (exercise_slugs_by_cohort.get(cohort_id, set()) or set())
    )
    
    # Total y completadas
    total_units = total_lessons + total_exercises
    completed_units = completed_lessons + completed_exercises
    
    # Validaciones
    if total_units and completed_units > total_units:
        completed_units = total_units
    if completed_units < 0:
        completed_units = 0
    
    return total_units, completed_units
```

**Ejemplo:**
```python
# Para user_id=1, cohort_id=10:
total_lessons = 45
completed_lessons = 40  # 40 de 45 lecciones completadas
total_exercises = 30
completed_exercises = 25  # 25 de 30 ejercicios completados

total_units = 45 + 30 = 75
completed_units = 40 + 25 = 65

return (75, 65)
```

---

#### Paso 11.2: Cálculo del Porcentaje de Progreso

**Función:** `_progress_percent(total_units, completed_units)`

**Ubicación:** `breathecode/admissions/actions.py` línea 677

**Código:**
```python
def _progress_percent(total_units: int, completed_units: int) -> tuple[int, bool]:
    if total_units <= 0:
        return 0, False
    
    ratio = (completed_units / total_units) * 100.0
    is_completed = ratio >= 99.99
    progress = int(round(ratio))
    progress = 0 if progress < 0 else progress
    progress = 100 if progress > 100 else progress
    if is_completed:
        progress = 100
    return progress, is_completed
```

**Ejemplo:**
```python
# Con total_units=75, completed_units=65:
ratio = (65 / 75) * 100.0 = 86.666...
is_completed = 86.666 >= 99.99 = False
progress = int(round(86.666)) = 87
return (87, False)

# Con total_units=75, completed_units=75:
ratio = (75 / 75) * 100.0 = 100.0
is_completed = 100.0 >= 99.99 = True
progress = 100
return (100, True)
```

**Nota:** Si `educational_status = "GRADUATED"`, el progreso se fuerza a 100% (línea 866).

---

#### Paso 11.3: Determinación del Status

**Función:** `_map_status_for_student_progress(cu, started, is_completed)`

**Ubicación:** `breathecode/admissions/actions.py` línea 666

**Código:**
```python
def _map_status_for_student_progress(cu: CohortUser, *, started: bool, is_completed: bool) -> str:
    edu = (cu.educational_status or "").upper()
    if edu in ("DROPPED", "NOT_COMPLETING", "SUSPENDED"):
        return "withdrawn"
    if is_completed:
        return "completed"
    if not started:
        return "not_started"
    return "in_progress"
```

**Lógica:**
1. Si `educational_status` es `DROPPED`, `NOT_COMPLETING`, o `SUSPENDED` → `"withdrawn"`
2. Si `is_completed = True` → `"completed"`
3. Si `started = False` → `"not_started"`
4. En cualquier otro caso → `"in_progress"`

**Cómo se determina `started`:**
```python
# Línea 849
started = bool((pair in tasks_any_by_pair) or started_by_pair.get(pair, False))
```

Donde `tasks_any_by_pair` se calcula consultando si el estudiante tiene **cualquier** tarea relacionada con slugs del syllabus (línea 789-794).

---

#### Paso 11.4: Construcción de Valores Finales

Para cada `CohortUser`, se construyen los valores finales:

**1. course_name:**
```python
course_name = getattr(cohort, "name", "") if cohort else ""
# Si es macro cohort, se añade "(Macro cohort)"
if is_macro:
    course_name = f"{course_name} (Macro cohort)"
```

**2. student_full_name:**
```python
full_name = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()
```

**3. student_email:**
```python
email = getattr(user, "email", "") if user else ""
```

**4. enrollment_date:**
```python
enrollment_date = cu.created_at  # Fecha de creación del CohortUser
```

**5. student_start_date:**
```python
student_start_date = started_at_by_pair.get(pair)  # Calculado en Fase 6
```

**6. status:**
```python
status = _map_status_for_student_progress(cu, started=started, is_completed=is_completed)
```

**7. progress_percentage:**
```python
progress, is_completed = _progress_percent(total_units, completed_units)
# Si GRADUATED, se fuerza a 100
if edu == "GRADUATED":
    progress = 100
```

**8. completion_date:**
```python
# Inicialmente None
completion_date = None

# Se calcula después si progress >= 100 (línea 922-937)
if item["progress"] >= 100:
    completion_date = completion_date_by_pair.get((user_id, cohort_id))
```

**9. certificate_url:**
```python
cert = cert_by_pair.get(pair)
certificate_url = None
if cert and cert.get("token"):
    certificate_url = f"https://certificate.4geeks.com/{cert.get('token')}"
```

**10. comments:**
Se construye concatenando varios mensajes:

```python
comments = ""

# Mensaje 1: Sin syllabus
if total_units == 0 and status_value != "completed":
    comments += "No syllabus lessons found and no learnpack telemetry; progress estimated as 0"

# Mensaje 2: Sin proyectos obligatorios
if not is_certificate_eligible:
    comments += " | This cohort does not include mandatory projects; certificates are not issued for it"

# Mensaje 3: Proyectos obligatorios pendientes
if progress >= 100 and cert is None:
    required = mandatory_project_slugs_by_cohort.get(cohort_id, set())
    approved = approved_mandatory_project_slugs_by_pair.get(pair, set())
    pending_mandatory = len(required - approved)
    
    if pending_mandatory > 0:
        comments += f" | Progress is 100% for lessons/exercises, but {pending_mandatory} mandatory project(s) are still pending; certificate not generated yet"
```

---

## 🎯 Caso Especial: Macro Cohorts

Si el cohort es un "macro cohort" (tiene micro_cohorts), el cálculo es diferente:

**Detección:**
```python
is_macro = bool(cohort and hasattr(cohort, "micro_cohorts") and cohort.micro_cohorts.exists())
```

**Cálculo:**
1. Se obtienen los micro_cohorts en los que el estudiante está inscrito
2. Se suman los `total_units` y `completed_units` de todos los micro_cohorts
3. Se calcula el progreso sobre el total sumado
4. La fecha de inicio es la más temprana de todos los micro_cohorts
5. La fecha de finalización es la más reciente de todos los micro_cohorts

**Código:**
```python
if is_macro:
    user_cohorts = cohort_ids_by_user.get(cu.user_id, set())
    micro_ids = [c.id for c in cohort.micro_cohorts.all() if c.id in user_cohorts]
    
    total_units = 0
    completed_units = 0
    
    for micro_id in micro_ids:
        micro_total, micro_completed = _get_units_for(cu.user_id, micro_id)
        total_units += micro_total
        completed_units += micro_completed
    
    progress, is_completed = _progress_percent(total_units, completed_units)
```

---

## 📊 Resumen del Flujo Completo (Detallado)

```
1. Obtener enrollments del cohort
   ↓
2. Extraer IDs únicos (user_ids, cohort_ids)
   ↓
3. Extraer slugs del syllabus ACTUAL (lecciones, ejercicios, proyectos)
   ⚠️ Solo cuenta tareas que están en el syllabus actual
   ↓
4. Parsear history_log (tareas entregadas, flag de inicio)
   ↓
5. Consultar Task para detalles de tareas entregadas
   ↓
6. Mapear task_ids a slugs de ejercicios (filtrar por syllabus actual)
   ↓
7. Consultar Task para lecciones completadas (filtrar por syllabus actual)
   ↓
8. Consultar Task para fecha de inicio
   ↓
9. Consultar Task para ejercicios completados (telemetría + status + history_log)
   ↓
10. Consultar UserSpecialty para certificados
   ↓
11. Consultar Task para proyectos obligatorios aprobados
   ↓
12. Consultar Task para fecha de finalización
   ↓
13. Para cada estudiante:
    - Calcular total_units (del syllabus actual)
    - Calcular completed_units (solo las que están en syllabus actual)
    - Calcular progress_percentage = (completed / total) * 100
    - Determinar status
    - Construir fila del CSV
   ↓
14. Generar CSV y retornar
```

---

## 🔍 Queries SQL Totales

En total, el proceso ejecuta aproximadamente **7-8 queries SQL**:

1. Query de enrollments (con select_related)
2. Query de tasks entregadas (del history_log)
3. Query de lecciones completadas
4. Query de fecha de inicio
5. Query de ejercicios completados (telemetría)
6. Query de ejercicios completados (status DONE)
7. Query de certificados
8. Query de proyectos obligatorios aprobados
9. Query de fecha de finalización
10. Query de tasks_any_by_pair (para determinar si empezó)

**Optimización:** Todas las queries usan `IN` con listas de IDs, por lo que son eficientes incluso con muchos estudiantes.

---

## 📝 Notas Importantes

1. **Intersección de Slugs (CRÍTICO):** Solo se cuentan como completadas las unidades cuyo `associated_slug` está en el **syllabus actual** del cohort. 
   - ✅ Si una tarea está completada Y está en el syllabus actual → se cuenta
   - ❌ Si una tarea está completada pero NO está en el syllabus actual → NO se cuenta
   - Esto evita contar tareas de otros cohorts o tareas que fueron removidas del syllabus

2. **Prioridad de Fuentes:** Para ejercicios completados, se usa telemetría primero, luego task_status, y finalmente history_log como fallback.

3. **Macro Cohorts:** El cálculo es más complejo porque suma unidades de múltiples micro_cohorts.

4. **Progreso 100%:** Se considera completado si `ratio >= 99.99%` (permite pequeños errores de redondeo).

5. **GRADUATED:** Si `educational_status = "GRADUATED"`, el progreso se fuerza a 100% independientemente del cálculo.

6. **Certificados:** Solo se generan si el cohort tiene proyectos obligatorios y el estudiante los ha aprobado todos.
