# LearnPack: `learn.json`, campos del asset y UI de 4Geeks.com

[Versión en inglés](./LEARNPACK_CONFIGURATION.md)

Este documento explica cómo el **`learn.json`** del repositorio se mapea a los campos del **`Asset`** en la API (`apply_learn_config` en `models.py`) y cómo esos campos condicionan la UI de lección/ejercicio en el sitio (`ProjectInstructions.jsx`, `ModalToCloneProject.jsx`).

> **Recordatorio — `grading` (`incremental` vs `isolated`):** En assets de **Breathecode**, ambos valores dan el mismo resultado en `interactive` / `gitpod`. Aun así debes elegir el que encaje con **el tipo de trabajo que harán los estudiantes en LearnPack**: flujos acumulativos o por pasos encajan con **`incremental`**; ejercicios que no dependen unos de otros encajan con **`isolated`**. Esa decisión va ligada al **`projectType`** y a cómo está armado el repo (**exercise** vs **project**, tutoriales, etc.), no solo a lo que muestra la UI de 4Geeks.

## Archivos y campos (resumen)

| Origen | Qué controla |
|--------|----------------|
| **`learn.json` en GitHub** | Tras el pull queda en `asset.config`; `apply_learn_config` actualiza título, preview, `interactive`, `gitpod`, delivery, technologies, etc. |
| **`learnpack_deploy_url` en el Asset** | **No** se lee hoy desde `learn.json`. Se define en el registro Breathecode (admin/API) al publicar el pack en LearnPack Cloud. Habilita el flujo **iframe / “iniciar interactivo”** cuando el cohort tiene SaaS. |
| **Cohort** | `available_as_saas` (iframe); **vendors** de provisioning (p. ej. GitHub Codespaces) por academia. |

Nombres de configuración que se obtienen del repo (ver `pull_learnpack_asset`): `learn.json`, `.learn/learn.json`, `bc.json`, `.learn/bc.json`.

## `interactive` y `gitpod` desde `learn.json`

La API **no** usa una clave de primer nivel `interactive` en `learn.json`. Deriva `interactive` y `gitpod` de **`grading`**, **`projectType`**, **`localhostOnly`** y, al final, de la clave opcional **`gitpod`**.

Lógica relevante en `Asset.apply_learn_config` (`registry/models.py`):

1. Si **no** hay `grading` y `projectType` **no** es `"tutorial"` → `interactive = False`.
2. Si **`projectType` es `"tutorial"`** → `interactive = True`, y `gitpod` depende de `localhostOnly`.
3. Si **`grading` es `"incremental"` o `"isolated"`** → `interactive = True`, y `gitpod =` (no `localhostOnly`).
4. Por último, si **`gitpod`** está en el JSON (`true` / `false`) → **sobrescribe** `gitpod`.

Para que **ambos** flags queden en **true** (caso típico “nube + modal local”):

```json
{
  "projectType": "exercise",
  "grading": "incremental",
  "localhostOnly": false,
  "gitpod": true
}
```

(`"isolated"` se comporta igual que `"incremental"` para estos dos flags, pero **elige el valor según cómo esté pensado el pack**; ver el recordatorio arriba.)

Para **interactive** pero **sin** provisioning en la nube en el modal, usa p. ej. `localhostOnly: true` y/o `"gitpod": false` (ver sección de UI).

### `grading`: incremental vs isolated

Para los flags del asset en **Breathecode**, ambos valores son equivalentes: activan `interactive = True` y la misma regla de `gitpod`. **Como autor, usa la elección con sentido en LearnPack:** **`incremental`** cuando los ejercicios avanzan sobre pasos anteriores o un mismo código base; **`isolated`** cuando cada ejercicio es autónomo. Alinea eso con el **`projectType`** y el encargo real a los estudiantes (tareas cortas vs proyectos por etapas); no elijas al azar solo porque en el sitio ambos valen igual para `interactive` / `gitpod`.

### `template_url`

Solo aplica a assets **`PROJECT`**. Si `template_url` aparece en `learn.json` de un **EXERCISE**, la API registra error y no lo aplica como plantilla. En proyectos usa p. ej. `"self"` o la URL real del repo plantilla.

### `projectType` en `learn.json`

Usa `"exercise"` o `"project"` según corresponda. `"tutorial"` es un `projectType` especial que también activa la rama interactiva (`gitpod` según `localhostOnly`).

## `learnpack_deploy_url` (solo registro)

Guardado en **`Asset.learnpack_deploy_url`**. **No** se rellena desde `learn.json` en `apply_learn_config`.

Hace falta (junto con SaaS del cohort y listas de exclusión) para que la UI muestre el botón recomendado **“iniciar ejercicio/proyecto interactivo”** que carga LearnPack en contexto, **junto con** “abrir en local”.

Ver `ProjectInstructions.jsx`:

- `startWithLearnpack = learnpack_deploy_url && cohortSession.available_as_saas && slug no está en la lista no-learnpack`

Slugs excluidos: `app/public/no-learnpack-in-cloud.json`.

## Comportamiento de la UI del sitio

### Dos botones: “Iniciar interactivo …” + “Abrir en local”

Se muestran cuando **`startWithLearnpack`** es true (URL de deploy + SaaS + slug permitido). El segundo botón abre **`ModalToCloneProject`**.

### Modal: provisioning (“abrir en la nube”) vs clonar en local

Desde `ModalToCloneProject.jsx`:

- **`showProvisioningLinks`** = `provisioningVendors.length > 0` **y** `currentAsset.gitpod === true`.
- **`isInteractive`** = `currentAsset.interactive` (pasos por SO vs enlaces directos a vendors).
- Los enlaces de **Codespaces** se construyen desde la URL del **repositorio GitHub** (`currentAsset.url` / `readme_url`); no deben ser solo una URL pública genérica de LearnPack.

