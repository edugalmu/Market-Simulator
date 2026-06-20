# Market Simulator — Documento maestro de objetivos técnicos para una simulación tipo Krafer Crypto

**Versión:** 1.0  
**Objetivo:** definir, con alto nivel técnico, cómo debe evolucionar el simulador actual hasta parecerse visual, mecánica y sistémicamente a una simulación de mercado tipo Krafer Crypto, manteniendo la arquitectura web como destino final.  
**Contexto actual del proyecto:** backend FastAPI, frontend React, gráfica OHLCV real, order book visible en modo DEV, órdenes limit con TTL, market orders, agentes, ballena del jugador, ballenas rivales, P&L, Whale Challenge, sesiones vivas por tick y order book persistente entre ticks.

---

## 1. Principio rector del simulador

El precio **no debe moverse por una fórmula directa**.

El precio debe emerger de:

1. un libro de órdenes vivo;
2. órdenes limit respaldadas por agentes con cartera;
3. órdenes de mercado que consumen liquidez;
4. liquidez irregular, fragmentada y asimétrica;
5. agentes con comportamiento simple pero persistente;
6. regímenes de mercado que alteran sesgos, volatilidad y liquidez;
7. ballenas que barren el libro;
8. reposición lenta de liquidez tras shocks;
9. eventos de absorción, gaps, pánico y squeezes;
10. OHLCV generado por trades reales.

Esto es esencial. Si una vela se dibuja directamente desde una función de ruido, el resultado será una gráfica artificial. El objetivo es que la vela sea una consecuencia del mercado, no un decorado.

---

## 2. Estado actual aceptado como punto de partida

El proyecto ya dispone de una base suficiente para evolucionar:

- Backend FastAPI.
- Frontend React.
- Simulación viva por tick.
- Order book visible en modo DEV.
- Order book persistente entre ticks.
- Órdenes limit con TTL.
- Market orders.
- Matching contra liquidez viva.
- OHLCV generado en backend.
- Gráfica principal de velas con volumen.
- Marcos temporales visuales.
- Ballena del jugador.
- Ballenas rivales sintéticas.
- P&L estimado y ejecutado.
- Whale Challenge.
- Top 10 agentes en modo DEV.
- Capital total y Mcap jugador.
- Tests backend y frontend.
- Commits funcionales ya cerrados.

El problema ya no es de interfaz básica. El problema ahora es de **calidad de simulación**.

---

## 3. Objetivo visual final

La gráfica debe parecer un mercado real, no una animación programada.

Debe mostrar de forma natural:

- velas pequeñas y grandes alternadas;
- mechas largas;
- pinbars;
- dojis;
- consolidaciones laterales;
- impulsos;
- retrocesos;
- falsas rupturas;
- barridos de liquidez;
- absorción;
- pánicos;
- short squeezes;
- zonas de bajo volumen;
- picos de volumen;
- patrón Bart Simpson;
- cambios de régimen;
- agotamiento de tendencia;
- rupturas fallidas;
- reversiones violentas.

El usuario debe sentir que está manipulando un mercado vivo, no que está pulsando botones contra una curva predecible.

---

## 4. Inspiración técnica extraída del análisis de Krafer Crypto

Del análisis obtenido mediante Gemini se consideran fiables los siguientes elementos observados o dichos explícitamente:

### 4.1 Elementos explícitos atribuidos al vídeo

- Hay traders con carteras reales.
- Cada orden del order book está asociada a un trader con dinero limitado.
- Cuando ocurre un trade, se intercambia dinero por Bitcoin real dentro del simulador.
- El mercado deja de ser infinito o puramente aleatorio.
- Con carteras limitadas, el mercado tiende a mantenerse cerca de un equilibrio.
- El jugador puede manipular el mercado con órdenes grandes.
- El volumen se muestra para ver cuándo ocurren los trades grandes.
- El patrón Bart Simpson aparece de forma emergente.
- El order book visual fue eliminado o reducido por problemas de rendimiento gráfico.
- Se mencionan unos 100.000 traders.
- Se mencionan miles de velas, hasta unas 16.000.
- Se plantean futuras liquidaciones, futuros y apalancamiento.

