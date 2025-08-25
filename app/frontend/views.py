from flask import Blueprint, render_template, redirect

frontend_bp = Blueprint(
    'frontend', __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)


@frontend_bp.route('/')
def index():
    return redirect('/admin_panel_login')


@frontend_bp.route('/admin_panel_login')
def admin_panel_login_view():
    return render_template('admin_panel_login.html')


@frontend_bp.route('/admin_panel_main')
def admin_panel_main_view():
    return render_template('admin_panel_main.html')


@frontend_bp.route('/admin_panel_settings')
def admin_panel_settings_view():
    return render_template('admin_panel_settings.html')


@frontend_bp.route('/admin_panel_ad')
def admin_panel_ad_view():
    return render_template('admin_panel_ad.html')


@frontend_bp.route('/admin_panel_transaction')
def admin_panel_transaction_view():
    return render_template('admin_panel_tolovlar.html')


@frontend_bp.route('/admin_panel_tarif')
def admin_panel_tarif_view():
    return render_template('admin_panel_tarif.html')


@frontend_bp.route('/admin_panel_users')
def admin_panel_users_view():
    return render_template('admin_panel_users.html')


@frontend_bp.route('/admin_panel_details')
def admin_panel_details_view():
    return render_template('details.html')


@frontend_bp.route('/admin_panel_user_info')
def admin_panel_user_info_view():
    return render_template('user_info.html')


@frontend_bp.route('/wifi')
def wifi_view():
    return render_template('wifi.html')


@frontend_bp.route('/link_login/<string:university_name>')
def university_dashboard_view(university_name):
    return render_template('link_login.html', university_name=university_name)


@frontend_bp.route('/link_login/<string:university_name>/users')
def university_users_view(university_name):
    return render_template('link_login_users.html', university_name=university_name)


@frontend_bp.route('/link_login/<string:university_name>/transactions')
def university_transactions_view(university_name):
    return render_template('link_login_transactions.html', university_name=university_name)


@frontend_bp.route('/teachers')
def teachers_view():
    return render_template('teachers.html')


@frontend_bp.route('/admin_panel_monitoring')
def admin_panel_monitoring_view():
    return render_template('admin_panel_monitoring.html')
