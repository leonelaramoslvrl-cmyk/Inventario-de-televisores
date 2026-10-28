# -*- coding: utf-8 -*-
import os
from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuracion de PostgreSQL (Compatible con entorno local y Render)
database_url = os.getenv('DATABASE_URL')

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'postgresql://postgres:1234567@localhost:5432/inventario_tv'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo de la Base de Datos para los Televisores
class TVInventario(db.Model):
    __tablename__ = 'tv_inventario'
    
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(20), nullable=False)
    ubicacion = db.Column(db.String(50), nullable=True)
    marca = db.Column(db.String(50), nullable=False)
    modelo = db.Column(db.String(100), nullable=False)
    serial = db.Column(db.String(100), nullable=False)
    conexion = db.Column(db.String(50), nullable=True)
    perifericos = db.Column(db.String(10), nullable=True)
    intergo = db.Column(db.String(10), nullable=True)
    comentarios = db.Column(db.Text, nullable=True)
    instalacion = db.Column(db.String(50), nullable=True)
    createdAt = db.Column(db.BigInteger, server_default=db.func.extract('epoch', db.func.now()) * 1000)

    def to_dict(self):
        return {
            'id': self.id,
            'room': self.room,
            'ubicacion': self.ubicacion,
            'marca': self.marca,
            'modelo': self.modelo,
            'serial': self.serial,
            'conexion': self.conexion,
            'perifericos': self.perifericos,
            'intergo': self.intergo,
            'comentarios': self.comentarios,
            'instalacion': self.instalacion,
            'createdAt': self.createdAt
        }

# Asegurar que las tablas se creen tanto en local como con Gunicorn en Render
with app.app_context():
    db.create_all()

# Ruta principal que carga tu interfaz (index.html)
@app.route('/')
def index():
    return render_template('index.html')

# API: Obtener todos los registros ordenados
@app.route('/api/tvs', methods=['GET'])
def get_tvs():
    try:
        tvs = TVInventario.query.order_by(TVInventario.id.desc()).all()
        return jsonify([tv.to_dict() for tv in tvs]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: Crear un nuevo registro
@app.route('/api/tvs', methods=['POST'])
def add_tv():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        new_tv = TVInventario(
            room=data.get('room'),
            ubicacion=data.get('ubicacion'),
            marca=data.get('marca'),
            modelo=data.get('modelo'),
            serial=data.get('serial'),
            conexion=data.get('conexion'),
            perifericos=data.get('perifericos'),
            intergo=data.get('intergo'),
            comentarios=data.get('comentarios'),
            instalacion=data.get('instalacion')
        )
        db.session.add(new_tv)
        db.session.commit()
        return jsonify(new_tv.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API: Actualizar un registro existente
@app.route('/api/tvs/<int:tv_id>', methods=['PUT'])
def update_tv(tv_id):
    try:
        tv = TVInventario.query.get_or_404(tv_id)
        data = request.get_json()
        
        tv.room = data.get('room', tv.room)
        tv.ubicacion = data.get('ubicacion', tv.ubicacion)
        tv.marca = data.get('marca', tv.marca)
        tv.modelo = data.get('modelo', tv.modelo)
        tv.serial = data.get('serial', tv.serial)
        tv.conexion = data.get('conexion', tv.conexion)
        tv.perifericos = data.get('perifericos', tv.perifericos)
        tv.intergo = data.get('intergo', tv.intergo)
        tv.comentarios = data.get('comentarios', tv.comentarios)
        tv.instalacion = data.get('instalacion', tv.instalacion)
        
        db.session.commit()
        return jsonify(tv.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)