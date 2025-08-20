import os
import json
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash

# Base directories
PROJECT_ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = PROJECT_ROOT / 'uploads'
PROCESSED_DIR = PROJECT_ROOT / 'processed'
TEMPLATES_DIR = PROJECT_ROOT / 'templates'

# Ensure directories exist
for d in [UPLOAD_DIR, PROCESSED_DIR, TEMPLATES_DIR]:
	os.makedirs(d, exist_ok=True)

app = Flask(__name__, template_folder=str(TEMPLATES_DIR))
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret')

# Metadata for the trend
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


@app.route('/', methods=['GET'])

def index():
	return render_template('index.html')


@app.route('/upload', methods=['POST'])

def upload():
	if 'image' not in request.files:
		flash('Selecione um arquivo')
		return redirect(url_for('index'))
	file = request.files['image']
	if not file or file.filename == '':
		flash('Arquivo inválido')
		return redirect(url_for('index'))

	upload_path = UPLOAD_DIR / file.filename
	file.save(str(upload_path))

	processed_name = f"{upload_path.stem}-with-metadata{upload_path.suffix or '.heic'}"
	processed_path = PROCESSED_DIR / processed_name

	write_proc = run_exiftool_write(upload_path, processed_path, TREND_META)
	if write_proc.returncode != 0 or not processed_path.exists():
		flash('Falha ao gravar metadados. Tente outra imagem.')
		return redirect(url_for('index'))

	return render_template('result.html', processed_filename=processed_name)


@app.route('/download/<path:filename>')

def download(filename: str):
	return send_from_directory(str(PROCESSED_DIR), filename, as_attachment=True)


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5173)), debug=True)
