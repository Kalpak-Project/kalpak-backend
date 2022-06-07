from asyncio.log import logger
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
import logbook 
import sys
import copy

logger=logbook.Logger(__name__)

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

manning_collection = db.Manning

constraints_collection = db.Constraints

user_collection = db.Users

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
        newUserJson['isAdmin'] = False    
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


# home_page, Optional future roles table
@app.route("/api/optional_roles/<key>", methods=["GET"])
@login_required
def optional_roles(key):
    response = ""
    if request.method == "GET":
        userRoles = manning_collection.find({"User ID":key})
        
        # check if user has a manning
        if userRoles:
            userRoles = list(userRoles)
            if len(userRoles) > 0:
                sortedUserRoles = sorted(userRoles, key=lambda x: x['Job end date'], reverse=True)
                user_end_role = sortedUserRoles[0]["Job end date"].replace("Z", "+00:00")

        data_roles = []
        
        optionalRolesIndex = 0
        for doc in roles_collection.find({}):
            new_doc = doc.pop("_id")
            str_id_role = str(new_doc)
            doc["_id"] = str_id_role
            minn_filte = {"Role ID": str_id_role}
            add_role = True

            # filter all manning roles that end after 180 days from 'job end date'
            if userRoles:
                for man_doc in manning_collection.find(minn_filte):
                    date = man_doc["Job end date"].replace("Z", "+00:00")
                    if datetime.datetime.fromisoformat(date) - datetime.timedelta(days=180) >= datetime.datetime.fromisoformat(user_end_role):
                        add_role = False
                        break
                    break
            # filter all manning roles that end after 180 days from now (Because the user does not have a manned role)
            else:
                 for man_doc in manning_collection.find(minn_filte):
                    date = man_doc["Job end date"].replace("Z", "+00:00")
                    if datetime.datetime.fromisoformat(date) - datetime.timedelta(days=180) >= datetime.datetime.utcnow().astimezone():
                        add_role = False
                        break
                    break               
  
            if add_role:
                doc["index"] = optionalRolesIndex
                data_roles += [doc]
                optionalRolesIndex += 1
        
        current_user = user_collection.find_one({"_id": ObjectId(key)})
        if 'orderedOptionalRoles' in current_user: 

            for role in data_roles:
                if role['_id'] in current_user['orderedOptionalRoles']:
                    role['index'] = current_user['orderedOptionalRoles'][str(role['_id'])]
        
        response = flask.jsonify({"dataRoles": data_roles})
        response.headers.add("Access-Control-Allow-Origin", "*")
    return response

# recive optional feuture roles, ordered by user.
@app.route("/api/updateRolesOrder", methods=['POST'])
@login_required
def get_ordered_roles():
    data = request.data
    dataStr = data.decode("utf-8")
    newDataJson = json.loads(dataStr)
    print(newDataJson)
    orderRoleIDDict = {str(role['_id']): role['index'] for role in newDataJson['orderedList']}
    print("order role ID: ", orderRoleIDDict)
    fieldToAdd = {'orderedOptionalRoles': orderRoleIDDict}
    user_collection.update_one({'_id': ObjectId(newDataJson['userUpdate'])}, {'$set': fieldToAdd})
    return 'success'

def getUsersOrderedRoles():
    usersOrederList = {}
    for user in user_collection.find({}):
        if 'orderedOptionalRoles' in user:
            usersOrederList[str(user['_id'])] = user['orderedOptionalRoles']
    return usersOrederList    

#employee status
@app.route("/api/employee_status/<key>", methods=["GET"])
@login_required
def employee_status(key):
    employee_list = []
    users_filter = {"Employer": key}
    for employee in user_collection.find(users_filter):
        new_doc = employee.pop("_id")
        str_id_employee = str(new_doc)
        employee["_id"] = str_id_employee
        smile, date = get_smile_and_last_role(employee["_id"])
        employee_list += [{"employee": employee, "smile": smile}]
        print(employee_list)
    return jsonify({"employeeList": employee_list})

#userRole
@app.route("/api/user_role/<key>", methods=["GET"])
@login_required
def user_role(key):
    user_manning = manning_collection.find({"User ID": key})
    role = None
    smile, last_role = get_smile_and_last_role(key)
    if last_role:
        role_id_str = str(last_role['_id'])
        last_role['_id'] = role_id_str
        role = last_role
    return jsonify({"userRole": role})