### 4.2 Observaciones visuales relevantes

- Una compra grande puede generar una subida vertical.
- Tras el pump puede aparecer lateralización plana con poco volumen.
- Una venta grande puede generar una bajada vertical.
- Las mechas aparecen cuando el precio invade zonas con respuesta contraria.
- Los picos de volumen coinciden con grandes órdenes.
- El volumen bajo acompaña consolidaciones.
- La absorción visual aparece como mucho volumen con poco desplazamiento final.
- La gráfica no parece una caminata aleatoria continua; parece un sistema discreto de liquidez.

### 4.3 Inferencias técnicas razonables

- El motor probablemente es tick-driven u order-driven.
- Los agentes usan reglas simples, no IA pesada.
- Se procesa un subconjunto de agentes por tick o por lote.
- El order book probablemente está agregado por niveles o buckets para rendimiento.
- Las velas se dibujan con renderizado optimizado.
- La ballena del jugador opera con market orders.
- El volumen es acumulación de trades reales.
- Los patrones salen de la interacción entre order book, liquidez y agentes.

---

## 5. Arquitectura objetivo a largo plazo

La arquitectura debe estar pensada para:

1. desarrollo local;
2. despliegue web;
3. simulaciones remotas en servidor;
4. alto número de agentes;
5. posible uso de GPU en servidor;
6. frontend web ligero;
7. motor headless testeable;
8. escalado progresivo.

### 5.1 Arquitectura funcional final

```text
Frontend React/Web
  ├─ Chart renderer
  ├─ Order book DEV
  ├─ Whale controls
  ├─ Whale Challenge
  ├─ Stats / P&L / Score
  └─ WebSocket/polling snapshots

Backend API
  ├─ FastAPI / gateway HTTP
  ├─ Session manager
  ├─ Snapshot publisher
  ├─ Game mode manager
  └─ Auth/ranking futuro

Simulation Core
  ├─ Matching engine
  ├─ Order book
  ├─ Ledger / portfolios
  ├─ Agent scheduler
  ├─ Market regime supervisor
  ├─ Liquidity manager
  ├─ Whale impact manager
  ├─ OHLCV builder
  ├─ Event log
  └─ Replay/persistence futura

Compute Layer
  ├─ CPU NumPy / Rust / C++
  ├─ GPU optional backend
  └─ batch/vectorized agent decisions

Storage
  ├─ SQLite/PostgreSQL for sessions/users/rankings
  ├─ Parquet/event log for replay
  └─ object storage if needed
```

### 5.2 Separación obligatoria

El frontend no debe decidir:

- fills;
- precio;
- balance;
- P&L autoritativo;
- order book real;
- liquidaciones;
- score autoritativo;
- regímenes.

El frontend solo debe:

- mostrar snapshots;
- enviar órdenes del jugador;
- iniciar/reiniciar retos;
- elegir visualizaciones;
- mostrar estado.

---

## 6. Consideración sobre lenguaje de programación

El stack actual es correcto para MVP, pero se debe asumir una posible evolución.

### 6.1 Corto plazo

Mantener:

- Python/FastAPI;
- React;
- TypeScript;
- motor Python optimizado;
- NumPy cuando compense;
- estructuras eficientes;
- tests.

La prioridad actual es calibrar el modelo, no reescribir.

### 6.2 Medio plazo

Si el motor empieza a ser cuello de botella:

- separar `simulation_core`;
- mantener FastAPI como capa API;
- mover el núcleo crítico a Rust o C++;
- exponer el motor por:
  - Python bindings;
  - microservicio local;
  - gRPC;
  - WebSocket;
  - proceso worker.

### 6.3 Lenguaje recomendado para motor crítico

**Rust** sería la opción preferente por:

- seguridad de memoria;
- rendimiento cercano a C++;
- estructuras de datos eficientes;
- concurrencia segura;
- buena integración con Python mediante PyO3;
- posibilidad de compilar a WASM en el futuro si se desea simulación parcial cliente.

