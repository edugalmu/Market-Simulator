# Estrategia de GPU NVIDIA

## 1. Decision

La GPU debe ser una capacidad opcional y conmutada por configuracion.

No debe ser obligatoria para que el proyecto funcione ni localmente ni en servidor.

## 2. Donde la GPU si ayuda

Una GPU NVIDIA puede ayudar sobre todo en tareas batch y vectorizadas:

- calculo de medias, volatilidad y señales sobre muchos agentes,
- actualizacion paralela de estados numericos,
- calculo de probabilidades de activacion,
- analitica agregada,
- precomputacion de replay,
- y experimentos de calibracion masiva.

## 3. Donde la GPU no ayuda tanto

No conviene depender de GPU para:

- matching engine central,
- estructuras FIFO del libro de ordenes,
- cancelaciones finas de una sola orden,
- logica muy ramificada por evento,
- y cargas pequenas como el MVP de 1,000 agentes.

En 1,000 agentes la GPU puede incluso empeorar el rendimiento por overhead de transferencia.

## 4. Recomendacion tecnica

Usar una capa de abstraccion de computo:

- `compute/backend.py`
- `compute/cpu_numpy.py`
- `compute/gpu_cupy.py`

La API interna debe exponer funciones como:

- `compute_signals(...)`
- `compute_activation_mask(...)`
- `update_agent_state(...)`
- `compute_analytics(...)`

La simulacion no debe conocer si la implementacion es CPU o GPU.

## 5. Modos de ejecucion

Config recomendada:

```text
compute_mode = cpu | gpu_auto | gpu_force
```

Comportamiento:

- `cpu`: usa NumPy siempre.
- `gpu_auto`: intenta GPU si esta disponible y si el tamano de carga supera un umbral.
- `gpu_force`: exige GPU y falla si no esta disponible.

## 6. Umbrales sugeridos

Para esta arquitectura:

- 1,000 agentes: CPU por defecto.
- 5,000 a 20,000 agentes: benchmark obligatorio antes de activar GPU.
- 20,000+ agentes o analitica pesada: GPU probablemente util.

## 7. Requisitos en Windows local

Para activar GPU en Windows:

- driver NVIDIA estable,
- CUDA compatible,
- entorno Python con dependencias correctas,
- validacion de memoria GPU disponible.

La activacion debe ser visible en logs y en la UI para evitar confusiones.

## 8. Ruta recomendada

Fase 1:

- implementar CPU limpia y medible.

Fase 2:

- perfilar,
- localizar hotspots reales,
- mover solo calculos vectorizables a GPU.

No se debe introducir GPU antes de medir, porque aumenta complejidad operativa y de despliegue.

## 9. Implicaciones para la version web

En web el usuario no debe depender de su GPU para que la app funcione.

Opciones:

- servidor CPU normal,
- servidor con GPU para simulaciones pesadas,
- o seleccion dinamica segun capacidad del host.

La interfaz web no debe asumir que la simulacion usa GPU.
