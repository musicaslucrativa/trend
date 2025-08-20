import os
import json
import hashlib
import subprocess
import pymysql
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

# Base directories
PROJECT_ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = PROJECT_ROOT / 'uploads'
PROCESSED_DIR = PROJECT_ROOT / 'processed'
TEMPLATES_DIR = PROJECT_ROOT / 'templates'

# Ensure directories exist
for d in [UPLOAD_DIR, PROCESSED_DIR, TEMPLATES_DIR]:
	os.makedirs(d, exist_ok=True)

# MySQL Database Configuration
DB_CONFIG = {
    'host': 'srv1330.hstgr.io',
    'user': 'u733147707_trend',
    'password': '0EgZk/GkTb*',
    'database': 'u733147707_trend',
    'charset': 'utf8mb4',
    'autocommit': True
}

app = Flask(__name__, template_folder=str(TEMPLATES_DIR))
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret')
# Allow up to 16 MB per upload (reduced for mobile stability)
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_UPLOAD_MB', '16')) * 1024 * 1024

# Auth config (env vars preferred)
APP_USER = os.environ.get('APP_USER', 'admin')
_password_hash_env = os.environ.get('APP_PASSWORD_HASH')
_password_plain_env = os.environ.get('APP_PASSWORD')
if _password_hash_env:
	APP_PASSWORD_HASH = _password_hash_env
elif _password_plain_env:
	APP_PASSWORD_HASH = generate_password_hash(_password_plain_env)
else:
	APP_PASSWORD_HASH = generate_password_hash('admin123')  # default for dev

# Database functions
def get_db_connection():
    """Get MySQL database connection"""
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def init_database():
    """Initialize database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(50),
                INDEX idx_username (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database tables initialized successfully")
        
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

def create_user(username: str, password: str, is_admin: bool = False, created_by: str = 'system') -> bool:
    """Create a new user in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        password_hash = generate_password_hash(password)
        
        cursor.execute('''
            INSERT INTO users (username, password_hash, is_admin, created_by)
            VALUES (%s, %s, %s, %s)
        ''', (username, password_hash, is_admin, created_by))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except pymysql.IntegrityError:
        print(f"User {username} already exists")
        return False
    except Exception as e:
        print(f"Error creating user {username}: {e}")
        return False

def get_user(username: str) -> Optional[Dict[str, Any]]:
    """Get user from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return user
        
    except Exception as e:
        print(f"Error getting user {username}: {e}")
        return None

def get_all_users() -> List[Dict[str, Any]]:
    """Get all users from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        users = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return users
        
    except Exception as e:
        print(f"Error getting users: {e}")
        return []

