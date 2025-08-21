# from flask import Flask, jsonify, request, render_template, send_from_directory, redirect
# from logging.handlers import RotatingFileHandler
# from flask_cors import CORS
# import traceback
# import MySQLdb
# import logging
# import redis
# import math
# import gzip
# import json
# import sys
# import os
# from pathlib import Path
# from datetime import datetime
# from dotenv import load_dotenv
# from sqlalchemy import desc, or_
# from flask_migrate import Migrate
# from functions import allowed_file
# from urllib.parse import quote_plus
# from datetime import timedelta, datetime
# from MySQLdb.cursors import DictCursor
# from routeros_api import RouterOsApiPool
# from werkzeug.utils import secure_filename
# from werkzeug.exceptions import RequestEntityTooLarge
# from models import db, tariff_plan, Settings, ReklamaData, User, Transaction, Profiles, UserAuthorization
# from env import users, allowed_files, ADS_DIRECTORY, DB_HOST, DB_USER, DB_PASS, DB_NAME, mikrotik_ip, mikrotik_username, mikrotik_password
# from pyrad.dictionary import Dictionary
# from pyrad.packet import AccessRequest
# from MySQLdb.cursors import DictCursor
# from pyrad.client import Client

# from routeros_api import RouterOsApiPool
# from routeros_api.exceptions import RouterOsApiConnectionError


# import os
# from app import create_app
# from app.extensions import socketio

# env = "dev" if os.getenv("FLASK_ENV", "dev").startswith("dev") else "prod"
# app = create_app(env)

# if __name__ == "__main__":
#     # Run with SocketIO dev server so websockets work in local dev mode
#     socketio.run(app, debug=True, host="0.0.0.0", port=5000)


# from redis_utils import reload_all_active_tariffs

from redis_utils import reload_all_active_tariffs
import os
from app import create_app

env = "dev" if os.getenv("FLASK_ENV", "prod").startswith("dev") else "prod"
app = create_app(env)

with app.app_context():
    reload_all_active_tariffs()

@app.after_request
def remove_server_header(response):
    response.headers["Server"] = "EduWiFi Gateway"
    if "X-Powered-By" in response.headers:
        del response.headers["X-Powered-By"]
    return response


# @app.errorhandler(RequestEntityTooLarge)
# def handle_large_request(e):
#     return jsonify({'error': 'File size exceeds the allowed limit of 500 MB.'}), 413


# @app.route('/')
# def index():
#     return redirect('/admin_panel_login')


# @app.route('/admin_panel_login')
# def admin_panel_login_view():
#     return render_template('admin_panel_login.html')


# @app.route('/admin_panel_main')
# def admin_panel_main_view():
#     return render_template('admin_panel_main.html')


# @app.route('/admin_panel_settings')
# def admin_panel_settings_view():
#     return render_template('admin_panel_settings.html')


# @app.route('/admin_panel_ad')
# def admin_panel_ad_view():
#     return render_template('admin_panel_ad.html')


# @app.route('/admin_panel_transaction')
# def admin_panel_transaction_view():
#     return render_template('admin_panel_tolovlar.html')



# @app.route('/admin_panel_tarif')
# def admin_panel_tarif_view():
#     return render_template('admin_panel_tarif.html')


# @app.route('/admin_panel_users')
# def admin_panel_users_view():
#     return render_template('admin_panel_users.html')


# @app.route('/admin_panel_details')
# def admin_panel_details_view():
#     return render_template('details.html')


# @app.route('/admin_panel_user_info')
# def admin_panel_user_info_view():
#     return render_template('user_info.html')


# @app.route('/api/add_user', methods=['POST'])
# def add_user():
#     data = request.json
#     user_type = data.get('userType')
#     user_full_name = data.get('userFullName')
#     user_phone = data.get('userPhone')
#     user_tariff_minutes = data.get('userTarifMinutes')

#     logger.debug(f"[add_user] Received data: userType={user_type}, userFullName={user_full_name}, "
#                  f"userPhone={user_phone}, userTarifMinutes={user_tariff_minutes}")

#     if all([user_type, user_full_name, user_phone, user_tariff_minutes]):
#         last_user = User.query.order_by(User.merchant_trans_id.desc()).first()
#         merchant_trans_id = last_user.merchant_trans_id + 1 if last_user and last_user.merchant_trans_id else 10000

#         new_user = User(
#             fio=user_full_name.upper(),
#             phone_number=user_phone,
#             role=user_type,
#             merchant_trans_id=merchant_trans_id,
#             last_tariff_limit=str(user_tariff_minutes)
#         )
#         new_profile = Profiles(
#             fio=user_full_name.upper(),
#             phone_number=user_phone,
#         )

#         db.session.add(new_user)
#         db.session.add(new_profile)
#         db.session.commit()

#         logger.info(f"[add_user] User added successfully: phone={user_phone}, role={user_type}, merchant_trans_id={merchant_trans_id}")
#         return jsonify({'success': True, 'message': 'User added successfully'}), 200
#     else:
#         logger.warning(f"[add_user] Invalid data provided: {data}")
#         return jsonify({'error': 'Invalid data'}), 400


# @app.route('/api/login', methods=['POST'])
# def login():
#     data = request.json
#     login_name = data.get('login')
#     password = data.get('password')

#     logger.debug(f"[login] Attempted login with login={login_name}")

#     if login_name == users['admin'] and password == users['password']:
#         logger.info(f"[login] Admin login successful")
#         return jsonify({"success": True}), 200
#     else:
#         logger.warning(f"[login] Invalid login attempt: login={login_name}")
#         return jsonify({"success": False, "message": "Invalid login or password"}), 400


# @app.route('/api/tarif_plans', methods=['GET'])
# def get_tarif_plans_route():
#     try:
#         plans = tariff_plan.query.all()
#         local_list = [plan.to_dict() for plan in plans]

#         radius_data = get_radius_plans()

#         response = {
#             "local_plans": local_list,
#             "radius_plans": radius_data
#         }
#         return jsonify(response), 200
#     except Exception as e:
#         print(f"Error: {e}")
#         return jsonify({"error": "An error occurred"}), 500


# @app.route('/api/tarif_plans', methods=['POST'])
# def update_tarif_plans():
#     data = request.json
#     try:
#         bepul_timeout = None
#         bepul_rate = None
#         bepul_total = None

#         kun_timeout = None
#         kun_rate = None
#         kun_total = None

#         hafta_timeout = None
#         hafta_rate = None
#         hafta_total = None

#         oy_timeout = None
#         oy_rate = None
#         oy_total = None

#         for tarif in data['tarifData']:
#             plan_id = tarif['id']
#             plan = tariff_plan.query.get(plan_id)

#             if plan:
#                 existing_rate = tarif.get('rate_limit_db')
#                 plan.price = tarif.get('price', plan.price)
#                 plan.is_active = tarif.get('is_active', plan.is_active)
#                 plan.duration_days = tarif.get('name', plan.duration_days)
#                 plan.rate_limit = tarif.get('rate_limit', existing_rate)
#                 db.session.commit()

#                 logger.info(
#                     f"[update_tarif_plans] Updated plan ID {plan_id}: "
#                     f"price={plan.price}, active={plan.is_active}, "
#                     f"duration={plan.duration_days}, rate={plan.rate_limit}"
#                 )
#             else:
#                 logger.warning(f"[update_tarif_plans] Plan ID {plan_id} not found")

