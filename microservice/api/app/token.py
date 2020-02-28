from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)
from functools import wraps
import re
from flask import g, current_app, jsonify

from bson.objectid import ObjectId



def init_token():
   jwt = JWTManager()
   return jwt


def get_token(jwt, app):
   app.config['JWT_SECRET_KEY'] = 'qwerty'  # Change this!
   jwt.init_app(app)

   @jwt.user_identity_loader
   def user_identity_lookup(user):
       print("user_identity_lookup")
       print(user)
       return str(user)

   @jwt.user_loader_callback_loader
   def user_loader_callback(identity):
       print("user_loader_callback")
    #    user = mongo.db.users.find_one({
    #        "username": identity})
       print('load the user by its identity')
       print('load identity by user')
       if user is None or "username" not in user:
           return None
       return user

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()

        if user["role"] == "Admin":
            return fn(*args, **kwargs)

        if 'role' in user:
            if user['role'] != 'Admin':
                return jsonify(msg='Admins only!'), 403
            else:
                return fn(*args, **kwargs)
        return jsonify(msg='Admins only!'), 403
    return wrapper


def manager_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()
        if 'role' in user:
            if user['role'] == 'manager' or user['role'] == 'Admin':
                return fn(*args, **kwargs)
            else:
                return jsonify(msg='manager only!'), 403
        return jsonify(msg='manager only!'), 403
    return wrapper