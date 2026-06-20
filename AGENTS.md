# AGENTS.md

## Proposito

Este archivo es el protocolo operativo obligatorio para IAs y colaboradores automatizados que trabajen en este repositorio.

Su funcion es preservar decisiones aprobadas, evitar derivas de arquitectura y mantener trazabilidad entre codigo, documentacion y roadmap.

## Resumen del proyecto

Market Simulator es un simulador de mercado local-first. La direccion aprobada es:

- Windows local primero.
- Migracion posterior a web.
- Backend headless separado de la interfaz.
- Frontend web local con React + TypeScript.
- MVP con 1,000 agentes simples ampliables.
- GPU NVIDIA opcional, nunca requisito base.
- Determinismo por seed y reglas de matching estables.

## Orden de lectura obligatorio

Antes de cambiar codigo o documentacion, leer:

1. `README.md`
2. `docs/index.md`
3. `docs/architecture.md`
4. `docs/roadmap.md`
5. El documento de `docs/` que corresponda al area tocada.

Para cambios de agentes, GPU, migracion local-web o API, leer tambien:

- `docs/agent-system.md`
- `docs/gpu-strategy.md`
- `docs/local-to-web.md`
- `docs/api.md`

## Sources of truth

- Entrada humana del proyecto: `README.md`
- Protocolo para agentes: `AGENTS.md`
- Mapa de documentacion: `docs/index.md`
- Arquitectura y limites entre modulos: `docs/architecture.md`
- Contratos HTTP actuales: `docs/api.md`
- Flujo de desarrollo y comandos: `docs/development.md`
- Modelo de agentes: `docs/agent-system.md`
- Estrategia GPU: `docs/gpu-strategy.md`
- Migracion local a web: `docs/local-to-web.md`
- Roadmap: `docs/roadmap.md`
- Decisiones tecnicas: `docs/decisions/`

No declares como implementado algo que solo esta en roadmap o arquitectura objetivo.

## Estado verificable actual

Implementado:

- `backend/` es una app FastAPI con prefijo `/api/v1`.
- `frontend/` es una app Vite + React + TypeScript.
- La UI consulta `/health`, `/simulation/bootstrap`, `/simulation/whale-shock/preview` y `/simulation/live`.
- El backend puede servir `frontend/dist` para abrir la app integrada desde `http://127.0.0.1:8000/`.
- El backend genera una sesion bootstrap deterministica.
- El backend tambien puede crear una sesion viva minima en memoria con ticks automaticos.
- Hay modelos iniciales para agentes, ledger, order book, shocks, eventos y compute backend.
- Hay matching minimo para market sweeps, liquidacion del whale sintetico, market intents pequenos por tick y orden directa de ballena sobre la sesion viva.
- La UI ya muestra una grafica principal basada en `ohlcv_history`, permite reagruparla en 1T/5T/15T/30T y marca el ultimo impacto de ballena.
- La API de sesion viva ya expone `ohlcv_history` con `open`, `high`, `low`, `close`, `volume`, `trades`, `whale_side` y `whale_impact_bps`; `recent_mid_prices` queda como fallback de compatibilidad.
- La GPU solo se resuelve por configuracion; no hay calculo GPU real.
- La persistencia SQLite/Parquet esta aprobada, pero aun no implementada.
- El matching engine continuo completo sigue pendiente; lo implementado hoy cubre whale preview, sesion viva sintetica con libro resembrado por tick y modo jugable de ballena con impacto visible durante varios ticks.
- Existe un lanzador `Market Simulator.cmd` y un ejecutable empaquetado `release/MarketSimulator.exe`.

## Comandos principales

Backend:

```powershell
cd backend
python -m pip install -e .[dev]
python -m pytest
python -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
npm run lint
npm run build
```

## Reglas no negociables

1. No mezclar logica de simulacion con la interfaz.
2. No usar la interfaz como fuente de verdad de balances, fills ni order book.
3. No hacer depender el core de Windows, Tauri, Electron ni cualquier GUI.
4. No introducir GPU como requisito basico del sistema.
5. No optimizar con GPU antes de medir hotspots reales.
6. Mantener determinismo por seed cuando el cambio afecte simulacion.
7. Mantener price-time priority como regla de matching aprobada.
8. Documentar cualquier cambio importante en `docs/` y, si afecta reglas operativas, en este archivo.

