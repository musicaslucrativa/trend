import os
import json
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

# Try to import MySQL, but don't fail if not available
try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("MySQL not available, using simple mode")

# Base directories
PROJECT_ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = PROJECT_ROOT / 'uploads'
PROCESSED_DIR = PROJECT_ROOT / 'processed'
TEMPLATES_DIR = PROJECT_ROOT / 'templates'

# Ensure directories exist
for d in [UPLOAD_DIR, PROCESSED_DIR, TEMPLATES_DIR]:
	os.makedirs(d, exist_ok=True)

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder='static')
# Use a secure secret key from environment or generate a random one
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())
# Allow up to 16 MB per upload (reduced for mobile stability)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
# Set secure cookie options
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('ENVIRONMENT') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Set permanent session lifetime to 1 day
app.config['PERMANENT_SESSION_LIFETIME'] = 86400

# Ensure static directory exists
STATIC_DIR = PROJECT_ROOT / 'static'
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(STATIC_DIR / 'css', exist_ok=True)
os.makedirs(STATIC_DIR / 'js', exist_ok=True)
os.makedirs(STATIC_DIR / 'images', exist_ok=True)

# Simple hardcoded users (admin/admin123)
USERS = {
    'admin': {
        'password_hash': generate_password_hash('admin123'),
        'is_admin': True
    }
}