**C++** también sería válido si se prioriza máximo rendimiento y CUDA directa, pero aumenta riesgo de errores y deuda técnica.

**Go** no es ideal para matching ultraeficiente, aunque puede servir para workers.

**Python puro** es suficiente hasta que el perfilado demuestre lo contrario.

### 6.4 Regla

No reescribir por intuición. Reescribir solo cuando:

- haya benchmarks;
- los tests estén completos;
- el modelo esté estabilizado;
- el cuello de botella esté identificado.

---

## 7. Uso de GPU

La GPU no debe ser obligatoria.

### 7.1 Qué debe seguir en CPU

- matching engine;
- order book price-time priority;
- cancelaciones individuales;
- ledger;
- liquidaciones discretas;
- eventos de trade;
- escritura de logs.

Estas operaciones son secuenciales, ramificadas y dependientes del orden.

### 7.2 Qué puede ir a GPU

- cálculo de señales de agentes;
- activación probabilística de agentes;
- actualización vectorizada de intención;
- cálculo de medias móviles;
- volatilidad;
- riesgo de liquidación;
- scoring masivo;
- simulaciones batch;
- calibración de parámetros;
- backtests internos;
- replay precomputado.

### 7.3 Diseño de compute backend

Debe existir una capa abstracta:

```text
compute/
  backend.py
  cpu_numpy.py
  gpu_cupy.py
  rust_core.py
```

Interfaz conceptual:

```python
compute_activation_mask(agent_state, market_state, regime, rng)
compute_agent_signals(agent_state, prices, regime)
update_agent_intentions(agent_state, signals, regime)
compute_risk_metrics(agent_state, price)
compute_aggregates(agent_state)
```

### 7.4 Modos

```text
compute_mode = cpu | gpu_auto | gpu_force | native
```

- `cpu`: siempre CPU.
- `gpu_auto`: usa GPU si hay tamaño suficiente.
- `gpu_force`: falla si no hay GPU.
- `native`: usa motor Rust/C++ si está disponible.

### 7.5 Servidor futuro

El despliegue web debe permitir:

- servidor CPU normal para partidas estándar;
- servidor GPU para simulaciones grandes;
- workers de simulación separados del API gateway;
- colas si hay muchas partidas simultáneas;
- límites por usuario.

---

## 8. Escala de agentes

### 8.1 Fase actual recomendada

No saltar aún a 100.000 agentes.

Usar una fase de calibración:

```text
agent_count = 2,000
```

Distribución inicial:

| Tipo | % | Número |
|---|---:|---:|
| Noise traders | 50% | 1000 |
| Market makers | 20% | 400 |
| Momentum traders | 15% | 300 |
| Mean reversion/value | 10% | 200 |
| Directional funds | 4% | 80 |
| Aggressive whales | 1% | 20 |

### 8.2 Frecuencia de actuación

| Tipo | Probabilidad de actuar por tick | Orden típica |
|---|---:|---|
| Noise | 0.05 | pequeña limit/market |
| Market maker | 0.80 | limit bid/ask |
| Momentum | 0.20 | market o limit agresiva |
| Value | 0.30 | limit pasiva |
| Directional fund | 0.02 | bloques grandes persistentes |
| Aggressive whale | 0.005 | market grande |

### 8.3 Tamaños de orden

| Tipo | Tamaño USD |
|---|---:|
| Noise | 10 - 500 |
| Market maker | 1,000 - 5,000 |
| Momentum | 500 - 2,500 |
| Value | 1,000 - 3,000 |
| Directional fund | 10,000 - 50,000 |
| Aggressive whale | 100,000 - 500,000 |

### 8.4 Duración de intención

| Tipo | Duración |
|---|---:|
| Noise | 1 tick |
| Market maker | continuo |
| Momentum | 5 - 15 ticks |
| Value | 10 - 30 ticks |
| Directional fund | 50 - 200 ticks |
| Aggressive whale | 1 - 5 ticks |

### 8.5 TTL órdenes limit

