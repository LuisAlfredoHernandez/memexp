# gemini.md - Estándares de Desarrollo: Meme Fábrica Backend

Este documento establece las directrices arquitectónicas, de estilo y de desarrollo para el backend de **Meme Fábricas**, desarrollado con **FastAPI** y **Python 3.14**. El objetivo de estos lineamientos es garantizar un sistema altamente mantenible, escalable y preparado para la integración del motor de Machine Learning (ML) enfocado en la predicción de tiempos de culminación de órdenes.

---

## 1. Arquitectura del Proyecto y Modularización

El backend adopta una **Arquitectura Modular por Dominios**. Cada entidad central del negocio posee su propio ecosistema aislado. Queda estrictamente prohibido mezclar la lógica de diferentes actores dentro de un mismo archivo para evitar acoplamientos y errores de importación circular.

### 1.1 Estructura de Directorios Operativa

```text
app/
├── api/                  # Capa de transporte (HTTP Routers)
│   └── v1/               # Endpoints independientes por dominio
│       ├── ordenes.py
│       ├── operarios.py
│       ├── maquinas.py
│       ├── insumos.py
│       └── usuarios.py
├── core/                 # Configuraciones globales, seguridad y JWT
├── db/                   # Sesión y modelos de persistencia (SQLAlchemy / SQLModel)
├── schemas/              # Modelos de validación Pydantic v2 (Inmutables)
│   ├── orden.py
│   ├── operario.py
│   ├── maquina.py
│   ├── insumo.py
│   └── usuario.py
└── services/             # Lógica de Negocio y Conectores de Machine Learning
    ├── orden_service.py
    ├── operario_service.py
    ├── maquina_service.py
    ├── insumo_service.py
    └── ml_engine/        # Módulo aislado del Motor de IA
        ├── __init__.py
        ├── predictor.py  # Clase principal de inferencia asíncrona
        └── models/       # Binarios/Pesos del modelo (.pkl, .onnx) ```

---

## 2. Gestión del Entorno con Docker

El entorno de desarrollo y producción se gestiona a través de Docker y Docker Compose para asegurar la consistencia y reproducibilidad.

**Directriz clave:** Cada cambio de código generado que introduzca nuevas dependencias de sistema, librerías de Python, o servicios externos (como bases de datos, colas de mensajes, etc.), **debe** ir acompañado de las actualizaciones correspondientes en los archivos `Dockerfile` y/o `docker-compose.yml`.