# Sistema de agentes

## 1. Objetivo del MVP

El MVP debe usar 1,000 agentes simples, no porque sea el limite final, sino porque permite validar:

- contabilidad correcta,
- comportamiento emergente,
- whale shock,
- y rendimiento suficiente para desarrollar con seguridad.

## 2. Distribucion inicial recomendada

Distribucion sugerida para la primera fase:

- 450 noise traders
- 200 momentum traders
- 150 mean reversion traders
- 120 market makers simples
- 80 fundamental traders

El whale no tiene por que ser un agente permanente del pool. Puede ser un actor de control inyectado por el usuario o por el scheduler de shocks.

## 3. Estado financiero por agente

Cada agente debe tener, como minimo:

- `agent_id`
- `strategy_type`
- `cash_free`
- `cash_reserved`
- `asset_free`
- `asset_reserved`
- `avg_entry_price`
- `realized_pnl`
- `unrealized_pnl`
- `equity`

Regla contable:

- una orden de compra reserva cash,
- una orden de venta reserva asset,
- una cancelacion libera reservas,
- y un fill parcial ajusta saldo reservado y saldo libre.

## 4. Memoria estrategica por agente

Ademas del saldo, cada agente necesita memoria operativa:

- `last_action_tick`
- `cooldown_ticks`
- `last_seen_price`
- `short_ma`
- `long_ma`
- `vol_estimate`
- `fear_score`
- `fair_value_estimate`
- `inventory_target`
- `aggression_level`

Esta memoria no se guarda en la interfaz. Vive en el motor.

## 5. Como almacenar 1,000 agentes

Para el MVP se recomienda un modelo mixto:

- configuracion estatica por agente en registros ligeros,
- estado numerico en arrays,
- ordenes vivas referenciadas por `agent_id`.

La forma recomendada es `struct-of-arrays` para el estado numerico:

- `cash_free[i]`
- `cash_reserved[i]`
- `asset_free[i]`
- `asset_reserved[i]`
- `fear_score[i]`
- `fair_value_estimate[i]`

Esto es mas eficiente que miles de objetos pesados y facilita una futura aceleracion vectorizada.

## 6. Como definir el comportamiento

Cada agente debe responder a una funcion conceptual:

```text
decide(agent_state, market_snapshot, rng) -> intents
```

Un `intent` puede ser:

- `place_limit`
- `place_market`
- `cancel_order`
- `do_nothing`

## 7. Reglas minimas por arquetipo

### Noise trader

- Actua con probabilidad fija.
- Usa tamano pequeno.
- Elige buy/sell con sesgo neutral o suavemente dependiente del flujo.

### Momentum trader

- Compra si el retorno reciente es positivo.
- Vende si el retorno reciente es negativo.
- Puede usar market order pequena o limit agresiva.

### Mean reversion trader

- Vende cuando el precio se separa demasiado de una media local por arriba.
- Compra cuando se separa demasiado por abajo.

### Market maker simple

- Mantiene bid y ask alrededor de un precio de referencia.
- Ajusta spread segun volatilidad local.
- Reduce quoting si el inventario se desvía mucho.

### Fundamental trader

- Opera contra la diferencia entre precio observado y fair value interno.
- Su fair value puede tener ruido o drift lento.

## 8. Activacion por tick

No todos los agentes deben actuar en cada tick.

Para el MVP:

- seleccionar un subconjunto activo por tick,
- con probabilidad dependiente del arquetipo,
- y con cooldown para evitar ruido artificial excesivo.

Esto reduce carga y se acerca mejor a un mercado heterogeneo.

## 9. Whale mode

El whale mode debe ser un modulo de shocks, no una excepcion ad hoc.

Operaciones minimas:

- whale buy market
- whale sell market
- liquidity pull
- panic wave

El shock debe entrar por el mismo motor que cualquier otro evento para no romper la contabilidad.

## 10. Persistencia del estado

Persistencia recomendada:

- estado vivo del tick actual en RAM,
- snapshots periodicos del mercado,
- event log append-only,
- resumen final por sesion.

No hace falta persistir cada variable de cada agente en cada tick para el MVP. Eso se vuelve costoso demasiado pronto.

## 11. Ruta de escalado

Para pasar de 1,000 a mas agentes:

1. vectorizar senales y estados,
2. mantener el book central,
3. reducir frecuencia de snapshot,
4. separar simulacion y rendering,
5. mover calculos batch a GPU si compensa,
6. reescribir nucleo critico si el perfilado lo justifica.
