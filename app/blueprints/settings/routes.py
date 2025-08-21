import os
import json
from . import settings_bp
from ...config import Config
from flask import jsonify, request
from ...functions import allowed_file
from ...extensions import db, redis_client
from werkzeug.utils import secure_filename
from ...models import Settings, tariff_plan
from ...logging_config import configure_logging

logger = configure_logging()


@settings_bp.route('/api/settings_data', methods=['POST'])
def update_settings_data():
    try:
        settings_data_json = request.form.get('settingsData')
        if not settings_data_json:
            logger.warning("[update_settings_data] No settings data provided")
            return jsonify({'success': False, 'error': 'No settings data provided'}), 400

        settings_data = json.loads(settings_data_json)

        settings = Settings.query.first()
        if not settings:
            settings = Settings()

        settings.switch1 = settings_data.get('switch1', False)
        settings.switch2 = settings_data.get('switch2', False)
        settings.switch3 = settings_data.get('switch3', False)
        settings.switch4 = settings_data.get('switch4', False)
        settings.switch5 = settings_data.get('switch5', False)
        settings.switch6 = settings_data.get('switch6', False)
        settings.freeTime = settings_data.get('freeTime', '')
        settings.freeTimeRepeat = settings_data.get('freeTimeRepeat', '')
        settings.docx = settings_data.get('docx', '')
        settings.phone = settings_data.get('phone', '')
        settings.text1 = settings_data.get('text1', '')
        settings.text2 = settings_data.get('text2', '')

        if 'file1' in request.files:
            file1 = request.files['file1']
            if file1 and allowed_file(file1.filename):
                filename1 = secure_filename(file1.filename)
                file1.save(os.path.join(Config.UPLOAD_FOLDER, filename1))
                settings.file1Preview = f"/static/images/{filename1}"
                logger.info(f"[update_settings_data] Saved file1 as {filename1}")

        if 'file2' in request.files:
            file2 = request.files['file2']
            if file2 and allowed_file(file2.filename):
                filename2 = secure_filename(file2.filename)
                file2.save(os.path.join(Config.UPLOAD_FOLDER, filename2))
                settings.file2Preview = f"/static/images/{filename2}"
                logger.info(f"[update_settings_data] Saved file2 as {filename2}")

        if 'MINUT' in settings.freeTime:
            minutes = settings.freeTime.split()[0]
            tariff = tariff_plan.query.filter_by(id=settings_data['id']).first()
            if tariff:
                tariff.duration_days = f"{minutes} minutes"
                db.session.commit()
                logger.info(f"[update_settings_data] Updated tariff (id={settings_data['id']}) duration to {minutes} minutes")

        db.session.add(settings)
        db.session.commit()

        cache_key = 'view//api/get_admin_phone'
        second_cache_key = 'view//api/settings_data'
        # redis_client.delete(cache_key)
        # redis_client.delete(second_cache_key)

        logger.info("[update_settings_data] Settings updated successfully")
        return jsonify({'success': True}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"[update_settings_data] Error updating settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/api/settings_data', methods=['GET'])
def get_settings_data():
    settings = Settings.query.first()
    if settings:
        settings_dict = {
            'id': settings.id,
            'file1Preview': settings.file1Preview.decode('utf-8') if isinstance(settings.file1Preview, bytes)
            else settings.file1Preview,
            'file2Preview': settings.file2Preview.decode('utf-8') if isinstance(settings.file2Preview, bytes)
            else settings.file2Preview,
            'docx': settings.docx,
            'switch1': settings.switch1,
            'switch2': settings.switch2,
            'switch3': settings.switch3,
            'switch4': settings.switch4,
            'switch5': settings.switch5,
            'switch6': settings.switch6,
            'freeTime': settings.freeTime,
            'freeTimeRepeat': settings.freeTimeRepeat,
            'phone': settings.phone,
            'text1': settings.text1,
            'text2': settings.text2
        }

        for key, value in settings_dict.items():
            logger.warning(f"{key}: {type(value)}")

        return jsonify({'success': True, 'settingsData': settings_dict}), 200
    else:
        return jsonify({'success': False, 'error': 'No settings found'}), 404