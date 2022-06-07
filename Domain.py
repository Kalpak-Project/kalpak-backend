# Class for the domain of each variable
class Domain:

    def __init__(self, domain):
        self.domain = domain

    def addToDomain(self, value, valDoc):
        self.domain[value] = valDoc

    def removeFromDomain(self, value):
        if value in self.domain:
            del self.domain[value]

    def getNextFreeDomain(self):
        return self.domain[0]

    def getDomainDict(self):
        return self.domain