# manning
@app.route("/api/manning", methods=["GET", "POST"])
@login_required
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
        return response

    else:
        newManning = request.data
        manningStr = newManning.decode("utf-8")
        newManningJson = json.loads(manningStr)
        manning = {}
        for field in newManningJson:
            manning[field["key"]] = field["value"]
        print("addManning: ", manning)
        manning_collection.insert_one(manning)
        return response

    

@app.route("/api/selectedUserRole", methods=["POST"])
@login_required
def selectedUserRole():
    isAdmin = check_athority()
    if not isAdmin:
        raise Unauthorized()
    response = ""
    staffings = request.data
    print("staffings: ", staffings)
    staffingsStr = staffings.decode("utf-8")
    newStaffingsJson = json.loads(staffingsStr)
    
    users = newStaffingsJson["Users"]
    roles = newStaffingsJson["Roles"]
    staffingsList = []
    
    for i in range(len(roles)):
        if users[i]: # Checks whether a user has been staffed to this role
            role = {"Role ID": roles[i]}  
            user = {"User ID": users[i][0]}
            
            roleDuration = roles_collection.find_one({"_id":ObjectId(role['Role ID'])})["Duration"]
            dateOfStaffingOfCurrent = ""
            jobEndDateOfCurrent  = ""
        
            roleFoundInManning = manning_collection.find_one(role)
            if roleFoundInManning:
                print("roleFoundInManning: ", roleFoundInManning)
                dateOfStaffingOfCurrent = roleFoundInManning['Job end date'].replace("Z", "+00:00")
                jobEndDateOfCurrent = datetime.datetime.fromisoformat(dateOfStaffingOfCurrent) + datetime.timedelta(days=roleDuration)
            else:
                dateOfStaffingOfCurrent = datetime.datetime.utcnow().astimezone()
                jobEndDateOfCurrent = datetime.datetime.fromisoformat(str(dateOfStaffingOfCurrent)) + datetime.timedelta(days=roleDuration)

                
            print("user:", user)
            staffingsList += [{"User ID": user["User ID"], "Role ID": role["Role ID"],
                               "Date of staffing": str(dateOfStaffingOfCurrent), "Job end date": str(jobEndDateOfCurrent)}]
    
    manning_collection.insert_many(staffingsList)
    print("added to manning: ", staffingsList)
    response = jsonify({"success": "added into manning!"})
    return response
    
def stringToDate(str):
    date = str.replace("Z", "+00:00")
    return datetime.datetime.fromisoformat(date)

#Staffing Form
@app.route("/api/staffingForm", methods=["GET"])
def staffingForm():
    isAdmin = check_athority()
    if not isAdmin:
        raise Unauthorized()
    response = ""
    data_staffingForm = getRolesAndFreeUsers()
    response = flask.jsonify({"staffingForm": data_staffingForm})
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


