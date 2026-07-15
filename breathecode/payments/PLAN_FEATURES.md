# PlanFeatures: cómo agregar bullets de checkout a un plan

Documento operativo para una IA (o un operador) que deba cargar o editar los **features/bullets** de un plan en el checkout de 4Geeks.

## Qué es

`PlanFeatures` es un modelo OneToOne con `Plan`. Guarda un JSON multi-idioma con los bullets que se muestran en el accordion del checkout.

- **Modelo:** `breathecode.payments.models.PlanFeatures`
- **Admin Django:** `Payments → Plan features` (también inline dentro del plan)
- **API escritura (recomendada para IA/ops):** `PUT /v1/payments/academy/plan/{id|slug}/features`
- **API lectura pública en checkout:** `GET /v1/payments/plan/{slug}` → campo `features` (lista ya filtrada por idioma)
- **Frontend:** prioriza `plan.features`. Si viene vacío/`null`, usa legacy (JSON en `/locales/{lang}/plans/{slug}.json` o `GET /serviceitem?plan=`).

## Formato obligatorio del JSON (`bullets`)

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

- Claves de idioma: al menos `en` y `es` cuando el plan se venda en ambos idiomas.
- Cada bullet: solo `title` y `description` (strings o `null`).
- **No** uses la estructura legacy con `service` / `features[]`.
- Un plan = un solo registro `PlanFeatures` (OneToOne). El PUT hace upsert.

## Cómo hacerlo con la API (recomendado para IAs)

### PUT upsert

```http
PUT /v1/payments/academy/plan/{plan_id}/features
# o
PUT /v1/payments/academy/plan/{plan_slug}/features
```

Headers:

- `Authorization: Token <token>` o sesión autenticada
- `Academy: <academy_id>`
- `Content-Type: application/json`

Permiso: `crud_subscription` en esa academy.

Body:

```json
{
  "bullets": {
    "en": [
      { "title": "Feature one", "description": "Short description in English." }
    ],
    "es": [
      { "title": "Feature uno", "description": "Descripcion corta en espanol." }
    ]
  }
}
```

Respuesta `200`:

```json
{
  "id": 1,
  "plan": 12,
  "plan_slug": "full-stack-development",
  "bullets": { "en": [...], "es": [...] }
}
```

### GET bullets completos (admin)

```http
GET /v1/payments/academy/plan/{plan_id}/features
```

Permiso: `read_subscription`. Devuelve el JSON multi-idioma completo.  
Si el plan no tiene `PlanFeatures` → `404` (`plan-features-not-found`).

## Cómo hacerlo desde Django Admin

### Opción A — desde el plan

1. Abre Django Admin de 4Geeks (API / breathecode).
2. Ve a **Payments → Plans**.
3. Abre el plan por **slug**.
4. Baja al inline **Plan features**.
5. Pega el JSON en **Bullets** y guarda.

### Opción B — desde Plan features

1. Ve a **Payments → Plan features**.
2. Crea o edita el registro del plan.
3. Pega el JSON en **Bullets** y guarda.

## Verificación rápida

1. `GET /v1/payments/plan/{slug}` con `Accept-Language: es` → `features` = array `es`.
2. Mismo request con `Accept-Language: en` → `features` = array `en`.
3. Si no hay `PlanFeatures` o la lista del idioma está vacía → `features` es `null` (checkout legacy).
4. Abre el checkout del plan y confirma el accordion (title + description).

## Errores comunes

| Error | Causa | Qué hacer |
|--------|--------|-----------|
| `401/403` en PUT | Sin auth o sin `crud_subscription` | Autenticar y enviar header `Academy` |
| `404 not-found` | Plan no existe o no pertenece a la academy | Usar id/slug correcto |
| `400 invalid-bullets-format` | `bullets` no es un objeto | Enviar `{ "en": [...], "es": [...] }` |
| Checkout sigue con bullets viejos | `features` aún es null en el GET público | Confirmar que el PUT guardó y `GET plan/{slug}` ya trae `features` |

## Referencias de código

- Modelo: `apiv2/breathecode/payments/models.py` → `PlanFeatures`
- Vista: `apiv2/breathecode/payments/views.py` → `AcademyPlanFeaturesView`
- Serializer write: `PutPlanFeaturesSerializer`
- Serializer read (checkout): `GetPlanSerializer.get_features`
- URLs: `academy/plan/<id|slug>/features`
- Frontend: `app/src/hooks/useSignup.js` → `resolveCheckoutFeaturedInfo`
