from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper
from django.utils import timezone
from datetime import timedelta
from .models import Producto, Venta, Sucursal, DetalleVenta
from .forms import ProductoForm, DetalleVentaFormSet


@login_required
def dashboard(request):
    es_dueno = request.user.rol == 'dueno'

    ventas = Venta.objects.all()
    detalles = DetalleVenta.objects.all()
    if not es_dueno:
        ventas = ventas.filter(sucursal=request.user.sucursal)
        detalles = detalles.filter(venta__sucursal=request.user.sucursal)

    hoy = timezone.localdate()

    ventas_hoy = ventas.filter(fecha__date=hoy)
    total_hoy = ventas_hoy.aggregate(s=Sum('total'))['s'] or 0
    num_hoy = ventas_hoy.count()
    ticket_promedio = (total_hoy / num_hoy) if num_hoy else 0
    total_historico = ventas.aggregate(s=Sum('total'))['s'] or 0

    inicio = hoy - timedelta(days=6)
    ventas_semana = (ventas.filter(fecha__date__gte=inicio)
                     .values('fecha__date')
                     .annotate(total=Sum('total'))
                     .order_by('fecha__date'))
    mapa = {v['fecha__date']: float(v['total']) for v in ventas_semana}
    labels_dias, datos_dias = [], []
    for i in range(7):
        dia = inicio + timedelta(days=i)
        labels_dias.append(dia.strftime('%d/%m'))
        datos_dias.append(mapa.get(dia, 0))

    top_productos = (detalles
                     .values('producto__nombre')
                     .annotate(unidades=Sum('cantidad'),
                               ingreso=Sum(ExpressionWrapper(
                                   F('cantidad') * F('precio_unitario'),
                                   output_field=DecimalField())))
                     .order_by('-unidades')[:5])

    por_sucursal = None
    if es_dueno:
        por_sucursal = (ventas.values('sucursal__nombre')
                        .annotate(total=Sum('total'), num=Count('id'))
                        .order_by('-total'))

    return render(request, 'dashboard.html', {
        'es_dueno': es_dueno,
        'total_hoy': total_hoy,
        'num_hoy': num_hoy,
        'ticket_promedio': ticket_promedio,
        'total_historico': total_historico,
        'labels_dias': labels_dias,
        'datos_dias': datos_dias,
        'top_productos': top_productos,
        'por_sucursal': por_sucursal,
    })

# ---- Productos ----
@login_required
def producto_lista(request):
    productos = Producto.objects.all().order_by('nombre')
    categoria = request.GET.get('categoria', '')
    if categoria:
        productos = productos.filter(categoria=categoria)
    return render(request, 'productos/lista.html', {
        'productos': productos,
        'categoria_actual': categoria,
        'categorias': Producto.CATEGORIAS,
    })


@login_required
def producto_crear(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('producto_lista')
    else:
        form = ProductoForm()
    return render(request, 'productos/form.html', {'form': form, 'titulo': 'Nuevo producto'})


@login_required
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('producto_lista')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'productos/form.html', {'form': form, 'titulo': 'Editar producto'})


@login_required
def producto_borrar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        return redirect('producto_lista')
    return render(request, 'productos/confirmar_borrar.html', {'producto': producto})


# ---- Ventas ----
@login_required
def venta_crear(request):
    if not request.user.sucursal:
        return render(request, 'ventas/sin_sucursal.html')

    if request.method == 'POST':
        venta = Venta(sucursal=request.user.sucursal, usuario=request.user)
        formset = DetalleVentaFormSet(request.POST, instance=venta)
        if formset.is_valid():
            filas = [f for f in formset
                     if f.cleaned_data.get('producto') and f.cleaned_data.get('cantidad')]
            if filas:
                venta.save()
                total = 0
                for f in filas:
                    detalle = f.save(commit=False)
                    detalle.venta = venta
                    detalle.precio_unitario = detalle.producto.precio
                    detalle.save()
                    total += detalle.subtotal()
                venta.total = total
                venta.save()
                return redirect('venta_detalle', pk=venta.pk)
            error = 'Agrega al menos un producto con su cantidad.'
            return render(request, 'ventas/form.html', {'formset': formset, 'error': error})
    else:
        formset = DetalleVentaFormSet(instance=Venta())
    return render(request, 'ventas/form.html', {'formset': formset})


@login_required
def venta_lista(request):
    ventas = Venta.objects.select_related('sucursal', 'usuario')
    if request.user.rol == 'dueno':
        sucursal_id = request.GET.get('sucursal', '')
        if sucursal_id:
            ventas = ventas.filter(sucursal_id=sucursal_id)
    else:
        ventas = ventas.filter(sucursal=request.user.sucursal)
        sucursal_id = ''
    fecha = request.GET.get('fecha', '')
    if fecha:
        ventas = ventas.filter(fecha__date=fecha)
    ventas = ventas.order_by('-fecha')
    return render(request, 'ventas/lista.html', {
        'ventas': ventas,
        'sucursales': Sucursal.objects.all(),
        'sucursal_actual': sucursal_id,
        'fecha_actual': fecha,
        'es_dueno': request.user.rol == 'dueno',
    })


@login_required
def venta_detalle(request, pk):
    venta = get_object_or_404(Venta.objects.select_related('sucursal', 'usuario'), pk=pk)
    if request.user.rol != 'dueno' and venta.sucursal != request.user.sucursal:
        return redirect('venta_lista')
    return render(request, 'ventas/detalle.html', {'venta': venta})