| Tipo | TTL |
|---|---:|
| Noise | 3 - 10 ticks |
| Market maker | 1 - 3 ticks |
| Momentum limit | 3 - 12 ticks |
| Value | 20 - 50 ticks |
| Directional fund | 100 - 500 ticks |

---

## 9. Portfolios y sistema cerrado

Todo agente normal debe tener cartera real.

### 9.1 Campos mínimos

```python
agent_id
strategy_type
cash_free
cash_reserved
asset_free
asset_reserved
avg_entry_price
realized_pnl
unrealized_pnl
equity
```

### 9.2 Reglas

- Una orden de compra reserva cash.
- Una orden de venta reserva asset.
- Una cancelación libera reservas.
- Un fill parcial ajusta reservas.
- Un fill total cierra orden.
- Agentes normales no pueden tener cash ni asset negativos.
- Ballenas sintéticas pueden tener una capa especial de leverage simulado, separada.

### 9.3 Objetivo

El mercado debe estabilizarse cuando nadie manipula porque los agentes se quedan sin capacidad de seguir empujando indefinidamente.

---

## 10. Order book perfecto objetivo

### 10.1 Estructura

El book debe contener órdenes individuales, no solo niveles agregados.

```python
Order:
    order_id
    agent_id
    strategy_type
    side
    price
    quantity
    remaining_quantity
    created_tick
    ttl_ticks
    flags
```

### 10.2 Flags futuros

```text
normal
market_maker
iceberg
hidden
stop
liquidation
whale
synthetic
```

### 10.3 Agregación para UI

El frontend no debe recibir órdenes individuales masivas.

El snapshot DEV debe recibir niveles agregados:

```json
{
  "price": 100.12,
  "quantity": 120.5,
  "orders": 8,
  "dominant_strategy": "market_maker"
}
```

### 10.4 Book realista

El libro no debe ser uniforme.

Parámetros iniciales:

```text
levels_per_side = 100
level_price_gap = 0.5
base_quantity_per_level = 2000 USD
quantity_random_dispersion = ±80%
gap_probability = 0.15
maker_cancel_prob = 0.10
liquidity_recovery_ticks = 15-40
```

### 10.5 Huecos de liquidez

Debe haber niveles vacíos.

Efectos:

- una market order atraviesa varios niveles rápido;
- aparecen velas con mecha;
- se producen gaps;
- el precio se mueve de forma discreta.

### 10.6 Muros de liquidez

En números redondos:

```text
price % 500 == 0
```

o en niveles de soporte/resistencia detectados.

Multiplicador:

```text
liquidity_wall_multiplier = 10
```

Uso:

- absorption;
- falsas rupturas;
- soportes;
- resistencias;
- pinbars.

---

## 11. Matching engine

### 11.1 Reglas

- Price-time priority.
- FIFO dentro del mismo precio.
- Ejecución al precio maker.
- Fills parciales.
- Actualización de ledger.
- Actualización de OHLCV por cada trade.
- Emisión de eventos.

### 11.2 Market buy

Consume asks de menor a mayor precio.

### 11.3 Market sell

Consume bids de mayor a menor precio.

### 11.4 Métricas por trade

Cada trade debe emitir:

```python
trade_id
tick
price
quantity
notional
buyer_agent_id
seller_agent_id
maker_order_id
taker_order_id
maker_strategy
taker_strategy
is_whale
is_liquidation
is_iceberg
```

Esto permitirá:

- OHLCV real;
- volumen real;
- análisis DEV;
- replay;
- ranking;
- sonido;
- efectos visuales.

---

## 12. OHLCV

### 12.1 Regla

OHLCV debe salir de trades reales.

```text
open = primer trade del bucket
high = máximo trade price
low = mínimo trade price
close = último trade price
volume = suma quantity
trades = número de trades
```

### 12.2 Buckets

Mantener:

- barra base por tick;
- agregación frontend para 5s, 10s, 30s, 1min;
- en futuro, agregación backend para timeframes largos.

### 12.3 No hacer

No dibujar mechas artificiales sin trades.

