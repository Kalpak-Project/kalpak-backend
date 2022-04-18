# from ast import Delete
from flask import Flask, request
import flask
import json
from flask.json import jsonify
from extensions import mongo
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from werkzeug.exceptions import Unauthorized
import ssl
import datetime


from flask_login import (
    UserMixin,
    login_user,
    LoginManager,
    login_required,
    logout_user,
    current_user,
)


client = MongoClient(
    "mongodb+srv://UI_REACT:alex_has@project1.famyl.mongodb.net/KALPAK?retryWrites=true&w=majority",
    tlsAllowInvalidCertificates = True
)

db = client.get_database("KALPAK")

roles_collection = db.Roles
# roles_docs = roles_collection.find({})

persons_collection = db.Persons
# persons_docs = persons_collection.find({})

manning_collection = db.Manning
# manning_docs = manning_collection.find({})

placementMeetings_collection = db.PlacementMeetings
# placementMeetings_docs = placementMeetings_collection.find({})

user_collection = db.Users
users_docs = user_collection.find({})

app = Flask(__name__)

app.config["SECRET_KEY"] = "jkhkuih676agcjbuiy78w8t6t"

# Flask login stuff
login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, id_):
        self.id = id_

# Checks what the user's authority is.
# Returns true if the user is an admin, otherwise: false 
def check_athority():
    obj_id = current_user.get_id()
    user_name = user_collection.find_one({"_id": ObjectId(obj_id)})["user_name"]
    user = user_collection.find_one({"user_name": user_name})
    print(user)
    return user["isAdmin"]

@app.route("/api/current_user", methods=["GET"])
@login_required
def get_current_user():

    obj_id = current_user.get_id()
    user_name = user_collection.find_one({"_id": ObjectId(obj_id)})["user_name"] 
    return jsonify({"id": current_user.get_id(), "isAdmin": check_athority(), "user": user_name})


@app.route("/api/register", methods=["POST"])
def register():

    # need to fix the check if user already exists in the table
    # check if user already exists in the table

    newUser = request.data
    userStr = newUser.decode("utf-8")
    newUserJson = json.loads(userStr)

    username = newUserJson["user_name"]
    found = user_collection.find_one({"user_name": username})
    
    if found:
        return jsonify(
            {"status": 401, "reason": "Username already exist. Try another user name."})
    else:
        usr = {}
        hashed_password = generate_password_hash(newUserJson['password'])

        # Replacing the original password with the hashed password
        del newUserJson['password']
        newUserJson['password'] = hashed_password
    
        for key, value in newUserJson.items():
            usr[key] = value

        print(usr)
        user_collection.insert_one(usr)
        login_user(User(newUserJson["user_name"]))
        return jsonify({"success": True})


@login_manager.user_loader
def load_user(id_):
    return User(id_)


@app.route("/api/login", methods=["POST"])
def login():
    username = request.json.get("user_name", None)
    password = request.json.get("password", None)
    print(request.data)
    found = user_collection.find_one({"user_name": username})
    print("found:", found)
    if found:
        hashPassword = found["password"]
        correct = check_password_hash(hashPassword, password)
        if correct:
            user_id = str(found["_id"])
            print(user_id)
            login_user(User(user_id))
            return jsonify({"success": True})
        else:
            return jsonify({"status": 401, "reason": "password error"})

    else:
        return jsonify({"status": 402, "reason": "username doesn't exist"})


@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"success": "you logged out"})

# manning
@app.route("/api/manning", methods=["GET", "POST"])
def manning():
    isAdmin = check_athority()
    if not isAdmin:
        raise Unauthorized()
    response = ""
    if request.method == "GET":
        data_manning = []
        for doc in manning_collection.find({}):
            data_manning +=[dict(key = str(doc.pop("_id")),**doc)]

        response = flask.jsonify({"manning": data_manning})
        response.headers.add("Access-Control-Allow-Origin", "*")

    else:
        newManning = request.data
        manningStr = newManning.decode("utf-8")
        newManningJson = json.loads(manningStr)
        manning = {}
        for field in newManningJson:
            manning[field["key"]] = field["value"]

        print(manning)
        manning_collection.insert_one(manning)

    return response
    

