

class SFC(object):

    def __init__(self, ident, bandwithDemand, srcNode, dstNode, listFunctions, latencyMax, timeOfDeath):
        self.id = ident
        self.bd = bandwithDemand
        self.src = srcNode
        self.dst = dstNode
        self.functions = listFunctions
        self.timeOfDeath = timeOfDeath
        self.duration = 0
        self.latencyMax = latencyMax
        
    def setTimeOfDeath(self, t):
        self.timeOfDeath = t
        
    def __str__(self):
        fct = str(self.functions)
        fct = fct.replace("'", "")
        fct = fct.replace(" ", "")
        fct = fct.replace("[", "")
        fct = fct.replace("]", "")
        return str(self.id)+":"+str(self.bd)+" "+str(self.src)+","+str(self.dst)+" "+fct+" "+ str(self.latencyMax)+" "+ str(self.timeOfDeath)
    
    def __repr__(self):
        function = ""
        for f in self.functions:
            function+=f+","
        function = function[:-1]
        return str(self.id)+":"+str(self.bd)+" "+str(self.src)+","+str(self.dst)+" "+function+" "+ str(self.timeOfDeath)
    