Si se quiere una mecha, debe venir de:

- market order que barre niveles;
- liquidity gap;
- iceberg/absorción;
- respuesta contraria dentro de la vela;
- liquidación;
- stop sweep.

---

## 13. Regímenes de mercado

### 13.1 Estados iniciales

```text
neutral
accumulation
uptrend
distribution
downtrend
panic
short_squeeze
post_whale_consolidation
```

### 13.2 Modelo de estado

```python
MarketRegime:
    name
    ticks_remaining
    buy_bias
    sell_bias
    volatility_multiplier
    liquidity_multiplier
    spread_multiplier
    whale_activity_multiplier
    momentum_multiplier
    mean_reversion_multiplier
    maker_cancel_multiplier
    reason
```

### 13.3 Parámetros iniciales

| Régimen | Duración | Buy/Sell | Vol | Liq | Spread | Whale | Momentum | MeanRev |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| neutral | 100-500 | 50/50 | 0.5 | 1.5 | 1.0 | 0.7 | 0.8 | 1.2 |
| accumulation | 80-300 | 58/42 | 0.7 | 1.2 | 1.1 | 0.8 | 0.9 | 1.3 |
| uptrend | 50-200 | 70/30 | 1.2 | 1.0 | 1.2 | 1.0 | 1.5 | 0.7 |
| distribution | 80-300 | 42/58 | 0.8 | 1.2 | 1.1 | 0.8 | 0.9 | 1.3 |
| downtrend | 50-200 | 30/70 | 1.3 | 0.9 | 1.3 | 1.0 | 1.5 | 0.7 |
| panic | 10-30 | 10/90 | 3.0 | 0.3 | 4.0 | 1.8 | 2.0 | 0.3 |
| short_squeeze | 5-20 | 95/5 | 4.0 | 0.2 | 5.0 | 2.0 | 2.5 | 0.2 |
| post_whale_consolidation | 30-80 | 50/50 | 0.2 | 0.5 | 2.5 | 0.4 | 0.5 | 1.0 |

### 13.4 Condiciones de entrada

#### Neutral

- baja volatilidad;
- sin shocks recientes;
- volumen normal;
- precio cerca de media.

#### Accumulation

- volumen sube;
- precio no se desplaza mucho;
- bid depth aumenta;
- varias absorciones inferiores.

#### Uptrend

- varias velas verdes;
- breakout de máximo reciente;
- volumen creciente;
- momentum positivo.

#### Distribution

- volumen alto cerca de máximos;
- avance débil;
- ask depth aumenta;
- mechas superiores.

#### Downtrend

- varias velas rojas;
- ruptura de soporte;
- momentum negativo.

#### Panic

- caída > 3% en menos de 5 ticks;
- bid depth cae;
- spread se abre;
- market sells dominan.

#### Short squeeze

- ruptura de resistencia tras sesgo vendedor previo;
- ask depth bajo;
- volumen comprador extremo;
- liquidaciones short futuras.

#### Post-whale consolidation

- orden del jugador o ballena > umbral;
- liquidez barrida;
- spread amplio;
- volumen posterior bajo.

---

## 14. Liquidez y reposición

### 14.1 Reposición lenta

Tras un shock:

```text
liquidity_recovery_ticks = 15-40
```

Durante este periodo:

- menor número de órdenes nuevas;
- spreads más amplios;
- profundidad baja;
- ruido lateral estrecho;
- posibilidad de Bart Simpson.

### 14.2 Reposición por tipo

- Market makers reponen cerca del precio.
- Value traders reponen lejos.
- Directional funds ponen muros.
- Noise aporta microliquidez.
- Momentum rara vez aporta liquidez; consume.

### 14.3 Gap probability

Base:

```text
gap_probability = 0.15
```

Por régimen:

```text
neutral = 0.08
uptrend = 0.15
downtrend = 0.18
panic = 0.50
short_squeeze = 0.55
post_whale = 0.35
```

---

## 15. Patrones visuales

### 15.1 Mechas largas

Condición:

- market order grande;
- baja densidad;
- reacción contraria en la misma vela.