#             session_timeout = tarif.get('session_timeout_seconds')
#             mikrotik_rate = tarif.get('rate_limit_db')
#             mikrotik_total = tarif.get('session_total_bytes')

#             if plan_id == 1:
#                 bepul_timeout = session_timeout
#                 bepul_rate = mikrotik_rate
#                 bepul_total = mikrotik_total
#             elif plan_id == 2:
#                 kun_timeout = session_timeout
#                 kun_rate = mikrotik_rate
#                 kun_total = mikrotik_total
#             elif plan_id == 3:
#                 hafta_timeout = session_timeout
#                 hafta_rate = mikrotik_rate
#                 hafta_total = mikrotik_total
#             elif plan_id == 4:
#                 oy_timeout = session_timeout
#                 oy_rate = mikrotik_rate
#                 oy_total = mikrotik_total

#         update_tarif_tables(
#             bepul_timeout, bepul_rate, bepul_total,
#             kun_timeout,   kun_rate,   kun_total,
#             hafta_timeout, hafta_rate, hafta_total,
#             oy_timeout,    oy_rate,    oy_total
#         )

#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"[update_tarif_plans] Error updating tariff plans: {e}")
#         return jsonify({"error": "Update failed"}), 500

#     return jsonify({"message": "Tarif plans updated successfully"}), 200


# @app.route('/api/settings_data', methods=['POST'])
# def update_settings_data():
#     try:
#         settings_data_json = request.form.get('settingsData')
#         if not settings_data_json:
#             logger.warning("[update_settings_data] No settings data provided")
#             return jsonify({'success': False, 'error': 'No settings data provided'}), 400

#         settings_data = json.loads(settings_data_json)

#         settings = Settings.query.first()
#         if not settings:
#             settings = Settings()

#         settings.switch1 = settings_data.get('switch1', False)
#         settings.switch2 = settings_data.get('switch2', False)
#         settings.switch3 = settings_data.get('switch3', False)
#         settings.switch4 = settings_data.get('switch4', False)
#         settings.switch5 = settings_data.get('switch5', False)
#         settings.switch6 = settings_data.get('switch6', False)
#         settings.freeTime = settings_data.get('freeTime', '')
#         settings.freeTimeRepeat = settings_data.get('freeTimeRepeat', '')
#         settings.docx = settings_data.get('docx', '')
#         settings.phone = settings_data.get('phone', '')
#         settings.text1 = settings_data.get('text1', '')
#         settings.text2 = settings_data.get('text2', '')

#         # Handle file1Upload
#         if 'file1' in request.files:
#             file1 = request.files['file1']
#             if file1 and allowed_file(file1.filename):
#                 filename1 = secure_filename(file1.filename)
#                 file1.save(os.path.join(app.config['UPLOAD_FOLDER'], filename1))
#                 settings.file1Preview = f"/ads/{filename1}"
#                 logger.info(f"[update_settings_data] Saved file1 as {filename1}")

#         # Handle file2Upload
#         if 'file2' in request.files:
#             file2 = request.files['file2']
#             if file2 and allowed_file(file2.filename):
#                 filename2 = secure_filename(file2.filename)
#                 file2.save(os.path.join(app.config['UPLOAD_FOLDER'], filename2))
#                 settings.file2Preview = f"/ads/{filename2}"
#                 logger.info(f"[update_settings_data] Saved file2 as {filename2}")

#         if 'MINUT' in settings.freeTime:
#             minutes = settings.freeTime.split()[0]
#             tariff = tariff_plan.query.filter_by(id=settings_data['id']).first()
#             if tariff:
#                 tariff.duration_days = f"{minutes} minutes"
#                 db.session.commit()
#                 logger.info(f"[update_settings_data] Updated tariff (id={settings_data['id']}) duration to {minutes} minutes")

#         db.session.add(settings)
#         db.session.commit()

#         cache_key = 'view//api/get_admin_phone'
#         second_cache_key = 'view//api/settings_data'
#         redis_client.delete(cache_key)
#         redis_client.delete(second_cache_key)

#         logger.info("[update_settings_data] Settings updated successfully")
#         return jsonify({'success': True}), 200

#     except Exception as e:
#         db.session.rollback()
#         logger.error(f"[update_settings_data] Error updating settings: {e}")
#         return jsonify({'success': False, 'error': str(e)}), 500


# @app.route('/api/settings_data', methods=['GET'])
# def get_settings_data():
#     settings = Settings.query.first()
#     if settings:
#         settings_dict = {
#             'id': settings.id,
#             'file1Preview': settings.file1Preview.decode('utf-8') if isinstance(settings.file1Preview, bytes)
#             else settings.file1Preview,
#             'file2Preview': settings.file2Preview.decode('utf-8') if isinstance(settings.file2Preview, bytes)
#             else settings.file2Preview,
#             'docx': settings.docx,
#             'switch1': settings.switch1,
#             'switch2': settings.switch2,
#             'switch3': settings.switch3,
#             'switch4': settings.switch4,
#             'switch5': settings.switch5,
#             'switch6': settings.switch6,
#             'freeTime': settings.freeTime,
#             'freeTimeRepeat': settings.freeTimeRepeat,
#             'phone': settings.phone,
#             'text1': settings.text1,
#             'text2': settings.text2
#         }

#         # Optional: Log the types after conversion
#         for key, value in settings_dict.items():
#             logger.warning(f"{key}: {type(value)}")

#         return jsonify({'success': True, 'settingsData': settings_dict}), 200
#     else:
#         return jsonify({'success': False, 'error': 'No settings found'}), 404


# @app.route('/api/reklama_data', methods=['GET'])
# def get_reklama_data():
#     reklama_entries = ReklamaData.query.all()
#     reklama_list = []
#     for reklama in reklama_entries:
#         reklama_dict = {
#             'id': reklama.id,
#             'file1Preview': reklama.file1Preview,
#             'file2Preview': reklama.file2Preview,
#             'file3Preview': reklama.file3Preview,
#             'file4Preview': reklama.file4Preview,
#             'file5Preview': reklama.file5Preview,
#             'duration1': reklama.duration1,
#             'duration2': reklama.duration2,
#             'duration3': reklama.duration3,
#             'duration4': reklama.duration4,
#             'duration5': reklama.duration5,
#             'date_start1': reklama.date_start1,
#             'date_start2': reklama.date_start2,
#             'date_start3': reklama.date_start3,
#             'date_start4': reklama.date_start4,
#             'date_start5': reklama.date_start5,
#             'date_end1': reklama.date_end1,
#             'date_end2': reklama.date_end2,
#             'date_end3': reklama.date_end3,
#             'date_end4': reklama.date_end4,
#             'date_end5': reklama.date_end5,
#             'check1': reklama.check1,
#             'check2': reklama.check2,
#             'check3': reklama.check3,
#             'check4': reklama.check4,
#             'check5': reklama.check5,
#             'rek': reklama.rek,
#             'reko': reklama.reko
#         }
#         reklama_list.append(reklama_dict)
#     return jsonify({'success': True, 'reklamaData': reklama_list}), 200


