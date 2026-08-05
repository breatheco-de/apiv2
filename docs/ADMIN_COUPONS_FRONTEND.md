# Admin Frontend: API de Cupones de Academia

Guía para integrar una vista de administración que liste, cree y edite cupones usando el endpoint de academia.

Base URL: `/v1/payments/academy/coupon`

Documentación general del sistema: [`agent-docs/COUPONS.md`](./agent-docs/COUPONS.md)

---

## Autenticación y permisos

Todos los endpoints de academia requieren:

| Header | Valor | Notas |
|--------|--------|------|
| `Authorization` | `Token <access_token>` | Usuario autenticado |
| `Academy` | `<academy_id>` | ID numérico de la academia activa |

### Capabilities

| Método | Capability requerida |
|--------|----------------------|
| `GET` / `HEAD` | `read_subscription` |
| `POST` / `PUT` / `DELETE` | `crud_subscription` |

Sin el capability correcto la API responde `403`.

---

## Modelo mental (para el form del admin)

Un cupón promocional típico de academia tiene:

1. **Código** (`slug`) — único mientras el cupón esté vigente.
2. **Descuento** (`discount_type` + `discount_value`).
3. **Alcance** (`plans`) — a qué planes aplica. Vacío = global.
4. **Límite de usos** (`how_many_offers`).
5. **Vigencia** (`offered_at`, `expires_at`).
6. **Auto-aplicación** (`auto`) — si se aplica solo en checkout.

Para cupones promocionales de admin, usa casi siempre:

- `referral_type: "NO_REFERRAL"`
- `referral_value: 0`

Los cupones de referral (`PERCENTAGE` / `FIXED_PRICE`) no deben llevar `plans`.

---

## Enums

### `discount_type`

| Valor | Significado | `discount_value` |
|-------|-------------|------------------|
| `PERCENT_OFF` | Porcentaje de descuento | Decimal `0–1` (ej. `0.25` = 25%) |
| `FIXED_PRICE` | Monto fijo de descuento | Número absoluto (ej. `50`) |
| `NO_DISCOUNT` | Sin descuento | — |
| `HAGGLING` | Tipo especial de negociación | — |

### `referral_type`

| Valor | Significado |
|-------|-------------|
| `NO_REFERRAL` | Cupón normal (recomendado en admin) |
| `PERCENTAGE` | Comisión % al seller |
| `FIXED_PRICE` | Comisión fija al seller |

### `how_many_offers`

| Valor | Significado |
|-------|-------------|
| `-1` | Usos ilimitados (default) |
| `0` | Deshabilitado (nadie puede usarlo) |
| `> 0` | Máximo de usos permitidos |

---

## GET — Listar / detalle

### Comportamiento por defecto (listado)

```http
GET /v1/payments/academy/coupon
Authorization: Token <token>
Academy: <academy_id>
```

Por defecto devuelve **todos los cupones que se están ofreciendo ahora**:

- `offered_at` null o ya pasó
- `expires_at` null o en el futuro
- `how_many_offers` = `-1` o `> 0`
- sin cupones de referral (`referral_type = NO_REFERRAL`)

Incluye cupones con planes y sin planes (`plans: []` = aplica a cualquier plan).

#### Query params

| Param | Tipo | Descripción |
|-------|------|-------------|
| `plan` | slug (o id) | Solo cupones asociados a ese plan |
| `include_referral` | `true`/`1`/`yes` | Incluye cupones referral |
| `status` | `all` | Incluye también expirados / deshabilitados / no ofrecidos aún |
| `like` | string | Busca por slug (`icontains`) |
| `limit` / `offset` / `sort` | | Paginación y orden (`sort` default `-id`) |

#### Ejemplos

```bash
# Cupones vigentes (default)
curl -X GET "https://api.4geeks.com/v1/payments/academy/coupon" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4"

# Solo los de un plan
curl -X GET "https://api.4geeks.com/v1/payments/academy/coupon?plan=full-stack" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4"

# Incluir referral
curl -X GET "https://api.4geeks.com/v1/payments/academy/coupon?include_referral=true" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4"

# Histórico / no vigentes
curl -X GET "https://api.4geeks.com/v1/payments/academy/coupon?status=all" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4"
```

### Detalle por slug

```http
GET /v1/payments/academy/coupon/<coupon_slug>
```

