# PlanFeatures: brief para el admin (IA / frontend)

Documento operativo para implementar el flujo de **plan features** en el admin de 4Geeks. Un mismo `PlanFeatures` puede compartirse entre muchos planes; cada plan tiene como máximo uno.

## Modelo mental

- `PlanFeatures` guarda el JSON multi-idioma `bullets` (accordion del checkout).
- `Plan.features` es un ForeignKey opcional a `PlanFeatures`.
- Varios planes pueden apuntar al mismo registro → editar `bullets` afecta a **todos** esos planes.
- Acceso: `plan.features` / `plan_features.plans`.

```text
Plan A ──┐
Plan B ──┼──► PlanFeatures #1 (bullets compartidos)
Plan C ──────► PlanFeatures #2 (único)
```

## Formato de `bullets` (obligatorio)

```json
{
  "en": [
    { "title": "AI feedback", "description": "Get code reviews from our AI models." },
    { "title": "Mentorship", "description": "Book sessions with instructors." }
  ],
  "es": [
    { "title": "Feedback con IA", "description": "Recibe revisiones de código con nuestros modelos." },
    { "title": "Mentorías", "description": "Agenda sesiones con instructores." }
  ]
}
```

Reglas:

- Claves = códigos de idioma (`en`, `es`, …).
- Cada item: solo `title` y `description` (string o `null`).
- **No** uses la estructura legacy con `service` / `features[]`.

## Flujo UX del admin (implementar esto)

### 1. Entrar a plan features de un plan

Al abrir features de un plan:

1. `GET /v1/payments/academy/plan/{id|slug}/features`
2. Si `200` → el plan ya tiene features; mostrar editor con `bullets` y la lista `plans`.
3. Si `404` (`plan-features-not-found`) → el plan no tiene features; ofrecer:
   - **Crear nuevo**
   - **Reutilizar uno existente**

### 2. Crear nuevo

Body:

```json
{ "bullets": { "en": [...], "es": [...] } }
```

o forzar creación aunque ya tenga uno:

```json
{ "bullets": { "en": [...], "es": [...] }, "mode": "create" }
```

`PUT /v1/payments/academy/plan/{id|slug}/features`

### 3. Reutilizar existente

1. Cargar catálogo: `GET /v1/payments/academy/planfeatures`
2. El usuario elige un item de la lista.
3. Adjuntar al plan actual:

```json
{ "plan_features_id": 5 }
```

`PUT /v1/payments/academy/plan/{id|slug}/features`

Eso añade el plan actual a `plans` de ese `PlanFeatures` (no copia el JSON; lo comparte).

### 4. Editar features compartidos (warning obligatorio)

Antes de guardar cambios al JSON:

1. Mira `plans` del GET (o del catálogo).
2. Si hay **más de un plan** (o cualquier otro plan distinto al actual), muestra un **warning**:

> Vas a modificar los features de los siguientes planes: `{lista de slugs}`. ¿Seguro?

3. Si el usuario confirma → guardar sobre el registro compartido:

```json
{ "bullets": { "en": [...], "es": [...] } }
```

`PUT /v1/payments/academy/plan/{id|slug}/features`

Esto actualiza el mismo `PlanFeatures` y afecta a todos los planes en `plans`.

### 5. Opción en el warning: crear features únicos para este plan (fork)

En el mismo warning, ofrecer:

> Crear un plan features único solo para este plan (con los cambios actuales)

Si el usuario elige esa opción:

```json
{
  "bullets": { "en": [...], "es": [...] },
  "fork": true
}
```

`PUT /v1/payments/academy/plan/{id|slug}/features`

Efecto:

- Se crea un **nuevo** `PlanFeatures` con esos `bullets`.
- Solo el plan actual apunta al nuevo registro.
- Los demás planes siguen con el `PlanFeatures` anterior (sin los cambios).

## API (resumen)

Headers comunes:

- `Authorization: Token <token>` (o sesión)
- `Academy: <academy_id>`
- `Content-Type: application/json`

Permisos:

