import email
from flask import session, request
import requests
import json
import uuid
from datetime import datetime
import os
from google.cloud import secretmanager
import sys
import traceback
from dotenv import load_dotenv
import pytz
from zoneinfo import ZoneInfo

load_dotenv()

secret_project_id = os.getenv('EP_PROJECT_ID')
secret_id = os.getenv('secret_id')


# def get_user_details():
#     try:
#         admin_details = session.get('admin_details')
#         user = session.get('user')

#         if not isinstance(user, dict):
#             print("Invalid or missing 'user' in session.")
#             user = {}

#         if not isinstance(admin_details, dict):
#             print("Invalid or missing 'admin_details' in session.")
#             admin_details = {}

#         return {
#             "user": user,
#             "full_name": user.get('name', 'Unknown User'),
#             "picture": user.get('picture', '/static/default-avatar.png'),
#             "role_type": admin_details.get("role_type", 'guest')
#         }

#     except Exception as e:
#         print(f"Exception in get_user_details: {e}")
#         return {
#             "user": {},
#             "full_name": "Unknown User",
#             "picture": "",
#             "role_type": "guest"
#         }


def get_secret(project_id: str, secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(name=secret_name)
    return response.payload.data.decode("UTF-8")


api_key = get_secret(project_id=secret_project_id, secret_id=secret_id)

domain = "https://control-center-ednpoints-740032229271.us-west1.run.app/control_center"
key = api_key


def validate_user(user):
    try:
        StartDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

        log_api_activity(StartDate, "User Control Center - Validate User",
                         "Success", "", f"User {username} validated successfully.")

        return True

    except Exception as e:
        # log_api_activity(datetime.now().strftime(
        #     "%Y-%m-%d %H:%M:%S"), "User Control Center - Validate User", "Failed", str(e), f"Error during user validation. Details: {str(e)}")
        log_api_error_activity(
            "User Control Center - Validate User function", e)
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


def log_api_activity(StartDate, LogTitle, Status, ErrorMessage, Remarks):
    try:
        url = f"https://dma-dev-job-logs-174874363586.us-west1.run.app"

        EndDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(
            f"Parameters being sent to log_api_activity: {StartDate}, {EndDate}, {LogTitle}, {Status}, {ErrorMessage}, {Remarks}")

        payload = {
            "data": {
                "StartDate": StartDate,
                "EndDate": EndDate,
                "LogTitle": LogTitle,
                "Status": Status,
                "ErrorMessage": ErrorMessage,
                "Remarks": Remarks
            }
        }

        response = requests.post(url, json=payload)

        if response.status_code == 200:
            print(f"API activity logged successfully: {response.text}")
        else:
            print(
                f"Failed to log API activity: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Exception during logging API activity: {e}")


def save_application_data(function_mode, application_name, app_url, status, owner, permissions, dimensions, modules, created_by):
    try:
        StartDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

        log_api_activity(StartDate, "User Control Center - Save Application Data",
                         "Success", "", f"{application_name} was successfully saved.")

    except Exception as e:
        # log_api_activity(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "User Control Center - Save Application Data",
        #                  "Failed", str(e), f"Saving {application_name} encountered error. Details: {str(e)}")
        log_api_error_activity(
            "User Control Center - Save Application Data function", e)
        print(f"Exception during logging user activity: {e}")


def get_master_data():
    try:
        StartDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

        log_api_activity(StartDate, "User Control Center - Get Master Data",
                         "Success", "", f"Master data was successfully retrieved.")

        return master_details

    except Exception as e:
        # log_api_activity(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "User Control Center - Get Master Data",
        #                  "Failed", str(e), f"Getting master data encountered error. Details: {str(e)}")
        log_api_error_activity(
            "User Control Center - Get Master Data function", e)
        return False


def delete_application(app_id):
    try:
        StartDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

        log_api_activity(StartDate, "User Control Center - Delete Application",
                         "Success", "", f"Application with ID: {app_id} was successfully deleted.")

        return response.json()

    except Exception as e:
        # log_api_activity(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "User Control Center - Delete Application",
        #                  "Failed", str(e), f"Application with ID: {app_id} was failed to deleted. Details: {str(e)}")
        log_api_error_activity(
            "User Control Center - Delete Application function", e)
        return False


def get_modules(app_id):
    try:
        StartDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
            log_api_activity(StartDate, "User Control Center - Get Modules",
                             "Success", "", f"Modules was successfully retrieved.")
            return data.get("data", []) if isinstance(data, dict) else []
        else:

            log_api_activity(StartDate, "User Control Center - Get Modules",
                             "Failed", "", f"Modules was failed to retrieved.")
            print(
                f"Module fetch failed: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        # log_api_activity(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "User Control Center - Get Modules",
        #                  "Failed", str(e), f"Modules was failed to retrieved. Details: {str(e)}")
        log_api_error_activity(
            "User Control Center - Get Modules function", e)
        return []


def get_dimension(app_id):
    try:
        StartDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
            log_api_activity(StartDate, "User Control Center - Get Dimension",
                             "Success", "", f"Dimension was successfully retrieved.")
            return data.get("data", []) if isinstance(data, dict) else []
        else:
            print(
                f"Dimension fetch failed: {response.status_code} - {response.text}")
            log_api_activity(StartDate, "User Control Center - Get Dimension",
                             "Failed", "", f"Dimension was failed to retrieved.")
            return []
    except Exception as e:
        # log_api_activity(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "User Control Center - Get Dimension",
        #                  "Failed", str(e), f"Dimension was failed to retrieved. Details: {str(e)}")
        # print(f"Dimension fetch error: {e}")
        log_api_error_activity(
            "User Control Center - Get Dimension function", e)
        return []


# -----------------------------------------------------------------------------------------------------------------------------
# FRED

def load_administrators():
    url = f"{domain}/load_administrator"
    try:

        StartDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }

        payload = {
            "status": "success",
            "message": "This request post should trigger the load_administrator in API ",
            "result": ""
            # "X-API-KEY': api_key,

        }

        print(f"This will be the destination API of the request: {url}")
        print(f"This is the payload: {payload}")
        response = requests.post(url, headers=headers)

        print(f"This is the passing of data to API : {response}")

        # Wait response from API
        api_response = response.json()

        # api_response = requests.get(url, headers=headers)
        # print(f"This is getting the data FROM API : {api_response}")

        log_api_activity(StartDate, "User Control Center UI - load_administrator function",
                         "Success", "", f"Loaded successfully to gridview....")

        # return api_response.json()
        return api_response

    except Exception as e:
        log_api_error_activity(
            "User Control Center UI - load_administrator function", e)


# Pass the data to API
def search_hcm_id():

    url = f"{domain}/search_hcm_id"
    try:
        StartDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data = request.get_json()
        hcm_id = data['hcm_id']
        print(f"The user input of HCM ID was:{hcm_id}")

        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }

        payload = {
            "status": "success",
            "message": "This is user inputr of HCM ID",
            "result": hcm_id
        }

        print(f"This will be the destination API of the request: {url}")
        print(f"This is the payload: {payload}")
        response = requests.post(url, headers=headers, json=payload)

        print(f"This is the passing of data to API : {response}")

        # Wait response from API
        api_response = response.json()

        # api_response = requests.get(url, headers=headers)
        # print(f"This is getting the data FROM API : {api_response}")

        log_api_activity(StartDate, "User Control Center UI - search_hcm_id function",
                         "Success", "", f"hcm id was passed to API without issues....")

        # return api_response.json()
        return api_response

    # Logic that search if user exist in administrator_master table

    except Exception as e:
        log_api_error_activity(
            "User Control Center UI - search_hcm_id function", e)


