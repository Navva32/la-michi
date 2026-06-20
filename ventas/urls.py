from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('productos/', views.producto_lista, name='producto_lista'),
    path('productos/nuevo/', views.producto_crear, name='producto_crear'),
    path('productos/<int:pk>/editar/', views.producto_editar, name='producto_editar'),
    path('productos/<int:pk>/borrar/', views.producto_borrar, name='producto_borrar'),
    path('ventas/', views.venta_lista, name='venta_lista'),
    path('ventas/nueva/', views.venta_crear, name='venta_crear'),
    path('ventas/<int:pk>/', views.venta_detalle, name='venta_detalle'),
]