Implementación:

1. La orden barre niveles.
2. Se registra high/low extremo.
3. Mean reversion o muro contrario absorbe.
4. El close vuelve hacia el open.

Visual:

- volumen alto;
- cuerpo moderado/pequeño;
- mecha larga.

### 15.2 Cuerpos grandes

Condición:

- buy/sell bias fuerte;
- momentum activo;
- liquidez baja en dirección del movimiento.

Visual:

- cuerpo grande;
- poca mecha;
- volumen creciente.

### 15.3 Compresión lateral

Condición:

- neutral;
- alta liquidez;
- baja actividad agresiva.

Visual:

- dojis;
- cuerpos pequeños;
- volumen bajo;
- spread estrecho.

### 15.4 Ruptura de rango

Condición:

- compresión previa;
- acumulación de órdenes;
- directional fund o whale barre un lado.

Visual:

- vela grande;
- volumen alto;
- continuación o fallo.

### 15.5 Falsa ruptura

Condición:

- precio rompe nivel reciente;
- encuentra muro o iceberg;
- mean reversion responde.

Visual:

- mecha larga;
- cierre dentro del rango;
- volumen alto.

### 15.6 Absorción

Condición:

- market orders agresivas;
- muro/iceberg contrario.

Visual:

- volumen muy alto;
- poco desplazamiento;
- mecha;
- cierre cerca de apertura.

### 15.7 Panic

Condición:

- ruptura rápida de soporte;
- baja bid depth;
- momentum bajista;
- futuros liquidables en fase futura.

Visual:

- velas rojas encadenadas;
- gaps;
- volumen creciente;
- spread amplio.

### 15.8 Short squeeze

Condición:

- mercado venía bajista;
- compra fuerte rompe resistencia;
- shorts futuros obligados a comprar.

Visual:

- velas verdes parabólicas;
- volumen extremo;
- mecha superior al agotarse.

### 15.9 Bart Simpson

Secuencia:

1. Compra agresiva.
2. Subida vertical.
3. Post-whale consolidation.
4. Lateralización plana.
5. Venta agresiva.
6. Bajada vertical.

Parámetros:

```text
whale_order_size = 5-10% visible ask liquidity
post_whale_duration = 40-60 ticks
post_whale_liquidity_multiplier = 0.3-0.5
noise_range = ±0.2%
directional_defense_probability = 0.20
```

---

## 16. Absorción e Iceberg Orders

### 16.1 Iceberg order

```python
IcebergOrder:
    order_id
    agent_id
    side
    price
    display_qty
    hidden_qty
    replenish_qty
    max_total_qty
```

### 16.2 Mecánica

- Solo `display_qty` aparece en el book visible.
- Si se consume, se repone desde `hidden_qty`.
- El precio no se mueve hasta agotar el iceberg.
- Cuando se rompe, puede haber slippage fuerte.

### 16.3 Parámetros

```text
display_qty = 10,000
hidden_qty = 100,000
max_iceberg_size = 15% volumen ventana
activation_near_round_numbers = true
```

### 16.4 Visual

- volumen alto;
- poco desplazamiento;
- mecha de rechazo;
- posible ruptura violenta si se agota.

---

## 17. Ballena del jugador

### 17.1 Objetivo

La ballena debe sentirse poderosa, pero no invencible.

Sus órdenes deben:

- mover el precio;
- consumir liquidez;
- activar regímenes;
- provocar reacciones de agentes;
- crear oportunidades y riesgos.

### 17.2 Market buy

Debe consumir asks.

Impacto esperado:

- sube precio;
- reduce ask depth;
- puede activar uptrend, squeeze o post_whale.

### 17.3 Market sell

Debe consumir bids.

Impacto esperado:

- baja precio;
- reduce bid depth;
- puede activar downtrend, panic o post_whale.

### 17.4 Reacción del mercado

Tras orden grande:

- MMs reducen liquidez;
- spread se abre;
- momentum puede perseguir;
- value puede contrarrestar;
- directional funds pueden defender o atacar;
- noise queda atrapado en rango.

