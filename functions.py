from flask import session


def validate_user(user):
    print(f"Validating user: {user}")
    print(f"User email: {user.get('email')}")
    print(f"User name: {user['given_name']} {user['family_name']}")
    print(f"User Picture: {user['picture']}")
    session['picture'] = user['picture']
    return True
