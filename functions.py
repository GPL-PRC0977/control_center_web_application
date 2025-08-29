import email
from flask import session
import requests
import json
import uuid
from datetime import datetime
import os
from google.cloud import secretmanager
from dotenv import load_dotenv

load_dotenv()

secret_project_id = os.getenv('EP_PROJECT_ID')
secret_id = os.getenv('secret_id')


def get_secret(project_id: str, secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(name=secret_name)
    return response.payload.data.decode("UTF-8")


api_key = get_secret(project_id=secret_project_id, secret_id=secret_id)

domain = "http://127.0.0.1:5001/control_center"
key = api_key


# def validate_user(user):
#     try:
#         url = f"{domain}/control_center/admin"
#         print(f"Email: {user.get('email')}")
#         user_email = user.get('email')

#         if not user_email:
#             print("User email is missing.")
#             return False

#         username = user_email.split('@')[0]

#         payload = json.dumps({
#             "param": username
#         })
#         headers = {
#             'X-API-KEY': key,
#             'Content-Type': 'application/json'
#         }

#         response = requests.post(url, headers=headers, data=payload)

#         if response.status_code != 200:
#             print(
#                 f"Error validating user: {response.status_code} - {response.text}")
#             return False

#         # print(f"API Response: {response.text}")

#         admin_list = response.json().get('data', [])

#         if not admin_list:
#             print("No admin details found for the user.")
#             return False

#         admin_details = admin_list[0]

#         print(f"Admin Details: {admin_details}")

#         session['admin_details'] = {
#             'hcm_id': admin_details.get('hcm_id'),
#             'role_type': admin_details.get('role_type')
#         }

#         # print(f"User session updated: {session['admin_details']}")

#         return True

#     except Exception as e:
#         print(f"Exception during user validation: {e}")
#         return False

def validate_user(user):
    try:
        if not isinstance(user, dict):
            print("Invalid user object.")
            return False

        user_email = user.get('email')

        if not user_email:
            print("User email is missing.")
            return False

        username = user_email.split('@')[0]

        payload = json.dumps({"param": username})
        headers = {
            'X-API-KEY': key,
            'Content-Type': 'application/json'
        }

        url = f"{domain}/admin"
        response = requests.post(url, headers=headers, data=payload)

        if response.status_code != 200:
            print(
                f"Error validating user: {response.status_code} - {response.text}")
            return False

        try:
            admin_list = response.json().get('data', [])
        except ValueError:
            print("Invalid JSON response from admin API.")
            return False

        if not admin_list:
            print("No admin details found for the user.")
            return False

        admin_details = admin_list[0]

        if 'hcm_id' not in admin_details or 'role_type' not in admin_details:
            print("Missing expected admin details.")
            return False

        session['admin_details'] = {
            'hcm_id': admin_details['hcm_id'],
            'role_type': admin_details['role_type']
        }

        return True

    except Exception as e:
        print(f"Exception during user validation: {e}")
        return False


def log_user_activity(user, action, details):
    try:
        url = f"{domain}/log_activity"
        payload = {
            "user": user,
            "action": action,
            "details": details
        }
        headers = {
            'X-API-KEY': key,
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"User activity logged successfully: {response.text}")
        else:
            print(
                f"Failed to log user activity: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Exception during logging user activity: {e}")


def save_application_data(function_mode, application_name, app_url, status, owner, permissions, dimensions, modules, created_by):
    try:
        if function_mode == "modify":
            app_id = session.get('app_id_to_modify')
        else:
            app_id = str(uuid.uuid4())
            print(app_id)

        url = f"{domain}/save_application_data"
        payload = {
            "app_id": app_id,
            "function_mode": function_mode,
            "application_name": application_name,
            "app_url": app_url,
            "status": status,
            "owner": owner,
            "permissions": permissions,
            "dimensions": dimensions,
            "modules": modules,
            "created_by": created_by
        }
        headers = {
            'X-API-KEY': key,
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"Application successfully saved: {response.text}")
        else:
            print(
                f"Failed to save application: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Exception during logging user activity: {e}")


def get_master_data():
    try:
        url = f"{domain}/get_app_master_data"

        headers = {
            'X-API-KEY': key,
            'Content-Type': 'application/json'
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(
                f"Error getting master data: {response.status_code} - {response.text}")
            return False

        app_master_list = response.json()

        if not app_master_list:
            print("No application master data found.")
            return False

        master_details = app_master_list

        return master_details

    except Exception as e:
        print(f"Exception during getting master data: {e}")
        return False


def delete_application(app_id):
    try:
        url = f"{domain}/delete_app"

        payload = {
            "app_id": app_id
        }
        headers = {
            'X-API-KEY': key,
            'Content-Type': 'application/json'
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            print(
                f"Error deleting application: {response.status_code} - {response.text}")
            return False

        return response.json()

    except Exception as e:
        print(f"Exception error: {e}")
        return False


def get_modules(app_id):
    try:
        url = f"{domain}/get_modules"

        payload = {
            "app_id": app_id
        }
        headers = {
            'X-API-KEY': key,
            'Content-Type': 'application/json'
        }

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data.get("data", []) if isinstance(data, dict) else []
        else:
            print(
                f"Module fetch failed: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Module fetch error: {e}")
        return []


def get_dimension(app_id):
    try:
        url = f"{domain}/get_dimension"

        payload = {
            "app_id": app_id
        }
        headers = {
            'X-API-KEY': key,
            'Content-Type': 'application/json'
        }
        response = requests.post(
            url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data.get("data", []) if isinstance(data, dict) else []
        else:
            print(
                f"Dimension fetch failed: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Dimension fetch error: {e}")
        return []