El detalle **no** exige que el cupón esté vigente (así puedes editar expirados). Sigue excluyendo referral salvo `?include_referral=true`.

### Shape de respuesta (`GetAcademyCouponSerializer`)

```json
{
  "slug": "summer-2025",
  "discount_type": "PERCENT_OFF",
  "discount_value": 0.25,
  "referral_type": "NO_REFERRAL",
  "referral_value": 0.0,
  "auto": false,
  "how_many_offers": 100,
  "allowed_user": null,
  "plans": [
    {
      "title": "Full Stack",
      "slug": "full-stack",
      "status": "ACTIVE",
      "discontinued_reason": null,
      "time_of_life": 12,
      "time_of_life_unit": "MONTH",
      "trial_duration": 0,
      "trial_duration_unit": "DAY"
    }
  ],
  "offered_at": "2025-06-01T00:00:00Z",
  "expires_at": "2025-08-31T23:59:59Z",
  "times_used": 3,
  "last_used_at": "2025-07-10T12:00:00Z",
  "stats": {},
  "stats_updated_at": null
}
```

- `plans: []` → cupón global (sin restricción de plan)
- `plans: [...]` → solo aplica a esos planes

### HEAD — ¿existe el slug?

Útil para validar el código antes de crear:

```http
HEAD /v1/payments/academy/coupon/<coupon_slug>/exists
Authorization: Token <token>
Academy: <academy_id>
```

- `200` → el slug ya existe (globalmente)
- `404` → disponible

---

## POST — Crear cupón

```http
POST /v1/payments/academy/coupon
Authorization: Token <token>
Academy: <academy_id>
Content-Type: application/json
```

### Campos del body

| Campo | Requerido | Tipo | Notas |
|-------|-----------|------|------|
| `slug` | sí | string | Código único del cupón |
| `discount_type` | sí | string | Ver enums |
| `discount_value` | sí | number | Ver tabla de descuentos |
| `referral_type` | recomendado | string | Default del modelo: `NO_REFERRAL` |
| `referral_value` | recomendado | number | `0` si no es referral |
| `auto` | no | boolean | Default `false` |
| `how_many_offers` | no | int | Default `-1` |
| `plans` | no | array | IDs o slugs de planes |
| `offered_at` | no | datetime ISO | Si no se manda, el modelo puede setear `now` |
| `expires_at` | no | datetime ISO | `null` = no expira |
| `allowed_user` | no | int | User ID; solo ese user puede usarlo |
| `seller` | no | int | Seller ID (referral) |
| `referred_buyer` | no | int | User ID (rewards) |

### Payload recomendado (admin / promo)

```json
{
  "slug": "summer-2025",
  "discount_type": "PERCENT_OFF",
  "discount_value": 0.25,
  "referral_type": "NO_REFERRAL",
  "referral_value": 0,
  "auto": false,
  "how_many_offers": 100,
  "plans": [1, "full-stack-program"],
  "offered_at": "2025-06-01T00:00:00Z",
  "expires_at": "2025-08-31T23:59:59Z"
}
```

### Ejemplo curl

```bash
curl -X POST "https://api.4geeks.com/v1/payments/academy/coupon" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "summer-2025",
    "discount_type": "PERCENT_OFF",
    "discount_value": 0.25,
    "referral_type": "NO_REFERRAL",
    "referral_value": 0,
    "auto": false,
    "how_many_offers": 100,
    "plans": [1, 2],
    "expires_at": "2025-08-31T23:59:59Z"
  }'
```

### Respuesta

- Status: `201 Created`
- Body: mismo shape que GET (sin `plans` / `how_many_offers`)

### Validaciones del POST

1. Cada plan en `plans` debe existir.
2. Cada plan debe ser de la academia o global (`owner = null`).
3. Si `referral_type != NO_REFERRAL`, `plans` debe ir vacío.
4. `slug` no puede coincidir con otro cupón vigente (no expirado).
5. `discount_value` y `referral_value` no pueden ser negativos.
6. Si `referral_type == NO_REFERRAL`, `referral_value` debe ser `0`.
7. Si `auto == true`, `discount_type` no puede ser `NO_DISCOUNT`.

---

## PUT — Actualizar cupón

```http
PUT /v1/payments/academy/coupon/<coupon_slug>
Authorization: Token <token>
Academy: <academy_id>
Content-Type: application/json
```

Soporta **partial update**: puedes mandar solo los campos que cambian.

