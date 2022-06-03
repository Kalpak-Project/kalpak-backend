from app import getUsersOrderedRoles, getFreeUsers

class csp:
    
    def __init__(self):
        self.OrderedRolesLists = getUsersOrderedRoles() # dict of {userId: orderedRolesList}
        self.freeUsers = self.getRemovedIrrelevantFields() # list of dicts of {userId: userDoc}
        self.freeRoles = [role['Role'] for role in getFreeUsers()]
        self.currentAssignment = {}
        self.score = 0
        self.maxScoreAssignment = {} # dict of {score: assignment}
    
    
    def getRemovedIrrelevantFields(self):
        free = getFreeUsers()[0]['User']
        for user in free:
            user.pop('Family Name')
            user.pop('Private Name')
            user.pop('Personal ID')
        return free
    
    
        
aaa = csp()
        
        