# Market Simulator Frontend

Interfaz local Vite + React + TypeScript para el simulador de mercado.

La UI actual consume:

- `GET /api/v1/health`
- `GET /api/v1/simulation/bootstrap`

El bootstrap no ejecuta trades reales. Sirve para cablear interfaz, API y tipos antes de implementar matching, shocks y replay.

## Instalacion

```powershell
npm install
```

## Ejecucion

```powershell
npm run dev
```

Por defecto la API se lee desde:

```text
http://127.0.0.1:8000/api/v1
```

Para cambiarlo, usa `VITE_API_BASE_URL` o copia `.env.example`.

## Checks

```powershell
npm run lint
npm run build
```

## Reglas

- La UI no calcula balances autoritativos.
- La UI no decide fills ni muta el order book como fuente de verdad.
- Los tipos consumidos por la API viven en `src/types/market.ts`.
- Si cambia un contrato backend, actualizar los tipos y `../docs/api.md`.
