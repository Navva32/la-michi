# La Michi — Sistema de Gestión de Ventas

App web diseñada para digitalizar el proceso de ventas en paletería La Michi, el producto significa la transición entre lo analógico y lo digital mediante una plataforma con acceso por roles, registro de ventas, reportes y un análisis IA con sugerencias basadas en datos.

**Aplicación desplegada:** http://34.228.144.60

**Autor:** Diego Alejandro Nava

---

## El problema

La Michi opera varias sucursales que venden paletas, nieves y aguas frescas. Hasta ahora el registro de ventas se hacía a mano, con libreta y WhatsApp, lo que hacía difícil juntar la información, comparar cómo le iba a cada sucursal y tomar decisiones con datos en vez de a ojo. Lo que hice fue digitalizar el registro de ventas por sucursal y, encima de eso, darle al dueño reportes y recomendaciones que pueda usar.

---

## Qué hace

- **Acceso por roles:** tres tipos de usuario (dueño, encargado, empleado), cada uno con permisos distintos.
- **Registro de ventas:** se captura una venta con varios productos a la vez; el total se calcula solo y el precio de cada producto se guarda tal como estaba al momento de venderlo.
- **Gestión de productos:** crear, ver, editar y borrar productos, con filtro por categoría.
- **Listados con filtros:** las ventas se pueden filtrar por fecha y por sucursal.
- **Control por sucursal:** cada usuario ve únicamente las ventas de su sucursal; el dueño ve todas.
- **Dashboard:** números clave (ventas del día, ticket promedio, total histórico), gráfica de los últimos 7 días, top de productos y comparativo entre sucursales.
- **Análisis con IA:** usando Amazon Bedrock, genera recomendaciones de negocio a partir de los datos reales de ventas, con un respaldo por reglas si el servicio falla.

---

## Stack y por qué lo elegí

| Capa | Tecnología | Por qué |
|------|------------|---------|
| Backend + Frontend | Django 6 (templates) | Trae autenticación, ORM y panel de administración ya hechos, así que pude enfocar el tiempo en el negocio en lugar de armar todo desde cero. Al tener frontend y backend en un mismo proyecto, el despliegue se simplifica. |
| Base de datos | PostgreSQL | Relacional, sólida y se lleva bien con Amazon RDS. |
| Estilos | Bootstrap 5 | Para que la interfaz se viera limpia sin pelearme con CSS. |
| Gráficas | Chart.js | Ligera y suficiente para las gráficas del dashboard. |
| IA | Amazon Bedrock (Claude) | Generar recomendaciones en lenguaje natural sin salir del ecosistema de AWS. |
| Servidor de aplicación | Gunicorn | Para correr Django en producción (el runserver de Django no es para eso). |
| Servidor web | Nginx | Recibe las visitas, sirve los archivos estáticos y le pasa las peticiones a Gunicorn. |

---

## Arquitectura en AWS

Todo está desplegado de punta a punta en AWS:

- **EC2 (t2.micro, free tier):** servidor Ubuntu donde corre Django con Gunicorn, y Nginx al frente como servidor web público.
- **RDS PostgreSQL (db.t3.micro, free tier):** la base de datos, administrada por AWS y sin acceso público; solo el EC2 puede conectarse a ella mediante el grupo de seguridad.
- **Amazon Bedrock:** el servicio de IA, que el servidor invoca usando un rol de IAM, sin tener credenciales escritas en el código.

El flujo es: el usuario entra por HTTP, Nginx recibe la petición y se la pasa a Gunicorn, Django procesa la lógica y consulta RDS, y para el análisis Django llama a Bedrock. Las credenciales de AWS no están en el código: las maneja el rol de IAM asignado al EC2.

---

## Modelo de datos

Son cinco entidades principales:

- **Sucursal:** cada punto de venta de la franquicia.
- **Usuario:** parte del usuario de Django, pero le agregué el rol y la sucursal a la que pertenece.
- **Producto:** el catálogo (nombre, categoría, precio).
- **Venta:** cada venta registrada (fecha, sucursal, usuario, total).
- **DetalleVenta:** las líneas de cada venta (producto, cantidad, precio unitario); es la que conecta Venta con Producto.

Las relaciones: una sucursal tiene muchas ventas, una venta tiene muchos detalles, cada detalle apunta a un producto, y cada usuario pertenece a una sucursal.

---

## Cómo correrlo en local

### Necesitas
- Python 3.12 o superior
- PostgreSQL 16 o superior

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/Navva32/la-michi.git
cd la-michi

# 2. Crear y activar el ambiente virtual
python3 -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Crear la base de datos en PostgreSQL
createdb michi_db

# 5. Configurar variables de entorno
# Crear un archivo .env en la raíz con el contenido de abajo
```

Contenido del archivo `.env`:

```
SECRET_KEY=una-cadena-larga-y-aleatoria
DEBUG=True
DB_NAME=michi_db
DB_USER=tu_usuario_postgres
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1
```

```bash
# 6. Aplicar migraciones
python manage.py migrate

# 7. Crear un superusuario
python manage.py createsuperuser

# 8. Levantar el servidor
python manage.py runserver
```

Con eso la app queda en `http://127.0.0.1:8000/`.

---

## Roles y permisos

| Rol | Qué puede hacer |
|-----|-----------------|
| **Dueño** | Todo: ve todas las sucursales, el dashboard completo y el módulo de análisis con IA. |
| **Encargado** | Ve y registra ventas de su sucursal. |
| **Empleado** | Registra y consulta ventas de su sucursal. |

El control no es solo de lo que se muestra en pantalla: las consultas filtran los datos por sucursal, así que un usuario no puede meterse a la información de una sucursal que no es la suya aunque quiera.

---

## Sobre el módulo de IA

Lo armé separando la lógica en dos partes: una función junta un resumen de las ventas y otra genera las recomendaciones. A la hora de generar, primero intenta llamar a Claude por Amazon Bedrock, mandándole el resumen y pidiéndole recomendaciones de negocio. Si Bedrock no está disponible por lo que sea, entra un motor de reglas que usa esos mismos datos para dar recomendaciones, de modo que la sección nunca se queda sin responder. Lo hice así a propósito para que la demo no dependa de que todo salga perfecto en el momento.

---

## Decisiones que vale la pena mencionar

- **Variables de entorno:** los datos sensibles (la SECRET_KEY, la contraseña de la base) no están en el código, sino fuera. Por eso el repositorio puede ser público sin exponer nada.
- **Precio congelado en la venta:** cada línea de venta guarda el precio que tenía el producto en ese momento, así que si luego cambio el precio, las ventas viejas no se alteran.
- **Base de datos sin acceso público:** RDS solo acepta conexiones desde el EC2. Es más seguro y además evita el costo de una IP pública.
- **Rol de IAM para Bedrock:** el servidor usa la IA sin tener llaves escritas en el código.
- **Respaldo del módulo de IA:** si el servicio externo falla, el análisis igual responde.

---

## Siguientes pasos

- Módulo de inventario que descuente stock automáticamente con cada venta y avise cuando haya que reabastecer.
- Exportar reportes a Excel y PDF.
- Notificaciones de stock crítico.
- CI/CD para automatizar el despliegue.

---

*Proyecto desarrollado como reto técnico.*
