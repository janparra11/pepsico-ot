from datetime import timedelta

from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from taller.models import Taller, TipoVehiculo, Vehiculo
from ot.models import (
    OrdenTrabajo,
    EstadoOT,
    PausaOT,
)


class BaseOTTestCase(TestCase):
    def setUp(self):
        # Usuario mecánico
        self.user = User.objects.create_user(username="mecanico1", password="test123")

        # Taller
        self.taller = Taller.objects.create(
            nombre="Taller Principal",
            direccion="Calle Falsa 123",
            capacidad=10,
        )

        # Tipo de vehículo
        self.tipo = TipoVehiculo.objects.create(nombre="Camión")

        # Vehículo
        self.vehiculo = Vehiculo.objects.create(
            patente="AA-BB11",
            marca="Volvo",
            modelo="FH",
            tipo=self.tipo,
        )


class OrdenTrabajoModelTests(BaseOTTestCase):
    def test_duracion_horas_calculada_correctamente(self):
        """
        Verifica que duracion_horas calcule correctamente la diferencia entre
        fecha_ingreso y fecha_cierre en horas.
        """
        ahora = timezone.now()
        ot = OrdenTrabajo.objects.create(
            folio="OT-001",
            vehiculo=self.vehiculo,
            taller=self.taller,
            responsable="Juan Pérez",
            estado_actual=EstadoOT.INGRESADO,
        )

        # Simulamos 2 horas de trabajo
        ot.fecha_ingreso = ahora - timedelta(hours=2)
        ot.fecha_cierre = ahora
        ot.save()

        self.assertAlmostEqual(ot.duracion_horas, 2.0, places=2)

    def test_esta_atrasada_activa_con_compromiso_vencido(self):
        """
        Si la OT está activa y la fecha_compromiso ya pasó, debe marcarse como atrasada.
        """
        ahora = timezone.now()
        ot = OrdenTrabajo.objects.create(
            folio="OT-002",
            vehiculo=self.vehiculo,
            taller=self.taller,
            responsable="Juan Pérez",
            estado_actual=EstadoOT.REPARACION,
            fecha_compromiso=ahora - timedelta(hours=1),  # compromiso ya vencido
        )

        self.assertTrue(ot.esta_atrasada)

    def test_esta_atrasada_cerrada_antes_de_compromiso(self):
        """
        Si la OT se cerró antes de la fecha_compromiso, NO debe considerarse atrasada.
        """
        ahora = timezone.now()
        ot = OrdenTrabajo.objects.create(
            folio="OT-003",
            vehiculo=self.vehiculo,
            taller=self.taller,
            responsable="Juan Pérez",
            estado_actual=EstadoOT.CERRADO,
            fecha_compromiso=ahora + timedelta(hours=1),
            activa=False,
        )
        ot.fecha_ingreso = ahora - timedelta(hours=2)
        ot.fecha_cierre = ahora
        ot.save()

        self.assertFalse(ot.esta_atrasada)

    def test_unica_ot_activa_por_vehiculo(self):
        """
        La restricción uniq_ot_activa_por_vehiculo impide tener más de una OT activa
        por vehículo.
        """
        OrdenTrabajo.objects.create(
            folio="OT-010",
            vehiculo=self.vehiculo,
            taller=self.taller,
            responsable="Resp 1",
            estado_actual=EstadoOT.INGRESADO,
            activa=True,
        )

        with self.assertRaises(IntegrityError):
            OrdenTrabajo.objects.create(
                folio="OT-011",
                vehiculo=self.vehiculo,
                taller=self.taller,
                responsable="Resp 2",
                estado_actual=EstadoOT.DIAGNOSTICO,
                activa=True,
            )

    def test_puede_existir_ot_cerrada_y_activa_en_distintos_vehiculos(self):
        """
        Se pueden crear varias OTs mientras solo haya una activa por vehículo.
        """
        veh2 = Vehiculo.objects.create(
            patente="CC-DD22",
            marca="Scania",
            modelo="R500",
            tipo=self.tipo,
        )

        # OT activa en vehiculo 1
        OrdenTrabajo.objects.create(
            folio="OT-020",
            vehiculo=self.vehiculo,
            taller=self.taller,
            responsable="Resp 1",
            estado_actual=EstadoOT.INGRESADO,
            activa=True,
        )

        # OT activa en vehiculo 2 → permitido
        OrdenTrabajo.objects.create(
            folio="OT-021",
            vehiculo=veh2,
            taller=self.taller,
            responsable="Resp 2",
            estado_actual=EstadoOT.REPARACION,
            activa=True,
        )


class PausaOTModelTests(BaseOTTestCase):
    def setUp(self):
        super().setUp()
        self.ot = OrdenTrabajo.objects.create(
            folio="OT-P001",
            vehiculo=self.vehiculo,
            taller=self.taller,
            responsable="Resp",
            estado_actual=EstadoOT.REPARACION,
            activa=True,
        )

    def test_no_permite_dos_pausas_abiertas_para_misma_ot(self):
        """
        La constraint uq_pausa_abierta_por_ot impide dos pausas sin fin para la misma OT.
        """
        PausaOT.objects.create(
            ot=self.ot,
            motivo="Esperando repuesto",
        )

        with self.assertRaises(IntegrityError):
            PausaOT.objects.create(
                ot=self.ot,
                motivo="Segundo motivo",
            )

    def test_puede_crear_nueva_pausa_luego_de_cerrar_la_anterior(self):
        """
        Una vez que la pausa anterior tiene fin, se puede crear otra.
        """
        p1 = PausaOT.objects.create(
            ot=self.ot,
            motivo="Esperando repuesto",
        )
        p1.fin = timezone.now()
        p1.save()

        # Ahora sí se puede crear una nueva pausa abierta
        p2 = PausaOT.objects.create(
            ot=self.ot,
            motivo="Otra espera",
        )
        self.assertIsNone(p2.fin)