# return all free roles and free users. list of dicts: [{'Role': roleDoc, 'User': [freeUsers] }]
def getRolesAndFreeUsers():
    data_staffingForm = []
    daysForThreshold = 180 # take from user?    
    now = datetime.datetime.utcnow().astimezone()
    threshold = now + datetime.timedelta(days=daysForThreshold)
    
    manning = manning_collection.find({})
    
    userToDate = {}
    roleToDate = {}
    for man_doc in manning:
        addToUsers = False
        if man_doc['User ID'] in userToDate:
            if userToDate[man_doc['User ID']] < man_doc['Job end date']:
                addToUsers = True
        else:
            addToUsers = True
        addToRoles = False         
        if man_doc['Role ID'] in roleToDate:
            if roleToDate[man_doc['Role ID']] < man_doc['Job end date']:
                addToRoles = True
        else:
            addToRoles = True
        if addToUsers:
            userToDate[man_doc['User ID']] = man_doc['Job end date']
        if addToRoles:
            roleToDate[man_doc['Role ID']] = man_doc['Job end date']
    
    roles = roles_collection.find({})
    freeRolesToEndDate = {}
    free_roles_list = []
    
    for role_doc in roles:
        new_role_doc = role_doc.pop("_id")
        str_id_role = str(new_role_doc)
        role_doc["_id"] = str_id_role
        roleID = role_doc['_id']
        roleEndDateStr = roleToDate.get(roleID, str(now))
        roleEndDate = stringToDate(roleEndDateStr)
        if roleEndDate < threshold:
            freeRolesToEndDate[roleID] = roleEndDateStr
            role_doc['endDate'] = roleEndDate
            free_roles_list += [role_doc]
    
    users = user_collection.find({})
    # freeUsersToEndDate = {}
    # free_users_list = []
    # for user_doc in users:
    #     new_user_doc = user_doc.pop("_id")
    #     str_id_user = str(new_user_doc)
    #     user_doc["_id"] = str_id_user
    #     userID = user_doc['_id']
    #     # Remove irrelevant fields from the document
    #     user_doc.pop('password')   
    #     if 'isAdmin' in user_doc:
    #         user_doc.pop('isAdmin')
    #     if 'orderedOptionalRoles' in user_doc:
    #         user_doc.pop('orderedOptionalRoles')
    #     endDateStr = userToDate.get(userID, str(now))
    #     endDate = stringToDate(endDateStr)
    #     if endDate < threshold:
    #         freeUsersToEndDate[userID] = endDate
    #         free_users_list += [dict(key=str(user_doc["_id"]),**user_doc)]
    
    for free_role in free_roles_list:
        free_users = []
        usersList = list(copy.deepcopy(users))
        for user_doc in usersList:
            addUser = True
            new_user_doc = user_doc.pop("_id")
            str_id_user = str(new_user_doc)
            user_doc["_id"] = str_id_user
            userID = user_doc['_id']
            userEndDateStr = userToDate.get(userID, str(now - datetime.timedelta(days=1000)))
            userEndDate = stringToDate(userEndDateStr)
            roleEndDateStr = freeRolesToEndDate.get(free_role['_id'], str(now))
            roleEndDate = stringToDate(roleEndDateStr)
            # TODO fix this place and all this function.
            if free_role['_id'] == '629cdffb6466e86cd55215b9':
                print('role end date: ', roleEndDateStr)
                print('user date: ', userEndDateStr)
            if userEndDate < threshold and (userEndDate + datetime.timedelta(days=90) < roleEndDate or roleEndDate < now):
                # Remove irrelevant fields from the document
                user_doc.pop('password')
                if 'isAdmin' in user_doc:
                    user_doc.pop('isAdmin')
                if 'orderedOptionalRoles' in user_doc:
                    user_doc.pop('orderedOptionalRoles')
                if 'Constraints' in free_role:
                    userManning = getHistory(user_doc['_id'])
                    rolesIdList = list(map(lambda man: man['Role ID'], userManning))
                    for conId in free_role['Constraints']:
                        con = constraints_collection.find_one({'_id': ObjectId(conId)})
                        if con['requirement'] not in rolesIdList:
                            addUser = False
                            break
            else:
                addUser = False
            if addUser:
                free_users += [dict(key=str(user_doc["_id"]),**user_doc)]
        data_staffingForm += [{"Role":free_role , "User": free_users}]
    # for free_role in free_roles_list:
    #     free_users = list(copy.deepcopy(free_users_list))
    #     if 'Constraints' in free_role:
    #         for user in free_users:
    #             userRoles = getHistory(user['_id'])
    #             rolesIdList = list(map(lambda role: role['_id'], userRoles))
    #             if len(rolesIdList) == 0:
    #                 free_users.remove(user)
    #                 continue
    #             for conId in free_role['Constraints']:
    #                 con = constraints_collection.find_one({'_id': ObjectId(conId)})
    #                 if con['requirement'] not in rolesIdList:
    #                     free_users.remove(user)
    #                     break
    #     data_staffingForm += [{"Role":free_role , "User": free_users}]
    return data_staffingForm


#Placement Meetings
@app.route("/api/placementMeetings", methods=["GET"])
@login_required
def placementMeetings():
    isAdmin = check_athority()
    if not isAdmin:
        raise Unauthorized()
    response = ""
    data_placementMeetings = []

    for doc in roles_collection.find({}):
        new_doc = doc.pop("_id")
        str_id_role = str(new_doc)
        doc["_id"] = str_id_role
        smile = False
        minn_filte = {"Role ID": str_id_role}

        for man_doc in manning_collection.find(minn_filte):
            date = man_doc["Job end date"].replace("Z", "+00:00")
            print(datetime.datetime.fromisoformat(date) - datetime.timedelta(days=180))
            if datetime.datetime.fromisoformat(date) - datetime.timedelta(days=180) < datetime.datetime.utcnow().astimezone():
                smile = False
            else:
                smile = True
                break
        data_placementMeetings += [{"Role":doc, "Smile": smile}]
    response = flask.jsonify({"placementMeetings": data_placementMeetings})
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

