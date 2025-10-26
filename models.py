# models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# 1. MODELO DE USUARIO (Empleados)
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    documentos = db.relationship('Documento', backref='atendido_por', lazy=True)

# 2. MODELO DE CLIENTES
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    ruc_dni = db.Column(db.String(20), unique=True, nullable=False)
    direccion = db.Column(db.String(200), nullable=True)
    documentos = db.relationship('Documento', backref='cliente', lazy=True)

# 3. MODELO DE PRODUCTOS/SERVICIOS
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    detalles = db.relationship('DetalleDocumento', backref='producto', lazy=True)

# 4. MODELO DE DOCUMENTO (Factura o Boleta) - Actualizado
class Documento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(10), nullable=False)
    numero_documento = db.Column(db.String(50), unique=True, nullable=False)
    fecha_emision = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    subtotal = db.Column(db.Float, default=0.0)
    impuestos = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)

    # NUEVOS CAMPOS para anulación
    anulado = db.Column(db.Boolean, default=False)
    motivo_anulacion = db.Column(db.Text, nullable=True)
    fecha_anulacion = db.Column(db.DateTime, nullable=True)

    # Claves Foráneas
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    detalles = db.relationship('DetalleDocumento', backref='documento', lazy=True)

# 5. MODELO DE DETALLE DEL DOCUMENTO
class DetalleDocumento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    
    # Claves Foráneas
    documento_id = db.Column(db.Integer, db.ForeignKey('documento.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)