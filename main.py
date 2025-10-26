# main.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, make_response
from flask_login import login_required, current_user
from models import db, Cliente, Producto, Documento, DetalleDocumento, User
from datetime import datetime

main_bp = Blueprint('main', __name__)

# ----------------------------------------------------------------------
# 1. DASHBOARD PRINCIPAL
# ----------------------------------------------------------------------
@main_bp.route('/')
@login_required
def index():
    return render_template('dashboard.html', username=current_user.username)

# ----------------------------------------------------------------------
# 2. CRUD CLIENTES (CON BÚSQUEDA POR NOMBRE/RUC)
# ----------------------------------------------------------------------
@main_bp.route('/clientes')
@login_required
def clientes_index():
    query = request.args.get('q') # Obtiene el texto de búsqueda
    
    if query:
        search = f"%{query}%"
        clientes = Cliente.query.filter(
            (Cliente.nombre.like(search)) | 
            (Cliente.ruc_dni.like(search))
        ).all()
        flash(f'Mostrando resultados para: "{query}"', 'info')
    else:
        clientes = Cliente.query.all()
        
    return render_template('clientes_index.html', clientes=clientes, query=query)

@main_bp.route('/clientes/nuevo', methods=['GET', 'POST'])
@login_required
def crear_cliente():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        ruc_dni = request.form.get('ruc_dni')
        direccion = request.form.get('direccion')
        if Cliente.query.filter_by(ruc_dni=ruc_dni).first():
            flash('Ya existe un cliente con ese RUC/DNI.', 'danger')
            return redirect(url_for('main.crear_cliente'))
        nuevo_cliente = Cliente(nombre=nombre, ruc_dni=ruc_dni, direccion=direccion)
        db.session.add(nuevo_cliente)
        db.session.commit()
        flash('Cliente registrado exitosamente.', 'success')
        return redirect(url_for('main.clientes_index'))
    return render_template('clientes_form.html', title='Registrar Cliente')

