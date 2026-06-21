"""
Módulo de análisis de ventas.
Genera un resumen de datos y produce recomendaciones de negocio.
Por ahora usa un motor basado en reglas; está preparado para
conectarse a un LLM (Amazon Bedrock) en la fase de despliegue.
"""
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper
from django.utils import timezone
from datetime import timedelta
from .models import Venta, DetalleVenta


def construir_resumen():
    """Arma un resumen numérico de las ventas para alimentar el análisis."""
    hoy = timezone.localdate()
    inicio = hoy - timedelta(days=30)

    ventas = Venta.objects.filter(fecha__date__gte=inicio)
    detalles = DetalleVenta.objects.filter(venta__fecha__date__gte=inicio)

    # Ventas por sucursal
    por_sucursal = list(ventas.values('sucursal__nombre')
                        .annotate(total=Sum('total'), num=Count('id'))
                        .order_by('-total'))

    # Productos más vendidos
    top_productos = list(detalles.values('producto__nombre')
                         .annotate(unidades=Sum('cantidad'),
                                   ingreso=Sum(ExpressionWrapper(
                                       F('cantidad') * F('precio_unitario'),
                                       output_field=DecimalField())))
                         .order_by('-unidades')[:5])

    # Ventas por día de la semana (0=lunes ... 6=domingo)
    ventas_por_dia = {}
    for v in ventas:
        dia = v.fecha.weekday()
        ventas_por_dia[dia] = ventas_por_dia.get(dia, 0) + float(v.total)

    return {
        'periodo_dias': 30,
        'total_general': float(ventas.aggregate(s=Sum('total'))['s'] or 0),
        'num_ventas': ventas.count(),
        'por_sucursal': por_sucursal,
        'top_productos': top_productos,
        'ventas_por_dia': ventas_por_dia,
    }


def generar_recomendaciones(resumen):
    """
    Motor de recomendaciones basado en reglas sobre los datos reales.
    En la fase de AWS, esta función se reemplazará/complementará con
    una llamada a un LLM vía Amazon Bedrock.
    """
    recomendaciones = []
    dias_nombre = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']

    if resumen['num_ventas'] == 0:
        return ['Aún no hay suficientes ventas registradas para generar un análisis. '
                'Registra más ventas y vuelve a intentarlo.']

    # 1. Sucursal líder y rezagada
    suc = resumen['por_sucursal']
    if len(suc) >= 2:
        lider = suc[0]
        rezagada = suc[-1]
        recomendaciones.append(
            f"La sucursal {lider['sucursal__nombre']} es la de mayor venta "
            f"(${lider['total']:.2f} en {lider['num']} ventas). En contraste, "
            f"{rezagada['sucursal__nombre']} es la más baja (${rezagada['total']:.2f}). "
            f"Considera revisar qué está funcionando en {lider['sucursal__nombre']} "
            f"y replicarlo en {rezagada['sucursal__nombre']}."
        )

    # 2. Producto estrella
    if resumen['top_productos']:
        estrella = resumen['top_productos'][0]
        recomendaciones.append(
            f"Tu producto estrella es {estrella['producto__nombre']} con "
            f"{estrella['unidades']} unidades vendidas. Asegura su disponibilidad "
            f"constante y considera promociones que lo usen como gancho."
        )

    # 3. Día más fuerte y más débil
    vpd = resumen['ventas_por_dia']
    if vpd:
        dia_fuerte = max(vpd, key=vpd.get)
        dia_debil = min(vpd, key=vpd.get)
        if dia_fuerte != dia_debil:
            recomendaciones.append(
                f"El {dias_nombre[dia_fuerte]} es tu día más fuerte y el "
                f"{dias_nombre[dia_debil]} el más débil. Considera una promoción "
                f"especial los {dias_nombre[dia_debil]} para nivelar la demanda."
            )

    # 4. Ticket promedio
    if resumen['num_ventas'] > 0:
        ticket = resumen['total_general'] / resumen['num_ventas']
        recomendaciones.append(
            f"Tu ticket promedio es de ${ticket:.2f}. Para aumentarlo, considera "
            f"combos (paleta + agua) o sugerir un segundo producto al momento de la venta."
        )

    return recomendaciones