from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from inventario.models import Repuesto, MovimientoStock
from taller.models import Taller, TipoVehiculo, Vehiculo
from ot.models import OrdenTrabajo, EstadoOT


class BaseInventarioTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bodega1", password="test123")

        # Repuesto
        self.repuesto = Repuesto.objects.create(
            codigo="R-001",
            descripcion="Filtro de aceite",
            unidad="un",
            stock_actual=Decimal("10.00"),
            stock_minimo=Decimal("2.00"),
        )

        # Para movimientos asociados a OT
        self.taller = Taller.objects.create(nombre="Taller Central")
        tipo = TipoVehiculo.objects.create(nombre="Camión")
        veh = Vehiculo.objects.create(
            patente="EE-FF33",
            marca="Mercedes",
            modelo="Actros",
            tipo=tipo,
        )
        self.ot = OrdenTrabajo.objects.create(
            folio="OT-INV-001",
            vehiculo=veh,
            taller=self.taller,
            responsable="Resp",
            estado_actual=EstadoOT.INGRESADO,
        )


class MovimientoStockTests(BaseInventarioTestCase):
    def test_entrada_aumenta_stock(self):
        """
        Una ENTRADA debe aumentar el stock_actual del repuesto.
        """
        MovimientoStock.objects.create(
            repuesto=self.repuesto,
            tipo=MovimientoStock.ENTRADA,
            cantidad=Decimal("5.00"),
            motivo="Compra",
            creado_por=self.user,
        )
        self.repuesto.refresh_from_db()
        self.assertEqual(self.repuesto.stock_actual, Decimal("15.00"))

    def test_salida_disminuye_stock(self):
        """
        Una SALIDA debe disminuir el stock_actual del repuesto.
        """
        MovimientoStock.objects.create(
            repuesto=self.repuesto,
            tipo=MovimientoStock.SALIDA,
            cantidad=Decimal("3.00"),
            motivo="Consumo en OT",
            ot=self.ot,
            creado_por=self.user,
        )
        self.repuesto.refresh_from_db()
        self.assertEqual(self.repuesto.stock_actual, Decimal("7.00"))

    def test_salida_no_puede_dejar_stock_negativo(self):
        """
        No debe permitir salidas que dejen stock negativo.
        """
        with self.assertRaises(ValidationError):
            MovimientoStock.objects.create(
                repuesto=self.repuesto,
                tipo=MovimientoStock.SALIDA,
                cantidad=Decimal("999.00"),
                motivo="Consumo en OT",
                ot=self.ot,
                creado_por=self.user,
            )

    def test_salida_con_motivo_consumo_ot_sin_ot_lanza_error(self):
        """
        Si el motivo es 'Consumo en OT' pero no se asocia una OT, debe lanzar error.
        """
        with self.assertRaises(ValidationError):
            MovimientoStock.objects.create(
                repuesto=self.repuesto,
                tipo=MovimientoStock.SALIDA,
                cantidad=Decimal("1.00"),
                motivo="Consumo en OT",
                ot=None,
                creado_por=self.user,
            )

    def test_entrada_no_puede_tener_ot(self):
        """
        Las ENTRADAS no deben asociarse a una OT.
        """
        with self.assertRaises(ValidationError):
            MovimientoStock.objects.create(
                repuesto=self.repuesto,
                tipo=MovimientoStock.ENTRADA,
                cantidad=Decimal("5.00"),
                motivo="Compra",
                ot=self.ot,
                creado_por=self.user,
            )

    def test_ajuste_sin_motivo_lanza_error(self):
        """
        Un AJUSTE sin motivo debe lanzar ValidationError.
        """
        with self.assertRaises(ValidationError):
            MovimientoStock.objects.create(
                repuesto=self.repuesto,
                tipo=MovimientoStock.AJUSTE,
                cantidad=Decimal("1.00"),
                motivo="",
                creado_por=self.user,
            )

    def test_ajuste_puede_ser_positivo_o_negativo(self):
        """
        Un AJUSTE puede subir o bajar stock siempre que no quede negativo.
        """
        # Ajuste negativo válido
        MovimientoStock.objects.create(
            repuesto=self.repuesto,
            tipo=MovimientoStock.AJUSTE,
            cantidad=Decimal("-3.00"),
            motivo="Ajuste inventario",
            creado_por=self.user,
        )
        self.repuesto.refresh_from_db()
        self.assertEqual(self.repuesto.stock_actual, Decimal("7.00"))

        # Ajuste que dejaría stock negativo → error
        with self.assertRaises(ValidationError):
            MovimientoStock.objects.create(
                repuesto=self.repuesto,
                tipo=MovimientoStock.AJUSTE,
                cantidad=Decimal("-999.00"),
                motivo="Error inventario",
                creado_por=self.user,
            )
