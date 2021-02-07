import cplex
from cplex.exceptions import CplexSolverError

from Util import Util
from Util import pathGC

class SubProb(object):

    def __init__(self, nodes, links, functions, sfc, beta, nbSteps = -1):
        self.nodes = nodes
        self.links = links
        self.functions = functions
        self.sfc = sfc
        self.beta = beta
        self.num = 0
        self.keyAllPath = []
        self.nbSteps = nbSteps
        
        #number of the variables for changing the objective with the duals
        self.colObjPath = 0
        self.colObjLink = 0
        self.colObjNode = []
        self.colObjVNF = []
        
        self.prob = cplex.Cplex()
        self.prob.parameters.read.datacheck.set(0)
        
        self.prob.objective.set_sense(self.prob.objective.sense.minimize)
        self.prob.set_results_stream(None)
        
        #    ---------- ---------- ---------- First we build the model
        
        obj = []        #Objective
        ub = []         #Upper Bound
        rhs = []        #Result for each constraint
        sense = []      #Comparator for each constraint
        colname = []    #Name of the variables
        types = []      #type of the variables
        row = []        #Constraint
        #rowname=[]      #Name of the constraints
        numrow = 0
        numcol = 0
        
        frac = 'C'
                        
        self.nodesDC = {}
        for u in self.nodes:
            if(nodes[u][0]>0):
                self.nodesDC[u] = self.nodes[u]
                
        #Variable only used for the objective : update by the dual
        colname.append("dualPath")
        obj.append(0)
        ub.append(1)
        types.append(frac)
        numcol += 1
        row.append([["dualPath"], [1]])
        #rowname.append("c{}".format(numrow))
        numrow+=1
        sense.append('E')
        rhs.append(1)
        
        
        #And we create the variables for isUse        
        for f in self.sfc.functions:
            self.colObjVNF.append(numcol)
            for u in self.nodesDC:
                if f in self.nodesDC[u][1]:
                    colname.append("isUse,{},{}".format(u,f))
                    obj.append(beta)
                    ub.append(1)
                    types.append(frac)
                    numcol += 1
        
        
        #For each layer of the slice
        for i in range(len(sfc.functions)):
            self.colObjNode.append(numcol)
            #for each self.nodes
            for u in self.nodesDC:
                if(sfc.functions[i] in self.nodes[u][1]):
                    #We create a variable to know if we use a node for an option
                    colname.append("use,{},{}".format(i,u))
                    obj.append(0)
                    ub.append(1)
                    types.append(frac)
                    numcol +=1
                        
        self.colObjLink = numcol
        #For each layer of the slice
        for i in range(len(sfc.functions)+1):
            #for each arc we create a lp variable
            for (u,v) in self.links:
                colname.append("x,{},{},{}".format(i,u,v))
                obj.append(sfc.bd)
                ub.append(1)
                types.append(frac)
                numcol+=1
                    
        #Flow conservation constraints
        #Constraints number 8, 9, 10 in the paper
        for i in range(len(sfc.functions)+1):
            for u in self.nodes:
                listVar = []
                listVal = []
                #If the node is a datacenter
                if(nodes[u][0]>0):
                    #If it's the source layer
                    #Constraint number 8 in the paper
                    if(i==0):
                        if(sfc.functions[i] in self.nodes[u][1]):
                            listVar.append("use,{},{}".format(i,u))
                            listVal.append(1)
                        for (n,v) in self.links :
                            if(u==n):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(1)
                            elif(u==v):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(-1)
                        row.append([listVar, listVal])
                        #rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('E')
                        #If u is the source node
                        if (u==sfc.src):
                            rhs.append(1)
                        else:
                            rhs.append(0)
                        
                    #If it's the last layer
                    #Constraint number 9 in the paper
                    elif(i==(len(sfc.functions))):
                        if(sfc.functions[i-1] in self.nodes[u][1]):
                            listVar.append("use,{},{}".format(i-1,u))
                            listVal.append(-1)
                        for (n,v) in self.links :
                            if(u==n):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(1)
                            elif(u==v):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(-1)
                        row.append([listVar, listVal])
                        #rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('E')
                        #If u is the destination node
                        if (u==sfc.dst):
                            rhs.append(-1)
                        else:
                            rhs.append(0)
                            
                    #If it's in a middle layer
                    #Constraint number 10 in the paper
                    else :
                        if(sfc.functions[i] in self.nodes[u][1]):
                            listVar.append("use,{},{}".format(i,u))
                            listVal.append(1)
                        if(sfc.functions[i-1] in self.nodes[u][1]):
                            listVar.append("use,{},{}".format(i-1,u))
                            listVal.append(-1)
                        for (n,v) in self.links :
                            if(u==n):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(1)
                            elif(u==v):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(-1)
                        row.append([listVar, listVal])
                        #rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('E')
                        rhs.append(0)
                    
                #If the node is not a datacenter
                else :
                    
                    #If it's the source layer
                    #Constraint number 8 in the paper
                    if(i==0):
                        for (n,v) in self.links :
                            if(u==n):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(1)
                            elif(u==v):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(-1)
                        row.append([listVar, listVal])
                        #rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('E')
                        #If u is the source node
                        if (u==sfc.src):
                            rhs.append(1)
                        else:
                            rhs.append(0)
                        
                    #If it's the last layer
                    #Constraint number 9 in the paper
                    elif(i==(len(sfc.functions))):
                        for (n,v) in self.links :
                            if(u==n):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(1)
                            elif(u==v):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(-1)
                        row.append([listVar, listVal])
                        #rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('E')
                        #If u is the destination node
                        if (u==sfc.dst):
                            rhs.append(-1)
                        else:
                            rhs.append(0)
                            
                    #If it's in a middle layer
                    #Constraint number 10 in the paper
                    else :
                        for (n,v) in self.links :
                            if(u==n):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(1)
                            elif(u==v):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(-1)
                        row.append([listVar, listVal])
                        #rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('E')
                        rhs.append(0)
            
        #Only one node can be use as a function by slice, by layer
        for i in range(len(sfc.functions)):
            listVar = []
            listVal = []
            for u in self.nodesDC:
                if(sfc.functions[i] in self.nodes[u][1]):
                    listVar.append("use,{},{}".format(i,u))
                    listVal.append(1)
            row.append([listVar, listVal])
            #rowname.append("c{}".format(numrow))
            numrow+=1
            sense.append('E')
            rhs.append(1)
            
        listVar = []
        listVal = []
        #Latency constraint
        #Constraint number 11 in the paper
        for i in range(len(sfc.functions)+1):
            for (u,v) in self.links:
                listVar.append("x,{},{},{}".format(i,u,v))
                listVal.append(links[(u,v)][1])
        row.append([listVar, listVal])
        numrow+=1
        sense.append('L')
        rhs.append(sfc.latencyMax)
            
            
        #The constraint for isUse
        #Constraint number 12 in the paper
        for u in self.nodesDC:
            for i in range(len(sfc.functions)):
                f = sfc.functions[i]
                if f in self.nodes[u][1]:
                    row.append([["isUse,{},{}".format(u,f), "use,{},{}".format(i,u)], [1, -1]])
                    #rowname.append("c{}".format(numrow))
                    numrow+=1
                    sense.append('G')
                    rhs.append(0)
        
        self.prob.variables.add(obj=obj, types=types, ub=ub, names=colname)
        self.prob.linear_constraints.add(lin_expr=row, senses=sense, rhs=rhs)

    def updateObjective(self, duals, constraintOnePath, constraintLinkCapacity, constraintNodeCapacity, constraintVnfUsed, step = None):

        #Updating  with constraintOnePath
        dual = duals[constraintOnePath]
        """if dual < 0:
            dual = -dual"""
        self.prob.objective.set_linear(self.colObjPath, - dual)
        
        #Updating  with constraintNodeCapacity
        for i in range(len(self.sfc.functions)):
            numcol = self.colObjNode[i]
            for u in self.nodesDC:
                if(self.sfc.functions[i] in self.nodes[u][1]):
                    dual = duals[constraintNodeCapacity[u][step-1]]
                    #Normally the duals must be >= 0, you ensure this by putting your master in standard form
                    #This was not done at first and I forgot to do it afterwards
                    #The two lines were here temporarily. If the master is in standard form you don't need them
                    if dual < 0:
                        dual = -dual
                    self.prob.objective.set_linear(numcol, dual * self.sfc.bd * self.functions[self.sfc.functions[i]])
                    numcol+=1
                    
                    
        #Updating  with constraintLinkCapacity
        numcol = self.colObjLink
        for i in range(len(self.sfc.functions)+1):
            for (u,v) in self.links:
                dual = duals[constraintLinkCapacity[(u,v)][step-1]]
                #Normally the duals must be >= 0, you ensure this by putting your master in standard form
                #This was not done at first and I forgot to do it afterwards
                #The two lines were here temporarily. If the master is in standard form you don't need them
                if dual < 0:
                    dual = - dual
                self.prob.objective.set_linear(numcol, self.sfc.bd + dual * self.sfc.bd)
                numcol+=1
                
        
        #Updating  with constraintVnfUsed      
        for i in range(len(self.sfc.functions)):
            f = self.sfc.functions[i]
            numcol = self.colObjVNF[i]
            for u in self.nodesDC:
                if f in self.nodesDC[u][1]:
                    dual = duals[constraintVnfUsed[u][f][self.sfc.id]]
                    #Normally the duals must be >= 0, you ensure this by putting your master in standard form
                    #This was not done at first and I forgot to do it afterwards
                    #The two lines were here temporarily. If the master is in standard form you don't need them
                    if dual < 0:
                        dual = - dual
                    if not step == None:
                        if not step == self.nbSteps:
                            dual = 0
                    self.prob.objective.set_linear(numcol, dual * self.beta)
                    numcol+=1

    def solve(self, step = None):
              
        try:
            self.prob.set_problem_type(0)
            self.prob.parameters.simplex.tolerances.markowitz.set(0.1)
            self.prob.solve()
        except CplexSolverError:
            print("Exception raised during solve")
            return

        if self.prob.solution.get_status() != 1:
            print("No solution available")
            return 100, None
        
        rc = round(self.prob.solution.get_objective_value(),6)


        listPath = []
        path = None
        #We only take the path if the reduce cost is < 0
        if rc < 0:
            valsVar = self.prob.solution.get_values()
            namesVar = self.prob.variables.get_names()
            alloc={"link" : [], "node" : []}
            alloc["link"].append({})
            for i in range(len(self.sfc.functions)):
                alloc["link"].append({})
                alloc["node"].append({})
            
            for i in range(len(valsVar)):
                if(valsVar[i] < 0):
                    print("        {}    {}".format(namesVar[i], valsVar[i]))
                if(valsVar[i] > 0):
                    if namesVar[i][0] == "u":
                        tmp = namesVar[i].split(",")
                        layer = int(float(tmp[1]))
                        alloc["node"][layer][tmp[2]] = valsVar[i]
                    if namesVar[i][0] == "x":
                        tmp = namesVar[i].split(",")
                        layer = int(float(tmp[1]))
                        alloc["link"][layer][(tmp[2], tmp[3])] = valsVar[i]
                        
            #If the path is not a path (integral) but is a flow, we re-compute the sub in ILP
            if Util.isSinglePath(alloc):
                path = pathGC.fromAllocTopathGC(alloc, self.num)
                self.num +=1
                self.keyAllPath.append(path.key)
            else:
                return self.solveILP(step)
                
                        
        return rc, path
    
    def solveILP(self, step = None):
           
        for i in range(self.prob.variables.get_num()):
            self.prob.variables.set_types(i, 'B')
            
        #Set the problem to be an ILP
        self.prob.set_problem_type(1)
        
        try:
            self.prob.solve()
        except CplexSolverError:
            print("Exception raised during solve")
            return

        if self.prob.solution.get_status() != 101 and self.prob.solution.get_status() != 102 :
            print("No solution available")
            return 100, None
        rc = round(self.prob.solution.get_objective_value(),6)
        valsVar = self.prob.solution.get_values()
        namesVar = self.prob.variables.get_names()

        path = None
        if rc < 0:
            alloc = Util.recreateOneAllocGC(self.nodes, self.links, self.sfc, namesVar, valsVar)        
            path = pathGC.fromAllocTopathGC(alloc, self.num)
            if not path.key in self.keyAllPath:
                self.num +=1
                self.keyAllPath.append(path.key)
            else:
                rc = 100
                
        for i in range(self.prob.variables.get_num()):
            self.prob.variables.set_types(i, 'C')
        
        return rc, path

    
        
    #Used when the first path is already computed, but outside the subproblem
    def addPath(self, listPath):
        for path in listPath:
            self.keyAllPath.append(path.key)
            self.num +=1
            
    def end(self):
        self.prob.end()
        