def delete_user(username: str) -> bool:
    """Delete user from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM users WHERE username = %s AND is_admin = FALSE', (username,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        cursor.close()
        conn.close()
        return deleted
        
    except Exception as e:
        print(f"Error deleting user {username}: {e}")
        return False

def verify_password(username: str, password: str) -> tuple[bool, bool]:
    """Verify user password and return (success, is_admin)"""
    # Try MySQL first
    if ensure_db_initialized():
        user = get_user(username)
        if user and check_password_hash(user['password_hash'], password):
            return True, user['is_admin']
    
    # Fallback: check hardcoded admin
    if username == 'admin' and password == 'admin123':
        return True, True
    
    return False, False


def login_required(fn: Callable) -> Callable:
	def wrapper(*args, **kwargs):
		if not session.get('auth'):  # not logged in
			return redirect(url_for('login', next=request.path))
		return fn(*args, **kwargs)
	wrapper.__name__ = fn.__name__
	return wrapper


def admin_required(fn: Callable) -> Callable:
	def wrapper(*args, **kwargs):
		if not session.get('auth') or not session.get('is_admin'):
			flash('Acesso negado')
			return redirect(url_for('index'))
		return fn(*args, **kwargs)
	wrapper.__name__ = fn.__name__
	return wrapper

# Metadata for the trend (oculto ao usuário final)
TREND_META: Dict[str, Any] = {
	"checksum": "89c4e3c64b0175c4de454f5f34504434",
	"file_name": "photo-81_singular_display_fullPicture(2).HEIC",
	"file_size": "1466 kB",
	"file_type": "HEIC",
	"file_type_extension": "heic",
	"mime_type": "image/heic",
	"major_brand": "High Efficiency Image Format HEVC still image (.HEIC)",
	"minor_version": "0.0.0",
	"CompatibleBrands": {"0": "heic", "1": "mif1"},
	"handler_type": "Picture",
	"primary_item_reference": "49",
	"meta_image_size": "2743x3658",
	"exif_byte_order": "Big-endian (Motorola, MM)",
	"make": "Meta View",
	"model": "Ray-Ban Meta Smart Glasses",
	"orientation": "Horizontal (normal)",
	"tile_width": "512",
	"tile_length": "512",
	"exif_version": "220",
	"subject_distance": "0.1 m",
	"user_comment": "34D16852-7110-470A-8B25-D48E3A791E26",
	"color_space": "sRGB",
	"exif_image_width": 4032,
	"exif_image_height": 3024,
	"digital_zoom_ratio": 0,
	"subject_distance_range": "Macro",
	"gps_latitude_ref": "South",
	"gps_longitude_ref": "West",
	"color_profiles": "nclx",
	"color_primaries": "Unspecified",
	"transfer_characteristics": "Unspecified",
	"matrix_coefficients": "BT.601",
	"video_full_range_flag": "Full",
	"hevc_configuration_version": 1,
	"general_profile_space": "Conforming",
	"general_tier_flag": "Main Tier",
	"general_profile_idc": "Main Still Picture",
	"gen_profile_compatibility_flags": "Main Still Picture, Main 10, Main",
	"constraint_indicator_flags": "176 0 0 0 0 0",
	"general_level_idc": "90 (level 3.0)",
	"min_spatial_segmentation_idc": 0,
	"parallelism_type": 0,
	"chroma_format": "4:2:0",
	"bit_depth_luma": 8,
	"bit_depth_chroma": 8,
	"average_frame_rate": 0,
	"constant_frame_rate": "Unknown",
	"num_temporal_layers": 1,
	"temporal_id_nested": "No",
	"image_width": 2743,
	"image_height": 3658,
	"image_spatial_extent": "2743x3658",
	"rotation": "Horizontal (Normal)",
	"image_pixel_depth": "8 8 8",
	"media_data_size": 1463710,
	"media_data_offset": 2689,
	"image_size": "2743x3658",
	"megapixels": 10,
	"gps_latitude": "22 deg 58' 46.24\" S",
	"gps_longitude": "43 deg 24' 42.09\" W",
	"gps_position": "22 deg 58' 46.24\" S, 43 deg 24' 42.09\" W",
	"category": "image",
	"raw_header": "00 00 00 18 66 74 79 70 68 65 69 63 00 00 00 00 68 65 69 63 6D 69 66 31 00 00 0A 59 6D 65 74 61 00 00 00 00 00 00 00 22 68 64 6C 72 00 00 00 00 00 00 00 00 70 69 63 74 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 24 64 69 6E 66 00 00 00 1C 64 72 65 66 00 00 00 00 00 00 00 01 00 00 00 0C 75 72 6C 20 00 00 00 01 00 00 00 0E 70 69 74 6D 00 00 00 00 00 31 00 00 04 28 69 69 6E 66"
}

# EXIF tags we will write natively; the rest goes into XMP description JSON
EXIF_MAP = {
	"make": ("EXIF:Make", None),
	"model": ("EXIF:Model", None),
	"orientation": ("EXIF:Orientation", None),
	"exif_version": ("EXIF:ExifVersion", "0220"),
	"subject_distance": ("EXIF:SubjectDistance", None),
	"user_comment": ("EXIF:UserComment", None),
	"color_space": ("EXIF:ColorSpace", None),
	"exif_image_width": ("EXIF:ExifImageWidth", None),
	"exif_image_height": ("EXIF:ExifImageHeight", None),
	"digital_zoom_ratio": ("EXIF:DigitalZoomRatio", None),
	"subject_distance_range": ("EXIF:SubjectDistanceRange", None),
	"gps_latitude": ("EXIF:GPSLatitude", None),
	"gps_longitude": ("EXIF:GPSLongitude", None),
}


def build_exiftool_write_args(meta: Dict[str, Any]) -> List[str]:
	args: List[str] = []
	for key, (exif_tag, override_value) in EXIF_MAP.items():
		value = override_value if override_value is not None else meta.get(key)
		if value is None:
			continue
		args.append(f"-{exif_tag}={value}")
	remaining: Dict[str, Any] = {}
	for k, v in meta.items():
		if k in EXIF_MAP:
			continue
		remaining[k] = v
	desc_json = json.dumps(remaining, ensure_ascii=False)
	args.append(f"-XMP-dc:Description={desc_json}")
	return args


def run_exiftool_write(src: Path, dst: Path, meta: Dict[str, Any]) -> subprocess.CompletedProcess:
	args = ["exiftool", "-m", "-q", "-S"]
	args.extend(build_exiftool_write_args(meta))
	args.extend(["-o", str(dst), str(src)])
	return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def preserve_orientation(src: Path, dst: Path) -> subprocess.CompletedProcess:
	# First copy the file
	import shutil
	shutil.copy2(src, dst)
	
	# Then preserve orientation if possible
	args = ["exiftool", "-m", "-q", "-S", "-Orientation<Orientation", str(dst)]
	return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


@app.route('/test-login')
def test_login():
    try:
        mysql_available = ensure_db_initialized()
        
        response = {
            'status': 'ok',
            'version': 'mysql-hybrid',
            'mysql_available': mysql_available,
            'fallback_admin': True
        }
        
        if mysql_available:
            users = get_all_users()
            response.update({
                'total_users': len(users),
                'users': [{'username': u['username'], 'is_admin': u['is_admin']} for u in users]
            })
        else:
            response.update({
                'message': 'MySQL not available, using fallback admin (admin/admin123)'
            })
            
        return response
        
    except Exception as e:
        return {'status': 'error', 'version': 'mysql-hybrid', 'message': str(e)}


@app.route('/health')
def health_check():
    try:
        # Check if exiftool is available
        result = subprocess.run(['exiftool', '-ver'], capture_output=True, text=True)
        exiftool_ok = result.returncode == 0
        
        # Check directories
        upload_ok = UPLOAD_DIR.exists() and os.access(UPLOAD_DIR, os.W_OK)
        processed_ok = PROCESSED_DIR.exists() and os.access(PROCESSED_DIR, os.W_OK)
        
        return {
            'status': 'ok',
            'exiftool': exiftool_ok,
            'upload_dir': upload_ok,
            'processed_dir': processed_ok,
            'exiftool_version': result.stdout.strip() if exiftool_ok else 'not found'
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            print(f"Login attempt for user: {username}")
            
            if not username or not password:
                flash('Usuário e senha são obrigatórios')
                return redirect(url_for('login'))
            
            # Verify password using MySQL
            success, is_admin = verify_password(username, password)
            
            if success:
                session['auth'] = True
                session['username'] = username
                session['is_admin'] = is_admin
                print(f"Login successful: {username}, admin: {is_admin}")
                next_url = request.args.get('next') or url_for('index')
                return redirect(next_url)
            else:
                print(f"Login failed for user: {username}")
                flash('Credenciais inválidas')
                return redirect(url_for('login'))
            
    except Exception as e:
        print(f"Login error: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Erro interno no login. Tente novamente.')
        return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/logout')

def logout():
	session.clear()
	return redirect(url_for('login'))


@app.route('/admin', methods=['GET', 'POST'])
@admin_required

def admin():
	if not ensure_db_initialized():
		flash('Banco de dados não disponível')
		return redirect(url_for('index'))
		
	if request.method == 'POST':
		action = request.form.get('action')
		if action == 'create_user':
			username = request.form.get('username', '').strip()
			password = request.form.get('password', '').strip()
			
			if not username or not password:
				flash('Usuário e senha são obrigatórios')
				return redirect(url_for('admin'))
			
			if create_user(username, password, is_admin=False, created_by=session.get('username', 'admin')):
				flash(f'Usuário {username} criado com sucesso')
			else:
				flash('Usuário já existe ou erro ao criar')
			return redirect(url_for('admin'))
		
		elif action == 'delete_user':
			username = request.form.get('username', '').strip()
				if delete_user(username):
				flash(f'Usuário {username} removido')
			else:
				flash('Erro ao remover usuário ou usuário é admin')
			return redirect(url_for('admin'))
	
	if ensure_db_initialized():
		users = get_all_users()
	else:
		users = []
		flash('MySQL não disponível. Apenas funcionalidade básica.')
	return render_template('admin.html', users=users)


@app.route('/', methods=['GET'])
@login_required

def index():
	return render_template('index.html')


@app.route('/upload', methods=['POST'])
@login_required
def upload():
    try:
        if 'image' not in request.files:
            flash('Selecione uma imagem')
            return redirect(url_for('index'))
        
        file = request.files['image']
        if not file or file.filename == '':
            flash('Arquivo inválido')
            return redirect(url_for('index'))

        # Check file size
        file.seek(0, 2)  # Go to end
        file_size = file.tell()
        file.seek(0)  # Go back to start
        
        if file_size > 16 * 1024 * 1024:  # 16MB limit
            flash('Arquivo muito grande. Máximo 16MB.')
            return redirect(url_for('index'))

        # Sanitize filename for safe filesystem writes
        filename = secure_filename(file.filename)
        if not filename:
            flash('Nome de arquivo inválido')
            return redirect(url_for('index'))
            
        upload_path = UPLOAD_DIR / filename
        file.save(str(upload_path))
        
        # Verify file was saved
        if not upload_path.exists():
            flash('Erro ao salvar arquivo')
            return redirect(url_for('index'))

        # Simple approach for mobile - just copy with new name
        import shutil
        processed_name = f"{upload_path.stem}-trend{upload_path.suffix or '.heic'}"
        processed_path = PROCESSED_DIR / processed_name
        
        # Copy the file first
        shutil.copy2(upload_path, processed_path)
        
        # Try to apply metadata, but don't fail if it doesn't work
        try:
            write_proc = run_exiftool_write(upload_path, processed_path, TREND_META)
            if write_proc.returncode != 0:
                print(f"ExifTool warning: {write_proc.stderr}")
                # Continue anyway, file was already copied
        except Exception as e:
            print(f"ExifTool error (non-critical): {e}")
            # Continue anyway, file was already copied
        
        if not processed_path.exists():
            flash('Erro ao processar arquivo')
            return redirect(url_for('index'))

        return render_template('result.html', processed_filename=processed_name)
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Erro interno. Tente novamente.')
        return redirect(url_for('index'))


@app.route('/download/<path:filename>')
@login_required

def download(filename: str):
	return send_from_directory(str(PROCESSED_DIR), filename, as_attachment=True)


@app.errorhandler(500)
def internal_error(error):
    print(f"500 error: {error}")
    flash('Erro interno do servidor. Tente novamente.')
    return redirect(url_for('index'))


@app.errorhandler(413)
def too_large(error):
    flash('Arquivo muito grande. Máximo 32MB.')
    return redirect(url_for('index'))


def initialize_app():
    """Initialize database and create admin user - called lazily"""
    try:
        print("Initializing database...")
        init_database()
        
        # Create admin user if it doesn't exist
        if not get_user('admin'):
            if create_user('admin', 'admin123', is_admin=True, created_by='system'):
                print("Admin user created successfully")
            else:
                print("Failed to create admin user")
        else:
            print("Admin user already exists")
        return True
            
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

# Flag to track if initialization was attempted
_db_init_attempted = False
_db_available = False

def ensure_db_initialized():
    """Ensure database is initialized, but don't fail if it's not available"""
    global _db_init_attempted, _db_available
    
    if not _db_init_attempted:
        _db_available = initialize_app()
        _db_init_attempted = True
    
    return _db_available

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5173)), debug=True)
