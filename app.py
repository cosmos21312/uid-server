from flask import Flask, request, jsonify
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)

UID_FILE = "uids.json"

def load_uids():
    """Carga la base de UIDs"""
    if os.path.exists(UID_FILE):
        try:
            with open(UID_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_uids(data):
    """Guarda la base de UIDs"""
    with open(UID_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def check_uid_active(uid):
    """Verifica si un UID tiene días activos"""
    uids = load_uids()
    for entry in uids:
        if entry.get('uid') == str(uid):
            expire_date = entry.get('expire_date')
            if expire_date:
                expire_dt = datetime.fromisoformat(expire_date)
                if datetime.now() < expire_dt:
                    return True, entry
    return False, None

@app.route('/')
def home():
    return "UID Server Running! 🚀"

@app.route('/uids', methods=['GET'])
def get_uids():
    """Obtiene todos los UIDs"""
    uids = load_uids()
    return jsonify({
        "total": len(uids),
        "uids": uids
    })

@app.route('/uid', methods=['POST'])
def add_uid():
    """Agrega o actualiza un UID"""
    data = request.get_json()
    
    uid = str(data.get('uid', ''))
    region = data.get('region', '')
    openid = data.get('openid', '')
    access_token = data.get('access_token', '')
    platform = str(data.get('platform', ''))
    
    if not uid:
        return jsonify({"error": "UID requerido"}), 400
    
    uids = load_uids()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Buscar si ya existe
    found = False
    for entry in uids:
        if entry.get('uid') == uid:
            # Actualizar
            entry['region'] = region
            entry['openid'] = openid
            entry['access_token'] = access_token
            entry['platform'] = platform
            entry['last_seen'] = now
            found = True
            break
    
    if not found:
        # Crear nuevo sin días
        uids.append({
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
    
    save_uids(uids)
    
    return jsonify({
        "success": True,
        "uid": uid,
        "total_uids": len(uids)
    })

@app.route('/uid/<uid>', methods=['GET'])
def get_uid(uid):
    """Busca un UID específico"""
    uids = load_uids()
    for entry in uids:
        if entry.get('uid') == uid:
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
    is_active, entry = check_uid_active(uid)
    
    if is_active:
        expire_dt = datetime.fromisoformat(entry['expire_date'])
        days_left = (expire_dt - datetime.now()).days
        
        return jsonify({
            "active": True,
            "uid": uid,
            "days_left": days_left,
            "expire_date": entry['expire_date']
        })
    else:
        return jsonify({
            "active": False,
            "uid": uid,
            "message": "No tiene días activos. Contacte al administrador."
        })

@app.route('/uid/<uid>/adddays', methods=['POST'])
def add_days(uid):
    """Agrega días a un UID"""
    data = request.get_json()
    days = int(data.get('days', 0))
    
    if days <= 0:
        return jsonify({"error": "Días debe ser mayor a 0"}), 400
    
    uids = load_uids()
    
    for entry in uids:
        if entry.get('uid') == str(uid):
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
            
            entry['expire_date'] = new_expire.isoformat()
            entry['days_remaining'] = days
            
            save_uids(uids)
            
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
    uids = load_uids()
    
    for i, entry in enumerate(uids):
        if entry.get('uid') == str(uid):
            uids.pop(i)
            save_uids(uids)
            return jsonify({
                "success": True,
                "message": f"UID {uid} eliminado"
            })
    
    return jsonify({"error": "UID no encontrado"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
