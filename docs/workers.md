# Workers de Celery - Diagnóstico y Solución de Problemas

## Problema Identificado

### Síntomas
- Los workers de Celery aparecen como "up" en `heroku ps` pero no procesan tareas
- Solo algunos workers (8-12) están procesando tareas activamente
- Otros workers (1-7) están inactivos mostrando solo logs de pgbouncer
- La cola de RabbitMQ se satura debido a la falta de capacidad de procesamiento

### Diagnóstico Visual
```bash
# Ver estado de todos los workers
heroku ps --app breathecode

# Ver logs de un worker específico (worker inactivo)
heroku logs --tail --app breathecode --dyno=celeryworker.1

# Ver logs de un worker específico (worker activo)
heroku logs --tail --app breathecode --dyno=celeryworker.8
```

### Indicadores de Workers Inactivos
- Solo muestran logs de pgbouncer: `0 xacts/s, 0 queries/s`
- No hay logs de Celery o procesamiento de tareas
- Workers aparecen como "up" pero sin actividad real

## Comandos de Diagnóstico

### 1. Verificar Estado de Workers
```bash
# Ver todos los workers activos
heroku ps --app breathecode

# Ver workers específicos
heroku ps --app breathecode | grep celeryworker
```

### 2. Ver Logs de Workers Específicos
```bash
# Ver logs de un worker específico
heroku logs --tail --app breathecode --dyno=celeryworker.1
heroku logs --tail --app breathecode --dyno=celeryworker.2
heroku logs --tail --app breathecode --dyno=celeryworker.3

# Ver logs de workers activos para comparar
heroku logs --tail --app breathecode --dyno=celeryworker.8
heroku logs --tail --app breathecode --dyno=celeryworker.9
```

### 3. Verificar Conexión al Broker
```bash
# Verificar si los workers pueden conectarse al broker
heroku run "celery -A breathecode.celery inspect ping" --app breathecode

# Ver tareas activas
heroku run "celery -A breathecode.celery inspect active" --app breathecode

# Ver estadísticas de workers
heroku run "celery -A breathecode.celery inspect stats" --app breathecode
```

### 4. Verificar Configuración del Broker
```bash
# Ver variables de entorno relacionadas con el broker
heroku config --app breathecode | grep -E "(REDIS|RABBIT|BROKER|CLOUDAMQP)"
```

## Proceso de Solución

### Paso 1: Diagnóstico Inicial
```bash
# 1. Verificar estado de workers
heroku ps --app breathecode

# 2. Ver logs de workers inactivos
heroku logs --tail --app breathecode --dyno=celeryworker.1

# 3. Ver logs de workers activos para comparar
heroku logs --tail --app breathecode --dyno=celeryworker.8
```

### Paso 2: Verificar Conexión al Broker
```bash
# Verificar conexión de todos los workers
heroku run "celery -A breathecode.celery inspect ping" --app breathecode
```

### Paso 3: Reiniciar Workers Inactivos
```bash
# Opción 1: Reiniciar workers específicos
heroku ps:restart celeryworker.1 --app breathecode
heroku ps:restart celeryworker.2 --app breathecode
heroku ps:restart celeryworker.3 --app breathecode
heroku ps:restart celeryworker.4 --app breathecode
heroku ps:restart celeryworker.5 --app breathecode
heroku ps:restart celeryworker.6 --app breathecode

# Opción 2: Reiniciar todos los workers (recomendado)
heroku ps:restart celeryworker --app breathecode
```

### Paso 4: Verificación Post-Solución
```bash
# 1. Esperar 2-3 minutos para que los workers se estabilicen
# 2. Verificar estado de workers
heroku ps --app breathecode

# 3. Verificar conexión al broker
heroku run "celery -A breathecode.celery inspect ping" --app breathecode

# 4. Ver logs de workers para confirmar que están procesando tareas
heroku logs --tail --app breathecode --dyno=celeryworker.1
heroku logs --tail --app breathecode --dyno=celeryworker.2

# 5. Ver tareas activas
heroku run "celery -A breathecode.celery inspect active" --app breathecode
```

## Comandos de Monitoreo Continuo

### Monitoreo de Workers en Tiempo Real
```bash
# Ver logs de todos los workers
heroku logs --tail --app breathecode

# Ver solo logs de celery workers
heroku logs --tail --app breathecode | grep celeryworker

# Monitoreo de un worker específico
heroku logs --tail --app breathecode --dyno=celeryworker.1
```

### Comandos de Diagnóstico de Tareas
```bash
# Ver tareas atascadas
poetry run python manage.py check_task_status --hours=24 --check-execution --limit=10

# Ver resumen de TaskManager
poetry run python manage.py clear_task_manager_queue --show-summary

# Ver tareas por estado
poetry run python manage.py clear_task_manager_queue --status SCHEDULED --show-summary
poetry run python manage.py clear_task_manager_queue --status PENDING --show-summary
poetry run python manage.py clear_task_manager_queue --status ERROR --show-summary
```

## Causas Comunes del Problema

### 1. Problemas de Conexión al Broker
- Workers no pueden conectarse a Redis/RabbitMQ
- Configuración incorrecta de variables de entorno
- Problemas de red entre Heroku y el broker

### 2. Configuración de Autoscaling
- Workers en modo "standby"
- Configuración incorrecta de `CELERY_MIN_WORKERS` y `CELERY_MAX_WORKERS`

### 3. Problemas de Memoria
- Workers que se reinician constantemente
- Límites de memoria alcanzados

### 4. Problemas de Configuración de Colas
- Workers asignados a colas específicas
- Configuración incorrecta de routing

## Prevención

### Monitoreo Regular
```bash
# Script de monitoreo diario
heroku run "celery -A breathecode.celery inspect ping" --app breathecode
heroku ps --app breathecode
```

### Configuración Recomendada
- Mantener `CELERY_MIN_WORKERS` y `CELERY_MAX_WORKERS` balanceados
- Monitorear logs de workers regularmente
- Verificar conexión al broker periódicamente

## Notas Importantes

- Los workers pueden aparecer como "up" en Heroku pero no estar procesando tareas
- Los logs de pgbouncer (0 queries/s) indican workers inactivos
- El reinicio de workers es la solución más efectiva para problemas de conexión
- Siempre verificar la conexión al broker después de reiniciar workers
