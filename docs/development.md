# Desarrollo local

Este documento describe como instalar, ejecutar, probar y mantener el scaffold actual.

## Requisitos

- Python 3.11 o superior.
- Node.js y npm.
- Windows local como entorno inicial.

No se requiere GPU para desarrollar. El modo por defecto es CPU.

## Backend

Instalar dependencias:

```powershell
cd backend
python -m pip install -e .[dev]
```

Ejecutar API local:

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

Ejecutar tests:

```powershell
cd backend
python -m pytest
```

La API queda disponible por defecto en:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/api/v1/health`

## Frontend

Instalar dependencias:

```powershell
cd frontend
npm install
```

Ejecutar UI local:

```powershell
cd frontend
npm run dev
```

Checks disponibles:

```powershell
cd frontend
npm run lint
npm run build
```

La UI queda disponible por defecto en:

- `http://127.0.0.1:5173/`

## Abrir la app sin levantar dos procesos a mano

Opciones disponibles en Windows:

- `Market Simulator.cmd`: lanza la app usando el Python local y abre `http://127.0.0.1:8000/`.
- `release/MarketSimulator.exe`: ejecutable empaquetado que levanta la app integrada y abre el navegador.

Si relanzas la app y ya existe una instancia valida escuchando en `127.0.0.1:8000`, ambos lanzadores reutilizan esa instancia en vez de fallar por puerto ocupado.

Si el puerto `8000` pertenece a otro proceso ajeno al proyecto, el lanzador aborta con un mensaje claro para que liberes ese puerto.

Si ejecutas el `.cmd` desde PowerShell, usa:

```powershell
& '.\Market Simulator.cmd'
```

Scripts auxiliares:

- `scripts/launch-local.ps1`: compila `frontend/dist` si hace falta y arranca Uvicorn.
- `scripts/build-exe.ps1`: recompila frontend y genera `release/MarketSimulator.exe` con PyInstaller.

## Variables de entorno

Backend (`backend/.env.example`):

- `MARKET_SIMULATOR_APP_NAME`: nombre expuesto por la API.
- `MARKET_SIMULATOR_APP_VERSION`: version expuesta por la API.
- `MARKET_SIMULATOR_FRONTEND_DEV_URL`: origen permitido por CORS en desarrollo.
- `MARKET_SIMULATOR_DEFAULT_COMPUTE_MODE`: modo por defecto (`cpu`, `gpu_auto`, `gpu_force`).
- `MARKET_SIMULATOR_GPU_ENABLED`: habilita resolucion de GPU a nivel de configuracion.

Frontend (`frontend/.env.example`):

- `VITE_API_BASE_URL`: base URL de la API, por defecto `http://127.0.0.1:8000/api/v1`.

## Flujo recomendado

1. Leer `AGENTS.md` y el documento tecnico del area que se va a tocar.
2. Cambiar codigo manteniendo separacion entre motor e interfaz.
3. Actualizar documentacion si cambia contrato, comando, configuracion o arquitectura.
4. Ejecutar checks relevantes.
5. Reportar cambios, tests y dudas pendientes.

## Politica de cambios

- Cambios de API requieren actualizar `docs/api.md` y `frontend/src/types/market.ts` si la UI consume el contrato.
- Cambios de configuracion requieren actualizar `.env.example` y este documento.
- Cambios de simulacion requieren tests backend cuando afecten reglas de ledger, matching o determinismo.
- Cambios de frontend no deben mover logica autoritativa de mercado fuera del backend.

## Limitaciones actuales

- No hay WebSocket implementado.
- No hay persistencia SQLite/Parquet implementada.
- Solo hay matching minimo para market sweeps del whale preview; no hay matching continuo completo por tick.
- No hay sistema de ticks ni agentes tomando decisiones reales.
- No hay autenticacion ni despliegue remoto documentado.
- El `.exe` empaquetado no esta firmado; Windows puede mostrar advertencias de SmartScreen segun la configuracion del sistema.