#Placement Meetings
@app.route("/api/placementMeetings", methods=["GET", "POST"])
def placementMeetings():
    isAdmin = check_athority()
    if not isAdmin:
        raise Unauthorized()
    response = ""
    if request.method == "GET":
        data_placementMeetings = []

    for doc in roles_collection.find({}):
        val_id= doc["_id"]
        minn_filte = {"id": val_id}
        new_doc = doc.pop("_id")
        str_id_role = str(new_doc)
        doc["_id"] = str_id_role
        smile = False
        for man_doc in manning_collection.find(minn_filte):
            date = man_doc["Job end date"].replace("Z", "+00:00")
            if datetime.datetime.fromisoformat(date) - datetime.timedelta(days=180) < datetime.datetime.utcnow():
                smile = False
            else:
                smile = True
                break
        data_placementMeetings += [{"Role ID":doc, "Smile": smile}]
 
    response = flask.jsonify({"placementMeetings": data_placementMeetings})
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

#role<key>
@app.route("/api/roles/<key>", methods=["GET", "POST"])
def role(key):
    response = ""
    if request.method == "GET":
        role_=roles_collection.find_one({"_id":ObjectId(key)})
        response = flask.jsonify(dict(key = str(role_.pop("_id")),**role_))       
    return response

@app.route("/api/roles", methods=["GET", "POST"])
def roles():
    response = ""
    isAdmin = check_athority()
    if not isAdmin:
        raise Unauthorized()
    if request.method == "GET":
        data_roles = []
        for doc in roles_collection.find({}, {}):
            data_roles +=[dict(key = str(doc.pop("_id")),**doc)]

        response = flask.jsonify({"roles": data_roles})
        response.headers.add("Access-Control-Allow-Origin", "*")

    else:
        newRole = request.data
        roleStr = newRole.decode("utf-8")
        newRoleJson = json.loads(roleStr)
        role = {}
        for field in newRoleJson:
            role[field["key"]] = field["value"]

        print(role)
        roles_collection.insert_one(role)

    return response

#smile
@app.route("/api/users/<key>/smile", methods=["GET", "POST"])
def smile(key):
    for doc in manning_collection.find({"User ID": key}):
        date = doc["Job end date"].replace("Z", "+00:00")
        print(datetime.datetime.fromisoformat(date) - datetime.timedelta(days=90))
        if datetime.datetime.fromisoformat(date) - datetime.timedelta(days=90) < datetime.datetime.utcnow():
            return flask.jsonify({"smile":False})
    return flask.jsonify({"smile":True})


#user<key>
@app.route("/api/users/<key>", methods=["GET", "POST"])
def user(key):
    response = ""
    if request.method == "GET":
        user_=user_collection.find_one({"_id":ObjectId(key)})
        response = flask.jsonify(dict(key = str(user_.pop("_id")),**user_))
    return response


@app.route("/api/users", methods=["GET", "POST"])
def users():
    response = ""
    isAdmin = check_athority()
    if not isAdmin:
        raise Unauthorized()
    if request.method == "GET":
        data_users = []

        for doc in user_collection.find({}, {"password": 0}):
            data_users += [dict(key = str(doc.pop("_id")),**doc)]

        response = flask.jsonify({"users": data_users})
        response.headers.add("Access-Control-Allow-Origin", "*")
    else:
        
        # need to fix the check if user already exists in the table
        #  user = request.data
        # found = user_collection.find_one({"user_name": user[0].user_name}, {"_id": 0})
        
        # if found:
        #     return jsonify(
        #         {"status": 401, "reason": "Username already exist. Try another user name."})
        # else:

        newUser = request.data
        userStr = newUser.decode("utf-8")
        newUserJson = json.loads(userStr)
        default_password = generate_password_hash("password123")
        user = {"password": default_password}
        for field in newUserJson:
            user[field["key"]] = field["value"]

        print(user)
        user_collection.insert_one(user)
    
    return response


if __name__ == "__main__":
    app.run(debug=True)