# @app.route('/api/reklama_data', methods=['POST'])
# def update_reklama_data():
#     try:
#         # Retrieve reklamaData from form
#         reklama_data_json = request.form.get('reklamaData')
#         if not reklama_data_json:
#             return jsonify({'error': 'No reklama data provided'}), 400

#         reklama_data = json.loads(reklama_data_json)
#         logger.info(f"Received reklama data: {reklama_data}")

#         # Retrieve file paths from form data
#         file_paths = {}
#         for i in range(1, 6):
#             file_path_key = f'file{i}Path'
#             file_path = request.form.get(file_path_key)
            
#             # Now explicitly handle deletion
#             if file_path == 'DELETE_FILE' or reklama_data.get(f'delete_file{i}') == True:
#                 file_paths[f'file{i}Preview'] = None  # Set to None for deletion
#                 logger.info(f"Marking {file_path_key} for deletion")
#             elif file_path:  # Only update if there's a new file
#                 file_paths[f'file{i}Preview'] = file_path
#                 logger.info(f"Received {file_path_key}: {file_path}")

#         # Fetch existing ReklamaData record or create a new one
#         reklama = db.session.get(ReklamaData, reklama_data.get('id'))
#         if reklama:
#             # Update file paths if provided or marked for deletion
#             for key, path in file_paths.items():
#                 setattr(reklama, key, path)
#                 logger.info(f"Set {key} to {path}")

#             # Update other fields
#             reklama.duration1 = reklama_data.get('duration1')
#             reklama.duration2 = reklama_data.get('duration2')
#             reklama.duration3 = reklama_data.get('duration3')
#             reklama.duration4 = reklama_data.get('duration4')
#             reklama.duration5 = reklama_data.get('duration5')
#             reklama.date_start1 = reklama_data.get('date_start1')
#             reklama.date_start2 = reklama_data.get('date_start2')
#             reklama.date_start3 = reklama_data.get('date_start3')
#             reklama.date_start4 = reklama_data.get('date_start4')
#             reklama.date_start5 = reklama_data.get('date_start5')
#             reklama.date_end1 = reklama_data.get('date_end1')
#             reklama.date_end2 = reklama_data.get('date_end2')
#             reklama.date_end3 = reklama_data.get('date_end3')
#             reklama.date_end4 = reklama_data.get('date_end4')
#             reklama.date_end5 = reklama_data.get('date_end5')
#             reklama.check1 = reklama_data.get('check1')
#             reklama.check2 = reklama_data.get('check2')
#             reklama.check3 = reklama_data.get('check3')
#             reklama.check4 = reklama_data.get('check4')
#             reklama.check5 = reklama_data.get('check5')
#             reklama.rek = reklama_data.get('rek')
#             reklama.reko = reklama_data.get('reko')

#             db.session.commit()
#             logger.info(f"Updated ReklamaData ID {reklama.id}")
#         else:
#             # Create a new ReklamaData record
#             new_reklama = ReklamaData(
#                 id=reklama_data.get('id'),
#                 file1Preview=file_paths.get('file1Preview'),
#                 file2Preview=file_paths.get('file2Preview'),
#                 file3Preview=file_paths.get('file3Preview'),
#                 file4Preview=file_paths.get('file4Preview'),
#                 file5Preview=file_paths.get('file5Preview'),
#                 duration1=reklama_data.get('duration1'),
#                 duration2=reklama_data.get('duration2'),
#                 duration3=reklama_data.get('duration3'),
#                 duration4=reklama_data.get('duration4'),
#                 duration5=reklama_data.get('duration5'),
#                 date_start1=reklama_data.get('date_start1'),
#                 date_start2=reklama_data.get('date_start2'),
#                 date_start3=reklama_data.get('date_start3'),
#                 date_start4=reklama_data.get('date_start4'),
#                 date_start5=reklama_data.get('date_start5'),
#                 date_end1=reklama_data.get('date_end1'),
#                 date_end2=reklama_data.get('date_end2'),
#                 date_end3=reklama_data.get('date_end3'),
#                 date_end4=reklama_data.get('date_end4'),
#                 date_end5=reklama_data.get('date_end5'),
#                 check1=reklama_data.get('check1'),
#                 check2=reklama_data.get('check2'),
#                 check3=reklama_data.get('check3'),
#                 check4=reklama_data.get('check4'),
#                 check5=reklama_data.get('check5'),
#                 rek=reklama_data.get('rek'),
#                 reko=reklama_data.get('reko')
#             )
#             db.session.add(new_reklama)
#             db.session.commit()
#             logger.info(f"Created new ReklamaData ID {new_reklama.id}")

#         cache_key = 'view//api/reklama_data'
#         redis_client.delete(cache_key)

#         return jsonify({'success': True}), 200

#     except Exception as e:
#         logger.error(f"Error processing request: {e}")
#         db.session.rollback()
#         return jsonify({'error': str(e)}), 500


# @app.route('/api/ads_directory', methods=['GET'])
# def get_ads_directory():
#     try:
#         if not os.path.exists(ADS_DIRECTORY):
#             return jsonify({"success": False, "error": "Ads directory does not exist."}), 404

#         files = os.listdir(ADS_DIRECTORY)
#         ads_data = [{"filePath": f"/ads/{file}"} for file in files if os.path.isfile(os.path.join(ADS_DIRECTORY, file))]

#         return jsonify(ads_data)
#     except Exception as e:
#         return jsonify({"success": False, "error": str(e)}), 500


# @app.route('/api/upload', methods=['POST'])
# def upload_file():
#     if 'file' not in request.files:
#         logger.error("No file part in the request")
#         return jsonify({'success': False, 'error': 'No file part in the request'}), 400

#     file = request.files['file']
#     filename = request.form.get('filename', '')

#     if file.filename == '':
#         logger.error("No selected file")
#         return jsonify({'success': False, 'error': 'No selected file'}), 400

#     if file and allowed_file(file.filename):
#         filename_secure = secure_filename(file.filename)
#         file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_secure)
#         logger.info(f"Attempting to save file to: {file_path}")
#         try:
#             file.save(file_path)
#             file_url = f"/ads/{filename_secure}"
#             logger.info(f"File successfully saved at: {file_path}")
#             return jsonify({'success': True, 'filePath': file_url}), 200
#         except Exception as e:
#             logger.error(f"Error saving file: {e}")
#             return jsonify({'success': False, 'error': 'Error saving file'}), 500
#     else:
#         logger.error(f"File type not allowed: {file.filename}")
#         return jsonify({'success': False, 'error': 'File type not allowed'}), 400


# @app.route('/ads/<filename>', methods=['GET'])
# def serve_uploaded_file(filename):
#     try:
#         return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
#     except FileNotFoundError:
#         logger.error(f"File not found: {filename}")
#         return jsonify({'success': False, 'error': 'File not found'}), 404
    

# def parse_tariff_limit(limit_str):
#     if not limit_str:
#         return timedelta(0)

#     parts = limit_str.strip().split()
#     if len(parts) != 2:
#         return timedelta(0)

#     number, unit = parts
#     number = int(number)

