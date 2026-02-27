# Patch UI: selector de mes (iPhone) + normalización de input

## Archivos incluidos
- `public/index.html`

## Qué cambia
- El input de mensual pasa a `type="month"` (iPhone abre selector y entrega `YYYY-MM`).
- Agrega botón `/ready` y un indicador `ready`.
- Si pegas formatos tipo `2026/02/01-2026/02/28` o `2026/0201-...`, el front lo normaliza a `YYYY-MM`.

## Cómo aplicar
Descomprime este ZIP en la raíz del repo (sobrescribe `public/index.html`).

Luego commit y deploy.
