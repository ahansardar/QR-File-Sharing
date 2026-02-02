from flask import Blueprint, render_template, request, send_file, current_app, jsonify
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from urllib.parse import unquote
import os
import qrcode
import datetime


bp = Blueprint('main', __name__)


def file_age_in_days(filepath):
    file_creation_time = os.path.getctime(filepath)
    current_time = datetime.datetime.now().timestamp()
    return (current_time - file_creation_time) / 86400  


def cleanup_files():
    upload_folder = current_app.config['UPLOAD_FOLDER']
    for filename in os.listdir(upload_folder):
        file_path = os.path.join(upload_folder, filename)
        if os.path.isfile(file_path) and file_age_in_days(file_path) > 7:
            os.remove(file_path)
            print(f"Deleted: {file_path}")


scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_files, IntervalTrigger(days=1))
scheduler.start()


@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        upload_folder = current_app.config['UPLOAD_FOLDER']
        upload_path = os.path.join(upload_folder, filename)
        file.save(upload_path)

        
        download_link = f"http://{request.host}/download/{filename}"
        qr = qrcode.make(download_link)
        qr_filename = f"{filename}_qr.png"
        qr_path = os.path.join(upload_folder, qr_filename)
        qr.save(qr_path)

        return jsonify({
            'message': 'File uploaded successfully',
            'download_link': download_link,
            'qr_code': f"/static/uploads/{qr_filename}"
        })

    return jsonify({'error': 'File upload failed'}), 400

@bp.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    return jsonify({'error': 'File not found'}), 404

@bp.route('/cleanup', methods=['POST'])
def manual_cleanup():
    cleanup_files()
    return jsonify({'message': 'Cleanup executed successfully'}), 200
    
@bp.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    filename = unquote(filename)
    try:
        
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, filename)
        
        print(f"Attempting to delete file: {file_path}")

        if os.path.exists(file_path):
            os.remove(file_path)  
            print(f"File deleted: {file_path}")
            
            
            qr_code_path = os.path.join(upload_folder, f"{filename}_qr.png")
            if os.path.exists(qr_code_path):
                os.remove(qr_code_path)
                print(f"QR code deleted: {qr_code_path}")
            
            return jsonify({"success": True}), 200
        else:
            print(f"File not found: {file_path}")
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500



import atexit
atexit.register(lambda: scheduler.shutdown())

