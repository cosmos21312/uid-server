from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# ========== CONFIGURACIÓN MONGODB ==========
# REEMPLAZA ESTO con tu connection string de MongoDB
MONGO_URI = "mongodb+srv://martinococabrera_db_user:j87DNKimHvp1KAF@uid.mkzfekr.mongodb.net/?retryWrites=true&w=majority&appName=uid"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['uid_database']
    uids_collection = db['uids']
    # Test de conexión
    client.server_info()
    print("✅ Conectado a MongoDB Atlas")
except Exception as e:
    print(f"❌ Error conectando a MongoDB: {e}")
    uids_collection = None

# ========== RUTAS ==========

@app.route('/')
def home():
    return "UID Server Running with MongoDB! 🚀"


@app.route('/uids', methods=['GET'])
def get_uids():
    """Obtiene todos los UIDs"""
    if not uids_collection:
        return jsonify({"error": "Database not connected"}), 500
    
    uids = list(uids_collection.find({}, {'_id': 0}))
    return jsonify({
        "total": len(uids),
        "uids": uids
    })


@app.route('/uid', methods=['POST'])
def add_uid():
    """Agrega o actualiza un UID"""
    if not uids_collection:
        return jsonify({"error": "Database not connected"}), 500
    
    data = request.get_json()
    
    uid = str(data.get('uid', ''))
    region = data.get('region', '')
    openid = data.get('openid', '')
    access_token = data.get('access_token', '')
    platform = str(data.get('platform', ''))
    
    if not uid:
        return jsonify({"error": "UID requerido"}), 400
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Buscar si ya existe
    existing = uids_collection.find_one({"uid": uid})
    
    if existing:
        # Actualizar
        uids_collection.update_one(
            {"uid": uid},
            {"$set": {
                "region": region,
                "openid": openid,
                "access_token": access_token,
                "platform": platform,
                "last_seen": now
            }}
        )
    else:
        # Crear nuevo sin días
        uids_collection.insert_one({
            "uid": uid,
            "region": region,
            "openid": openid,
            "access_token": access_token,
            "platform": platform,
            "days_remaining": 0,
            "expire_date": None,
            "first_seen": now,
            "last_seen": now
        })
    
    total = uids_collection.count_documents({})
    
    return jsonify({
        "success": True,
        "uid": uid,
        "total_uids": total
    })


@app.route('/uid/<uid>', methods=['GET'])
def get_uid(uid):
    """Busca un UID específico"""
    if not uids_collection:
        return jsonify({"error": "Database not connected"}), 500
    
    entry = uids_collection.find_one({"uid": uid}, {'_id': 0})
    
    if entry:
        # Calcular días restantes
        if entry.get('expire_date'):
            expire_dt = datetime.fromisoformat(entry['expire_date'])
            days_left = (expire_dt - datetime.now()).days
            entry['days_left'] = max(0, days_left)
        return jsonify(entry)
    
    return jsonify({"error": "UID no encontrado"}), 404


@app.route('/uid/<uid>/check', methods=['GET'])
def check_uid(uid):
    """Verifica si un UID tiene acceso activo"""
    if not uids_collection:
        return jsonify({"error": "Database not connected"}), 500
    
    entry = uids_collection.find_one({"uid": uid})
    
    if entry and entry.get('expire_date'):
        expire_dt = datetime.fromisoformat(entry['expire_date'])
        
        if datetime.now() < expire_dt:
            days_left = (expire_dt - datetime.now()).days
            return jsonify({
                "active": True,
                "uid": uid,
                "days_left": days_left,
                "expire_date": entry['expire_date']
            })
    
    return jsonify({
        "active": False,
        "uid": uid,
        "message": "No tiene días activos. Contacte al administrador."
    })


@app.route('/uid/<uid>/adddays', methods=['POST'])
def add_days(uid):
    """Agrega días a un UID"""
    if not uids_collection:
        return jsonify({"error": "Database not connected"}), 500
    
    data = request.get_json()
    days = int(data.get('days', 0))
    
    if days <= 0:
        return jsonify({"error": "Días debe ser mayor a 0"}), 400
    
    entry = uids_collection.find_one({"uid": str(uid)})
    
    if entry:
        # Si ya tiene fecha de expiración, extender desde ahí
        if entry.get('expire_date'):
            expire_dt = datetime.fromisoformat(entry['expire_date'])
            # Si ya expiró, empezar desde ahora
            if expire_dt < datetime.now():
                new_expire = datetime.now() + timedelta(days=days)
            else:
                new_expire = expire_dt + timedelta(days=days)
        else:
            # Primera vez, empezar desde ahora
            new_expire = datetime.now() + timedelta(days=days)
        
        uids_collection.update_one(
            {"uid": str(uid)},
            {"$set": {
                "expire_date": new_expire.isoformat(),
                "days_remaining": days
            }}
        )
        
        return jsonify({
            "success": True,
            "uid": uid,
            "days_added": days,
            "expire_date": new_expire.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return jsonify({"error": "UID no encontrado"}), 404


@app.route('/uid/<uid>/remove', methods=['DELETE'])
def remove_uid(uid):
    """Elimina un UID"""
    if not uids_collection:
        return jsonify({"error": "Database not connected"}), 500
    
    result = uids_collection.delete_one({"uid": str(uid)})
    
    if result.deleted_count > 0:
        return jsonify({
            "success": True,
            "message": f"UID {uid} eliminado"
        })
    
    return jsonify({"error": "UID no encontrado"}), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
