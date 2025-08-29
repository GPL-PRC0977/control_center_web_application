from flask import Flask, request, jsonify, render_template, url_for, session, redirect
from authlib.integrations.flask_client import OAuth
import os
from dotenv import load_dotenv
from functions import validate_user, save_application_data, get_master_data, delete_application, get_modules, get_dimension
import sys
import traceback

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_secret_key'


oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    },
    redirect_uri=os.getenv('GOOGLE_REDIRECT_URI'),
)


@app.route('/')
def home():
    try:
        if 'user' in session and session['user']:
            if validate_user(session['user']):
                user_details = get_user_details()
                return render_template(
                    'home.html',
                    picture=user_details['picture'],
                    user=user_details['user'],
                    full_name=user_details['full_name'],
                    role_type=user_details['role_type'],
                    status='True',
                    master_data=get_master_data())
            else:
                return render_template('noaccess.html', error="User validation failed.")
        else:
            return render_template('index.html')
    except Exception as e:
        print(f"Error in home route: {e}")
        return render_template('noaccess.html', error=str(e))


@app.route('/login')
def login():
    redirect_uri = url_for('callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/callback')
def callback():
    token = google.authorize_access_token()
    user_info = google.get(
        'https://openidconnect.googleapis.com/v1/userinfo').json()
    session['user'] = user_info
    print(user_info)
    return redirect('/')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/modify_app', methods=['POST'])
def modify_app():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        required_keys = ['app_id', 'app_name',
                         'app_url', 'status', 'app_owner']
        missing_keys = [key for key in required_keys if key not in data]

        if missing_keys:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_keys)}"}), 400

        if not isinstance(data.get('app_id'), str) or not data.get('app_id').strip():
            return jsonify({"error": "Invalid app ID"}), 400

        session['app_id_to_modify'] = data['app_id']
        session['app_name'] = data['app_name']
        session['app_url'] = data['app_url']
        session['app_status'] = data['status']
        session['owner'] = data['app_owner']
        session['perm_read'] = data['perm_read']
        session['perm_write'] = data['perm_write']
        session['perm_update'] = data['perm_update']
        session['perm_delete'] = data['perm_delete']

        print(f"App modification data stored in session for: {data['app_id']}")

        return jsonify({"redirect": url_for('modify_app_form')}), 200

    except Exception as e:
        print(f"Exception in modify_app: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/modify_app_form', methods=['GET'])
def modify_app_form():
    try:
        user_details = get_user_details()

        app_id = session.get('app_id_to_modify')
        app_name = session.get('app_name', 'Unnamed App')
        app_url = session.get('app_url', '')
        app_status = session.get('app_status', 'Unknown')
        app_owner = session.get('owner', 'Not Assigned')
        perm_read = session.get('perm_read')
        perm_write = session.get('perm_write')
        perm_update = session.get('perm_update')
        perm_delete = session.get('perm_delete')

        if not app_id:
            print(
                "Warning: No app ID found in session. Redirecting or showing error may be appropriate.")

        return render_template(
            'modify_app.html',
            user=user_details.get("user", {}),
            app_id=app_id,
            app_name=app_name,
            app_url=app_url,
            app_status=app_status,
            app_owner=app_owner,
            full_name=user_details.get("full_name", "Unknown User"),
            role_type=user_details.get("role_type", "guest"),
            picture=user_details.get("picture", "/static/default-avatar.png"),
            perm_read=perm_read,
            perm_write=perm_write,
            perm_update=perm_update,
            perm_delete=perm_delete,
            dimensions=get_dimension(app_id),
            modules=get_modules(app_id)
        )

    except Exception as e:
        print(f"Error rendering modify_app_form: {e}")
        return render_template('noaccess.html', error="Something went wrong loading the form.")


def get_user_details():
    try:
        admin_details = session.get('admin_details')
        user = session.get('user')

        if not isinstance(user, dict):
            print("Invalid or missing 'user' in session.")
            user = {}

        if not isinstance(admin_details, dict):
            print("Invalid or missing 'admin_details' in session.")
            admin_details = {}

        return {
            "user": user,
            "full_name": user.get('name', 'Unknown User'),
            "picture": user.get('picture', '/static/default-avatar.png'),
            "role_type": admin_details.get("role_type", 'guest')
        }

    except Exception as e:
        print(f"Exception in get_user_details: {e}")
        return {
            "user": {},
            "full_name": "Unknown User",
            "picture": "",
            "role_type": "guest"
        }


@app.route('/submit-app-data', methods=['POST'])
def submit_app_data():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        user_email = session.get('user')

        save_application_data(
            function_mode=data.get('function_mode'),
            application_name=data.get('application_name'),
            app_url=data.get('application_link'),
            status=data.get('status'),
            owner=data.get('owner'),
            permissions=data.get('permissions'),
            dimensions=data.get('selected_dimensions'),
            modules=data.get('modules'),
            created_by=user_email
        )

        return jsonify({"message": "Success"}), 200

    except Exception as e:
        print(f"Error in submit_app_data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/delete_app', methods=['POST'])
def delete_app():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No parameter provided"}), 400

        app_id = data.get('app_id')
        print(f"Selected App ID: {app_id}")

        result = delete_application(app_id)

        if not result or result.get("status") != "success":
            return jsonify({"error": "Failed to delete application"}), 500

        return jsonify({"message": "Deletion Success"}), 200

    except Exception as e:
        print(f"Error in application deletion: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/app_modules', methods=['POST'])
def app_modules():
    data = request.get_json()
    app_id = data.get('app_id', '').strip() if data else ''
    app_name = data.get('app_name', '').strip() if data else ''

    if not app_id:
        return jsonify({"error": "Invalid or missing app_id"}), 400

    session['app_owner_id'] = app_id
    session['app_name'] = app_name
    print(f"App ID stored in session: {app_id}")
    return jsonify({"redirect": url_for('get_modules_form')}), 200


@app.route('/get_modules_form', methods=['GET'])
def get_modules_form():
    app_id = session.get('app_owner_id')
    app_name = session.get('app_name')
    if not app_id:
        return render_template('noaccess.html', error="App ID not found in session.")

    modules = get_modules(app_id)
    print(modules)

    user_details = get_user_details()

    return render_template('modules.html', app_id=app_id, app_name=app_name, modules=modules, error="Failed to load modules.", user=user_details)


@app.route('/app_dimension', methods=['POST'])
def app_dimension():
    data = request.get_json()
    app_id = data.get('app_id', '').strip() if data else ''
    app_name = data.get('app_name', '').strip() if data else ''

    if not app_id:
        return jsonify({"error": "Invalid or missing app_id"}), 400

    session['app_owner_id'] = app_id
    session['app_name'] = app_name
    print(f"App ID stored in session: {app_id}")
    return jsonify({"redirect": url_for('get_dimension_form')}), 200


@app.route('/get_dimension_form', methods=['GET'])
def get_dimension_form():
    app_id = session.get('app_owner_id')
    app_name = session.get('app_name')
    if not app_id:
        return render_template('noaccess.html', error="App ID not found in session.")

    dimension = get_dimension(app_id)
    print(dimension)

    user_details = get_user_details()

    return render_template('dimensions.html', app_id=app_id, app_name=app_name, dimensions=dimension, error="Failed to load modules.", user=user_details)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
