# 0002 - CPU por defecto y GPU opcional

## Status

Accepted

## Context

El MVP apunta a 1,000 agentes simples. En ese rango, ejecutar calculos en GPU puede no compensar por overhead y complejidad operativa.

El matching engine central usa estructuras secuenciales y reglas FIFO, por lo que no es buen candidato inicial para GPU.

## Decision

Mantener CPU como modo por defecto y tratar GPU NVIDIA como acelerador opcional para calculos batch y vectorizables.

La interfaz interna de configuracion es:

- `compute_mode=cpu`
- `compute_mode=gpu_auto`
- `compute_mode=gpu_force`

El backend debe funcionar sin GPU.

## Consequences

Ventajas:

- reduce complejidad del MVP;
- mantiene compatibilidad local y futura web;
- permite medir antes de optimizar;
- evita que usuarios sin GPU queden bloqueados.

Costes:

- los beneficios de GPU se posponen hasta tener hotspots medidos;
- habra que mantener una frontera clara entre compute backend y motor.

## Alternatives considered

No se registran alternativas con evidencia medida. Cualquier cambio hacia GPU obligatoria debe justificarse con perfilado o requisitos concretos.
