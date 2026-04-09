---
name: syllabus-overrides-validation
description: Documenta la validación del JSON de syllabus (root vs overrides *.vN o N:*.vN), placeholders permitidos en overrides (null/{} por índice), y el bloqueo de self-override. Usar cuando se editen/valide macrosyllabus, overrides, o aparezcan errores de test_syllabus en admissions.
---

# Validación de syllabus JSON (root vs overrides)

## Cuándo aplica

- Cuando se hace `PUT`/`POST` a endpoints de admissions que guardan `SyllabusVersion.json` y aparece el error `There are N errors in your syllabus...`.
- Cuando se editan **overrides** en un macrosyllabus (claves `*.vN` o `N:*.vN`).

## Cómo distingue “principal” vs “override”

- **Principal (root)**: `days` en la raíz del JSON.
- **Override/referencia**: cualquier clave de primer nivel que matchee `^.+\.v\d+$` o `^\d+:.+\.v\d+$` (por ejemplo `basics-of-front-end-development.v2` o `0:basics-of-front-end-development.v2`), cuyo valor debe ser un objeto con `days`.

## Reglas de validación (resumen)

### Root `days` (estricto)

- Cada módulo/día debe ser objeto.
- Debe incluir (salvo `ignore`): `lessons`, `quizzes`, `replits`, `assignments`.
- Cada una debe ser lista.
- Cada item (salvo `{ "status": "DELETED" }`) debe ser objeto con `slug` string.
- `teacher_instructions` vacío genera warning.

### Overrides `*.vN` o `N:*.vN` (parcial por posición)

- El valor de la clave `*.vN` o `N:*.vN` debe ser objeto y contener `days` (lista).
- Cada módulo en `days` puede ser **sparse patch**: no se exigen todas las listas.
- Si una lista está presente (`lessons/quizzes/replits/assignments`), se valida su forma:
  - Debe ser lista.
  - Items pueden ser **placeholders por índice**: `null` o `{}` (no-op; no requieren `slug`).
  - Items con contenido real deben ser objeto con `slug` string (salvo marcador `DELETED`).

## Restricción: self-override (prohibido)

- Si el JSON root tiene `slug` y `version`, es inválido incluir la referencia exacta `"<slug>.v<version>"` dentro del mismo JSON, con o sin prefijo numérico (ej: `0:<slug>.v<version>`).

## Ejemplo: override por índice sin tocar posiciones 0/1

```json
{
  "basics-of-front-end-development.v2": {
    "days": [
      {},
      {},
      {
        "lessons": [null, {}, { "slug": "keep-your-projects", "title": "Keep your projects" }]
      }
    ]
  }
}
```

