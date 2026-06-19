# Arquitectura

## Resumen

La arquitectura aprobada es local-first con separacion estricta entre motor de simulacion e interfaz:

- backend Python/FastAPI como autoridad del mercado;
- frontend React/TypeScript como capa de control y visualizacion;
- comunicacion HTTP en el scaffold actual;
- WebSocket o streaming como extension futura cuando existan ticks vivos;
- persistencia SQLite/Parquet planificada para sesiones, snapshots, eventos y replay.

No se recomienda una GUI nativa de Windows para la primera fase porque dificultaria la migracion posterior a web.

## Stack verificable actual

Backend:

- Python 3.11+
- FastAPI
- Pydantic
- NumPy como dependencia base
- Uvicorn para ejecucion local
- Pytest + HTTPX para tests

Frontend:

- React
- TypeScript
- Vite
- ESLint

Persistencia:

- Aprobada: SQLite para sesiones/configuracion y Parquet para eventos/replay.
- Estado actual: solo existen stubs o dataclasses en `backend/app/storage/`; no hay escritura real a SQLite o Parquet.

GPU:

- Aprobada como opcional.
- Estado actual: resolucion de compute backend por configuracion; no hay calculo GPU real.

## Estado implementado

El repositorio contiene:

```text
backend/
  app/
    api/
      routes/
        health.py
        simulation.py
    agents/
    compute/
    config/
    core/
    simulation/
    storage/
  tests/
frontend/
  src/
    api/
    components/
    hooks/
    types/
docs/
```

El flujo implementado hoy es doble:

```text
Frontend React
  -> GET /api/v1/health
  -> GET /api/v1/simulation/bootstrap
  -> GET /api/v1/simulation/live
  -> POST /api/v1/simulation/live/start cuando no existe sesion viva
Backend FastAPI
  -> crea perfiles de agentes
  -> crea ledger inicial
  -> siembra order book sintetico
  -> calcula metricas de bootstrap
  -> devuelve SimulationSummary
```

Para la sesion viva minima implementada hoy:

```text
Frontend React
  -> consulta snapshot /api/v1/simulation/live
  -> inicia o reinicia la sesion viva
  -> poll cada 1s para refrescar estado
Backend FastAPI
  -> mantiene una sesion en memoria
  -> selecciona un subconjunto activo por tick
  -> ejecuta market intents pequenos sobre liquidez sintetica
  -> recompone el libro alrededor del nuevo precio
  -> expone tick, metricas y `recent_mid_prices` para la visualizacion viva
```

El flujo todavia no implementa persistencia, ordenes limite vivas, cancelaciones, replay ni streaming.

La visualizacion principal actual no recibe OHLCV autoritativo del backend. La UI agrupa `recent_mid_prices` por bloques para dibujar velas simples con apertura, maximo, minimo y cierre, mantiene el ultimo impacto de ballena como marcador y deja el volumen por barra como pendiente.

## Limite funcional de la primera fase

La primera fase no intentara replicar 100,000 agentes. El objetivo defendible es:

- 1,000 agentes simples;
- order book determinista;
- ledger con reservas y liquidacion correcta;
- whale shock manual;
- velas, volumen, market cap y patrimonio medio;
- base clara para escalar sin rehacer la interfaz.

## Responsabilidades

### Interfaz

La interfaz puede:

- mostrar health, bootstrap, snapshots y metricas;
- enviar configuracion de sesiones cuando existan endpoints;
- disparar shocks cuando existan endpoints;
- agrupar `recent_mid_prices` para visualizacion local cuando el backend aun no expone OHLCV;
- reproducir eventos cuando exista replay.

La interfaz no puede:

- decidir fills;
- calcular balances autoritativos;
- mutar el order book como fuente de verdad;
- inventar volumen real de mercado que el backend no haya calculado;
- almacenar memoria estrategica de agentes.

### Backend API

La API debe:

- validar parametros y contratos;
- exponer estado del motor;
- mantener los contratos consumidos por la UI;
- aislar a la UI de detalles internos del motor.

### Motor de simulacion

El motor debe:

- mantener el ledger;
- validar reservas;
- generar decisiones de agentes;
- insertar, cancelar y matchear ordenes;
- emitir eventos de mercado;
- producir snapshots y metricas.

### Core

`backend/app/core/` debe contener las piezas autoritativas:

- order book;
- matching;
- ledger;
- eventos.

El matching engine central es la parte menos paralelizable y debe mantenerse como autoridad unica.

## Flujo objetivo de simulacion

```text
1. Cargar configuracion de sesion
2. Crear agentes y asignar balances iniciales
3. Sembrar order book inicial
4. Repetir por tick:
   a. seleccionar agentes activos
   b. calcular senales y decisiones
   c. validar saldo disponible
   d. reservar cash o asset
   e. insertar/cancelar ordenes
   f. ejecutar matching
   g. actualizar ledger y memoria del agente
   h. calcular metricas agregadas
   i. emitir snapshot y eventos
5. Persistir resumen y logs
```

Este flujo sigue siendo el objetivo del MVP completo. El estado actual cubre una version minima en memoria con market intents y recentering sintetico del libro.

## Orden y determinismo

Reglas obligatorias para el matching futuro:

- FIFO dentro del mismo nivel de precio.
- Ejecucion al precio del maker segun reglas definidas.
- Uso de seed por sesion para reproducibilidad.
- Orden estable de aplicacion de eventos.

Esto permite depurar, comparar runs y migrar a servidor sin comportamientos divergentes.

## Donde escalar mas adelante

Zonas candidatas a optimizacion:

- calculo vectorizado de senales;
- activacion probabilistica de agentes;
- analitica agregada;
- serializacion de snapshots.

No mover matching central a GPU en la primera fase.

## Metricas minimas del MVP

- OHLCV
- spread
- bid depth / ask depth
- market cap simulada
- patrimonio medio por agente
- numero de trades por ventana
- impacto del whale shock

## Preparacion para funciones futuras

El diseno debe dejar sitio para:

- leverage;
- liquidaciones;
- futuros;
- market makers mas sofisticados;
- multiproducto;
- simulaciones remotas multiusuario.