#     if unit in ('minutes', 'minute'):
#         return timedelta(minutes=number)
#     elif unit in ('days', 'day'):
#         return timedelta(days=number)
#     elif unit in ('weeks', 'week'):
#         return timedelta(weeks=number)
#     elif unit in ('months', 'month'):
#         return timedelta(days=30 * number)
#     return timedelta(0)


# @app.route('/api/users', methods=['GET'])
# def get_users():
#     try:
#         page = int(request.args.get('page', 1))
#         limit = int(request.args.get('limit', 20))
#         offset = (page - 1) * limit

#         users = User.query.offset(offset).limit(limit).all()
#         total_users = User.query.count()
#         result = []

#         def parse_tariff_limit(limit_str):
#             if not limit_str:
#                 return timedelta(0)
#             parts = limit_str.strip().split()
#             if len(parts) != 2:
#                 return timedelta(0)
#             number, unit = parts
#             number = int(number)
#             if unit in ['minutes', 'minute']:
#                 return timedelta(minutes=number)
#             elif unit in ['days', 'day']:
#                 return timedelta(days=number)
#             elif unit in ['weeks', 'week']:
#                 return timedelta(weeks=number)
#             elif unit in ['months', 'month']:
#                 return timedelta(days=30 * number)
#             return timedelta(0)

#         for u in users:
#             last_auth = None
#             last_act = None
#             last_tf = None
#             last_tariff_limit = None

#             if u.authorizations:
#                 sorted_auths = sorted(u.authorizations, key=lambda a: a.authorization_date, reverse=True)
#                 for a in sorted_auths:
#                     act = a.authorization_activeness
#                     if act not in ['NOINTERNET', 'NOINTERNETPAY']:
#                         last_auth = a.authorization_date
#                         last_act = act
#                         last_tf = a.selected_tariff
#                         last_tariff_limit = a.tariff_limit
#                         break
#                 if not last_auth:
#                     a = sorted_auths[0]
#                     last_auth = a.authorization_date
#                     last_act = a.authorization_activeness
#                     last_tf = a.selected_tariff
#                     last_tariff_limit = a.tariff_limit

#             last_limit_dt = None
#             limit_duration = None

#             if last_tf and last_tf not in ['Teacher', 'Student', 'Guest']:
#                 tariff_id = last_tf.replace('tariff', '')
#                 tariff = tariff_plan.query.get(int(tariff_id)) if tariff_id.isdigit() else None
#                 if tariff and last_auth:
#                     limit_duration = parse_tariff_limit(tariff.duration_days or '')
#                     if isinstance(last_auth, str):
#                         try:
#                             last_auth = datetime.strptime(last_auth, "%d-%m-%Y %H:%M:%S")
#                         except ValueError:
#                             last_auth = None
#                     if isinstance(last_auth, datetime):
#                         last_limit_dt = last_auth + limit_duration

#             elif last_auth and last_tf in ['Teacher', 'Student', 'Guest']:
#                 try:
#                     minutes = int(last_tariff_limit) if last_tariff_limit else 0
#                     limit_duration = timedelta(minutes=minutes)
#                     last_limit_dt = last_auth + limit_duration
#                 except Exception:
#                     last_limit_dt = None

#             result.append({
#                 'id': u.id,
#                 'MAC': u.MAC,
#                 'fio': u.fio,
#                 'phone_number': u.phone_number,
#                 'last_authorization': last_auth.strftime("%d-%m-%Y %H:%M:%S") if isinstance(last_auth, datetime) else None,
#                 'last_authorization_limit': last_limit_dt.strftime("%d-%m-%Y %H:%M:%S") if isinstance(last_limit_dt, datetime) else None,
#                 'authorization_activeness': last_act,
#                 'role': u.role,
#                 'last_tariff_limit': last_tariff_limit
#             })

#         payload = {'users': result, 'total': total_users}
#         return jsonify(payload), 200

#     except Exception as e:
#         logger.error(f"Error in get_users: {e}")
#         return jsonify({'success': False, 'message': 'Internal server error'}), 500
    

# def cleanup_radius(mac):
#     try:
#         logger.info(f"[RADIUS] Connecting to MySQL for MAC={mac}")
#         conn = MySQLdb.connect(
#             host=DB_HOST, user=DB_USER, passwd=DB_PASS,
#             db=DB_NAME, charset='utf8', cursorclass=DictCursor
#         )
#         cur = conn.cursor()
#         if radius_auth(mac, mac):
#             logger.info(f"[RADIUS] Authenticated, deleting radgroupreply for group tariff_{mac}")
#             cur.execute("DELETE FROM radgroupreply WHERE groupname = %s", (f"tariff_{mac}",))
#             logger.info(f"[RADIUS] Deleting radusergroup for username {mac}")
#             cur.execute("DELETE FROM radusergroup WHERE username = %s", (mac,))
#         conn.commit()
#         logger.info(f"[RADIUS] Commit complete")
#     except Exception as e:
#         logger.error(f"[RADIUS] Error cleaning up: {e}")
#     finally:
#         cur.close()
#         conn.close()


# def cleanup_mikrotik(mac):
#     try:
#         logger.info(f"[MikroTik] Connecting to RouterOS API")
#         api = RouterOsApiPool(
#             mikrotik_ip, username=mikrotik_username,
#             password=mikrotik_password, plaintext_login=True
#         )
#         hotspot_active = api.get_api().get_resource('/ip/hotspot/active')

#         active = hotspot_active.get()
#         found = False
#         for entry in active:
#             if entry.get('user', '').strip().upper() == mac.strip().upper():
#                 logger.info(f"[MikroTik] Removing active session id={entry['id']} for MAC={mac}")
#                 try:
#                     hotspot_active.remove(id=entry['id'])
#                 except Exception as e:
#                     logger.warning(f"[MikroTik] Tried to remove non-existent active session: {e}")
#                 found = True
#                 break
#         if not found:
#             hotspot_host = api.get_api().get_resource('/ip/hotspot/host')
#             hosts = hotspot_host.get()
#             for host in hosts:
#                 if host.get('mac-address', '').strip().upper() == mac.strip().upper():
#                     logger.info(f"[MikroTik] Removing host id={host['id']} for MAC={mac}")
#                     try:
#                         hotspot_host.remove(id=host['id'])
#                     except Exception as e:
#                         logger.warning(f"[MikroTik] Tried to remove non-existent host: {e}")
#                     break

#         api.disconnect()
#         logger.info(f"[MikroTik] Disconnected from RouterOS")
#     except Exception as e:
#         logger.error(f"[MikroTik] Error cleaning up: {e}")
    

# @app.route('/api/users/search', methods=['GET'])
# def search_users():
#     try:
#         # 1. Qidiruv so‘rovi qabul qilindi va log qilindi
#         search_term = request.args.get('search', default='', type=str).strip().lower()
#         logger.info(f"[search_users] Kiritilgan search parameter: '{search_term}'")
#         pattern = f"%{search_term}%"

#         # 2. Agar search bo‘sh bo‘lsa, barcha foydalanuvchilar o‘qiladi
#         if not search_term:
#             users = User.query.all()
#             logger.info(f"[search_users] Bo‘sh qidiruv – barcha foydalanuvchilar o‘qildi (soni={len(users)})")
#         else:
#             users = User.query.filter(
#                 or_(
#                     User.MAC.ilike(pattern),
#                     User.fio.ilike(pattern),
#                     User.phone_number.ilike(pattern),
#                     User.role.ilike(pattern)
#                 )
#             ).all()
#             logger.info(f"[search_users] Filtrlash natijasi – topilgan foydalanuvchilar soni={len(users)}")

