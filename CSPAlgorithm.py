import copy
from unittest import result
from Domain import Domain
from RoleVar import RoleVar
from Constraint import *
from app import getUsersOrderedRoles, getRolesAndFreeUsers, get_constraits

class csp:
    
    def __init__(self):
        self.freeUsersAndRoles = getRolesAndFreeUsers()
        self.values = self.getRemovedIrrelevantFields() # dicts of {userId: userDoc}        
        self.vars = self.getVars([role['Role'] for role in self.freeUsersAndRoles]) # dict of {roleId: RoleVar}
        self.constraints = self.getConstraints() # list of [Constraint]
        self.currentAssignment = {}
        # self.maxScoreAssignment = {} # dict of {score: assignment}
        # self.OrderedRolesLists = getUsersOrderedRoles() # dict of {userId: orderedRolesList}
        # self.score = 0
    
    def getRemovedIrrelevantFields(self):
        free = self.freeUsersAndRoles[0]['User'] # all fields of freeUsers are equal. that why we chose [0]
        freeUsers = {}
        for user in free:
            user.pop('Family Name')
            user.pop('Private Name')
            user.pop('Personal ID')
            user.pop('key')
            user.pop('Employer')
            freeUsers[user['_id']] = user
        return freeUsers
    
    def getVars(self, roles):
        vars = {}
        for role in roles:
            roleId = role['_id']
            vars[roleId] = RoleVar(role, self.getDomain(roleId))
        return vars
    
    def getDomain(self, var):
        # need to add here domain reduction for all relevant Domains.
        # need to make sure that send the values by value and not by reference.
        valuesCopy = dict(copy.deepcopy(self.values))
        return Domain(valuesCopy)
    
    def getConstraints(self):
        constraints = get_constraits()
        cons = [AllDifferent(self.vars)]
        for con in constraints:
            consType = con['type']
            if consType == 'TrainingRequired':
                cons += [TrainingRequired(str(con['_id']), con['requirement'])]
            # for each type of constraint, need to add here in 'elif'.
        return cons
    
    # Checks if all assignments have been completed
    def isComplete(self, result):
        if not result:
            return False
        return len(result) == len(self.vars)
    
    # Backtracking algorithm for finding the right assignment for the words entered
    def backtracking(self, assignments):
        if self.isComplete(assignments):
            return assignments
        # the main point: which var to choose?
        var = self.getUnassignedVar(assignments)
        # Check the possible assignments of the current character
        dom = copy.deepcopy(self.vars[var].getDomain().getDomainDict())
        for val in dom:
            if self.checkConsistency(assignments, var, val):
                assignments[var] = val
                self.updateDomains(val)
                res = self.backtracking(assignments)
                if res != -1:
                    return res
                assignments.pop(var)
                self.cancelDomains(var, val)
        return -1
    
    # Return a vars that has not yet been assigned
    def getUnassignedVar(self, assignments):
        unassignedVars = list(filter(lambda x: x not in assignments, self.vars))
        return unassignedVars[0]
    
    # Check whether the new assignment satisfies all the constraints
    def checkConsistency(self, ass, newVar, newValue):
        assCopy = dict(copy.deepcopy(ass))
        assCopy[newVar] = newValue
        for cons in self.constraints:
            if not cons.isConsist(assCopy, self.vars, self.values):
                return False
        return True
    
    # Domains reduction for new assignment
    def updateDomains(self, val):
        for v in self.vars:
            if v != val:
                self.vars[v].getDomain().removeFromDomain(val)

    # Cancel domains reduction after canceling an inappropriate assignment
    def cancelDomains(self, var, value):
        valDoc = self.values[value]
        for v in self.vars:
            if v != var:
                self.vars[v].getDomain().addToDomain(value, valDoc)
    
    

aaa = csp()
result = aaa.backtracking(aaa.currentAssignment)
bbb = []
for attr in result:
    bbb += [(attr, result[attr])]
ccc = list(map(lambda ass: {aaa.vars[ass[0]].var['Title']: aaa.values[ass[1]]['user_name']}, bbb))
print(ccc)  

        