### 17.5 No hacer

No garantizar que siempre gane.

Un 20% de las veces, la manipulación debe fallar por:

- absorción;
- directional fund contrario;
- iceberg;
- falta de liquidez para salir;
- slippage.

---

## 18. Ballenas rivales

### 18.1 Estado

Las ballenas rivales deben ser agentes especiales, no agentes normales.

Campos:

```python
rival_whale_id
cash
asset
synthetic_leverage
bias
cooldown
intent_side
intent_ticks_remaining
risk_appetite
last_action_tick
```

### 18.2 Reglas

- Pueden usar leverage sintético.
- Pueden tener saldos sintéticos negativos, pero no dentro del ledger normal.
- Tienen cooldown.
- No deben actuar cada tick.
- Deben dejar huella en DEV.

### 18.3 Actividad

Base:

```text
rival_whale_activity = 0.005 por tick
```

Multiplicadores:

- panic: x1.8
- squeeze: x2.0
- post_whale: x0.4
- neutral: x0.7

---

## 19. Agentes

### 19.1 Noise traders

Objetivo:

- microvolatilidad;
- trades pequeños;
- ruido constante.

Reglas:

- tamaño pequeño;
- probabilidad baja;
- TTL corto;
- poca memoria.

### 19.2 Market makers

Objetivo:

- liquidez;
- spread;
- book visible.

Reglas:

- cotizan bid/ask;
- cancelan rápido;
- ajustan spread por volatilidad;
- reducen tamaño en panic/squeeze;
- reponen lento tras shock.

### 19.3 Momentum

Objetivo:

- aceleraciones;
- rupturas;
- squeezes.

Reglas:

- leen retornos recientes;
- intención 5-15 ticks;
- market orders en ruptura;
- limit agresivas en continuación.

### 19.4 Mean reversion/value

Objetivo:

- retrocesos;
- absorción parcial;
- estabilización.

Reglas:

- compran bajo media;
- venden sobre media;
- órdenes limit alejadas;
- TTL largo.

### 19.5 Directional funds

Objetivo:

- presión persistente.

Reglas:

- intención 50-200 ticks;
- bloques grandes;
- muros en soportes/resistencias;
- toman beneficios.

### 19.6 Aggressive whales

Objetivo:

- shocks aleatorios;
- grandes velas;
- riesgo.

Reglas:

- cooldown largo;
- market orders grandes;
- comportamiento dependiente de régimen.

---

## 20. Modo DEV

Debe mostrar:

- order book;
- spread;
- depth;
- imbalance;
- top agents;
- market regime;
- whale mood;
- recent whale events;
- liquidity recovery state;
- gap probability actual;
- active iceberg count;
- active directional funds;
- pending liquidations futuras.

No debe invadir la gráfica principal.

---

## 21. Roadmap técnico desde el estado actual

### Iteración 1 — Regímenes de mercado explícitos

Objetivo:

- añadir `market_regime`;
- exponerlo en snapshot;
- mostrarlo en DEV;
- que modifique agentes, spread, liquidez y ballenas.

Archivos probables:

- `live.py`
- `models.py`
- `App.tsx`
- `market.ts`
- `App.css`
- `test_engine.py`

Tests:

- snapshot incluye régimen;
- régimen cambia;
- régimen afecta sesgo;
- OHLCV y book siguen válidos.

Impacto visual:

- tendencias menos aleatorias;
- fases reconocibles.

Riesgo:

- bajo/medio.

### Iteración 2 — Liquidity gaps y reposición lenta

Objetivo:

- introducir huecos de liquidez reales;
- variar gap probability por régimen;
- reponer tras shock lentamente.

Archivos:

- `order_book.py`
- `live.py`
- `test_engine.py`

Tests:

- gaps existen;
- panic aumenta gaps;
- post_whale reduce reposición.

Impacto visual:

- mechas;
- gaps;
- movimientos menos lineales.

Riesgo:

- medio.

### Iteración 3 — Absorción e Iceberg Orders

Objetivo:

