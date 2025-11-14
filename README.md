PepsiCo Taller – Sistema de Gestión de Órdenes de Trabajo, Ingresos y Agenda

    Versión: 1.0 – Proyecto Final

    Sistema web desarrollado para la gestión operativa de un taller de PepsiCo: control de ingresos de vehículos, creación y seguimiento de Órdenes de Trabajo (OT), administración de repuestos, agenda de eventos, reportes, notificaciones y panel de administración con roles.

1. Características Principales
    Órdenes de Trabajo (OT)

    - Creación automática al ingresar un vehículo.
    - Flujo completo: ingreso → asignación → ejecución → cierre.
    - Estados y prioridades configurables.
    - Adjuntar imágenes o PDF como evidencia.
    - Agenda interna por OT (eventos, citas, recordatorios).

    Ingreso de Vehículos

    - Patente, conductor, tipo, fecha/hora automática.
    - Observaciones.
    - Adjuntar fotos o documentos.
    - Asignación automática de la OT correspondiente.

    Inventario de Repuestos

    - Registro de repuestos con stock mínimo.
    - Movimientos de entrada y salida.
    - Alerta de stock bajo.
    - Integración con reportes y dashboard.

    Agenda FullCalendar

    - Vista Mes / Semana / Día.
    - Modal de creación/edición.
    - Eventos estilizados.
    - Enlace a OT desde el calendario.
    - Drag & drop deshabilitado para evitar errores.

    Dashboard Ejecutivo

    - KPIs en tiempo real.
    - Gráficos de rendimiento.
    - OTs activas, cerradas, por taller, por mecánico.
    - Top vehículos y top repuestos usados.

    Notificaciones Internas

    - Notificaciones por usuario.
    - Marcado como leído y ver todas.
    - Indicador dinámico en el navbar.
    - Generación automática por acciones del sistema (OTs, inventario).

    Control de Usuarios y Roles

    - Roles: Admin, Jefe de Taller, Supervisor, Mecanico, Guardia, Recepcionista, Asistente de Repuestos.
    - Accesos y menús dinámicos según rol.
    - Panel para crear usuarios, activar/desactivar y reasignar roles.
    - Cambio de contraseña por administración.

    UX y Estética PepsiCo

    - Navbar corporativa con logo.
    - Paleta PepsiCo: azul #003DA5, blanco, gris.
    - Cards limpias con sombras.
    - Dashboard moderno.
    - Formularios ordenados y consistentes.

2. Requisitos del Sistema
    
    - Backend
    - Python 3.13+
    - Django 5.1+
    - Django ORM (SQLite para desarrollo)
    - Frontend
    - Bootstrap 5
    - FullCalendar 6.1
    - SweetAlert2 (opcional)
    - Íconos Bootstrap
    - Entorno
    - Git instalado
    - virtualenv o entorno Python venv

3. Instalación y Configuración

    3.1 Clonar repositorio
    - git clone <tu_repo>
    - cd pepsico-ot

    3.2 Crear entorno virtual
    - python -m venv .venv
    - source .venv/bin/activate  # Linux/Mac
    - .venv\Scripts\activate     # Windows

    3.3 Instalar dependencias
    - pip install -r requirements.txt

    3.4 Migrar base de datos
    - python manage.py makemigrations
    - python manage.py migrate

    3.5 Crear usuario administrador
    - python manage.py createsuperuser

    3.6 Ejecutar servidor
    - python manage.py runserver

4. Estructura del Proyecto

    pepsico-ot/
    │
    ├── core/               # Usuarios, roles, notificaciones, agenda
    ├── ot/                 # Órdenes de Trabajo
    ├── inventario/         # Repuestos y movimientos
    ├── taller/             # Vehículos y talleres
    │
    ├── templates/          # Todos los templates HTML
    ├── static/             # CSS, JS, imágenes (logo PepsiCo, favicon)
    │
    ├── config/             # Configuración global del proyecto
    └── manage.py

5. Roles y Permisos

    Rol - Permisos principales
    Admin - Ve todo, edita todo, panel de usuarios
    Jefe Taller	- Dashboard, OTs, inventario, agenda
    Supervisor - Dashboard, reportes, OTs
    Mecánico - Mis OTs asignadas
    Recepcionista - Ingreso de vehículos, agenda
    Guardia - Registrar solo ingreso
    Asistente de Repuestos - Inventario y movimientos

6. Datos Iniciales (Carga Rápida)

    - Puedes usar el Django Admin para crear:
    - Usuarios por rol
    - Tipos de vehículo
    - Repuestos base
    - Estados de OT
    - Taller(es)