## Limites entre capas

Frontend:

- Puede arrancar/detener simulaciones cuando existan endpoints para ello.
- Puede configurar parametros y shocks a traves de API.
- Puede mostrar snapshots, metricas y replay.
- No puede calcular balances autoritativos.
- No puede decidir fills ni mutar el order book localmente como verdad del sistema.

Backend:

- Mantiene ledger, order book, agentes, shocks, eventos y persistencia.
- Expone contratos HTTP/WebSocket cuando existan.
- Debe poder ejecutarse sin frontend.

Core de simulacion:

- No debe importar React, Vite, componentes UI, Tauri, Electron ni dependencias de navegador.
- No debe asumir rutas absolutas de Windows para persistencia.

## Documentation maintenance

Future agents must update documentation when changing:

- installation steps;
- commands;
- environment variables;
- configuration;
- project structure;
- architecture;
- module responsibilities;
- public APIs or contracts;
- database schema or migrations;
- authentication or authorization;
- security-sensitive behavior;
- deployment or operational procedures;
- testing strategy.

Reglas concretas:

- Si cambias un endpoint, actualiza `docs/api.md` y los tipos frontend si aplican.
- Si cambias variables de entorno, actualiza `docs/development.md` y los `.env.example`.
- Si implementas SQLite, Parquet, replay o migraciones, crea o actualiza documentacion de persistencia.
- Si cambias el flujo de simulacion, actualiza `docs/architecture.md` y `docs/roadmap.md`.
- Si cambias arquetipos o estado de agentes, actualiza `docs/agent-system.md`.
- Si cambias compute mode o dependencias GPU, actualiza `docs/gpu-strategy.md`.
- Si tomas una decision tecnica duradera, agrega un ADR en `docs/decisions/`.

## Politica de tests

- Cambios en backend deben ejecutar `python -m pytest` desde `backend/`.
- Cambios en frontend deben ejecutar al menos `npm run build`; si afectan lint o TS, ejecutar tambien `npm run lint`.
- Cambios de contratos API deben tener tests backend o una razon explicita si todavia no se agregan.
- Si no puedes ejecutar un test, reporta el comando y el motivo.

## Politica de dependencias

- No agregues dependencias nuevas sin necesidad concreta.
- Prefiere NumPy en CPU antes de introducir Numba/CuPy.
- CuPy o GPU solo deben entrar despues de perfilado o de un requisito explicito acotado.
- Mantener el backend ejecutable sin GPU.
- Mantener el frontend desacoplado del motor.

## Zonas sensibles

- `backend/app/core/`: autoridad futura para order book, matching, ledger y eventos.
- `backend/app/simulation/`: orquestacion de sesiones, ticks, shocks y metricas.
- `backend/app/agents/`: perfiles y comportamiento de agentes.
- `backend/app/compute/`: frontera CPU/GPU.
- `backend/app/storage/`: persistencia futura; no asumir que ya hay SQLite/Parquet operativo.
- `frontend/src/types/market.ts`: debe reflejar los contratos API usados por la UI.
- `docs/`: fuente funcional aprobada; evitar contradicciones con codigo real.

## Incertidumbre

Si algo no se puede verificar en codigo, configuracion, tests o docs existentes:

- no lo afirmes como hecho;
- usa `TODO:` para informacion pendiente;
- usa `PENDING_DECISION:` para decisiones no tomadas;
- si una decision bloquea implementacion y no hay forma razonable de inferirla, pregunta al usuario.

## Task completion checklist

Before considering a task complete, agents should report:

- what changed;
- what tests were run;
- what documentation was updated;
- what remains uncertain;
- any risks or follow-up work.

## Siguiente hito recomendado

El siguiente hito tecnico razonable es completar el mercado minimo jugable:

1. matching engine con price-time priority;
2. ledger con reservas y liquidacion de fills;
3. agentes simples activos por tick;
4. whale shocks persistentes entrando por el mismo motor de una sesion viva;
5. sustituir el polling HTTP por streaming de snapshots y eventos.
