from django.db import models
from django.contrib.auth.models import AbstractUser


class Sucursal(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    ROLES = [
        ('dueno', 'Dueño'),
        ('encargado', 'Encargado'),
        ('empleado', 'Empleado'),
    ]
    rol = models.CharField(max_length=20, choices=ROLES, default='empleado')
    sucursal = models.ForeignKey(
        Sucursal, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='usuarios'
    )

    def __str__(self):
        return f"{self.username} ({self.rol})"


class Producto(models.Model):
    CATEGORIAS = [
        ('paleta', 'Paleta'),
        ('nieve', 'Nieve'),
        ('agua', 'Agua fresca'),
    ]
    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS)
    precio = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    sucursal = models.ForeignKey(
        Sucursal, on_delete=models.CASCADE, related_name='ventas'
    )
    usuario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, related_name='ventas'
    )
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Venta #{self.id} - {self.sucursal.nombre}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE, related_name='detalles'
    )
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=6, decimal_places=2)

    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"