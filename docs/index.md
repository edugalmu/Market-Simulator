# Indice de documentacion

Este indice es el mapa tecnico del repositorio. Usalo para decidir que leer antes de cambiar codigo o documentacion.

## Por donde empezar

1. [../README.md](../README.md): entrada rapida para humanos, estado y comandos basicos.
2. [../AGENTS.md](../AGENTS.md): reglas operativas obligatorias para IAs.
3. [architecture.md](./architecture.md): limites entre backend, frontend, motor y persistencia.
4. [roadmap.md](./roadmap.md): fases aprobadas y proximo hito.

## Documentos por area

- [development.md](./development.md): instalacion, variables de entorno, comandos y politica de checks.
- [api.md](./api.md): endpoints HTTP actuales, parametros y modelos de respuesta.
- [architecture.md](./architecture.md): arquitectura objetivo y estado implementado.
- [agent-system.md](./agent-system.md): arquetipos, estado financiero y reglas de agentes.
- [gpu-strategy.md](./gpu-strategy.md): GPU opcional, compute modes y criterios de activacion.
- [local-to-web.md](./local-to-web.md): como pasar de Windows local a web sin rehacer el core.
- [roadmap.md](./roadmap.md): fases de implementacion.
- [decisions/](./decisions/): decisiones tecnicas duraderas.

## Fuentes de verdad

- Contratos HTTP actuales: [api.md](./api.md) y codigo en `backend/app/api/`.
- Tipos consumidos por la UI: `frontend/src/types/market.ts`.
- Configuracion backend: `backend/app/config/settings.py` y `backend/.env.example`.
- Configuracion frontend: `frontend/src/api/client.ts` y `frontend/.env.example`.
- Tests backend: `backend/tests/`.

## Pendiente conocido

- TODO: documentar persistencia cuando SQLite/Parquet pasen de stubs a implementacion real.
- TODO: documentar WebSocket o streaming cuando exista contrato implementado.
- TODO: documentar replay cuando existan endpoints, formatos o comandos.
- TODO: documentar decisiones de despliegue cuando haya entorno distinto al local.
