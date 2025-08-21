import os
import json
from . import reklama_bp
from ...config import Config
from ...env import ADS_DIRECTORY
from ...models import ReklamaData
from ...functions import allowed_file
from ...extensions import db, redis_client
from werkzeug.utils import secure_filename
from ...logging_config import configure_logging
from flask import jsonify, request, send_from_directory

logger = configure_logging()

@reklama_bp.route('/api/reklama_data', methods=['GET'])
def get_reklama_data():
    reklama_entries = ReklamaData.query.all()
    reklama_list = []
    for reklama in reklama_entries:
        reklama_dict = {
            'id': reklama.id,
            'file1Preview': reklama.file1Preview,
            'file2Preview': reklama.file2Preview,
            'file3Preview': reklama.file3Preview,
            'file4Preview': reklama.file4Preview,
            'file5Preview': reklama.file5Preview,
            'duration1': reklama.duration1,
            'duration2': reklama.duration2,
            'duration3': reklama.duration3,
            'duration4': reklama.duration4,
            'duration5': reklama.duration5,
            'date_start1': reklama.date_start1,
            'date_start2': reklama.date_start2,
            'date_start3': reklama.date_start3,
            'date_start4': reklama.date_start4,
            'date_start5': reklama.date_start5,
            'date_end1': reklama.date_end1,
            'date_end2': reklama.date_end2,
            'date_end3': reklama.date_end3,
            'date_end4': reklama.date_end4,
            'date_end5': reklama.date_end5,
            'check1': reklama.check1,
            'check2': reklama.check2,
            'check3': reklama.check3,
            'check4': reklama.check4,
            'check5': reklama.check5,
            'rek': reklama.rek,
            'reko': reklama.reko
        }
        reklama_list.append(reklama_dict)
    return jsonify({'success': True, 'reklamaData': reklama_list}), 200


@reklama_bp.route('/api/reklama_data', methods=['POST'])
def update_reklama_data():
    try:
        reklama_data_json = request.form.get('reklamaData')
        if not reklama_data_json:
            return jsonify({'error': 'No reklama data provided'}), 400

        reklama_data = json.loads(reklama_data_json)
        logger.info(f"Received reklama data: {reklama_data}")

        file_paths = {}
        for i in range(1, 6):
            file_path_key = f'file{i}Path'
            file_path = request.form.get(file_path_key)
            
            if file_path == 'DELETE_FILE' or reklama_data.get(f'delete_file{i}') == True:
                file_paths[f'file{i}Preview'] = None  
                logger.info(f"Marking {file_path_key} for deletion")
            elif file_path: 
                file_paths[f'file{i}Preview'] = file_path
                logger.info(f"Received {file_path_key}: {file_path}")

        reklama = db.session.get(ReklamaData, reklama_data.get('id'))
        if reklama:
            for key, path in file_paths.items():
                setattr(reklama, key, path)
                logger.info(f"Set {key} to {path}")

            reklama.duration1 = reklama_data.get('duration1')
            reklama.duration2 = reklama_data.get('duration2')
            reklama.duration3 = reklama_data.get('duration3')
            reklama.duration4 = reklama_data.get('duration4')
            reklama.duration5 = reklama_data.get('duration5')
            reklama.date_start1 = reklama_data.get('date_start1')
            reklama.date_start2 = reklama_data.get('date_start2')
            reklama.date_start3 = reklama_data.get('date_start3')
            reklama.date_start4 = reklama_data.get('date_start4')
            reklama.date_start5 = reklama_data.get('date_start5')
            reklama.date_end1 = reklama_data.get('date_end1')
            reklama.date_end2 = reklama_data.get('date_end2')
            reklama.date_end3 = reklama_data.get('date_end3')
            reklama.date_end4 = reklama_data.get('date_end4')
            reklama.date_end5 = reklama_data.get('date_end5')
            reklama.check1 = reklama_data.get('check1')
            reklama.check2 = reklama_data.get('check2')
            reklama.check3 = reklama_data.get('check3')
            reklama.check4 = reklama_data.get('check4')
            reklama.check5 = reklama_data.get('check5')
            reklama.rek = reklama_data.get('rek')
            reklama.reko = reklama_data.get('reko')

            db.session.commit()
            logger.info(f"Updated ReklamaData ID {reklama.id}")
        else:
            new_reklama = ReklamaData(
                id=reklama_data.get('id'),
                file1Preview=file_paths.get('file1Preview'),
                file2Preview=file_paths.get('file2Preview'),
                file3Preview=file_paths.get('file3Preview'),
                file4Preview=file_paths.get('file4Preview'),
                file5Preview=file_paths.get('file5Preview'),
                duration1=reklama_data.get('duration1'),
                duration2=reklama_data.get('duration2'),
                duration3=reklama_data.get('duration3'),
                duration4=reklama_data.get('duration4'),
                duration5=reklama_data.get('duration5'),
                date_start1=reklama_data.get('date_start1'),
                date_start2=reklama_data.get('date_start2'),
                date_start3=reklama_data.get('date_start3'),
                date_start4=reklama_data.get('date_start4'),
                date_start5=reklama_data.get('date_start5'),
                date_end1=reklama_data.get('date_end1'),
                date_end2=reklama_data.get('date_end2'),
                date_end3=reklama_data.get('date_end3'),
                date_end4=reklama_data.get('date_end4'),
                date_end5=reklama_data.get('date_end5'),
                check1=reklama_data.get('check1'),
                check2=reklama_data.get('check2'),
                check3=reklama_data.get('check3'),
                check4=reklama_data.get('check4'),
                check5=reklama_data.get('check5'),
                rek=reklama_data.get('rek'),
                reko=reklama_data.get('reko')
            )
            db.session.add(new_reklama)
            db.session.commit()
            logger.info(f"Created new ReklamaData ID {new_reklama.id}")

        cache_key = 'view//api/reklama_data'
        redis_client.delete(cache_key)

        return jsonify({'success': True}), 200

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@reklama_bp.route('/api/ads_directory', methods=['GET'])
def get_ads_directory():
    try:
        if not os.path.exists(ADS_DIRECTORY):
            return jsonify({"success": False, "error": "Ads directory does not exist."}), 404

        files = os.listdir(ADS_DIRECTORY)
        ads_data = [{"filePath": f"/ads/{file}"} for file in files if os.path.isfile(os.path.join(ADS_DIRECTORY, file))]

        return jsonify(ads_data)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@reklama_bp.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        logger.error("No file part in the request")
        return jsonify({'success': False, 'error': 'No file part in the request'}), 400

    file = request.files['file']
    filename = request.form.get('filename', '')

    if file.filename == '':
        logger.error("No selected file")
        return jsonify({'success': False, 'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename_secure = secure_filename(file.filename)
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename_secure)
        logger.info(f"Attempting to save file to: {file_path}")
        try:
            file.save(file_path)
            file_url = f"/ads/{filename_secure}"
            logger.info(f"File successfully saved at: {file_path}")
            return jsonify({'success': True, 'filePath': file_url}), 200
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return jsonify({'success': False, 'error': 'Error saving file'}), 500
    else:
        logger.error(f"File type not allowed: {file.filename}")
        return jsonify({'success': False, 'error': 'File type not allowed'}), 400


@reklama_bp.route('/ads/<filename>', methods=['GET'])
def serve_uploaded_file(filename):
    try:
        return send_from_directory(Config.UPLOAD_FOLDER, filename)
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        return jsonify({'success': False, 'error': 'File not found'}), 404