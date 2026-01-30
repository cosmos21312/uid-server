from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

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
        if entry.get('uid') == uid and entry.get('region') == region:
            # Actualizar
            entry['openid'] = openid
            entry['access_token'] = access_token
            entry['platform'] = platform
            entry['last_seen'] = now
            found = True
            break
    
    if not found:
        # Crear nuevo
        uids.append({
            "uid": uid,
            "region": region,
            "openid": openid,
            "access_token": access_token,
            "platform": platform,
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
            return jsonify(entry)
    return jsonify({"error": "UID no encontrado"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