### Ejemplo: cambiar descuento y expiración

```bash
curl -X PUT "https://api.4geeks.com/v1/payments/academy/coupon/summer-2025" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Academy: 4" \
  -H "Content-Type: application/json" \
  -d '{
    "discount_value": 0.3,
    "expires_at": "2025-09-30T23:59:59Z"
  }'
```

### Ejemplo: reemplazar planes

```json
{
  "plans": [3, 4]
}
```

Si envías `plans`, **reemplaza** la relación completa (no hace merge).

Para dejarlo global (todos los planes):

```json
{
  "plans": []
}
```

### Respuesta

- Status: `200 OK`
- Body: shape de GET actualizado

### Errores comunes

| Status | Slug / causa |
|--------|----------------|
| `404` | `not-found` — cupón no encontrado para esa academia |
| `404` | `plan-not-found` — algún plan no existe |
| `403` | `plan-not-belonging-to-academy` — plan de otra academia |
| `400` | `invalid-referral-coupon-with-plans` — referral + plans |
| `400` | `invalid-plan-identifier` — valor inválido en `plans` |
| `400` | validación de modelo (slug duplicado vigente, valores inválidos, etc.) |

---

## DELETE (bonus)

```http
DELETE /v1/payments/academy/coupon/<coupon_slug>
```

- Capability: `crud_subscription`
- Respuesta: `204 No Content`
- Solo borra cupones visibles para la academia (mismos filtros que GET/PUT)

---

## Sugerencia de UI para el admin

### Pantallas

1. **Lista**
   - `GET /academy/coupon?like=&plan=&limit=`
   - Columnas útiles: `slug`, `discount_type`, `discount_value`, `auto`, `expires_at`, `times_used`
2. **Crear**
   - Form → `POST /academy/coupon`
   - Validar slug con `HEAD .../exists` antes de submit
3. **Editar**
   - Form → `PUT /academy/coupon/<slug>`
   - Partial update: solo campos tocados

### Inputs recomendados en el form

| Campo UI | API field | Control sugerido |
|----------|-----------|------------------|
| Código | `slug` | text + check `HEAD .../exists` |
| Tipo de descuento | `discount_type` | select |
| Valor | `discount_value` | number (si %: UI en 0–100 y convertir a 0–1) |
| Usos máximos | `how_many_offers` | number (`-1` = ilimitado) |
| Auto aplicar | `auto` | toggle |
| Planes | `plans` | multi-select de planes de la academia |
| Inicio | `offered_at` | datetime (opcional) |
| Expira | `expires_at` | datetime (opcional) |
| Usuario restringido | `allowed_user` | user picker (opcional, avanzado) |

Defaults al crear:

```json
{
  "referral_type": "NO_REFERRAL",
  "referral_value": 0,
  "auto": false,
  "how_many_offers": -1
}
```

### Conversión de porcentaje en UI

Si el admin escribe `25` (%):

```js
discount_value = 25 / 100; // 0.25
```

Si el API devuelve `0.25`, mostrar `25%` en la tabla/form.

### Multi-select de planes

`plans` acepta mezcla de IDs y slugs:

```json
"plans": [12, "plan-pro", 15]
```

Solo planes de la academia activa o globales.

---

## Checklist rápido de integración

- [ ] Headers `Authorization` + `Academy` en todas las calls
- [ ] Verificar capability `read_subscription` / `crud_subscription`
- [ ] Lista con `GET` (vigentes por default) + filtros `plan` / `include_referral` / `status=all`
- [ ] Crear con `POST` y defaults de referral en `0` / `NO_REFERRAL`
- [ ] Editar con `PUT` partial
- [ ] Convertir % UI ↔ decimal API
- [ ] Recordar que GET no trae `plans` ni `how_many_offers`
- [ ] Opcional: `HEAD .../exists` para validar slug
- [ ] Opcional: `DELETE` para borrar

---

## Endpoints relacionados (no admin, pero útiles)

| Endpoint | Uso |
|----------|-----|
| `GET /v1/payments/coupon?coupons=X&plan=Y` | Validar cupón público para un plan |
| `GET /v1/payments/me/coupon` | Cupones de referral del usuario (seller) |
| `PUT /v1/payments/bag/<id>/coupon` | Aplicar cupón en checkout |

Para el admin de academia, con `GET` / `POST` / `PUT` de `/v1/payments/academy/coupon` alcanza.