Por tanto:

- Las **opciones en la nube en el modal** requieren **`gitpod: true`** en el asset (desde `learn.json` como arriba) y que la academia/cohort devuelva **vendors de provisioning** con Codespaces (o Gitpod).
- Los **botones directos** Codespace/Gitpod dentro del modal requieren **`selectedOption === 'provisioning_vendors'`** y **`isInteractive`** cuando se muestra la lista abreviada (ver el componente).

### Un solo CTA (sin “iniciar interactivo” / iframe) — solo modal, nube + local

Úsalo cuando **no** quieras el iframe de LearnPack en la lección (**“Iniciar interactivo …”**) pero sí que el estudiante abra **`ModalToCloneProject`** y elija **provisioning** (p. ej. Codespaces / Gitpod) **o** **abrir en local**.

En **`ButtonsHandler`** (`ProjectInstructions.jsx`), si **`startWithLearnpack`** es **false**, la UI muestra **un** botón. El texto sale de **`common:learnpack.start-asset`** (en inglés suele verse **“Start exercise”** / **“Start project”** según `asset_type`; en otros idiomas, la traducción de esa clave). Ese botón abre el **mismo** modal que **“Abrir en local”** en el layout de dos botones; dentro del modal, **`showProvisioningLinks`** y **`isForOpenLocaly`** siguen dependiendo de **`gitpod`**, **`interactive`** y los vendors como arriba.

**Para no mostrar el iframe ni los dos botones de cabecera:** mantén **`startWithLearnpack`** en false. Opciones habituales:

- **No** definir **`learnpack_deploy_url`** en el **Asset** en el registro (sin URL de deploy para el flujo iframe), **o**
- Incluir el **`slug`** del asset en **`app/public/no-learnpack-in-cloud.json`** para saltar el iframe aunque exista deploy URL (p. ej. la URL se usa fuera de la app pero no el botón interactivo recomendado).

Sigue haciendo falta para nube + local **dentro del modal**: **`interactive`** y **`gitpod`** vía **`learn.json`** (p. ej. el mismo fragmento con `grading`, `localhostOnly: false`, `gitpod: true`), **cohort** con **`available_as_saas`** para cargar los **vendors** de la academia, y URL de repo **GitHub** válida en el asset para Codespaces.

**Ejemplo (`learn.json`)** — mismos flags que un ejercicio interactivo con nube; lo que cambia es **solo el registro** (sin URL de deploy, o slug en `no-learnpack-in-cloud.json`):

```json
{
  "slug": "example-exercise-modal-only",
  "title": "Example (solo modal, sin iframe)",
  "description": "…",
  "preview": "https://example.com/preview.png",
  "projectType": "exercise",
  "difficulty": "EASY",
  "grading": "incremental",
  "localhostOnly": false,
  "gitpod": true,
  "technologies": ["javascript"]
}
```

**Registro:** deja **`learnpack_deploy_url`** sin definir (o usa **`no-learnpack-in-cloud.json`** como arriba). Tras el sync, la lección muestra un solo CTA tipo **iniciar ejercicio/proyecto** (`start-asset`) que abre el modal con **abrir en la nube** / **abrir en local** cuando los vendors y las URLs lo permiten.

### “Solo iniciar interactivo” (un solo CTA)

Si **`startWithLearnpack`** es true, la UI actual **siempre** muestra **ambos**: inicio interactivo y “abrir en local”. Ocultar el segundo botón **no** es configurable solo con `learn.json`.

### “Iniciar interactivo + abrir en local” pero **sin** nube en el modal

Mantén **`learnpack_deploy_url`** + SaaS para los dos botones de cabecera. Pon el **`gitpod`** del asset en **`false`** vía `learn.json`, p. ej.:

```json
{
  "projectType": "exercise",
  "grading": "incremental",
  "localhostOnly": true,
  "gitpod": false
}
```

No aparecerán los enlaces de provisioning (`showProvisioningLinks` false); el flujo local sigue funcionando con `interactive` en true.

## Fragmentos de ejemplo

### Exercise — modal completo con nube + local (tras sync)

```json
{
  "slug": "example-exercise",
  "title": "Example",
  "description": "…",
  "preview": "https://example.com/preview.png",
  "projectType": "exercise",
  "difficulty": "EASY",
  "grading": "incremental",
  "localhostOnly": false,
  "gitpod": true,
  "technologies": ["typescript"],
  "editor": { "agent": "vscode", "version": "5.0" }
}
```

Además **`learnpack_deploy_url`** en el asset del registro si necesitas iframe + los dos botones.

### Project — mismos flags, con plantilla

```json
{
  "slug": "example-project",
  "title": "Example project",
  "description": "…",
  "preview": "https://example.com/preview.png",
  "projectType": "project",
  "difficulty": "INTERMEDIATE",
  "grading": "incremental",
  "localhostOnly": false,
  "gitpod": true,
  "template_url": "self",
  "technologies": ["react"]
}
```

## Código relacionado

- `breathecode/registry/models.py` — `Asset.apply_learn_config`, `learn_config_to_metadata`, `to_learn_config`
- `breathecode/registry/actions.py` — `pull_learnpack_asset`
- `app/src/components/GuidedExperience/ProjectInstructions.jsx`
- `app/src/components/GuidedExperience/ModalToCloneProject.jsx`

## Nota histórica

El ejemplo antiguo en `registry/README.md` usa campos como `graded` / `intro` como cadenas. Prefiere la forma actual (`grading`, `video`, `projectType`, etc.) alineada con `apply_learn_config` y los tests en `registry/tests/test_asset_learn_config.py`.
