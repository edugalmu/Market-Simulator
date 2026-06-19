# API actual

La API actual es un contrato HTTP local para cablear la UI con el backend. Ya expone una sesion viva minima en memoria, pero todavia no representa el motor completo del MVP final.

Base URL por defecto:

```text
http://127.0.0.1:8000/api/v1
```

OpenAPI interactivo:

```text
http://127.0.0.1:8000/docs
```

## GET /

Endpoint raiz fuera del prefijo `/api/v1`.

Si existe `frontend/dist`, sirve la app web integrada.

Si no existe `frontend/dist`, devuelve nombre, version, fase y enlaces utiles como comprobacion manual rapida.

## GET /api/v1/health

Devuelve estado basico de la API y configuracion de compute.

Respuesta:

```json
{
  "name": "Market Simulator API",
  "version": "0.1.0",
  "phase": "scaffold",
  "compute_modes": ["cpu", "gpu_auto", "gpu_force"],
  "default_compute_mode": "cpu",
  "gpu_enabled": false,
  "docs": ["/docs", "/api/v1/simulation/defaults", "/api/v1/simulation/bootstrap"]
}
```

## GET /api/v1/simulation/defaults

Devuelve la configuracion base de una sesion.

Modelo:

```json
{
  "seed": 7,
  "agent_count": 1000,
  "initial_price": 100.0,
  "initial_cash": 50000.0,
  "initial_asset": 1.25,
  "compute_mode": "cpu"
}
```

## GET /api/v1/simulation/bootstrap

Genera una sesion bootstrap deterministica para la UI.

Este endpoint no ejecuta ticks continuos ni persistencia. Siembra perfiles de agentes, ledger inicial y order book sintetico para exponer metricas de arranque.

Parametros query:

- `seed`: entero `>= 1`, por defecto `7`.
- `agent_count`: entero entre `100` y `5000`, por defecto `1000`.
- `initial_price`: numero `> 0`, por defecto `100.0`.
- `initial_cash`: numero `> 0`, por defecto `50000.0`.
- `initial_asset`: numero `>= 0`, por defecto `1.25`.
- `compute_mode`: `cpu`, `gpu_auto` o `gpu_force`, por defecto `cpu`.

Respuesta resumida:

```json
{
  "session_id": "bootstrap-7-1000",
  "status": "bootstrap",
  "config": {
    "seed": 7,
    "agent_count": 1000,
    "initial_price": 100.0,
    "initial_cash": 50000.0,
    "initial_asset": 1.25,
    "compute_mode": "cpu"
  },
  "agent_mix": [
    { "strategy": "noise", "count": 450 }
  ],
  "order_book": {
    "best_bid": 99.9,
    "best_ask": 100.1,
    "mid_price": 100.0,
    "spread_bps": 20.0,
    "bid_depth": 124.8,
    "ask_depth": 124.8,
    "bids": [],
    "asks": []
  },
  "metrics": {
    "market_cap": 125000.0,
    "average_agent_equity": 50125.0,
    "total_asset_inventory": 1250.0,
    "active_compute_backend": "cpu"
  },
  "notes": []
}
```

La lista `agent_mix` contiene todas las estrategias del mix calculado. Las listas `bids` y `asks` contienen hasta cinco niveles por lado en la respuesta real.

Errores:

- `400` si `compute_mode=gpu_force` y `MARKET_SIMULATOR_GPU_ENABLED` no esta habilitado.
- `422` si FastAPI rechaza parametros que no cumplen las restricciones de tipo o rango.

## GET /api/v1/simulation/whale-shock/preview

Ejecuta un barrido real de liquidez sobre el libro sembrado usando un shock sintetico de ballena.

Este endpoint no persiste la sesion. Reconstruye un mercado bootstrap, aplica una market order de compra o venta y devuelve el estado antes y despues del barrido.

Parametros query:

- `side`: `buy` o `sell`, por defecto `sell`.
- `notional`: numero `> 0`, por defecto `1000.0`.
- `seed`: entero `>= 1`, por defecto `7`.
- `agent_count`: entero entre `100` y `5000`, por defecto `1000`.
- `initial_price`: numero `> 0`, por defecto `100.0`.
- `initial_cash`: numero `> 0`, por defecto `50000.0`.
- `initial_asset`: numero `>= 0`, por defecto `1.25`.
- `compute_mode`: `cpu`, `gpu_auto` o `gpu_force`, por defecto `cpu`.

Respuesta resumida:

```json
{
  "session_id": "whale-sell-7-1000",
  "config": {
    "seed": 7,
    "agent_count": 1000,
    "initial_price": 100.0,
    "initial_cash": 50000.0,
    "initial_asset": 1.25,
    "compute_mode": "cpu"
  },
  "shock": {
    "side": "sell",
    "requested_notional": 3000.0,
    "requested_quantity": 30.0,
    "matched_notional": 2993.4,
    "matched_quantity": 30.0,
    "quantity_remaining": 0.0,
    "average_fill_price": 99.78,
    "trades_executed": 3,
    "price_impact_bps": -18.0
  },
  "order_book_before": {},
  "order_book_after": {},
  "whale_balance": {
    "cash_free": 2993.4,
    "cash_reserved": 0.0,
    "asset_free": 0.0,
    "asset_reserved": 0.0,
    "total_equity": 2993.4
  },
  "notes": []
}
```

La respuesta real incluye snapshots completos de `order_book_before` y `order_book_after`.

Errores:

