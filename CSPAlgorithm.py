import copy
import datetime
from Domain import Domain
from RoleVar import RoleVar
from Constraint import *
from app import getRolesAndFreeUsers, get_constraits

class csp:
    
    def __init__(self, rolesAndUsers):
        self.freeUsersAndRoles = rolesAndUsers
        self.values = self.getRemovedIrrelevantFields() # dicts of {userId: userDoc}        
        self.vars = self.getVars([role['Role'] for role in self.freeUsersAndRoles]) # dict of {roleId: RoleVar}
        self.constraints = self.getConstraints() # list of [Constraint]
        self.currentAssignment = {}
        # self.maxScoreAssignment = {} # dict of {score: assignment}
        # self.OrderedRolesLists = getUsersOrderedRoles() # dict of {userId: orderedRolesList}
        # self.score = 0
    
    def getRemovedIrrelevantFields(self):
        users = []
        for role in self.freeUsersAndRoles:
            users += role['User']
        free = list({user['_id']: user for user in users}.values())
        print("Free: ", free)
        freeUsers = {}
        for user in free:
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
        dom = {}
        for role in self.freeUsersAndRoles:
            role_id = role['Role']['_id']
            if role_id == var:
                users_list = role['User']
                for user in users_list:
                    dom[user['_id']] = user
        
        return Domain(dom)
    
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
        sortedDomain = self.sortByMRV(unassignedVars)
        biggerDomain = list(filter(lambda x: len(self.vars[x].domain.domain) == len(self.vars[sortedDomain[0]].domain.domain), sortedDomain))
        if len(biggerDomain) > 1:
            return self.sortByDegree(biggerDomain)[0]
        return sortedDomain[0]

    # Sort the array of characters received according to the heuristic 'minimum remaining values'
    def sortByMRV(self, unassignedVars):
        sortedDomains = sorted(unassignedVars, key=lambda x: len(self.vars[x].domain.domain))
        return sortedDomains
    
    # Sort the array of characters received according to 'degree heuristic'
    def sortByDegree(self, biggers):
        vars = list(map(lambda x: self.vars[x].var, biggers))
        consNum = {var['_id']: self.getConsNum(var) for var in sorted(vars, key=lambda var: self.getConsNum(var))}
        return list(consNum.keys())
    
    # get var and returns the number of constraints in which the variable is involved
    def getConsNum(self, var):
        if 'Constraints' in var:
            return len(var['Constraints'])
        return 0
        
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
    

def run_csp(rolesAndUsers):
    # check
    start = datetime.datetime.now()
    csp_solver = csp(rolesAndUsers)
    end = datetime.datetime.now()
    print("time for constructor: ", end - start)
    # check
    start = datetime.datetime.now()
    res = csp_solver.backtracking(csp_solver.currentAssignment)
    end = datetime.datetime.now()
    print("time for backtracking: ", end - start)
    return res
 

        