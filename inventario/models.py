from django.db import models, transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# Opcional: si ya tienes unidades normalizadas, usa choices; si no, texto libre
UNIDADES = [
    ("un", "Unidad"),
    ("kg", "Kilogramo"),
    ("lt", "Litro"),
    ("mt", "Metro"),
]

class Repuesto(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=255)
    unidad = models.CharField(max_length=10, choices=UNIDADES, default="un")
    stock_actual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.descripcion}"

    @property
    def en_minimo(self):
        try:
            return float(self.stock_actual) <= float(self.stock_minimo)
        except Exception:
            return False


class MovimientoStock(models.Model):
    ENTRADA = "ENTRADA"
    SALIDA  = "SALIDA"
    AJUSTE  = "AJUSTE"
    TIPO_CHOICES = [(ENTRADA, "Entrada"), (SALIDA, "Salida"), (AJUSTE, "Ajuste")]

    repuesto = models.ForeignKey(Repuesto, on_delete=models.PROTECT, related_name="movimientos")
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    motivo = models.CharField(max_length=255, blank=True, default="")
    # Asocia consumo a OT si corresponde (salidas)
    ot = models.ForeignKey("ot.OrdenTrabajo", on_delete=models.SET_NULL, null=True, blank=True, related_name="movimientos_repuesto")
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]

    def clean(self):
        if self.cantidad is None or self.cantidad == 0:
            raise ValidationError("La cantidad debe ser distinta de 0.")
        if self.tipo == self.SALIDA and not self.ot and self.motivo == "Consumo en OT":
            raise ValidationError("Debe asociar la OT al consumo.")
            # política: forzamos asociar salida a una OT (puedes relajar esto si quieres)
            raise ValidationError("Las salidas deben asociarse a una OT.")
        if self.tipo == self.ENTRADA and self.ot:
            raise ValidationError("Las entradas no se asocian a OT.")
        if self.tipo == self.AJUSTE and not self.motivo:
            raise ValidationError("El ajuste requiere un motivo.")

    def aplicar_stock(self):
        # Aplica el movimiento al stock actual. Protegido por transacción en save()
        if self.tipo == self.ENTRADA:
            self.repuesto.stock_actual = (self.repuesto.stock_actual or 0) + self.cantidad
        elif self.tipo == self.SALIDA:
            nuevo = (self.repuesto.stock_actual or 0) - self.cantidad
            if nuevo < 0:
                raise ValidationError("Stock insuficiente para realizar la salida.")
            self.repuesto.stock_actual = nuevo
        elif self.tipo == self.AJUSTE:
            # Ajuste puede ser positivo o negativo (cantidad con signo)
            nuevo = (self.repuesto.stock_actual or 0) + self.cantidad
            if nuevo < 0:
                raise ValidationError("El ajuste deja stock negativo.")
            self.repuesto.stock_actual = nuevo

    def save(self, *args, **kwargs):
        self.clean()
        with transaction.atomic():
            super().save(*args, **kwargs)  # guardo el movimiento
            # recargo repuesto con lock for update si quisieras en DB robustas
            self.repuesto.refresh_from_db()
            # aplicar y guardar repuesto
            self.aplicar_stock()
            self.repuesto.save()

            # Alerta por stock mínimo (si cae al mínimo luego del movimiento)
            try:
                from core.services import notificar
                if self.repuesto.en_minimo and self.tipo != self.ENTRADA:
                    # notifica a quien crea (o al admin/jefe taller) — por ahora al creador si existe
                    if self.creado_por:
                        notificar(
                            destinatario=self.creado_por,
                            titulo=f"Stock bajo: {self.repuesto.codigo}",
                            mensaje=f"{self.repuesto.descripcion} en mínimo (stock {self.repuesto.stock_actual} / min {self.repuesto.stock_minimo}).",
                            url="/inventario/repuestos/"
                        )
            except Exception:
                pass
