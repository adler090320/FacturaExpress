# app.py

from flask import Flask
from models import db, User 
from routes import auth_bp 
from main import main_bp 
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

def create_app():
    app = Flask(__name__)
    
    # 1. CONFIGURACIÓN PRINCIPAL
    app.config['SECRET_KEY'] = 'tu_nueva_clave_secreta_aqui_cambiala'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///facturacion.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 2. DATOS DE LA EMPRESA (CORREGIDOS)
    app.config['EMPRESA_NOMBRE'] = 'ADLER GRANDEZ P.'
    app.config['EMPRESA_DIRECCION'] = 'ELIAS SOPLIN VARGAS'
    app.config['EMPRESA_TELEFONO'] = '+51 929 974 627'
    app.config['EMPRESA_CORREO'] = 'A76047901@GMAIL.COM'
    app.config['EMPRESA_RUC'] = '1076047901' # <-- ¡NUEVO CAMPO CON RUC CORREGIDO!
    
    # 3. INICIALIZACIÓN DE EXTENSIONES
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 4. REGISTRO DE BLUEPRINTS (Módulos de Rutas)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp) 

    return app

if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        # Crea todas las tablas en SQLite y el usuario administrador si no existe
        db.create_all() 
        
        if not User.query.filter_by(username='admin').first():
            print("Creando usuario administrador: admin / 123456")
            hashed_password = generate_password_hash('123456', method='pbkdf2:sha256')
            admin_user = User(username='admin', password_hash=hashed_password)
            db.session.add(admin_user)
            db.session.commit()
            
    app.run(debug=True)