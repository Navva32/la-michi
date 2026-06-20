from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Sucursal, Usuario, Producto, Venta, DetalleVenta


class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Datos La Michi', {'fields': ('rol', 'sucursal')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Datos La Michi', {'fields': ('rol', 'sucursal')}),
    )
    list_display = ('username', 'rol', 'sucursal', 'is_staff')


admin.site.register(Sucursal)
admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Producto)
admin.site.register(Venta)
admin.site.register(DetalleVenta)