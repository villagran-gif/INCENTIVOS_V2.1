Hotfix: Render deploy timeout (PORT)

Qué corrige:
- Render requiere que tu app escuche en el puerto asignado automáticamente vía la variable de entorno PORT.
- Tu render.yaml estaba forzando PORT=8000, lo que provoca que Render no pueda enrutar tráfico al contenedor y el deploy termina en "Timed Out".

Archivos incluidos:
- render.yaml: elimina la env var PORT.
- src/server.js: escucha explícitamente en 0.0.0.0.

Cómo aplicar (desde la raíz del repo):
  unzip incentivos_hotfix_render_port.zip -d .
  git status
  git add render.yaml src/server.js
  git commit -m "Hotfix: remove PORT override for Render"
  git push

Luego redeploy en Render.
