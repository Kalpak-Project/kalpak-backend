from abc import ABC, abstractmethod
from app import getHistory


# Abstract class for constraints
class Constraint(ABC):

    @abstractmethod
    def isConsist(self, assignment):
        pass

class TrainingRequired(Constraint):
    
    def __init__(self, consId, requirement):
        self.consId = consId
        self.requirement = requirement
        
    def isConsist(self, assignment, vars, values):
        for ass in assignment:
            if 'Constraints' in vars[ass].var:
                if self.consId in vars[ass].var['Constraints']:
                    strUserID = assignment[ass]
                    user_roles = getHistory(strUserID)
                    roleIdList = list(map(lambda role: role['Role ID'], user_roles))
                    if self.requirement not in roleIdList:
                        # vars[ass].getDomain().removeFromDomain(assignment[ass])
                        return False        
        return True


# Class for constraint Type:
# The values of the variables must be different from each other
class AllDifferent(Constraint):

    def __init__(self, vars):
        self.vars = vars

    def isConsist(self, assignment, vars, values):
        filteredVars = list(filter(lambda x: (x in assignment), self.vars))
        values = list(map(lambda x: assignment[x], filteredVars))
        valuesSet = set(values)
        return len(valuesSet) == len(values)            
                

            