#         def parse_tariff_limit(limit_str):
#             if not limit_str:
#                 return timedelta(0)
#             parts = limit_str.strip().split()
#             if len(parts) != 2:
#                 return timedelta(0)
#             num, unit = parts
#             num = int(num)
#             if unit.startswith('minute'):
#                 return timedelta(minutes=num)
#             if unit.startswith('day'):
#                 return timedelta(days=num)
#             if unit.startswith('week'):
#                 return timedelta(weeks=num)
#             if unit.startswith('month'):
#                 return timedelta(days=30 * num)
#             return timedelta(0)

#         def get_activation_source(val):
#             try:
#                 if val is not None and str(val).strip().isdigit():
#                     return "Admin"
#             except Exception:
#                 pass
#             return "Portal"

#         result = []
#         now = datetime.now()

#         # 3. Har bir topilgan user uchun kerakli maydonlar tayyorlanadi va log qilinadi
#         for u in users:
#             if u.authorizations:
#                 latest_auth = max(u.authorizations, key=lambda a: a.authorization_date)
#                 last_auth = latest_auth.authorization_date
#                 last_act = latest_auth.authorization_activeness
#                 last_tf = latest_auth.selected_tariff
#                 last_tariff_limit = latest_auth.tariff_limit

#                 logger.debug(
#                     f"[search_users] User ID={u.id} – Oxirgi authorization: "
#                     f"date={last_auth}, activeness={last_act}, "
#                     f"tariff={last_tf}, limit={last_tariff_limit}"
#                 )
#             else:
#                 last_auth = None
#                 last_act = None
#                 last_tf = None
#                 last_tariff_limit = None
#                 logger.debug(f"[search_users] User ID={u.id} da authorization yozuvi yo‘q")

#             last_limit_dt = None
#             if last_tf and last_tf not in ['Teacher', 'Student', 'Guest']:
#                 tariff_id = last_tf.replace('tariff', '')
#                 tariff = tariff_plan.query.get(int(tariff_id)) if tariff_id.isdigit() else None
#                 if tariff and last_auth:
#                     limit_duration = parse_tariff_limit(tariff.duration_days or '')
#                     if isinstance(last_auth, str):
#                         try:
#                             last_auth = datetime.strptime(last_auth, "%d-%m-%Y %H:%M:%S")
#                         except ValueError:
#                             last_auth = None
#                     if isinstance(last_auth, datetime):
#                         last_limit_dt = last_auth + limit_duration
#             elif last_auth and last_tf in ['Teacher', 'Student', 'Guest']:
#                 try:
#                     minutes = int(last_tariff_limit) if last_tariff_limit else 0
#                     limit_duration = timedelta(minutes=minutes)
#                     last_limit_dt = last_auth + limit_duration
#                 except Exception:
#                     last_limit_dt = None

#             result.append({
#                 'id': u.id,
#                 'MAC': u.MAC,
#                 'fio': u.fio,
#                 'phone_number': u.phone_number,
#                 'SSID': None,
#                 'last_authorization': (
#                     last_auth.strftime("%d-%m-%Y %H:%M:%S") if isinstance(last_auth, datetime) else None
#                 ),
#                 'last_authorization_limit': (
#                     last_limit_dt.strftime("%d-%m-%Y %H:%M:%S") if isinstance(last_limit_dt, datetime) else None
#                 ),
#                 'authorization_activeness': last_act,
#                 'role': u.role,
#                 'last_tariff_limit': last_tariff_limit,
#                 'activated_by': get_activation_source(last_tariff_limit),
#             })

#         # 4. Natija JSON shaklida va log qilinib qaytariladi
#         logger.info(f"[search_users] So‘rov natijasi tayyor, jami {len(result)} ta user qaytarilmoqda")
#         return jsonify({
#             "users": result,
#             "total": len(result)
#         }), 200

#     except Exception as e:
#         logger.error(f"[search_users] Xatolik yuz berdi: {e}")
#         return jsonify({"error": "Search failed"}), 500


# @app.route('/api/users/<int:user_id>', methods=['GET'])
# def get_user_details(user_id):
#     try:
#         logger.info(f"[get_user_details] Kiritilgan user_id: {user_id}")

#         DT_FMT = "%H:%M:%S %d-%m-%Y"
#         user = User.query.get(user_id)
#         if user is None:
#             logger.warning(f"[get_user_details] User topilmadi – ID={user_id}")
#             return jsonify({'error': 'User not found'}), 404

#         logger.debug(f"[get_user_details] User topildi – ID={user.id}, MAC={user.MAC}, fio={user.fio}")

#         authorizations = sorted(user.authorizations, key=lambda x: x.authorization_date)
#         earliest_auth = authorizations[0] if authorizations else None
#         latest_auth   = authorizations[-1] if authorizations else None

#         if earliest_auth:
#             earliest_date = earliest_auth.authorization_date
#             earliest_tariff = earliest_auth.selected_tariff
#             earliest_limit = earliest_auth.tariff_limit
#             logger.debug(
#                 f"[get_user_details] Eng birinchi authorization: date={earliest_date}, "
#                 f"tariff={earliest_tariff}, limit={earliest_limit}"
#             )
#         else:
#             earliest_date = None
#             earliest_tariff = None
#             earliest_limit = None
#             logger.debug("[get_user_details] User da birorta ham authorization yozuvi yo‘q")

#         if latest_auth:
#             latest_date = latest_auth.authorization_date
#             latest_act = latest_auth.authorization_activeness
#             latest_tariff = latest_auth.selected_tariff
#             latest_limit = latest_auth.tariff_limit
#             logger.debug(
#                 f"[get_user_details] Eng so‘ngi authorization: date={latest_date}, "
#                 f"activeness={latest_act}, tariff={latest_tariff}, limit={latest_limit}"
#             )
#         else:
#             latest_date = None
#             latest_act = None
#             latest_tariff = None
#             latest_limit = None

#         # 1. Qolgan vaqtni hisoblash
#         remaining_str = None
#         if latest_date and latest_limit:
#             try:
#                 if latest_tariff in ['Teacher', 'Student', 'Guest']:
#                     td = timedelta(minutes=int(user.last_tariff_limit))
#                 else:
#                     parts = str(latest_limit).strip().split()
#                     if len(parts) == 2:
#                         num, unit = parts
#                         num = int(num)
#                         if unit.startswith('minute'):
#                             td = timedelta(minutes=num)
#                         elif unit.startswith('day'):
#                             td = timedelta(days=num)
#                         elif unit.startswith('week'):
#                             td = timedelta(weeks=num)
#                         elif unit.startswith('month'):
#                             td = timedelta(days=30 * num)
#                         else:
#                             td = timedelta(0)
#                     else:
#                         td = timedelta(0)
#                 remaining_time = max(timedelta(0), (latest_date + td) - datetime.now())
#                 total_seconds = int(remaining_time.total_seconds())
#                 hours, remainder = divmod(total_seconds, 3600)
#                 minutes, seconds = divmod(remainder, 60)
#                 remaining_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
#                 logger.debug(f"[get_user_details] Foydalanuvchining qolgan vaqti: {remaining_str}")
#             except Exception as ex:
#                 remaining_str = None
#                 logger.error(f"[get_user_details] Qolgan vaqtni hisoblashda xato: {ex}")
#         else:
#             logger.debug("[get_user_details] Qolgan vaqtni hisoblashi uchun ma’lumot yetarli emas")

