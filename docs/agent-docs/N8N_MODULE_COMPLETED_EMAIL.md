# Correo al terminar el primer módulo

Un solo workflow de N8N escucha `assignment.assignment_status_updated`. La audiencia sale de `plan_slugs`. La cohort y el macro dicen dónde pasó, no qué correo mandar: Fluency, Flex y AI Engineering pueden compartir la misma micro o el mismo macro.

## Qué mirar del payload

- `task_status == DONE`
- `module_completed == true`
- `completed_module_name`: label del módulo que acaba de cerrarse
- `plan_slugs`: planes vigentes (suscripción `ACTIVE`, financiamiento `ACTIVE` o `FULLY_PAID`)
- `user.id`: no viene el email
- `cohort` y `macro_cohort`: contexto, no filtro de audiencia

`macro_cohort` usa `CohortUser.source_macro_cohort`. Si está vacío y el alumno está inscrito en un solo padre de esa micro, usa ese padre. Con cero o con más de uno, va `null`.

## Flujo

1. Entrar solo si `task_status` es `DONE` y `module_completed` es `true`.
2. Quedarse con el primer módulo. Hoy el payload trae el nombre, no el índice. El filtro estable es el índice `0`; ese campo todavía no existe.
3. Cruzar `plan_slugs` con las listas de abajo. Cada lista que coincida abre su rama.
4. Buscar el email con `user.id`.
5. Enviar la plantilla de esa familia.
6. Guardar `user.id + familia + cohort.id + completed_module_name` y no reenviar si el alumno vuelve a marcar un asset en `DONE`.

### Fluency

`ai-fluency`, `ai-fluency-ue`, `ai-fluency-latam`

### Flex

`ai-flex-basic`, `ai-flex-basic-latam`, `ai-flex-basic-ue`, `ai-flex-pro`, `ai-flex-pro-latam`, `ai-flex-pro-ue`, `ai-flex-plan-pro`

Flex no lleva lista de cohorts. Cualquier micro cae en la misma rama por el plan.

## Alumno con los dos planes

`plan_slugs` solo dice que tiene los dos. No dice cuál estaba cursando.

- Un solo plan: el plan alcanza.
- Los dos planes y una micro o un macro compartido: ni el plan, ni la cohort, ni el macro separan el correo.

Si el correo es para quien tiene el plan y termina el módulo, se mandan los dos. Si el correo es el del programa que estaba cursando, este payload no lo puede decidir.
