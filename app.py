# GlobalTest DATA Download API
# Production-ready Flask API for secure data download with license verification

from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import sqlite3
from datetime import datetime
from functools import wraps

app = Flask(__name__)
CORS(app)

# Konfiguratsiya
DATA_FILE = os.environ.get('DATA_FILE', '/var/www/globaltest/data.zip')
DATABASE = os.environ.get('DATABASE', '/var/www/globaltest/licenses.db')
API_SECRET = os.environ.get('API_SECRET', 'GlobalTest2025SecretKey159')

# ============= Database Functions =============

def get_db():
    """Database connection olish"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Database jadvallarini yaratish"""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            computer_id TEXT NOT NULL,
            license_key TEXT NOT NULL,
            max_computers INTEGER DEFAULT 1,
            expires_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            customer_name TEXT,
            customer_phone TEXT,
            notes TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            computer_id TEXT NOT NULL,
            downloaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_computer_id ON licenses(computer_id)')
    conn.commit()
    conn.close()

# ============= Auth Decorator =============

def require_api_key(f):
    """Admin API uchun API key tekshiruvi"""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != API_SECRET:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

# ============= Public Endpoints =============

@app.route('/api/download', methods=['POST'])
def download_data():
    # 1. Secret Key tekshirish (Header orqali)
    client_secret = request.headers.get('X-Api-Secret')
    if client_secret != API_SECRET:
        return jsonify({"error": "Unauthorized: Invalid or missing secret key"}), 401
    
    # 2. CompId ni olish (Log uchun)
    # compId ni query params, form data yoki JSON body dan olishga harakat qilamiz
    comp_id = request.args.get('compId')
    if not comp_id:
        comp_id = request.form.get('compId')
    if not comp_id:
        data = request.get_json(silent=True)
        if data:
            comp_id = data.get('compId')
            
    if not comp_id:
        comp_id = "UNKNOWN_CLIENT"

    try:
        if not os.path.exists(DATA_FILE):
             return jsonify({"error": "File not found on server"}), 404

        # Downloadni bazaga yozish
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO downloads (computer_id, ip_address) VALUES (?, ?)",
            (comp_id, request.remote_addr)
        )
        conn.commit()
        conn.close()

        return send_file(
            DATA_FILE,
            mimetype='application/zip',
            as_attachment=True,
            download_name='data.zip'
        )
    
    if not os.path.exists(DATA_FILE):
        return jsonify({'error': 'DATA fayli topilmadi'}), 404
    
    return send_file(
        DATA_FILE,
        mimetype='application/zip',
        as_attachment=True,
        download_name='data.zip'
    )

@app.route('/api/check', methods=['GET'])
def check_license():
    """Litsenziyani tekshirish"""
    comp_id = request.args.get('compId', '').strip()
    key = request.args.get('key', '').strip()
    
    conn = get_db()
    license = conn.execute(
        'SELECT * FROM licenses WHERE computer_id = ? AND license_key = ? AND is_active = 1',
        (comp_id, key)
    ).fetchone()
    conn.close()
    
    if license:
        # Muddati tekshirish
        if license['expires_at']:
            expires = datetime.fromisoformat(license['expires_at'])
            if datetime.now() > expires:
                return jsonify({'valid': False, 'reason': 'expired'})
        
        return jsonify({
            'valid': True,
            'maxComputers': license['max_computers'],
            'expiresAt': license['expires_at']
        })
    
    return jsonify({'valid': False, 'reason': 'not_found'}), 403

# ============= Admin Endpoints =============

@app.route('/api/admin/licenses', methods=['GET'])
@require_api_key
def list_licenses():
    """Barcha litsenziyalarni ko'rish"""
    conn = get_db()
    licenses = conn.execute('SELECT * FROM licenses ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return jsonify([dict(l) for l in licenses])

@app.route('/api/admin/licenses', methods=['POST'])
@require_api_key
def create_license():
    """Yangi litsenziya yaratish (KeyGenerator dan)"""
    data = request.get_json()
    
    if not data or not data.get('computer_id') or not data.get('license_key'):
        return jsonify({'error': 'computer_id va license_key kerak'}), 400
    
    conn = get_db()
    
    # Mavjudligini tekshirish
    existing = conn.execute(
        'SELECT id FROM licenses WHERE computer_id = ?',
        (data['computer_id'],)
    ).fetchone()
    
    if existing:
        # Mavjud bo'lsa yangilash
        conn.execute('''
            UPDATE licenses SET 
                license_key = ?,
                max_computers = ?,
                expires_at = ?,
                customer_name = ?,
                customer_phone = ?,
                notes = ?,
                is_active = 1
            WHERE computer_id = ?
        ''', (
            data['license_key'],
            data.get('max_computers', 1),
            data.get('expires_at'),
            data.get('customer_name'),
            data.get('customer_phone'),
            data.get('notes'),
            data['computer_id']
        ))
    else:
        # Yangi yaratish
        conn.execute('''
            INSERT INTO licenses (computer_id, license_key, max_computers, expires_at, customer_name, customer_phone, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['computer_id'],
            data['license_key'],
            data.get('max_computers', 1),
            data.get('expires_at'),
            data.get('customer_name'),
            data.get('customer_phone'),
            data.get('notes')
        ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Litsenziya saqlandi'})

@app.route('/api/admin/licenses/<int:license_id>', methods=['DELETE'])
@require_api_key
def delete_license(license_id):
    """Litsenziyani o'chirish/deaktivatsiya qilish"""
    conn = get_db()
    conn.execute('UPDATE licenses SET is_active = 0 WHERE id = ?', (license_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/admin/downloads', methods=['GET'])
@require_api_key
def list_downloads():
    """Download statistikasi"""
    conn = get_db()
    downloads = conn.execute('''
        SELECT d.*, l.customer_name 
        FROM downloads d 
        LEFT JOIN licenses l ON d.computer_id = l.computer_id 
        ORDER BY d.downloaded_at DESC 
        LIMIT 100
    ''').fetchall()
    conn.close()
    
    return jsonify([dict(d) for d in downloads])

@app.route('/api/health', methods=['GET'])
def health_check():
    """Server holati"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'data_file_exists': os.path.exists(DATA_FILE)
    })

# ============= Startup =============

if __name__ == '__main__':
    init_db()
    print(f"DATA file: {DATA_FILE}")
    print(f"Database: {DATABASE}")
    app.run(host='0.0.0.0', port=5000, debug=False)