#         # 2. So‘ngi IP-manzil va umumiy sessiyalar soni olish
#         last_ip = None
#         session_cnt = 0
#         try:
#             conn = MySQLdb.connect(
#                 host=DB_HOST, user=DB_USER, passwd=DB_PASS,
#                 db=DB_NAME, charset='utf8', cursorclass=DictCursor
#             )
#             cursor = conn.cursor()
#             cursor.execute("""
#                 SELECT framedipaddress FROM radacct
#                 WHERE username = %s
#                 ORDER BY acctstarttime DESC
#                 LIMIT 1
#             """, (user.MAC,))
#             row = cursor.fetchone()
#             last_ip = row['framedipaddress'] if row else None

#             cursor.execute("""
#                 SELECT COUNT(*) AS cnt FROM radacct
#                 WHERE username = %s
#             """, (user.MAC,))
#             session_cnt = cursor.fetchone()['cnt'] if cursor else 0
#             cursor.close()
#             conn.close()
#             logger.debug(f"[get_user_details] So‘ngi IP: {last_ip}, sessiyalar soni: {session_cnt}")
#         except Exception as ex:
#             logger.error(f"[get_user_details] RADIUS ma’lumotlarini olishda xato: {ex}")

#         # 3. Tariff nomini o‘zgartirish
#         if latest_tariff == 'tariff1':
#             latest_tariff_str = '1-Tarif'
#         elif latest_tariff == 'tariff2':
#             latest_tariff_str = '2-Tarif'
#         elif latest_tariff == 'tariff3':
#             latest_tariff_str = '3-Tarif'
#         elif latest_tariff == 'tariff4':
#             latest_tariff_str = '4-Tarif'
#         elif latest_tariff in ['Student', 'Teacher', 'Guest']:
#             latest_tariff_str = f"{user.last_tariff_limit}-minut"
#         else:
#             latest_tariff_str = latest_tariff

#         # 4. Natija tayyorlanadi
#         result = {
#             'id': user.id,
#             'MAC': user.MAC,
#             'fio': user.fio,
#             'phone_number': user.phone_number,
#             'confirmation_code': user.confirmation_code,
#             'role': user.role,
#             'overall_authorizations': user.overall_authorizations,
#             'overall_payed_sum': user.overall_payed_sum,
#             'block': user.block,
#             'first_authorization': earliest_date.strftime(DT_FMT) if earliest_date else None,
#             'last_authorization': latest_date.strftime(DT_FMT) if latest_date else None,
#             'authorization_activeness': latest_act,
#             'selectedTariff': latest_tariff_str,
#             'tariff_limit': latest_limit,
#             'remaining_time': (
#                 remaining_str if latest_act == 'AKTIV' and remaining_str is not None else '00:00:00'
#             ),
#             'last_ip_address': last_ip,
#             'total_sessions': session_cnt
#         }

#         logger.info(f"[get_user_details] Foydalanuvchi ma’lumotlari tayyor, ID={user.id}")
#         logger.debug(f"[get_user_details] Qaytarilayotgan JSON: {result}")

#         return jsonify(result), 200

#     except Exception as e:
#         logger.error(f"[get_user_details] Xatolik yuz berdi: {e}")
#         return jsonify({'error': 'Internal server error'}), 500
    

# def format_timedelta(td: timedelta) -> str:
#     total = int(td.total_seconds())
#     days, rem = divmod(total, 86400)
#     hours, rem = divmod(rem, 3600)
#     minutes, _ = divmod(rem, 60)

#     parts = []
#     if days:
#         parts.append(f"{days} kun")
#     if hours:
#         parts.append(f"{hours} soat")
#     if minutes or not parts:
#         parts.append(f"{minutes} minut")
#     return " ".join(parts)
    

# def mikrotik_session_info(mac: str) -> dict:
#     mac = mac.upper() 
#     pool = None

#     try:
#         pool = RouterOsApiPool(
#             host            = MIKROTIK_HOST,
#             username        = MIKROTIK_USER,
#             password        = MIKROTIK_PASSWORD,
#             port            = 1813,
#             use_ssl         = False,
#             plaintext_login = True
#         )

#         api  = pool.get_api()

#         active_rsc = api.get_resource("/ip/hotspot/active")
#         active     = active_rsc.get( mac_address=mac )

#         if active:
#             last_ip = active[0]["address"]
#         else:
#             last_ip = None

#         host_rsc = api.get_resource("/ip/hotspot/host")
#         all_hosts = host_rsc.get( mac_address=mac )

#         total_sessions = len(all_hosts)

#         return {
#             "last_ip": last_ip,
#             "total_sessions": total_sessions
#         }

#     except RouterOsApiConnectionError as err:
#         print(f"[mikrotik] Connection error: {err}")
#         return {
#             "last_ip": None,
#             "total_sessions": 0,
#             "error": "mikrotik_connection_error"
#         }
#     finally:
#         if pool:
#             pool.disconnect()
    

# @app.route('/api/updateMacAddress', methods=['POST'])
# def update_mac_address():
#     data = request.json
#     phone_number = data.get('phone_number')
#     old_mac = data.get('oldMAC')
#     new_mac = data.get('newMAC')
#     logger.info(f"[updateMacAddress] Received request: phone_number={phone_number}, oldMAC={old_mac}, newMAC={new_mac}")

#     if not phone_number or not new_mac or not old_mac:
#         logger.error("[updateMacAddress] Missing data in request")
#         return jsonify({'success': False, 'error': 'Missing data'}), 400

#     user = User.query.filter_by(MAC=old_mac).first()
#     if not user:
#         logger.error(f"[updateMacAddress] User not found for oldMAC={old_mac}")
#         return jsonify({'success': False, 'error': 'User not found'}), 404

#     user.MAC = new_mac
#     db.session.commit()
#     logger.info(f"[updateMacAddress] Updated MAC from {old_mac} to {new_mac} for phone_number={phone_number}")

#     return jsonify({'success': True}), 200


# @app.route('/api/updateStatus', methods=['POST'])
# def update_status():
#     data = request.get_json()
#     new_status = data.get('status')
#     phone_number = data.get('phone_number')
#     logger.info(f"[updateStatus] Received request: phone_number={phone_number}, status={new_status}")

#     if not phone_number or new_status is None:
#         logger.error("[updateStatus] Invalid data in request")
#         return jsonify({'error': 'Invalid data'}), 400

#     status_flag = 1 if new_status == 'Bloklangan' else 0
#     logger.debug(f"[updateStatus] Mapped status '{new_status}' to flag {status_flag}")

#     user = User.query.filter_by(phone_number=phone_number).first()
#     if user:
#         user.block = status_flag
#         db.session.commit()
#         logger.info(f"[updateStatus] Updated block={status_flag} for phone_number={phone_number}")
#         return jsonify({'message': 'Status updated successfully'}), 200
#     else:
#         logger.error(f"[updateStatus] User not found for phone_number={phone_number}")
#         return jsonify({'error': 'User not found'}), 404
    

