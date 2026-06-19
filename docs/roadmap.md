# Roadmap de implementacion

Este roadmap separa estado implementado, aceptacion y fases futuras. No debe usarse para afirmar que una funcionalidad existe si el codigo aun no la implementa.

## Fase 0. Base documental

Objetivo:

- registrar decisiones de arquitectura;
- definir modelo de agentes;
- definir estrategia GPU;
- documentar migracion local a web;
- establecer `AGENTS.md` como memoria operativa.

Estado actual: completada y mantenida en `docs/`.

## Fase 1. Scaffold tecnico

Objetivo:

- crear backend y frontend base;
- definir configuracion;
- exponer API minima;
- dejar pipeline de desarrollo local;
- conectar UI con bootstrap deterministico de la API.

Estado actual: implementada como scaffold.

Aceptacion actual verificada:

- backend FastAPI arranca con `app.main:app`;
- frontend React existe y consume la API;
- endpoints `/api/v1/health`, `/api/v1/simulation/defaults`, `/api/v1/simulation/bootstrap`, `/api/v1/simulation/whale-shock/preview` y `/api/v1/simulation/live*` existen;
- tests backend cubren health, bootstrap y sesion viva minima.

Pendiente dentro del scaffold:

- fortalecer docs cuando cambien contratos;
- mantener `frontend/README.md` alineado con el proyecto, no con la plantilla Vite.

## Fase 2. Mercado minimo jugable

Objetivo:

- order book funcional;
- matching engine price-time priority;
- ledger con reservas y liquidacion de fills;
- 1,000 agentes simples activos por tick;
- shocks manuales;
- chart OHLCV y volumen.

Aceptacion:

- price-time priority correcta;
- saldos consistentes despues de fills parciales y cancelaciones;
- whale sell y whale buy visibles;
- metricas minimas disponibles desde API y UI;
- tests de ledger/matching/determinismo.

Estado actual: en progreso. Ya existe una sesion viva minima jugable con orden directa de ballena, pero el mercado continuo completo aun no esta cerrado.

Avance parcial ya implementado:

- el order book sembrado ya puede sufrir market sweeps sinteticos;
- existe matching minimo para el whale preview;
- el ledger ya valida reservas y liquidacion del agente sintetico de whale shock;
- existe una sesion viva en memoria con ticks automaticos;
- un subconjunto de agentes simples actua por tick con market intents pequenos;
- la UI ya muestra tick actual, estado, traza de precios y controles de iniciar, detener y avanzar.
- el usuario ya puede ejecutar `Whale Buy` y `Whale Sell` sobre la sesion viva y ver impacto visible en precio, traza y balance.
- la UI ya muestra una grafica principal de velas agrupadas desde `recent_mid_prices` para seguir el precio vivo por tick y destacar el ultimo impacto de ballena.
- el volumen real por barra sigue pendiente hasta que el backend exponga OHLCV o volumen historico autoritativo.

## Fase 3. Persistencia y replay

Objetivo:

- guardar eventos y snapshots;
- reproducir una sesion;
- comparar runs por seed.

Aceptacion:

- replay reproducible;
- resumen por sesion;
- export basico;
- documentacion de esquema/formatos.

Estado actual: pendiente. Existen stubs en `backend/app/storage/`.

## Fase 4. Rendimiento y perfilado

Objetivo:

- medir hotspots;
- reducir coste de rendering;
- vectorizar donde compense.

Aceptacion:

- benchmarks guardados;
- criterio claro de cuando activar GPU;
- estabilidad de simulacion.

Estado actual: implementada y verificada mediante `.cmd` y `.exe`.

## Fase 5. GPU opcional

Objetivo:

- backend de computo CPU/GPU con misma interfaz;
- fallback seguro;
- activacion visible por configuracion.

Aceptacion:

- modo CPU operativo;
- modo GPU detectable;
- mismas salidas funcionales para operaciones equivalentes;
- tests o benchmarks que justifiquen activacion.

Estado actual: solo resolucion de compute mode por configuracion.

## Fase 6. Empaquetado local

Objetivo:

- facilitar uso en Windows sin pasos manuales complejos.

Opciones:

- browser local;
- empaquetado desktop.

Estado actual: pendiente.

## Fase 7. Migracion a web

Objetivo:

- mover backend a servidor;
- soportar sesiones remotas;
- mantener misma UX base.

Estado actual: pendiente.

## Funciones posteriores al MVP

- leverage;
- liquidaciones;
- futuros;
- market makers avanzados;
- multiasset;
- simulacion masiva.