# Pass the data to API
def insert_enroll_administrator_function(user):
    try:
        StartDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        url = f"{domain}/insert_enroll_administrator"

        data = request.get_json()
        # print(f"This is the contents of the request.get_json data: {data}")

        # Get the username based on user email address then use Split() method to only get the "firstname.lastname" format
        username_delimiter = '@'
        raw_username = data['email']
        splitted_username = raw_username.split(username_delimiter, 1)

        print(
            f"There is the contents of the splitted email: {splitted_username}")

        print(f"There is the data: {data}")

        # Get user input from UI, passed by Javascript
        user_id = data['user_id']
        hcm_id = data['hcm_id']
        full_name = data['full_name']
        email = data['email']
        sbu = data['sbu']
        job_position = data['job_position']
        ticket_number = data['ticket_number']
        access_start_date = data['access_start_date']
        access_end_date = data['access_end_date']
        role_type = data['role_type']
        username = splitted_username[0]
        mode = data['mode']
        current_logged_in = user['email']

        print("Data from UI was successfully retrieved, here are the items ")

        print(f"HCM ID: {hcm_id}")
        # print(f"FULL NAME: {full_name}")
        print(f"USERNAME: {username}")
        print(f"EMAIL: {email}")
        print(f"SBU: {sbu}")
        print(f"JOB POSITION: {job_position}")
        print(f"TICKET NUMBER: {ticket_number}")
        print(f"ACCESS START DATE: {access_start_date}")
        print(f"ACCESS END DATE: {access_end_date}")
        print(f"ROLE TYPE: {role_type}")
        print(f"MODE: {mode}")
        print(f"CURRENT LOGGED IN: {current_logged_in}")

        print('insert_enroll_administrator_function will now pass the data to API ')

        data_from_UI = {
            "user_id": user_id,
            "hcm_id": hcm_id,
            "full_name": full_name,
            "email": email,
            "sbu": sbu,
            "job_position": job_position,
            "ticket_number": ticket_number,
            "access_start_date": access_start_date,
            "access_end_date": access_end_date,
            "role_type": role_type,
            "username": username,
            "mode": mode,
            "current_logged_in": current_logged_in
        }

        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }

        payload = {
            "status": "success",
            "message": "This is user input from controls",
            "payload": data_from_UI
        }

        print(f"This will be the destination API of the request: {url}")
        print(f"This is the payload: {payload}")

        response = requests.post(url, headers=headers, json=payload)

        # return response
        print(f"This is the passing of data to API : {response}")

        if response.status_code != 200:
            print(
                f"Error in searching user: {response.status_code} - {response.text}")
            return False

        # Get the response from API
        api_response = response.json()

        # api_response = requests.get(url, headers=headers)
        # print(f"This is getting the data FROM API : {api_response}")

        log_api_activity(StartDate, "User Control Center UI - insert_enroll_administrator_function function",
                         "Success", "", f"enroll administrator was passed to API without issues....")

        return api_response

    except Exception as e:
        log_api_error_activity(
            "User Control Center UI - insert_enroll_administrator_function function", e)