- Lectura: `read_subscription`
- Escritura: `crud_subscription`

### Catálogo (reutilizar)

```http
GET /v1/payments/academy/planfeatures
```

Respuesta `200`:

```json
[
  {
    "id": 1,
    "bullets": { "en": [...], "es": [...] },
    "plans": [
      { "id": 12, "slug": "full-stack-development", "owner_id": 4 },
      { "id": 15, "slug": "full-stack-development-2", "owner_id": 9 }
    ]
  }
]
```

### Features de un plan

```http
GET /v1/payments/academy/plan/{id|slug}/features
PUT /v1/payments/academy/plan/{id|slug}/features
```

Respuesta `200` (GET y PUT):

```json
{
  "id": 1,
  "bullets": { "en": [...], "es": [...] },
  "plans": [
    { "id": 12, "slug": "full-stack-development", "owner_id": 4 }
  ]
}

`owner_id` identifies the academy that owns each linked plan (`null` = global plan). Features can be attached to plans from any academy.
```

### Modos del PUT

| Intención | Body | Efecto |
|-----------|------|--------|
| Crear (plan sin features) | `{ "bullets": {...} }` | Crea `PlanFeatures` y lo asigna |
| Crear forzado | `{ "bullets": {...}, "mode": "create" }` | Siempre crea uno nuevo y reasigna este plan |
| Reutilizar | `{ "plan_features_id": <id> }` | Asigna el existente a este plan |
| Editar compartido | `{ "bullets": {...} }` (plan ya tiene features, sin fork) | Actualiza `bullets` de todos los planes enlazados |
| Fork / único | `{ "bullets": {...}, "fork": true }` | Nuevo registro solo para este plan |

No envíes `plan_features_id` y `bullets` a la vez.

## Lectura pública (checkout)

```http
GET /v1/payments/plan/{slug}
Accept-Language: es
```

Campo `features`: lista ya filtrada por idioma, o `null` si el plan no tiene `PlanFeatures` / lista vacía.

Ejemplo:

```json
{
  "slug": "full-stack-development",
  "features": [
    { "title": "Feedback con IA", "description": "..." }
  ]
}
```

El contrato público **no** incluye `plans`; eso es solo admin.

## Checklist de implementación admin

1. Pantalla plan features: crear nuevo **o** reutilizar (catálogo).
2. Al reutilizar: `PUT` con `plan_features_id`.
3. Al editar: warning con slugs de `plans` si hay más de este plan.
4. Confirmar warning → `PUT` con `bullets` (edición compartida).
5. En el warning: acción secundaria “crear únicos para este plan” → `PUT` con `bullets` + `fork: true`.
6. Verificar en checkout / `GET /v1/payments/plan/{slug}` que `features` refleja el idioma.

## Errores comunes

| Error | Causa | Qué hacer |
|--------|--------|-----------|
| `401/403` | Sin auth o sin permiso / header `Academy` | Autenticar y enviar `Academy` |
| `404 not-found` | Plan inexistente o `DELETED` | Revisar id/slug (features aceptan planes de cualquier academia) |
| `404 plan-features-not-found` | Plan sin features (GET) o `plan_features_id` inválido | Crear o elegir otro id |
| `400 invalid-bullets-format` | `bullets` no es objeto | Enviar `{ "en": [...], "es": [...] }` |
| `400 plan-features-conflicting-payload` | `plan_features_id` y `bullets` juntos | Enviar solo uno de los dos |
| `400 plan-features-missing-payload` | Body vacío | Enviar `plan_features_id` o `bullets` |

## Referencias de código (backend)

- Modelo: `apiv2/breathecode/payments/models.py` → `Plan.features`, `PlanFeatures`
- Vista plan: `AcademyPlanFeaturesView`
- Catálogo: `AcademyPlanFeaturesListView`
- Serializer write: `PutPlanFeaturesSerializer`
- Serializer público: `GetPlanSerializer.get_features`
- URLs: `academy/planfeatures`, `academy/plan/<id|slug>/features`
