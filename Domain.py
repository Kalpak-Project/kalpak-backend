# Class for the domain of each variable
from copy import copy, deepcopy


class Domain:

    def __init__(self, domain):
        self.domain = domain
        self.original = deepcopy(domain)

    def addToDomain(self, value, valDoc):
        if value in self.original:
            self.domain[value] = valDoc

    def removeFromDomain(self, value):
        if value in self.domain:
            del self.domain[value]

    def getNextFreeDomain(self):
        return self.domain[0]

    def getDomainDict(self):
        return self.domain