# @app.route('/api/unauthorization', methods=['POST'])
# def unauthorize_user():
#     data = request.get_json()
#     user_id      = data.get('id')
#     phone_number = data.get('phone_number')
#     mac          = data.get('MAC') or data.get('macAddress')
#     logger.info(f"[unauthorization] Received request: id={user_id}, phone_number={phone_number}, MAC={mac}")

#     if user_id:
#         user = User.query.get(user_id)
#         logger.debug(f"[unauthorization] Queried User by id={user_id}: {user}")
#     elif mac:
#         user = User.query.filter_by(MAC=mac).first()
#         logger.debug(f"[unauthorization] Queried User by MAC={mac}: {user}")
#     else:
#         logger.error("[unauthorization] Missing user identifier")
#         return jsonify({'success': False, 'error': 'Missing user identifier'}), 400

#     if not user:
#         logger.error("[unauthorization] User not found")
#         return jsonify({'success': False, 'error': 'User not found'}), 404

#     password = user.MAC
#     logger.info(f"[unauthorization] Deauthorizing user with MAC={password}")
#     try:
#         conn = MySQLdb.connect(
#             host=DB_HOST, user=DB_USER, passwd=DB_PASS, db=DB_NAME,
#             charset='utf8', cursorclass=DictCursor
#         )
#         cur = conn.cursor()
#         if radius_auth(password, password):
#             cur.execute(
#                 "DELETE FROM radgroupreply WHERE groupname = %s",
#                 (f"tariff_{password}",)
#             )
#             cur.execute(
#                 "DELETE FROM radusergroup WHERE username = %s",
#                 (password,)
#             )
#             logger.info(f"[unauthorization] Removed RADIUS entries for username={password}")
#         conn.commit()
#     except Exception as e:
#         logger.error(f"[unauthorization] Error cleaning RADIUS: {e}")
#     finally:
#         cur.close()
#         conn.close()

#     api = RouterOsApiPool(
#         mikrotik_ip, username=mikrotik_username,
#         password=mikrotik_password, plaintext_login=True
#     )
#     hotspot_active = api.get_api().get_resource('/ip/hotspot/active')

#     def _remove(mac_addr):
#         active = hotspot_active.get()
#         for u in active:
#             if u.get('user', '').strip().upper() == mac_addr.strip().upper():
#                 hotspot_active.remove(id=u['id'])
#                 logger.info(f"[unauthorization] Removed active hotspot session id={u['id']} for MAC={mac_addr}")
#                 return True
#         return False

#     removed = _remove(password)
#     if not removed:
#         hosts = api.get_api().get_resource('/ip/hotspot/host').get()
#         for h in hosts:
#             if h.get('mac-address', '').strip().upper() == password.strip().upper():
#                 api.get_api().get_resource('/ip/hotspot/host').remove(id=h['id'])
#                 logger.info(f"[unauthorization] Removed hotspot host id={h['id']} for MAC={password}")
#                 break

#     api.disconnect()
#     logger.info("[unauthorization] Disconnected from RouterOS API")

#     deactivate_latest_authorization_for_mac(user.MAC)
#     remove_user_tariff(mac)
#     logger.info(f"[unauthorization] Deactivated latest authorization and removed tariff for MAC={mac}")

#     return jsonify({'success': True, 'message': 'User unauthorized successfully'}), 200


# @app.route('/api/deleteUser', methods=['DELETE'])
# def delete_user():
#     data        = request.get_json()
#     mac_address = data.get('MAC') or data.get('macAddress')
#     logger.info(f"[deleteUser] Received request: MAC={mac_address}")

#     if not mac_address:
#         logger.error("[deleteUser] Missing user identifier")
#         return jsonify({'success': False, 'error': 'Missing user identifier'}), 400

#     user    = User.query.filter_by(MAC=mac_address).first()
#     profile = Profiles.query.filter_by(MAC=mac_address).first()
#     logger.debug(f"[deleteUser] Queried User: {user}, Profile: {profile}")

#     if not user or not profile:
#         logger.error("[deleteUser] User or profile not found")
#         return jsonify({'success': False, 'error': 'User not found'}), 404

#     logger.info(f"[deleteUser] Deleting authorizations for user MAC={mac_address}")
#     UserAuthorization.query.filter_by(user_mac=user.MAC).delete()
#     db.session.delete(user)
#     db.session.delete(profile)
#     db.session.commit()
#     logger.info(f"[deleteUser] Deleted User and Profile from database: MAC={mac_address}")

#     password = user.MAC
#     if password:
#         try:
#             conn = MySQLdb.connect(
#                 host=DB_HOST, user=DB_USER, passwd=DB_PASS,
#                 db=DB_NAME, charset='utf8', cursorclass=DictCursor
#             )
#             cur = conn.cursor()
#             if radius_auth(password, password):
#                 cur.execute(
#                     "DELETE FROM radgroupreply WHERE groupname = %s",
#                     (f"tariff_{password}",)
#                 )
#                 cur.execute(
#                     "DELETE FROM radusergroup WHERE username = %s",
#                     (password,)
#                 )
#                 logger.info(f"[deleteUser] Removed RADIUS entries for username={password}")
#             conn.commit()
#         except Exception as e:
#             logger.error(f"[deleteUser] Error cleaning RADIUS: {e}")
#         finally:
#             cur.close()
#             conn.close()

#         api = RouterOsApiPool(
#             mikrotik_ip, username=mikrotik_username,
#             password=mikrotik_password, plaintext_login=True
#         )
#         hotspot_active = api.get_api().get_resource('/ip/hotspot/active')

#         def _remove(mac_addr):
#             active = hotspot_active.get()
#             for u in active:
#                 if u.get('user', '').strip().upper() == mac_addr.strip().upper():
#                     hotspot_active.remove(id=u['id'])
#                     logger.info(f"[deleteUser] Removed active hotspot session id={u['id']} for MAC={mac_addr}")
#                     return True
#             return False

#         removed = _remove(password)
#         if not removed:
#             hosts = api.get_api().get_resource('/ip/hotspot/host').get()
#             for h in hosts:
#                 if h.get('mac-address', '').strip().upper() == password.strip().upper():
#                     api.get_api().get_resource('/ip/hotspot/host').remove(id=h['id'])
#                     logger.info(f"[deleteUser] Removed hotspot host id={h['id']} for MAC={password}")
#                     break

#         api.disconnect()
#         logger.info("[deleteUser] Disconnected from RouterOS API")

#     remove_user_tariff(user.MAC)
#     logger.info(f"[deleteUser] Removed user tariff for MAC={user.MAC}")

#     return jsonify({'success': True, 'message': 'User deleted successfully'}), 200
    

# @app.route('/api/users/<int:user_id>/authorizations', methods=['GET'])
# def get_user_authorizations(user_id):
#     try:
#         logger.info(f"[get_user_authorizations] Request received for user_id={user_id}")
#         user = User.query.get(user_id)
#         if not user:
#             logger.error(f"[get_user_authorizations] User not found: user_id={user_id}")
#             return jsonify({"error": "User not found"}), 404

