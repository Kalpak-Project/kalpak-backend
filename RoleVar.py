class RoleVar:
    
    def __init__(self, var, domain):
        self.id = str(var['_id'])
        self.var = var
        self.domain = domain
    
    def getId(self):
        return self.id
    
    def getVar(self):
        return self.var

    def getDomain(self):
        return self.domain
