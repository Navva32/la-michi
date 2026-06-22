"""
Módulo de análisis de ventas.
Genera un resumen de datos y produce recomendaciones de negocio.
Usa Amazon Bedrock (Claude) para el análisis, con un motor de
reglas como respaldo si el servicio no está disponible.
"""
import json
import boto3
from botocore.exceptions import ClientError
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper
from django.utils import timezone
from datetime import timedelta
from .models import Venta, DetalleVenta

BEDROCK_MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"
AWS_REGION = "us-east-1"


def construir_resumen():
    """Arma un resumen numérico de las ventas para alimentar el análisis."""
    hoy = timezone.localdate()
    inicio = hoy - timedelta(days=30)

    ventas = Venta.objects.filter(fecha__date__gte=inicio)
    detalles = DetalleVenta.objects.filter(venta__fecha__date__gte=inicio)

    por_sucursal = list(ventas.values('sucursal__nombre')
                        .annotate(total=Sum('total'), num=Count('id'))
                        .order_by('-total'))

    top_productos = list(detalles.values('producto__nombre')
                         .annotate(unidades=Sum('cantidad'),
                                   ingreso=Sum(ExpressionWrapper(
                                       F('cantidad') * F('precio_unitario'),
                                       output_field=DecimalField())))
                         .order_by('-unidades')[:5])

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
    Intenta generar recomendaciones con Claude vía Amazon Bedrock.
    Si falla, usa el motor de reglas como respaldo.
    """
    if resumen['num_ventas'] == 0:
        return ['Aún no hay suficientes ventas registradas para generar un análisis. '
                'Registra más ventas y vuelve a intentarlo.']

    try:
        return _recomendaciones_con_bedrock(resumen)
    except Exception as e:
        print(f"Bedrock no disponible, usando respaldo. Detalle: {e}")
        return _recomendaciones_con_reglas(resumen)


def _recomendaciones_con_bedrock(resumen):
    """Llama a Claude vía Bedrock para generar el análisis."""
    dias_nombre = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
    vpd = {dias_nombre[k]: round(v, 2) for k, v in resumen['ventas_por_dia'].items()}

    datos = {
        'periodo': f"últimos {resumen['periodo_dias']} días",
        'venta_total': resumen['total_general'],
        'numero_de_ventas': resumen['num_ventas'],
        'ventas_por_sucursal': resumen['por_sucursal'],
        'productos_mas_vendidos': resumen['top_productos'],
        'ventas_por_dia_semana': vpd,
    }

    prompt = (
        "Eres un analista de negocios para una franquicia de paleterías llamada La Michi. "
        "A partir de los siguientes datos de ventas, genera entre 3 y 5 recomendaciones "
        "de negocio concretas, accionables y específicas para el dueño. Responde en español, "
        "en un tono profesional pero claro. Devuelve ÚNICAMENTE una lista JSON de strings, "
        "sin texto adicional, sin markdown. Ejemplo de formato: "
        '["recomendación 1", "recomendación 2"].\n\n'
        f"Datos:\n{json.dumps(datos, ensure_ascii=False, indent=2)}"
    )

    client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}],
    })

    response = client.invoke_model(modelId=BEDROCK_MODEL_ID, body=body)
    respuesta = json.loads(response['body'].read())
    texto = respuesta['content'][0]['text'].strip()

    recomendaciones = json.loads(texto)
    return recomendaciones


def _recomendaciones_con_reglas(resumen):
    """Motor de respaldo basado en reglas sobre los datos reales."""
    recomendaciones = []
    dias_nombre = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']

    suc = resumen['por_sucursal']
    if len(suc) >= 2:
        lider = suc[0]
        rezagada = suc[-1]
        recomendaciones.append(
            f"La sucursal {lider['sucursal__nombre']} es la de mayor venta "
            f"(${lider['total']:.2f} en {lider['num']} ventas). En contraste, "
            f"{rezagada['sucursal__nombre']} es la más baja (${rezagada['total']:.2f}). "
            f"Considera revisar qué funciona en {lider['sucursal__nombre']} "
            f"y replicarlo en {rezagada['sucursal__nombre']}."
        )

    if resumen['top_productos']:
        estrella = resumen['top_productos'][0]
        recomendaciones.append(
            f"Tu producto estrella es {estrella['producto__nombre']} con "
            f"{estrella['unidades']} unidades vendidas. Asegura su disponibilidad "
            f"constante y úsalo como gancho en promociones."
        )

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

    if resumen['num_ventas'] > 0:
        ticket = resumen['total_general'] / resumen['num_ventas']
        recomendaciones.append(
            f"Tu ticket promedio es de ${ticket:.2f}. Para aumentarlo, considera "
            f"combos (paleta + agua) o sugerir un segundo producto en cada venta."
        )

    return recomendaciones