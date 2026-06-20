# Market Simulator

Simulador de mercado local-first para construir y observar un mercado con order book central, ledger, agentes parametrizados y shocks controlados.

El proyecto ya supera el scaffold puro. Ahora existen un backend FastAPI, un frontend React + TypeScript, una sesion bootstrap deterministica y una sesion viva minima jugable en memoria con ticks, agentes simples activos y control directo de ballena.

## Estado actual

Implementado y verificable en el repositorio:

- Backend Python 3.11+ con FastAPI.
- Frontend Vite + React + TypeScript.
- API HTTP local bajo `/api/v1`.
- Bootstrap deterministico de 1,000 agentes por defecto.
- Sesion viva minima en memoria con ticks automaticos y controles de iniciar, detener, avanzar y operar como ballena.
- Grafica principal con OHLCV real por tick desde backend en la UI, con agrupacion visual 1s/5s/10s/30s/1 min, ventana reciente limitada para no saturar la vista y fallback local si aun faltan barras suficientes.
- Primer minijuego local `Whale Challenge - 60 segundos` con score, contador, resumen final y reinicio sobre la misma sesion viva.
- Panel DEV de `Order Book` con bids/asks agregados, spread y profundidad visible desde el snapshot vivo.
- El `Order Book` de la sesion viva ahora persiste entre ticks: envejece, expira por TTL, se consume con market orders y se refresca de forma parcial.
- Supervisor de régimen de mercado con fases como `neutral`, `uptrend`, `downtrend`, `panic`, `short_squeeze` y `post_whale_consolidation`, visible en modo DEV.
- Resumen `icebergs` en el snapshot vivo y panel DEV de absorcion oculta con conteo por lado, absorcion reciente y ultimo nivel observado.
- Order book sembrado alrededor de un precio inicial para snapshots.
- Ledger inicial con saldos libres/reservados y calculo de equity.
- Configuracion de compute mode con `cpu`, `gpu_auto` y `gpu_force`.
- Tests backend para health, bootstrap, simulacion viva y ordenes de ballena sobre sesion viva.

Pendiente para el MVP jugable:

- matching engine operativo con price-time priority completo;
- liquidacion de fills contra un libro continuo, no solo liquidez sintetica por tick;
- shocks persistentes adicionales conectados al motor;
- persistencia SQLite/Parquet;
- streaming o replay de mercado.

## Requisitos

- Python 3.11 o superior.
- Node.js y npm compatibles con Vite.
- Windows local es el entorno inicial previsto.
- GPU NVIDIA no es requisito. La CPU es el modo por defecto.

## Instalacion

Backend:

```powershell
cd backend
python -m pip install -e .[dev]
```

Frontend:

```powershell
cd frontend
npm install
```

Puedes copiar los ejemplos de variables de entorno si necesitas cambiar puertos, CORS o URL de API:

- `backend/.env.example`
- `frontend/.env.example`

## Ejecucion local

### Opcion mas simple en Windows

Tienes dos formas rapidas de abrir la app:

1. Doble clic en `Market Simulator.cmd`
2. Doble clic en `release/MarketSimulator.exe`

Ambas opciones levantan el backend local y abren la app en el navegador en:

- `http://127.0.0.1:8000/`

Si quieres lanzar el `.cmd` desde PowerShell en vez de hacer doble clic:

```powershell
& '.\Market Simulator.cmd'
```

La diferencia es:

- `Market Simulator.cmd` usa tu entorno Python local.
- `release/MarketSimulator.exe` usa el ejecutable empaquetado generado en este repositorio.

Si vuelves a ejecutar cualquiera de las dos opciones mientras Market Simulator ya esta corriendo en `127.0.0.1:8000`, el lanzador reutiliza la instancia activa en vez de romperse por puerto ocupado.

Si el puerto `8000` lo esta usando otra aplicacion distinta, cierra ese proceso antes de abrir Market Simulator.

### Modo desarrollo manual

Backend:

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm run dev
```

Rutas utiles:

- Frontend dev: `http://127.0.0.1:5173/`
- App integrada local: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/v1/health`
- Bootstrap: `http://127.0.0.1:8000/api/v1/simulation/bootstrap`
- Whale preview: `http://127.0.0.1:8000/api/v1/simulation/whale-shock/preview`
- Live session: `http://127.0.0.1:8000/api/v1/simulation/live`
- Live game start: `http://127.0.0.1:8000/api/v1/simulation/live/game/start`
- Live whale order: `http://127.0.0.1:8000/api/v1/simulation/live/whale-order`

Al cargar la app integrada, la UI intenta recuperar una sesion viva. Si no existe ninguna, crea una nueva automaticamente y empieza a avanzar ticks en memoria. Desde esa misma vista puedes lanzar `Whale Buy` y `Whale Sell` para impactar el libro vivo actual, cambiar entre velas 1s/5s/10s/30s/1 min, limitar la vista a la ventana reciente, ajustar la velocidad entre normal, rapido y muy rapido y jugar un reto corto `Whale Challenge - 60 segundos` con score y resumen final. En `Modo DEV` tambien puedes inspeccionar `Market Regime`, `Order Book` y el resumen de `Icebergs` expuesto por el backend.

## Tests y checks

Backend:

```powershell
cd backend
python -m pytest
```

Frontend:

```powershell
cd frontend
npm run lint
npm run build
```

## Estructura

- `backend/`: API FastAPI, core de simulacion, agentes, compute y stubs de almacenamiento.
- `frontend/`: interfaz React local conectada al backend y compilable a `frontend/dist`.
- `scripts/`: lanzadores y build de ejecutable para Windows.
- `release/`: salida del ejecutable generado.
- `docs/`: arquitectura, roadmap, guias y contratos.
- `AGENTS.md`: protocolo operativo obligatorio para futuras IAs.

## Generar o regenerar el .exe

Si haces cambios y quieres reconstruir el ejecutable:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-exe.ps1
```

Salida esperada:

- `release/MarketSimulator.exe`

## Documentacion

Empieza por [docs/index.md](./docs/index.md).

Fuentes principales:

- [AGENTS.md](./AGENTS.md): reglas operativas para agentes.
- [docs/architecture.md](./docs/architecture.md): arquitectura y limites entre UI y motor.
- [docs/api.md](./docs/api.md): contratos HTTP actuales.
- [docs/development.md](./docs/development.md): comandos, entorno y flujo de trabajo.
- [docs/roadmap.md](./docs/roadmap.md): fases de implementacion.