# Pass the data to API
def delete_administrator(user):

    try:
        StartDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        url = f"{domain}/delete_administrator"

        data = request.get_json()
        user_id = data.get('user_id') if data else None
        deletion_reason = data.get('deletion_reason') if data else None
        current_logged_in = user['email']

        print(f"Logged user: {current_logged_in}")

        print(f" This is the user input to delete {deletion_reason}")

        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }

        payload = {
            "status": "success",
            "message": "This is the user id with reason of deletion",
            "payload": {
                "user_id": user_id,
                "deletion_reason": deletion_reason,
                "deleted_by": current_logged_in
            }
        }

        print(f"This will be the destination API of the request: {url}")
        print(f"This is the payload: {payload}")
        response = requests.post(url, headers=headers, json=payload)

        # return response
        print(f"This is the passing of data to API : {response}")

        if response.status_code != 200:
            print(
                f"Error in searching user: {response.status_code} - {response.text}")
            return False

        api_response = response.json()

        # api_response = requests.get(url, headers=headers)
        # print(f"This is getting the data FROM API : {api_response}")

        log_api_activity(StartDate, "User Control Center UI - delete_administrator",
                         "Success", "", f"Deletion request was passed to API without issues for deletion....")

        return api_response

    except Exception as e:
        log_api_error_activity(
            "User Control Center UI - delete_administrator function", e)


# Pass the data to API
def retrieve_administrator_details_to_gridview():
    try:
        StartDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        url = f"{domain}/retrieve_administrator_details"
        print(url)

        print(request.form)

        user_id = request.form.get('txt_search_employee')
        print(f"The HCM ID to search was: {user_id}")

        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }

        payload = {
            "status": "success",
            "message": "This is user input from controls",
            "payload": {
                "user_id": user_id
            }
        }

        response = requests.post(url, headers=headers, json=payload)

        # return response
        print(f"This is the passing of data to API : {response}")

        if response.status_code != 200:
            print(
                f"Error in searching user: {response.status_code} - {response.text}")
            return False

        api_response = response.json()

        # api_response = requests.get(url, headers=headers)
        # print(f"This is getting the data FROM API : {api_response}")

        log_api_activity(StartDate, "User Control Center UI - retrieve_administrator_details_to_gridview function",
                         "Success", "", f"retrieve data request to API without issues....")

        return api_response

    # Logic that search if user exist in administrator_master table

    except Exception as e:
        log_api_error_activity(
            "User Control Center UI - retrieve_administrator_details_to_gridview function", e)


def log_api_error_activity(title, e):
    StartDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    exc_type, exc_obj, exc_tb = sys.exc_info()
    file_name = exc_tb.tb_frame.f_code.co_filename
    line_number = exc_tb.tb_lineno

    print(f"Error occurred in file: {file_name}")
    print(f"Error occurred on line: {line_number}")
    print(f"Error message: {e}")

    log_api_activity(StartDate, title, "Failed",
                     f"Error in file {file_name} at line {line_number}", str(e))