- crear muros ocultos;
- mucho volumen con poco desplazamiento.

Archivos:

- `order_book.py`
- `matching.py`
- `models.py`
- `live.py`
- `test_engine.py`

Tests:

- iceberg absorbe;
- volumen sube;
- precio no atraviesa hasta agotar hidden qty.

Impacto visual:

- pinbars;
- falsas rupturas;
- soportes y resistencias.

Riesgo:

- medio/alto.

### Iteración 4 — Agentes especializados por régimen

Objetivo:

- calibrar momentum, mean reversion, directional funds y makers.

Archivos:

- `base.py`
- `registry.py`
- `live.py`
- `test_engine.py`

Tests:

- momentum compra en breakout;
- value vende sobre media;
- makers reducen liquidez en panic;
- funds sostienen intención.

Impacto visual:

- más organicidad;
- menos curva programada.

Riesgo:

- medio.

### Iteración 5 — Liquidaciones sintéticas

Objetivo:

- añadir leveraged traders;
- long/short;
- liquidation_price;
- forced market orders.

Archivos:

- nuevos modelos de leverage;
- `live.py`
- `matching.py`
- `models.py`
- DEV panel.

Tests:

- liquidación long en caída;
- liquidación short en subida;
- liquidación genera trade forzado;
- no contamina ledger normal.

Impacto visual:

- cascadas;
- squeezes;
- pánico realista.

Riesgo:

- alto.

---

## 22. Despliegue web objetivo

### 22.1 Arquitectura servidor

```text
Client Browser
  ↓ HTTPS/WebSocket
API Gateway / FastAPI
  ↓
Simulation Session Manager
  ↓
Worker Pool
  ↓
Simulation Core
  ↓
Storage / Replay / Ranking
```

### 22.2 Workers

Cada partida puede ejecutarse en:

- proceso worker;
- thread dedicado;
- task async controlada;
- contenedor aislado en fase avanzada.

### 22.3 Escalado

- sesiones cortas tipo Whale Challenge;
- límite de agentes según plan;
- snapshot rate limitado;
- replay comprimido;
- ranking guardado tras partida.

### 22.4 Seguridad

- no permitir ejecución arbitraria;
- limitar duración de partidas;
- limitar notional;
- evitar abuso de CPU;
- rate limiting;
- cleanup automático de sesiones.

---

## 23. Persistencia futura

No es prioritaria ahora, pero el diseño debe permitir:

```text
sessions
events
trades
ohlcv
orders
agent_snapshots
leaderboard
replays
```

### 23.1 Event log

Cada evento:

```python
event_id
session_id
tick
event_type
payload
```

Eventos:

- order_placed;
- order_cancelled;
- trade_executed;
- whale_order;
- regime_changed;
- iceberg_created;
- liquidation;
- game_started;
- game_ended.

---

## 24. Métricas de éxito

### 24.1 Visuales

- mechas frecuentes pero no constantes;
- picos de volumen alineados con trades grandes;
- lateralizaciones naturales;
- impulsos y retrocesos;
- Bart Simpson posible pero no garantizado;
- absorción visible;
- book que cambia gradualmente.

### 24.2 Jugabilidad

- el jugador entiende que mueve mercado;
- el jugador puede manipular;
- el jugador puede equivocarse;
- el mercado reacciona;
- el reto tiene tensión;
- cada partida es distinta.

### 24.3 Técnicas

- tests verdes;
- determinismo por seed opcional;
- backend fuente de verdad;
- snapshot estable;
- frontend sin lógica financiera autoritativa;
- rendimiento aceptable;
- posibilidad de escalar.

---

## 25. Regla final

No buscar “realismo financiero perfecto” antes de lograr “sensación de mercado vivo”.

Prioridad:

1. book vivo;
2. liquidez irregular;
3. regímenes;
4. agentes simples persistentes;
5. absorción;
6. liquidaciones;
7. rendimiento masivo;
8. GPU/nativo si los benchmarks lo exigen.

El simulador debe ser primero **jugable, visualmente creíble y manipulable**. Después será financieramente más fiel.