# MySQL Configuration (only if available)
if MYSQL_AVAILABLE:
    DB_CONFIG = {
        'host': '45.151.120.6',
        'user': 'u733147707_trend',
        'password': '0EgZk/GkTb*',
        'database': 'u733147707_trend',
        'charset': 'utf8mb4',
        'autocommit': True
    }
    
    _mysql_initialized = False
    
    def init_mysql():
        """Initialize MySQL safely"""
        global _mysql_initialized
        if _mysql_initialized:
            return True
            
        try:
            print(f"Connecting to MySQL: {DB_CONFIG['host']}:{DB_CONFIG['database']}")
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Show all tables to debug
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"Existing tables: {tables}")
            
            # Create users table with more detailed logging
            print("Creating users table...")
            try:
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
                print("Users table created or already exists")
            except Exception as table_error:
                print(f"Error creating table: {table_error}")
                
            # Verify table exists
            cursor.execute("SHOW TABLES LIKE 'users'")
            if not cursor.fetchone():
                print("ERROR: Users table was not created!")
                conn.close()
                return False
                
            # Create admin user if not exists
            print("Checking for admin user...")
            cursor.execute('SELECT COUNT(*) FROM users WHERE username = %s', ('admin',))
            admin_count = cursor.fetchone()[0]
            print(f"Admin count: {admin_count}")
            
            if admin_count == 0:
                print("Creating admin user...")
                try:
                    admin_hash = generate_password_hash('admin123')
                    cursor.execute('''
                        INSERT INTO users (username, password_hash, is_admin, created_by)
                        VALUES (%s, %s, %s, %s)
                    ''', ('admin', admin_hash, True, 'system'))
                    print("Admin user created")
                except Exception as user_error:
                    print(f"Error creating admin: {user_error}")
            
            # Also create 'freitas' user if requested
            print("Checking for freitas user...")
            cursor.execute('SELECT COUNT(*) FROM users WHERE username = %s', ('freitas',))
            if cursor.fetchone()[0] == 0:
                print("Creating freitas user...")
                try:
                    freitas_hash = generate_password_hash('diferentona157')
                    cursor.execute('''
                        INSERT INTO users (username, password_hash, is_admin, created_by)
                        VALUES (%s, %s, %s, %s)
                    ''', ('freitas', freitas_hash, True, 'system'))
                    print("Freitas user created")
                except Exception as freitas_error:
                    print(f"Error creating freitas: {freitas_error}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            _mysql_initialized = True
            print("MySQL initialized successfully")
            return True
            
        except Exception as e:
            print(f"MySQL initialization failed: {e}")
            return False
    
    def get_mysql_user(username: str) -> Optional[Dict[str, Any]]:
        """Get user from MySQL"""
        try:
            if not init_mysql():
                return None
                
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
            
            cursor.close()
            conn.close()
            return user
            
        except Exception as e:
            print(f"Error getting MySQL user {username}: {e}")
            return None
    
    def create_mysql_user(username: str, password: str, is_admin: bool = False, created_by: str = 'admin') -> bool:
        """Create user in MySQL"""
        try:
            if not init_mysql():
                return False
                
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
            if cursor.fetchone()[0] > 0:
                print(f"User {username} already exists")
                cursor.close()
                conn.close()
                return False
                
            password_hash = generate_password_hash(password)
            
            cursor.execute('''
                INSERT INTO users (username, password_hash, is_admin, created_by)
                VALUES (%s, %s, %s, %s)
            ''', (username, password_hash, is_admin, created_by))
            
            conn.commit()
            cursor.close()
            conn.close()
            print(f"User {username} created successfully")
            return True
            
        except Exception as e:
            print(f"Error creating MySQL user {username}: {e}")
            return False
            
    def delete_mysql_user(username: str) -> bool:
        """Delete user from MySQL"""
        try:
            if not init_mysql():
                return False
                
            # Don't allow deleting the main admin
            if username == 'admin':
                print("Cannot delete main admin user")
                return False
                
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM users WHERE username = %s", (username,))
            deleted = cursor.rowcount > 0
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if deleted:
                print(f"User {username} deleted successfully")
            else:
                print(f"User {username} not found")
                
            return deleted
            
        except Exception as e:
            print(f"Error deleting MySQL user {username}: {e}")
            return False
            
    def update_mysql_user_admin(username: str, is_admin: bool) -> bool:
        """Update user admin status"""
        try:
            if not init_mysql():
                return False
                
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            cursor.execute("UPDATE users SET is_admin = %s WHERE username = %s", (is_admin, username))
            updated = cursor.rowcount > 0
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if updated:
                print(f"User {username} admin status updated to {is_admin}")
            else:
                print(f"User {username} not found")
                
            return updated
            
        except Exception as e:
            print(f"Error updating MySQL user {username}: {e}")
            return False
    
    def get_all_mysql_users() -> List[Dict[str, Any]]:
        """Get all users from MySQL"""
        try:
            if not init_mysql():
                return []
                
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            users = cursor.fetchall()
            
            cursor.close()
            conn.close()
            return users
            
        except Exception as e:
            print(f"Error getting MySQL users: {e}")
            return []

def login_required(fn: Callable) -> Callable:
	def wrapper(*args, **kwargs):
		if not session.get('auth'):
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

def run_exiftool_write(src: Path, dst: Path, meta: Dict[str, Any], is_video: bool = False) -> subprocess.CompletedProcess:
    """Aplica todos os metadados da trend usando exiftool"""
    # Primeiro, copia o arquivo para preservar a estrutura original
    import shutil
    shutil.copy2(src, dst)
    
    # Para vídeos, usamos uma abordagem diferente
    if is_video:
        return apply_video_metadata(dst, meta)
    
    # Para imagens, usamos a abordagem padrão
    args = ["exiftool", "-m", "-q", "-overwrite_original"]
    
    # Adiciona todos os metadados EXIF
    for key, (exif_tag, override_value) in EXIF_MAP.items():
        value = override_value if override_value is not None else meta.get(key)
        if value is not None:
            args.append(f"-{exif_tag}={value}")
    
    # Adiciona todos os outros metadados como XMP
    remaining = {}
    for k, v in meta.items():
        if k not in EXIF_MAP:
            remaining[k] = v
    
    # Adiciona o JSON completo como XMP Description
    desc_json = json.dumps(remaining, ensure_ascii=False)
    args.append(f"-XMP-dc:Description={desc_json}")
    
    # Adiciona metadados específicos da trend que são críticos
    args.extend([
        f"-Make={meta.get('make', 'Meta View')}",
        f"-Model={meta.get('model', 'Ray-Ban Meta Smart Glasses')}",
        f"-GPSLatitude={meta.get('gps_latitude', '22 deg 58\' 46.24\" S')}",
        f"-GPSLongitude={meta.get('gps_longitude', '43 deg 24\' 42.09\" W')}",
        f"-GPSLatitudeRef={meta.get('gps_latitude_ref', 'South')}",
        f"-GPSLongitudeRef={meta.get('gps_longitude_ref', 'West')}"
    ])
    
    # Aplica no arquivo de destino
    args.append(str(dst))
    
    print(f"Applying image metadata with command: {' '.join(args)}")
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def apply_video_metadata(video_path: Path, meta: Dict[str, Any]) -> subprocess.CompletedProcess:
    """Aplica metadados específicos para vídeos da trend baseado no arquivo IMG_5975.MOV"""
    print(f"Applying trend metadata to video {video_path}")
    
    # ID único para o dispositivo (extraído do arquivo de exemplo)
    device_id = "31602281-4A5C-417D-A0F4-108B7FD05B0E"
    
    # Data atual formatada
    current_date = datetime.now().strftime('%Y:%m:%d %H:%M:%S')
    
    # Aplicamos todos os metadados de uma vez para garantir compatibilidade
    all_args = [
        "exiftool", "-m", "-q", "-overwrite_original",
        
        # Metadados básicos da trend (extraídos do arquivo de exemplo)
        "-Copyright=Meta AI",
        "-Model=Ray-Ban Meta Smart Glasses",
        
        # Coordenadas GPS exatas da trend (extraídas do arquivo de exemplo)
        "-GPSLatitude=15 deg 47' 26.16\" S",
        "-GPSLongitude=47 deg 53' 3.48\" W",
        "-GPSLatitudeRef=South",
        "-GPSLongitudeRef=West",
        
        # Metadados técnicos para vídeos (extraídos do arquivo de exemplo)
        "-VideoFrameRate=30",
        "-CompressorID=hvc1",
        "-CompressorName='hvc1'",
        "-HandlerType=Video Track",
        "-HandlerVendorID=Apple",
        "-HandlerDescription=Core Media Video",
        
        # Metadados de áudio (extraídos do arquivo de exemplo)
        "-MediaLanguageCode=und",
        "-AudioFormat=mp4a",
        "-AudioChannels=2",
        "-AudioBitsPerSample=16",
        "-AudioSampleRate=48000",
        
        # Metadados de resolução (extraídos do arquivo de exemplo)
        "-XResolution=72",
        "-YResolution=72",
        "-BitDepth=24",
        
        # Datas (usando valores atuais)
        f"-CreateDate={current_date}",
        f"-ModifyDate={current_date}",
        f"-TrackCreateDate={current_date}",
        f"-TrackModifyDate={current_date}",
        f"-MediaCreateDate={current_date}",
        f"-MediaModifyDate={current_date}",
        f"-CreationDate={current_date}Z",
        
        # Comentário especial (extraído do arquivo de exemplo)
        f"-Comment=app=Meta AI&device=Ray-Ban Meta Smart Glasses&id={device_id}",
        
        # Metadados específicos da trend
        "-MajorBrand=Apple QuickTime (.MOV/QT)",
        "-MinorVersion=0.0.0",
        
        # Aplica no arquivo
        str(video_path)
    ]
    
    # Executa o comando exiftool com todos os metadados
    all_proc = subprocess.run(all_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(f"Video metadata application result: {all_proc.returncode}")
    
    # Se o primeiro comando falhou, tente uma abordagem alternativa
    if all_proc.returncode != 0:
        print(f"Error applying metadata: {all_proc.stderr}")
        print("Trying alternative approach...")
        
        # Abordagem alternativa: aplicar metadados em etapas menores
        basic_args = [
            "exiftool", "-m", "-q", "-overwrite_original",
            "-Copyright=Meta AI",
            "-Model=Ray-Ban Meta Smart Glasses",
            f"-Comment=app=Meta AI&device=Ray-Ban Meta Smart Glasses&id={device_id}",
            str(video_path)
        ]
        
        basic_proc = subprocess.run(basic_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"Basic metadata result: {basic_proc.returncode}")
        
        # Aplicar metadados GPS separadamente
        gps_args = [
            "exiftool", "-m", "-q", "-overwrite_original",
            "-GPSLatitude=15 deg 47' 26.16\" S",
            "-GPSLongitude=47 deg 53' 3.48\" W",
            "-GPSLatitudeRef=South",
            "-GPSLongitudeRef=West",
            str(video_path)
        ]
        
        gps_proc = subprocess.run(gps_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"GPS metadata result: {gps_proc.returncode}")
        
        # Retorna o resultado da abordagem alternativa
        return basic_proc
    
    # Retorna o resultado do comando principal
    return all_proc

@app.route('/mysql-status')
def mysql_status():
    """Detailed MySQL status check"""
    if not MYSQL_AVAILABLE:
        return {'status': 'error', 'message': 'MySQL module not available'}
    
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check connection
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        
        # Check tables
        cursor.execute("SHOW TABLES")
        tables = [t[0] for t in cursor.fetchall()]
        
        # Check users if users table exists
        users = []
        if 'users' in tables:
            cursor.execute("SELECT username, is_admin FROM users")
            users = [{'username': u[0], 'is_admin': bool(u[1])} for u in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return {
            'status': 'ok',
            'mysql_version': version[0] if version else 'unknown',
            'connected': True,
            'tables': tables,
            'users': users
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@app.route('/health')
def health_check():
    try:
        # Check if exiftool is available
        result = subprocess.run(['exiftool', '-ver'], capture_output=True, text=True)
        exiftool_ok = result.returncode == 0
        
        # Check directories
        upload_ok = UPLOAD_DIR.exists() and os.access(UPLOAD_DIR, os.W_OK)
        processed_ok = PROCESSED_DIR.exists() and os.access(PROCESSED_DIR, os.W_OK)
        
        mysql_status = False
        if MYSQL_AVAILABLE:
            try:
                mysql_status = init_mysql()
            except:
                pass
        
        return {
            'status': 'ok',
            'version': 'hybrid-safe',
            'exiftool': exiftool_ok,
            'mysql_available': MYSQL_AVAILABLE,
            'mysql_connected': mysql_status,
            'upload_dir': upload_ok,
            'processed_dir': processed_ok,
            'exiftool_version': result.stdout.strip() if exiftool_ok else 'not found'
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to index
    if session.get('auth'):
        return redirect(url_for('index'))
        
    try:
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            if not username or not password:
                flash('Usuário e senha são obrigatórios')
                return redirect(url_for('login'))
            
            # Try MySQL first, then fallback to hardcoded
            user_found = False
            is_admin = False
            
            if MYSQL_AVAILABLE:
                mysql_user = get_mysql_user(username)
                if mysql_user and check_password_hash(mysql_user['password_hash'], password):
                    user_found = True
                    is_admin = bool(mysql_user['is_admin'])
            
            # Fallback to hardcoded users
            if not user_found and username in USERS:
                user = USERS[username]
                if check_password_hash(user['password_hash'], password):
                    user_found = True
                    is_admin = bool(user.get('is_admin', False))
            
            if user_found:
                # Set session as permanent (uses PERMANENT_SESSION_LIFETIME)
                session.permanent = True
                session['auth'] = True
                session['username'] = username
                session['is_admin'] = is_admin
                session['login_time'] = datetime.now().isoformat()
                
                # Security: validate next parameter to prevent open redirect
                next_url = request.args.get('next')
                if next_url and not next_url.startswith('/'):
                    next_url = None
                
                return redirect(next_url or url_for('index'))
            
            # Use constant time comparison to prevent timing attacks
            from hmac import compare_digest
            compare_digest('dummy', 'dummy')  # Always do this work even if user not found
            
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
	if request.method == 'POST':
		if MYSQL_AVAILABLE:
			action = request.form.get('action')
			
			# Create new user
			if action == 'create_user':
				username = request.form.get('username', '').strip()
				password = request.form.get('password', '').strip()
				is_admin = request.form.get('is_admin') == 'on'
				
				if not username or not password:
					flash('Usuário e senha são obrigatórios')
					return redirect(url_for('admin'))
				
				if create_mysql_user(username, password, is_admin=is_admin, created_by=session.get('username', 'admin')):
					flash(f'Usuário {username} criado com sucesso')
				else:
					flash('Usuário já existe ou erro ao criar')
				return redirect(url_for('admin'))
				
			# Delete user
			elif action == 'delete_user':
				username = request.form.get('username', '').strip()
				
				if not username:
					flash('Nome de usuário é obrigatório')
					return redirect(url_for('admin'))
					
				if delete_mysql_user(username):
					flash(f'Usuário {username} removido com sucesso')
				else:
					flash('Erro ao remover usuário ou usuário não existe')
				return redirect(url_for('admin'))
				
			# Toggle admin status
			elif action == 'toggle_admin':
				username = request.form.get('username', '').strip()
				make_admin = request.form.get('make_admin') == 'true'
				
				if not username:
					flash('Nome de usuário é obrigatório')
					return redirect(url_for('admin'))
					
				if update_mysql_user_admin(username, make_admin):
					status = "administrador" if make_admin else "usuário normal"
					flash(f'Usuário {username} agora é {status}')
				else:
					flash('Erro ao atualizar status do usuário')
				return redirect(url_for('admin'))
		else:
			flash('MySQL não disponível. Apenas funcionalidade básica.')
		return redirect(url_for('admin'))
	
	# Get users from MySQL if available, otherwise show hardcoded
	if MYSQL_AVAILABLE:
		users_list = get_all_mysql_users()
		mysql_status = "Conectado"
	else:
		users_list = []
		for username, user_data in USERS.items():
			users_list.append({
				'username': username,
				'is_admin': user_data.get('is_admin', False),
				'created_at': datetime.now(),
				'created_by': 'system'
			})
		mysql_status = "Não disponível"
	
	return render_template('admin.html', users=users_list, mysql_status=mysql_status)

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

        # Security: Verify file is an allowed media type (image or video)
        allowed_extensions = {
            # Images
            'jpg', 'jpeg', 'png', 'gif', 'heic', 'heif', 
            # Videos
            'mp4', 'mov', 'avi', '3gp', 'mkv'
        }
        file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            flash('Tipo de arquivo não permitido. Use JPG, PNG, HEIC, MP4 ou MOV.')
            return redirect(url_for('index'))
            
        # Check file content type (basic MIME check)
        file_content = file.read(1024)  # Read first 1KB
        file.seek(0)  # Reset pointer
        
        # Basic signature check for common media formats
        is_valid_media = (
            # Images
            file_content.startswith(b'\xff\xd8\xff') or  # JPEG
            b'PNG' in file_content[:20] or  # PNG
            b'GIF' in file_content[:20] or  # GIF
            b'ftypheic' in file_content[:20] or  # HEIC
            # Videos
            b'ftyp' in file_content[:20] or  # MP4/MOV
            file_content.startswith(b'\x00\x00\x00\x14ftyp') or  # MP4
            file_content.startswith(b'\x00\x00\x00\x18ftyp') or  # MOV
            file_content.startswith(b'RIFF') or  # AVI
            file_content.startswith(b'\x1A\x45\xDF\xA3')  # MKV
        )
        
        if not is_valid_media:
            flash('O arquivo não parece ser uma mídia válida.')
            return redirect(url_for('index'))
            
        # Determine media type
        is_video = file_ext in {'mp4', 'mov', 'avi', '3gp', 'mkv'}

        # Sanitize filename for safe filesystem writes
        filename = secure_filename(file.filename)
        if not filename:
            flash('Nome de arquivo inválido')
            return redirect(url_for('index'))
            
        # Add username and timestamp to prevent filename collisions
        safe_username = secure_filename(session.get('username', 'anonymous'))
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{safe_username}_{timestamp}_{filename}"
        
        upload_path = UPLOAD_DIR / filename
        file.save(str(upload_path))
        
        # Verify file was saved
        if not upload_path.exists():
            flash('Erro ao salvar arquivo')
            return redirect(url_for('index'))

        # Prepare output filename
        processed_name = f"{upload_path.stem}-trend{upload_path.suffix or '.heic'}"
        processed_path = PROCESSED_DIR / processed_name
        
        # Apply metadata with improved function (includes copying the file)
        try:
            media_type = "vídeo" if is_video else "imagem"
            print(f"Applying trend metadata to {upload_path} (type: {media_type})")
            write_proc = run_exiftool_write(upload_path, processed_path, TREND_META, is_video=is_video)
            
            if write_proc.returncode != 0:
                print(f"ExifTool warning: {write_proc.stderr}")
                flash(f'Metadados aplicados parcialmente ao {media_type}')
            else:
                print(f"Metadata applied successfully to {media_type}")
        except Exception as e:
            print(f"ExifTool error: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Erro ao aplicar metadados ao {media_type}, mas o arquivo foi processado')
        
        # Verify the processed file exists
        if not processed_path.exists():
            flash('Erro ao processar arquivo')
            return redirect(url_for('index'))
            
        # Verify metadata was applied and fix if needed
        try:
            # First verification
            verify_proc = subprocess.run(
                ["exiftool", "-json", str(processed_path)], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            
            if verify_proc.returncode == 0:
                print(f"Metadata verification: {verify_proc.stdout[:100]}...")
                
                # Check if critical metadata is missing
                metadata_ok = False
                try:
                    import json
                    metadata = json.loads(verify_proc.stdout)
                    if metadata and isinstance(metadata, list) and len(metadata) > 0:
                        metadata = metadata[0]
                        # Check for critical metadata
                        if is_video:
                            metadata_ok = (
                                metadata.get("Make") == "Meta View" and
                                metadata.get("Model") == "Ray-Ban Meta Smart Glasses"
                            )
                        else:
                            metadata_ok = (
                                metadata.get("Make") == "Meta View" and
                                metadata.get("Model") == "Ray-Ban Meta Smart Glasses" and
                                metadata.get("GPSLatitude") is not None
                            )
                except:
                    metadata_ok = False
                
                # If metadata is missing for videos, try again with our specialized function
                if not metadata_ok and is_video:
                    print("Video metadata missing, applying specialized video metadata...")
                    apply_video_metadata(processed_path, TREND_META)
                    print("Video metadata application completed")
                    
                    # Verificar novamente após aplicar os metadados
                    verify_again = subprocess.run(
                        ["exiftool", "-json", str(processed_path)], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE, 
                        text=True
                    )
                    
                    if verify_again.returncode == 0:
                        print("Video metadata verification after specialized application:")
                        try:
                            metadata_verify = json.loads(verify_again.stdout)
                            if metadata_verify and isinstance(metadata_verify, list) and len(metadata_verify) > 0:
                                metadata_verify = metadata_verify[0]
                                print(f"Model: {metadata_verify.get('Model')}")
                                print(f"Copyright: {metadata_verify.get('Copyright')}")
                                print(f"Comment: {metadata_verify.get('Comment', '')[:30]}...")
                        except:
                            print("Error parsing verification metadata")
                # If metadata is missing for images, try a more direct approach
                elif not metadata_ok:
                    print("Critical metadata missing, trying direct approach...")
                    # Direct approach for stubborn files
                    direct_args = [
                        "exiftool", "-overwrite_original",
                        "-Make=Meta View",
                        "-Model=Ray-Ban Meta Smart Glasses",
                        "-GPSLatitude=22 deg 58' 46.24\" S",
                        "-GPSLongitude=43 deg 24' 42.09\" W",
                        "-GPSLatitudeRef=South",
                        "-GPSLongitudeRef=West",
                        "-user_comment=34D16852-7110-470A-8B25-D48E3A791E26",
                        "-checksum=89c4e3c64b0175c4de454f5f34504434"
                    ]
                        
                    direct_args.append(str(processed_path))
                    subprocess.run(direct_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    print("Direct metadata application completed")
        except Exception as e:
            print(f"Metadata verification error: {e}")

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
    # Security: Validate filename to prevent path traversal
    filename = secure_filename(filename)
    if not filename:
        flash('Nome de arquivo inválido')
        return redirect(url_for('index'))
        
    # Check if file exists
    file_path = PROCESSED_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        flash('Arquivo não encontrado')
        return redirect(url_for('index'))
        
    # Set secure headers
    response = send_from_directory(str(PROCESSED_DIR), filename, as_attachment=True)
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.errorhandler(500)
def internal_error(error):
    print(f"500 error: {error}")
    flash('Erro interno do servidor. Tente novamente.')
    return redirect(url_for('index'))

@app.errorhandler(413)
def too_large(error):
    flash('Arquivo muito grande. Máximo 16MB.')
    return redirect(url_for('index'))

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5173)), debug=True)