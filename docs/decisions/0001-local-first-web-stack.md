# 0001 - Arquitectura local-first con backend FastAPI y frontend React

## Status

Accepted

## Context

El proyecto necesita ejecutarse primero en Windows local y conservar una ruta razonable hacia una version web posterior.

Tambien necesita mantener separada la logica de simulacion de la interfaz para que el order book, el ledger y los agentes puedan evolucionar sin depender de una GUI concreta.

## Decision

Usar:

- backend Python con FastAPI;
- frontend React + TypeScript con Vite;
- comunicacion HTTP en el scaffold inicial;
- WebSocket o streaming solo cuando el motor tenga ticks vivos;
- core de simulacion headless dentro del backend.

## Consequences

Ventajas:

- la UI puede correr localmente en navegador y migrar despues a web;
- el motor puede testearse sin frontend;
- los contratos API separan visualizacion y fuente de verdad;
- evita atar el core a Windows, Tauri, Electron o una GUI nativa.

Costes:

- hay que mantener contratos API y tipos frontend alineados;
- el desarrollo local requiere dos procesos mientras no haya empaquetado;
- la persistencia multiusuario queda para una fase posterior.

## Alternatives considered

TODO: no hay registro detallado de alternativas evaluadas mas alla de descartar una GUI nativa como primera fase por dificultar la migracion web.