#         page     = request.args.get('page',     default=1,   type=int)
#         per_page = request.args.get('per_page', default=20,  type=int)
#         search   = request.args.get('search',   default="",  type=str).strip().lower()
#         logger.debug(f"[get_user_authorizations] Parameters: page={page}, per_page={per_page}, search='{search}'")

#         def fetch_price(tarif_name):
#             if tarif_name and tarif_name.startswith("tariff") and tarif_name[6:].isdigit():
#                 plan_id = int(tarif_name[6:])
#                 row = tariff_plan.query.filter_by(id=plan_id).first()
#                 price = row.price if row else "Unknown"
#                 logger.debug(f"[get_user_authorizations] Fetched price for {tarif_name}: {price}")
#                 return price
#             return "Admin"

#         # Sort in descending order by authorization_date
#         authorizations = sorted(user.authorizations, key=lambda x: x.authorization_date, reverse=True)
#         logger.info(f"[get_user_authorizations] Found {len(authorizations)} total authorizations for user_id={user_id}")

#         all_items = []
#         for auth in authorizations:
#             status = auth.authorization_activeness
#             if status not in ['AKTIV', 'NOAKTIV']:
#                 continue

#             date_str = auth.authorization_date.strftime("%d-%m-%Y %H:%M:%S") \
#                        if isinstance(auth.authorization_date, datetime) else str(auth.authorization_date)
#             tarif    = auth.selected_tariff
#             limit    = auth.tariff_limit
#             price    = fetch_price(tarif)
#             hostname = auth.ip_address if hasattr(auth, 'ip_address') else ""

#             if tarif == 'tariff1':
#                 tarif_display = '1-Tarif'
#             elif tarif == 'tariff2':
#                 tarif_display = '2-Tarif'
#             elif tarif == 'tariff3':
#                 tarif_display = '3-Tarif'
#             elif tarif == 'tariff4':
#                 tarif_display = '4-Tarif'
#             elif tarif in ['Student', 'Teacher', 'Guest']:
#                 tarif_display = (limit or '') + "-minut"
#                 price = "Admin"
#             else:
#                 tarif_display = tarif or ""

#             item = {
#                 "date":     date_str,
#                 "hostname": hostname or "",
#                 "tarif":    tarif_display,
#                 "price":    price,
#                 "status":   status
#             }
#             all_items.append(item)

#         logger.debug(f"[get_user_authorizations] After filtering/formatting: {len(all_items)} items")

#         # Apply search filter if provided
#         if search:
#             def matches(item):
#                 return (
#                     search in item["date"].lower() or
#                     search in item["hostname"].lower() or
#                     search in item["tarif"].lower() or
#                     search in str(item["price"]).lower() or
#                     search in str(item["status"]).lower()
#                 )
#             filtered = list(filter(matches, all_items))
#             logger.info(f"[get_user_authorizations] Search term '{search}' filtered items: {len(filtered)}")
#             all_items = filtered

#         total       = len(all_items)
#         total_pages = max(1, math.ceil(total / per_page))
#         page = max(1, min(page, total_pages))
#         start = (page - 1) * per_page
#         end   = start + per_page
#         items = all_items[start:end]
#         logger.info(f"[get_user_authorizations] Paginated to page={page}/{total_pages}, items_on_page={len(items)}")

#         result = {
#             "page":        page,
#             "per_page":    per_page,
#             "total":       total,
#             "total_pages": total_pages,
#             "items":       items
#         }
#         logger.debug(f"[get_user_authorizations] Response payload prepared for user_id={user_id}")
#         return jsonify(result), 200

#     except Exception as e:
#         logger.error(f"[get_user_authorizations] Error: {e}")
#         return jsonify({"error": "An error occurred, please check the server logs."}), 500


# from flask import Flask, jsonify, request
# from sqlalchemy import desc
# from models import Transaction, User

# @app.route('/api/transactions', methods=['GET'])
# def get_transactions():
#     try:
#         page   = int(request.args.get('page', 1))
#         limit  = int(request.args.get('limit', 20))
#         offset = (page - 1) * limit

#         total_transactions = Transaction.query.count()

#         transactions = (
#             Transaction.query
#             .order_by(desc(Transaction.create_time))
#             .offset(offset)
#             .limit(limit)
#             .all()
#         )

#         transaction_list = []
#         for trans in transactions:
#             user = User.query.filter_by(phone_number=trans.phone_number).first()
#             fio = user.fio if user else "Unknown"

#             if trans.status == 'success':
#                 date_value = trans.perform_time if trans.perform_time else trans.create_time
#             elif trans.status == 'pending':
#                 date_value = trans.create_time
#             else:
#                 date_value = trans.cancel_time

#             date_str = date_value.strftime("%d-%m-%Y %H:%M:%S") if date_value else "N/A"

#             item = {
#                 "id":       trans.id,
#                 "fio":      fio,
#                 "phone":    trans.phone_number,
#                 "amount":   trans.amount,
#                 "trans_id": trans.transaction_id,
#                 "status":   trans.status,
#                 "date":     date_str
#             }
#             transaction_list.append(item)

#         response_payload = {
#             "transactions": transaction_list,
#             "total":        total_transactions
#         }
#         return jsonify(response_payload), 200

#     except Exception as e:
#         logger.error(f"[get_transactions] Error fetching transactions: {e}")
#         return jsonify({"error": "Failed to fetch transactions"}), 500
    

# @app.route('/api/transactions/search', methods=['GET'])
# def search_transactions():
#     try:
#         term = request.args.get('search', default='', type=str).strip().lower()
#         logger.info(f"[search_transactions] Search request received: term='{term}'")
#         if not term:
#             logger.debug("[search_transactions] Empty search term provided, returning empty list")
#             return jsonify({"transactions": [], "total": 0}), 200

#         pattern = f"%{term}%"
#         q = (
#             Transaction.query
#             .join(User, Transaction.phone_number == User.phone_number)
#             .filter(
#                 or_(
#                     Transaction.phone_number.ilike(pattern),
#                     Transaction.transaction_id.ilike(pattern),
#                     User.fio.ilike(pattern),
#                     Transaction.amount.ilike(pattern),
#                     Transaction.status.ilike(pattern)
#                 )
#             )
#             .order_by(desc(Transaction.create_time))
#         )

#         total = q.count()
#         logger.debug(f"[search_transactions] Found {total} matching records")

#         transactions = q.all()
#         result = []
#         for t in transactions:
#             usr = User.query.filter_by(phone_number=t.phone_number).first()
#             fio = usr.fio if usr else "Unknown"
#             item = {
#                 "id":       t.id,
#                 "fio":      fio,
#                 "phone":    t.phone_number,
#                 "amount":   t.amount,
#                 "trans_id": t.transaction_id,
#                 "status":   t.status,
#                 "date":     t.create_time.strftime("%d-%m-%Y %H:%M:%S") \
#                             if t.create_time else None
#             }
#             result.append(item)

#         logger.info(f"[search_transactions] Returning {len(result)} items for term='{term}'")
#         return jsonify({
#             "transactions": result,
#             "total":        total
#         }), 200

#     except Exception as e:
#         logger.error(f"[search_transactions] Error: {e}")
#         return jsonify({"error": "Search failed"}), 500
