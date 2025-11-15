PepsiCo Taller – Sistema de Gestión de Órdenes de Trabajo, Ingresos y Agenda

Versión: 1.0 – Proyecto Final
Descripción: Sistema web completo para la gestión operativa del taller de PepsiCo: control de ingresos, órdenes de trabajo, inventario, agenda, notificaciones y administración por roles.

1. Características Principales
    Órdenes de Trabajo (OT)

    - Creación automática al registrar un ingreso.
    - Flujo completo: Ingreso → Diagnóstico → Ejecución → Pausa → Finalización.
    - Estados y prioridades configurables.
    - Adjuntar imágenes o PDF como evidencia.
    - Agenda interna por OT (eventos, citas, recordatorios).
    - Historial de estados y asignación de mecánico.

    Ingreso de Vehículos

    - Registro de patente, conductor, taller y tipo de vehículo (catálogo o personalizado).
    - Fecha y hora automáticas.
    - Observaciones.
    Subida de evidencias (fotos, PDF).
    Creación automática de la OT correspondiente.

    Inventario de Repuestos

    Registro y edición de repuestos con stock mínimo.
    Movimientos de entrada y salida.
    Alertas de stock bajo.
    Integración con reportes y dashboard.
        
    Agenda (FullCalendar)

    Vista mensual, semanal y diaria.
    Modal de creación/edición de eventos.
    Enlace directo a la OT asociada.
    Eventos con colores y estilo profesionales.
    Drag & drop deshabilitado para evitar errores.

    Dashboard Ejecutivo

    KPIs en tiempo real:
        OTs activas
        OTs en pausa
        Vehículos finalizados
        Ingresos diarios

    Gráficos y estadísticas claves:
        OTs por estado
        Por taller
        Por prioridad
        Motivos de pausa más frecuentes

    Notificaciones Internas

    Notificaciones por usuario.
    Sistema de leído/no leído.
    Indicador dinámico en el navbar.
    Autogeneración por acciones como:
    Cambios de estado de OT
    Documentos añadidos
    Pausas iniciadas/finalizadas

    Control de Usuarios y Roles

    Roles incluidos:
        Admin, Jefe de Taller, Supervisor, Mecánico, Guardia, Recepcionista, Asistente de Repuestos
    Menús dinámicos según permisos.
    Panel completo de administración:
        Crear usuarios
        Cambiar roles
        Activar/desactivar usuario
        Resetear contraseña
    Cambio de contraseña para usuarios desde el menú.

    Interfaz UX corporativa PepsiCo

    Navbar con logo oficial.
    Paleta corporativa azul #003DA5.
    Cards limpias con sombras suaves.
    Formularios modernos y responsivos.
    Dashboard digno de producción.

2. Requisitos del Sistema
Backend

Python 3.13+
Django 5.1+
Django ORM
SQLite (desarrollo) / PostgreSQL recomendado (producción)
Frontend
Bootstrap 5
FullCalendar 6.1
Íconos Bootstrap
SweetAlert2 (opcional)
Entorno
Git
virtualenv o venv de Python

3. Instalación y Configuración
3.1 Clonar repositorio
git clone <tu_repo>
cd pepsico-ot

3.2 Crear entorno virtual
python -m venv .venv


Activar:

Windows:

.venv\Scripts\activate


Linux / Mac:

source .venv/bin/activate

3.3 Instalar dependencias
pip install -r requirements.txt

3.4 Migrar base de datos
python manage.py makemigrations
python manage.py migrate

3.5 Crear usuario administrador
python manage.py createsuperuser

3.6 Ejecutar servidor
python manage.py runserver

4. Estructura del Proyecto
pepsico-ot/
│
├── core/               # Usuarios, roles, notificaciones, agenda
├── ot/                 # Órdenes de Trabajo
├── inventario/         # Repuestos y movimientos
├── taller/             # Vehículos y talleres
│
├── templates/          # HTML templates
├── static/             # CSS, JS, imágenes
│
├── config/             # Configuración global
└── manage.py

5. Roles y Permisos
Rol	Accesos principales
Admin	Todo el sistema, usuarios, roles
Jefe de Taller	Dashboard, OTs, inventario, agenda
Supervisor	Dashboard, reportes, OTs
Mecánico	Solo OTs asignadas (Mis OTs)
Recepcionista	Ingreso de vehículos, agenda
Guardia	Solo registrar ingreso
Asistente de Repuestos	Inventario y movimientos
6. Datos Iniciales (Carga Rápida)

Desde el Django Admin, puedes crear rápidamente:

Usuarios por rol

Tipos de vehículo

Repuestos base

Talleres

Estados de OT