- `400` si el modo de compute no puede resolverse o si algun valor genera una validacion interna del motor.
- `422` si FastAPI rechaza parametros por tipo o rango.

## POST /api/v1/simulation/live/start

Inicia una sesion viva minima en memoria. Si ya existe una sesion viva, la reemplaza por una nueva con la configuracion solicitada.

Parametros query:

- `seed`: entero `>= 1`, por defecto `7`.
- `agent_count`: entero entre `100` y `5000`, por defecto `1000`.
- `initial_price`: numero `> 0`, por defecto `100.0`.
- `initial_cash`: numero `> 0`, por defecto `50000.0`.
- `initial_asset`: numero `>= 0`, por defecto `1.25`.
- `tick_interval_ms`: entero entre `200` y `5000`, por defecto `750`.
- `compute_mode`: `cpu`, `gpu_auto` o `gpu_force`, por defecto `cpu`.

Respuesta resumida:

```json
{
  "session_id": "live-7-8453eb37",
  "status": "running",
  "tick": 1,
  "tick_interval_ms": 750,
  "config": {},
  "order_book": {
    "mid_price": 100.0
  },
  "recent_mid_prices": [100.0],
  "last_tick": {
    "tick": 1,
    "active_agents": 23,
    "trades_executed": 23,
    "price_change_bps": 0.0,
    "mid_price": 100.0
  }
}
```

La respuesta real incluye `agent_mix`, `metrics`, timestamps y el snapshot completo del libro.

Errores:

- `400` si el modo de compute no puede resolverse o si algun valor no pasa la validacion interna del motor.
- `422` si FastAPI rechaza parametros por tipo o rango.

## GET /api/v1/simulation/live

Devuelve el snapshot de la sesion viva actual.

Si no existe una sesion activa o detenida en memoria, devuelve `404`.

Campos principales:

- `status`: `running` o `stopped`.
- `tick`: tick actual.
- `tick_interval_ms`: frecuencia objetivo del loop.
- `order_book`: snapshot autoritativo resumido.
- `metrics`: metricas agregadas del mercado.
- `recent_mid_prices`: traza compacta de mid-prices recientes.
- `last_tick`: resumen del ultimo tick ejecutado.

## POST /api/v1/simulation/live/step

Avanza manualmente la sesion viva actual.

Parametros query:

- `ticks`: entero entre `1` y `120`, por defecto `1`.

Si la sesion esta corriendo, este endpoint fuerza ticks adicionales sobre el mismo estado en memoria. Si la sesion esta detenida, permite seguir avanzandola manualmente.

Errores:

- `404` si no existe una sesion viva en memoria.
- `422` si FastAPI rechaza el parametro `ticks`.

## POST /api/v1/simulation/live/whale-order

Ejecuta una orden de ballena sobre la sesion viva actual. No reconstruye un bootstrap nuevo: actua sobre el order book y el estado vivo que ya estan corriendo en memoria.

Body JSON:

```json
{
  "side": "buy",
  "notional": 3000
}
```

Tambien acepta `"side": "sell"`.

Reglas actuales:

- usa el libro vivo actual;
- actualiza el snapshot de la sesion;
- actualiza el balance de la ballena;
- deja un sesgo de impacto que decae en varios ticks para que el shock sea visible y jugable;
- registra `last_whale_order` en la sesion viva.

Respuesta resumida:

```json
{
  "snapshot": {
    "session_id": "live-7-ea931f8c",
    "status": "running",
    "tick": 29,
    "order_book": {
      "mid_price": 100.31
    },
    "last_whale_order": {
      "side": "buy",
      "impact_label": "BUY IMPACT",
      "requested_notional": 3000.0,
      "matched_notional": 3000.0,
      "matched_quantity": 29.887,
      "average_fill_price": 100.38,
      "trades_executed": 4,
      "mid_price_before": 100.16,
      "mid_price_after": 100.31,
      "absolute_price_change": 0.15,
      "price_impact_bps": 14.98,
      "remaining_side_depth": 78.913
    },
    "whale_balance": {
      "cash_free": 247000.0,
      "asset_free": 5029.887,
      "total_equity": 751547.97
    }
  },
  "whale_order": {},
  "whale_balance": {}
}
```

Campos relevantes de `whale_order`:

- `requested_notional`
- `matched_notional`
- `matched_quantity`
- `quantity_remaining`
- `average_fill_price`
- `trades_executed`
- `mid_price_before`
- `mid_price_after`
- `absolute_price_change`
- `price_impact_bps`
- `remaining_side_depth`
- `impact_label`

Errores:

- `404` si no existe una sesion viva actual.
- `400` si el notional es invalido o si la cuenta de ballena no tiene saldo suficiente.
- `422` si FastAPI rechaza el body.

## POST /api/v1/simulation/live/stop

Detiene la sesion viva actual pero deja el ultimo snapshot en memoria para inspeccion o avance manual posterior.

Errores:

- `404` si no existe una sesion viva en memoria.

## Contratos frontend

La UI consume estos modelos en:

- `frontend/src/types/market.ts`
- `frontend/src/api/client.ts`

Si cambia cualquier campo consumido por la UI, actualizar esos archivos junto con este documento.

## Contratos pendientes

- TODO: endpoint de pausa/reanudacion sin recrear la sesion.
- TODO: canal de streaming para ticks, snapshots y eventos.
- TODO: aplicar shocks persistentes adicionales aparte de la orden directa de ballena.
- TODO: endpoints de persistencia y replay.