#role<key>
@app.route("/api/roles/<key>", methods=["GET", "POST"])
@login_required
def role(key):
    response = ""
    if request.method == "GET":
        role_=roles_collection.find_one({"_id":ObjectId(key)})
        response = flask.jsonify(dict(key = str(role_.pop("_id")),**role_))
    else:
        updatedRole = request.data
        roleStr = updatedRole.decode("utf-8")
        newRoleJson = json.loads(roleStr)
        print('newJsonRole: ', newRoleJson)
        roles_collection.update_one({'_id': ObjectId(key)}, {'$set': {
            'Title': newRoleJson['Title'], 'Duration': newRoleJson['Duration'],
            'Description': newRoleJson['Description']
        }})
        found = roles_collection.find_one({'_id': ObjectId(key)})
        print('found: ', found)
        response = 'successfully updated!'
    return response


@app.route("/api/roles", methods=["GET", "POST"])
@login_required
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
@login_required
def smile(key):
    smiley, last_role = get_smile_and_last_role(key)
    return(flask.jsonify({"smile": smiley}))

# recive user_id and returns if the user should be worry or not (smile or not)
def get_smile_and_last_role(key):
    smile = False
    lastRole = None
    userRoles = manning_collection.find({'User ID': key})
    if userRoles:
        userRoles = list(userRoles)
        if len(userRoles) > 0:
            sortedUserRoles = sorted(userRoles, key=lambda x: x['Job end date'], reverse=True)
            lastRole = sortedUserRoles[0]
            date = datetime.datetime.fromisoformat(lastRole['Job end date'].replace("Z", "+00:00"))
            
            if date - datetime.timedelta(days=90) >= datetime.datetime.utcnow().astimezone():
                print("happy: ", date)
                smile = True
        
    return smile, lastRole

#user<key>
@app.route("/api/users/<key>", methods=["GET", "POST"])
@login_required
def user(key):
    response = ""
    if request.method == "GET":
        user_=user_collection.find_one({"_id":ObjectId(key)})
        response = flask.jsonify(dict(key = str(user_.pop("_id")),**user_))
    return response


@app.route("/api/users", methods=["GET", "POST"])
@login_required
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

@app.get("/api/rolesHistory/<key>")
@login_required
def getRolesHistory(key):
    sortedRolesHistory = getHistory(key)
    print('rolesHistory: ', sortedRolesHistory)
    return flask.jsonify({"rolesHistory": sortedRolesHistory})

def getHistory(key):
    rolesHistory = manning_collection.find({'User ID': key})
    if rolesHistory:
        rolesHistory = list(rolesHistory)
        sortedRolesHistory = sorted(rolesHistory, key=lambda x: x['Job end date'], reverse=True)
        for role in sortedRolesHistory:
            newRole = role.pop("_id")
            strID = str(newRole)
            role['_id'] = strID
            job_staffing = role['Date of staffing'].replace("Z", "+00:00")
            job_staffing = datetime.datetime.fromisoformat(job_staffing)
            job_staffing_format = job_staffing.strftime("%d/%m/%Y")
            role['Date of staffing'] =  job_staffing_format
            job_end_date = role["Job end date"].replace("Z", "+00:00")
            job_end_date = datetime.datetime.fromisoformat(job_end_date)
            job_end_date_format = job_end_date.strftime("%d/%m/%Y")
            role["Job end date"] = job_end_date_format
        addRolesTitle(sortedRolesHistory)
        return sortedRolesHistory
    return rolesHistory

def addRolesTitle(rolesHistory):
    for role in rolesHistory:
        roleInRoles = roles_collection.find_one({'_id': ObjectId(role['Role ID'])})
        roleTitle = roleInRoles['Title']
        role['Title'] = roleTitle

@app.get('/api/getFileOfRole/<key>')
@login_required
def getFileOfRole(key):
    print('key: ', key)
    role = manning_collection.find_one({'_id': ObjectId(key)})
    path = role['file_path']
    pdfFile = open(path)
    return pdfFile


def get_constraits():
    return constraints_collection.find({})
        

if __name__ == "__main__":
    logbook.StreamHandler(sys.stdout).push_application() 
    # app.run(ssl_context=('cert.pem', 'key.pem'))
    app.run(debug=True)