@main_bp.route('/clientes/editar/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    if request.method == 'POST':
        cliente.nombre = request.form.get('nombre')
        cliente.ruc_dni = request.form.get('ruc_dni')
        cliente.direccion = request.form.get('direccion')
        db.session.commit()
        flash(f'Cliente {cliente.nombre} actualizado exitosamente.', 'success')
        return redirect(url_for('main.clientes_index'))
    return render_template('clientes_form.html', title='Editar Cliente', cliente=cliente)

@main_bp.route('/clientes/eliminar/<int:cliente_id>', methods=['POST'])
@login_required
def eliminar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    db.session.delete(cliente)
    db.session.commit()
    flash(f'Cliente {cliente.nombre} eliminado.', 'info')
    return redirect(url_for('main.clientes_index'))

# ----------------------------------------------------------------------
# 3. CRUD PRODUCTOS (CON BÚSQUEDA POR NOMBRE)
# ----------------------------------------------------------------------
@main_bp.route('/productos')
@login_required
def productos_index():
    query = request.args.get('q') # Obtiene el texto de búsqueda
    
    if query:
        search = f"%{query}%"
        productos = Producto.query.filter(Producto.nombre.like(search)).all()
        flash(f'Mostrando resultados para: "{query}"', 'info')
    else:
        productos = Producto.query.all()
        
    return render_template('productos_index.html', productos=productos, query=query)

@main_bp.route('/productos/nuevo', methods=['GET', 'POST'])
@login_required
def crear_producto():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        try:
            precio_unitario = float(request.form.get('precio_unitario'))
        except ValueError:
            flash('El precio unitario debe ser un número válido.', 'danger')
            return redirect(url_for('main.crear_producto'))
        if Producto.query.filter_by(nombre=nombre).first():
             flash(f'Ya existe un producto con el nombre "{nombre}".', 'danger')
             return redirect(url_for('main.crear_producto'))
        nuevo_producto = Producto(nombre=nombre, precio_unitario=precio_unitario)
        db.session.add(nuevo_producto)
        db.session.commit()
        flash('Producto/Servicio registrado exitosamente.', 'success')
        return redirect(url_for('main.productos_index'))
    return render_template('productos_form.html', title='Registrar Producto/Servicio')

@main_bp.route('/productos/editar/<int:producto_id>', methods=['GET', 'POST'])
@login_required
def editar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    if request.method == 'POST':
        producto.nombre = request.form.get('nombre')
        try:
            producto.precio_unitario = float(request.form.get('precio_unitario'))
        except ValueError:
            flash('El precio unitario debe ser un número válido.', 'danger')
            return redirect(url_for('main.editar_producto', producto_id=producto.id))
        db.session.commit()
        flash(f'Producto {producto.nombre} actualizado exitosamente.', 'success')
        return redirect(url_for('main.productos_index'))
    return render_template('productos_form.html', title='Editar Producto/Servicio', producto=producto)

@main_bp.route('/productos/eliminar/<int:producto_id>', methods=['POST'])
@login_required
def eliminar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    db.session.delete(producto)
    db.session.commit()
    flash(f'Producto {producto.nombre} eliminado.', 'info')
    return redirect(url_for('main.productos_index'))
    
# ----------------------------------------------------------------------
# 4. CREAR DOCUMENTO (IGV OPCIONAL Y CORRELATIVOS POR TIPO)
# ----------------------------------------------------------------------
@main_bp.route('/documentos/crear', methods=['GET', 'POST'])
@login_required
def crear_documento():
    clientes = Cliente.query.all()
    productos = Producto.query.all()
    
    if request.method == 'POST':
        tipo_documento = request.form.get('tipo_documento')
        cliente_id = request.form.get('cliente_id')
        usar_igv = request.form.get('usar_igv') == 'on' # IGV Opcional
        
        cliente = Cliente.query.get(cliente_id)
        if not cliente:
            flash('Debe seleccionar un cliente válido.', 'danger')
            return redirect(url_for('main.crear_documento'))

        item_ids = request.form.getlist('item_producto_id[]')
        item_cantidades = request.form.getlist('item_cantidad[]')
        
        if not item_ids:
            flash('El documento debe contener al menos un producto.', 'danger')
            return redirect(url_for('main.crear_documento'))
            
        subtotal = 0.0
        detalles_a_guardar = []
        
        for prod_id, cantidad_str in zip(item_ids, item_cantidades):
            try:
                cantidad = int(cantidad_str)
                producto = Producto.query.get(prod_id)
                
                if producto and cantidad > 0:
                    precio_unitario = producto.precio_unitario
                    precio_linea = precio_unitario * cantidad
                    subtotal += precio_linea
                    
                    detalles_a_guardar.append({
                        'producto_id': producto.id,
                        'cantidad': cantidad,
                        'precio_unitario': precio_unitario
                    })
            except (ValueError, TypeError):
                continue
                
        # Calcular impuestos y total (Lógica IGV Opcional)
        IMPUESTO_PORCENTAJE = 0.18
        
        if usar_igv:
            impuestos = subtotal * IMPUESTO_PORCENTAJE
        else:
            impuestos = 0.0
            
        total = subtotal + impuestos
        
        # Generar número de documento por tipo (Lógica de Correlativo)
        count_doc = Documento.query.filter_by(tipo=tipo_documento).count()
        new_correlative = count_doc + 1
        new_doc_number = f"{tipo_documento[0]}-{new_correlative}" 
        
        # Crear y guardar el Documento
        nuevo_documento = Documento(
            tipo=tipo_documento,
            numero_documento=new_doc_number,
            cliente_id=cliente.id,
            user_id=current_user.id, # Atendido por
            subtotal=subtotal,
            impuestos=impuestos,
            total=total
        )
        db.session.add(nuevo_documento)
        db.session.commit()
        
        # Guardar los Detalles
        for detalle_data in detalles_a_guardar:
            nuevo_detalle = DetalleDocumento(
                documento_id=nuevo_documento.id,
                producto_id=detalle_data['producto_id'],
                cantidad=detalle_data['cantidad'],
                precio_unitario=detalle_data['precio_unitario']
            )
            db.session.add(nuevo_detalle)
        
        db.session.commit()
        
        flash(f'{tipo_documento} N° {new_doc_number} creada y guardada. Atendida por: {current_user.username}', 'success')
        return redirect(url_for('main.ver_documento', documento_id=nuevo_documento.id)) 
        
    return render_template(
        'documento_form.html', 
        clientes=clientes, 
        productos=productos,
        title='Crear Factura/Boleta'
    )
    
# ----------------------------------------------------------------------
# 5. HISTORIAL Y DETALLE DE DOCUMENTOS
# ----------------------------------------------------------------------
@main_bp.route('/documentos')
@login_required
def documentos_index():
    documentos = Documento.query.order_by(Documento.fecha_emision.desc()).all()
    
    documentos_con_datos = []
    for doc in documentos:
        cliente_nombre = Cliente.query.get(doc.cliente_id).nombre if doc.cliente_id else 'N/A'
        atendido_por = User.query.get(doc.user_id).username if doc.user_id else 'N/A'
        
        documentos_con_datos.append({
            'documento': doc,
            'cliente_nombre': cliente_nombre,
            'atendido_por': atendido_por
        })
        
    return render_template('documentos_index.html', documentos_con_datos=documentos_con_datos)

@main_bp.route('/documentos/<int:documento_id>')
@login_required
def ver_documento(documento_id):
    documento = Documento.query.get_or_404(documento_id)
    
    # ACCESO SEGURO A LOS DATOS DE LA EMPRESA
    empresa_data = {
        'nombre': current_app.config.get('EMPRESA_NOMBRE', 'Nombre de Empresa No Configurado'),
        'direccion': current_app.config.get('EMPRESA_DIRECCION', 'Dirección No Configurada'),
        'telefono': current_app.config.get('EMPRESA_TELEFONO', 'Teléfono No Configurado'),
        'correo': current_app.config.get('EMPRESA_CORREO', 'Correo No Configurado')
    }
    
    cliente = Cliente.query.get_or_404(documento.cliente_id)
    empleado = User.query.get_or_404(documento.user_id)
    
    detalles = DetalleDocumento.query.filter_by(documento_id=documento.id).all()
    
    detalles_con_nombres = []
    for detalle in detalles:
        producto_nombre = Producto.query.get(detalle.producto_id).nombre if detalle.producto_id else 'Servicio Eliminado'
        detalles_con_nombres.append({
            'nombre': producto_nombre,
            'cantidad': detalle.cantidad,
            'precio_unitario': detalle.precio_unitario,
            'total_linea': detalle.cantidad * detalle.precio_unitario
        })

    return render_template(
        'documento_detalle.html', 
        documento=documento, 
        cliente=cliente, 
        empleado=empleado,
        detalles=detalles_con_nombres,
        empresa=empresa_data # Pasar datos de la empresa a la plantilla
    )

# ----------------------------------------------------------------------
# 6. ANULACIÓN DE DOCUMENTO
# ----------------------------------------------------------------------
@main_bp.route('/documentos/anular/<int:documento_id>', methods=['POST'])
@login_required
def anular_documento(documento_id):
    documento = Documento.query.get_or_404(documento_id)
    motivo = request.form.get('motivo_anulacion')
    
    if not motivo:
        flash('Debe proporcionar un motivo para la anulación.', 'danger')
        return redirect(url_for('main.ver_documento', documento_id=documento.id))

    if documento.anulado:
        flash(f'{documento.tipo} N° {documento.numero_documento} ya está anulado.', 'warning')
        return redirect(url_for('main.documentos_index'))

    documento.anulado = True
    documento.motivo_anulacion = motivo
    documento.fecha_anulacion = datetime.utcnow()
    db.session.commit()

    flash(f'{documento.tipo} N° {documento.numero_documento} anulada exitosamente. Motivo: {motivo}', 'info')
    return redirect(url_for('main.documentos_index'))
    
# ----------------------------------------------------------------------
# 7. DESCARGAR REPORTE (EXPORTAR A CSV/EXCEL DETALLADO Y ORDENADO)
# ----------------------------------------------------------------------
@main_bp.route('/documentos/reporte/descargar')
@login_required
def descargar_reporte():
    # 1. Obtener todos los documentos
    documentos = Documento.query.order_by(Documento.fecha_emision.asc()).all()
    
    csv_lines = []
    
    # --- 2. ENCABEZADO DEL REPORTE ---
    report_title = "REPORTE DE VENTAS - HISTORIAL COMPLETO"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    csv_lines.append(f"{report_title}")
    csv_lines.append(f"Generado el: {timestamp}")
    csv_lines.append("") 
    
    # --- 3. ENCABEZADO DE COLUMNAS (DETALLE DE TABLA) ---
    header = [
        "Nº CORRELATIVO",
        "TIPO DOCUMENTO",
        "CLIENTE",
        "RUC/DNI",
        "ATENDIDO POR",
        "FECHA EMISION",
        "TOTAL VENTA (S/.)",
        "SUBTOTAL",
        "IMPUESTOS",
        "ESTADO"
    ]
    csv_lines.append(";".join(header))
    
    # --- 4. DETALLE DE FILAS ---
    for doc in documentos:
        # Recuperar datos relacionados
        cliente = Cliente.query.get(doc.cliente_id)
        empleado = User.query.get(doc.user_id)
        
        # Formatear la línea de datos
        line = [
            doc.numero_documento,
            doc.tipo,
            cliente.nombre if cliente else 'N/A',
            cliente.ruc_dni if cliente else 'N/A',
            empleado.username if empleado else 'N/A',
            doc.fecha_emision.strftime('%Y-%m-%d %H:%M:%S'),
            f"{doc.total:.2f}",
            f"{doc.subtotal:.2f}",
            f"{doc.impuestos:.2f}",
            "ANULADO" if doc.anulado else "ACTIVO"
        ]
        csv_lines.append(";".join(line))
        
    # 5. Crear la respuesta HTTP para la descarga
    csv_string = "\n".join(csv_lines)
    response = make_response(csv_string.encode('utf-8'))
    
    # Configurar las cabeceras para la descarga
    download_filename = f"Reporte_Ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response.headers["Content-Disposition"] = f"attachment; filename={download_filename}"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    
    return response