# De Windows local a web

## 1. Enfoque recomendado

La forma correcta de empezar en Windows local y poder migrar despues es:

- ejecutar backend y frontend localmente,
- abrir la interfaz en navegador,
- mantener contratos estables entre UI y motor,
- y evitar cualquier dependencia fuerte de Windows en el core.

## 2. Como ejecutar localmente

Modo inicial recomendado:

- backend FastAPI en `localhost`
- frontend React en `localhost`
- WebSocket para streaming de mercado
- SQLite y Parquet en disco local

Mas adelante, si interesa, se puede empaquetar como escritorio con Tauri sin redisenar el motor.

## 3. Que queda igual al migrar a web

Si se hace bien, estas piezas no deberian cambiar mucho:

- el matching engine,
- el ledger,
- la logica de agentes,
- el scheduler de shocks,
- el formato de eventos,
- el frontend React,
- y la mayor parte de la API.

## 4. Que si cambia al migrar a web

- autenticacion y usuarios,
- aislamiento de sesiones,
- cola o scheduler para simulaciones concurrentes,
- persistencia multiusuario,
- observabilidad,
- y politicas de recursos.

## 5. Reglas para que la migracion sea sencilla

1. No meter logica de simulacion en React.
2. No meter dependencias de GUI dentro del motor.
3. No acoplar el almacenamiento a rutas de Windows.
4. No depender de estado de proceso de la UI como fuente de verdad.
5. No asumir GPU en cliente ni en servidor.

## 6. Fases de migracion recomendadas

### Fase A: local puro

- un solo usuario,
- una sesion activa,
- almacenamiento local,
- control manual de whale shocks.

### Fase B: local empaquetado

- mismo backend,
- misma UI,
- empaquetado tipo desktop.

### Fase C: web privada

- backend en servidor,
- frontend desplegado,
- sesiones por usuario,
- almacenamiento centralizado.

### Fase D: web escalable

- multiples simulaciones,
- pool de workers,
- opcion de hosts CPU y GPU,
- replay historico y colas.

## 7. Conclusion practica

Si se sigue esta arquitectura, migrar de local a web no es rehacer el proyecto. Es cambiar el lugar donde corre el backend y endurecer la capa operativa.
