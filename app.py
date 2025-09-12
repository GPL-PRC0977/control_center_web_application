import json
from google.cloud import secretmanager
from flask import Flask, request, jsonify, render_template, url_for, session, redirect
from authlib.integrations.flask_client import OAuth
import os
from dotenv import load_dotenv
from functions import validate_user, save_application_data, get_master_data, delete_application, get_modules, get_dimension, search_hcm_id, insert_enroll_administrator_function, delete_administrator, retrieve_administrator_details_to_gridview, load_administrators, log_api_activity
import sys
import traceback

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_secret_key'


def get_oauth_config_from_secret(project_id: str, secret_id: str) -> dict:
    secret_client = secretmanager.SecretManagerServiceClient()
    secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

    response = secret_client.access_secret_version(
        request={"name": secret_name})
    secret_payload = response.payload.data.decode("UTF-8")

    # Parse the JSON string into a dictionary
    oauth_config = json.loads(secret_payload)
    return oauth_config


oauth_secrets = get_oauth_config_from_secret(
    os.getenv('EP_PROJECT_ID'), "google-oauth")

client_id = oauth_secrets["GOOGLE_CLIENT_ID"]
client_secret = oauth_secrets["GOOGLE_CLIENT_SECRET"]
redirect_uri = oauth_secrets["GOOGLE_REDIRECT_URI"]

print(f"Client ID: {client_id}")
print(f"Client Secret: {client_secret}")
print(f"Redirect URI: {redirect_uri}")

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=client_id,
    client_secret=client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    },
    redirect_uri=redirect_uri,
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


@app.route('/manage_users')
def manage_users():
    user_details = get_user_details()
    return_processed = load_administrators()
    return render_template('users.html', headers=return_processed['headers'], data=return_processed['rows'], user=user_details['user'], full_name=user_details['full_name'],
                           role_type=user_details['role_type'],
                           status='True')


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

# Search function in modal


# ------------------------------------------------------------------------------------------------------------------------
# FRED

@app.route('/search_hcm_id', methods=['POST'])
def enroll_administrator():
    # get_users()
    print(f"enroll_administrator function was triggered, will now process data")
    return_processed = search_hcm_id()

    if return_processed['status'] == 'error':
        return jsonify(return_processed)
    else:
        return jsonify(return_processed), 200


# Search function in Gridview
# AS IT IS HARDCODED


@app.route('/retrieve_administrator_details', methods=['POST'])
def retrieve_administrator_details():
    try:

        return_processed = retrieve_administrator_details_to_gridview()

        print(
            f"Data processed from API for retrieve_administrator_details :{retrieve_administrator_details_to_gridview}")

        user_details = get_user_details()

        return render_template('users.html', headers=return_processed['headers'], data=return_processed['rows'], message=return_processed['message'], status=True, status2=return_processed['status'], user=user_details['user'], full_name=user_details['full_name'],
                               role_type=user_details['role_type'])

    # Logic that search if user exist in administrator_master table

    except Exception as e:
        # full_traceback = traceback.format_exc()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        file_name = exc_tb.tb_frame.f_code.co_filename
        line_number = exc_tb.tb_lineno

        print(f"Error occurred in file: {file_name}")
        print(f"Error occurred on line number: {line_number}")
        print(f"Error message: {e}")
        # print(f"Full Traceback: {full_traceback}")


@app.route('/insert_enroll_administrator', methods=['POST'])
def insert_enroll_administrator():

    try:
        print("The insert_enroll_administrator_function was triggered")
        # Call the function here
        return_processed = insert_enroll_administrator_function(
            session.get('user'))

        if return_processed['status'] == 'error':
            return jsonify(return_processed), 409
        else:
            return jsonify(return_processed), 200
    except Exception as e:
        # full_traceback = traceback.format_exc()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        file_name = exc_tb.tb_frame.f_code.co_filename
        line_number = exc_tb.tb_lineno

        print(f"Error occurred in file: {file_name}")
        print(f"Error occurred on line number: {line_number}")
        print(f"Error message: {e}")


# FUNCTION TO DELETE ADMINISTRATOR
@app.route('/delete_administrator', methods=['POST'])
def handle_delete_administrator():

    try:
        print(f"Delete Administrator Function was triggered and called ")

        return_processed = delete_administrator(session.get('user'))

        if return_processed['status'] == 'error':
            return jsonify(return_processed), 409
        else:
            return jsonify(return_processed), 200
    except Exception as e:
        # full_traceback = traceback.format_exc()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        file_name = exc_tb.tb_frame.f_code.co_filename
        line_number = exc_tb.tb_lineno

        print(f"Error occurred in file: {file_name}")
        print(f"Error occurred on line number: {line_number}")
        print(f"Error message: {e}")


if __name__ == '__main__':
    app.run(debug=True)
