# Meme Fábricas Backend 🚀

Sistema centralizado de gestión de producción para fábricas textiles, diseñado para optimizar el flujo de trabajo, el control de inventarios y la asignación de maquinaria. Este backend está preparado para la integración de un motor de Machine Learning destinado a la predicción de tiempos de culminación de órdenes.

## 📋 Descripción del Proyecto

Meme Fábricas Backend proporciona una API robusta y escalable construida con **FastAPI** y **Python 3.14**. El sistema permite gestionar el ciclo de vida completo de una orden de producción, desde la verificación de insumos hasta el seguimiento del operario en la maquinaria.

### Características Principales:
*   **Gestión de Órdenes:** Control detallado de líneas de pedido, estados y prioridades.
*   **Control de Inventario:** Gestión de insumos (telas, hilos, botones) con alertas de stock mínimo.
*   **Monitoreo de Maquinaria:** Seguimiento del estado operativo de máquinas (Merrow, Planas, Corte, etc.).
*   **Gestión de Operarios:** Registro de habilidades por tipo de máquina y eficiencia.
*   **Seguridad:** Autenticación basada en JWT (OAuth2) con control de roles (Admin, Supervisor, Operario).
*   **Preparado para IA:** Arquitectura diseñada para alimentar un motor de inferencia asíncrona.

---

## 🛠️ Stack Tecnológico

*   **Lenguaje:** [Python 3.14+](https://www.python.org/)
*   **Framework API:** [FastAPI](https://fastapi.tiangolo.com/)
*   **Validación de Datos:** [Pydantic v2](https://docs.pydantic.dev/latest/)
*   **ORM / Base de Datos:** [SQLModel](https://sqlmodel.tiangolo.com/) (SQLAlchemy + Pydantic)
*   **Base de Datos:** PostgreSQL 15
*   **Seguridad:** Passlib (Bcrypt) & Python-jose
*   **Contenedores:** Docker & Docker Compose

---

## 🏗️ Arquitectura

El proyecto sigue una **Arquitectura Modular por Dominios**, lo que facilita la mantenibilidad y evita acoplamientos innecesarios.

```text
app/
├── api/v1/           # Routers de FastAPI (Capa de Transporte)
├── core/             # Configuraciones globales y Seguridad
├── db/               # Modelos de persistencia y sesiones
├── schemas/          # Modelos de validación Pydantic (Inmutables)
└── services/         # Lógica de Negocio y Motor ML
```

Para más detalles sobre los estándares de desarrollo, consulta el archivo [GEMINI.md](./GEMINI.md).

---

## 🚀 Instalación y Despliegue

### Requisitos Previos
*   Docker y Docker Compose instalados.
*   Un archivo `.env` configurado en la raíz (ver `.env.example`).

### Pasos para levantar el entorno:

1.  **Clonar el repositorio:**
    ```bash
    git clone <url-del-repositorio>
    cd memexp
    ```

2.  **Configurar variables de entorno:**
    Crea un archivo `.env` basado en la configuración necesaria para `DATABASE_URL` y `SECRET_KEY`.

3.  **Levantar con Docker Compose:**
    ```bash
    docker-compose up --build
    ```

La API estará disponible en `http://localhost:8000` y la documentación interactiva en:
*   **Swagger UI:** `http://localhost:8000/docs`
*   **ReDoc:** `http://localhost:8000/redoc`

---

## 🔑 Autenticación

El sistema utiliza tokens de acceso JWT. Para probar los endpoints protegidos:
1.  Usa el endpoint `/login` para obtener un `access_token`.
2.  Incluye el token en el encabezado de tus peticiones:
    `Authorization: Bearer <tu_token>`

---

## 🧪 Desarrollo y Pruebas

*   **Migraciones:** El sistema utiliza `create_db_and_tables()` para inicialización en desarrollo. Para producción, se recomienda el uso de Alembic.
*   **Logs:** Los logs de SQL se pueden activar mediante la variable `ECHO_SQL=True` en el `.env`.

---

## 📧 Contacto
Desarrollado por el equipo de ingeniería de Consorcio Flexus.
```

<!--
[PROMPT_SUGGESTION]Crea un archivo .env.example que incluya todas las variables necesarias mencionadas en el README[/PROMPT_SUGGESTION]
[PROMPT_SUGGESTION]Implementa un servicio base en app/services/orden_service.py para gestionar la creación de órdenes[/PROMPT_SUGGESTION]
