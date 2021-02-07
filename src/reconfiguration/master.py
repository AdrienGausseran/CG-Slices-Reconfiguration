
import cplex
from cplex.exceptions import CplexSolverError
from Util.Util import checkStepOfReconfiguration

NBPATHTUSED = 5

class Master(object):

    #dictPath contain all the path
    #dictPathIntitiale contain only the path for the initial alloc and it contain it's value : dictPathIntitiale[s.id] = [(valPath1, path1), (valPath2, path2)]
    #dictPathIntitiale contain multiple path for each sfc only if we have fractional paths
    #The paths in dictPathIntitiale are in dictPath
    def __init__(self, nodes, links, functions, newSfc, listSfc, nbEtapes, beta, dictPath, integral):
        self.links = links	#links of the network
        self.nodes = nodes	#nodes of the network
        self.functions = functions	#the list of VNFs
        self.listSfc = listSfc
        self.nbEtapes = nbEtapes    #Number of time steps of the reconf
        self.beta = beta	#Price of the VNFs (see the paper and the readme for explanation)
        self.numcol = 0
        self.allPath = {}
        self.nbIter = 0
        self.integral = integral
        
        #The number of the row for each slice and each constraints for the duals
        self.rowOnePath = {}
        self.rowLinkCapacity = {}
        self.rowNodeCapacity = {}
        self.rowVnfUsed = {}
        
        self.numColToChangeUB = []
            
        
        self.prob = cplex.Cplex()
        
        self.prob.parameters.read.datacheck.set(0)
        
        self.prob.objective.set_sense(self.prob.objective.sense.minimize)
        self.prob.set_results_stream(None)
        self.numrow = 0
        
        #    ---------- ---------- ---------- First we build the model
    
        obj = []        #Objective
        ub = []         #Upper Bound
        rhs = []        #Result for each constraint
        sense = []      #Comparator for each constraint
        colname = []    #Name of the variables
        types = []      #type of the variables
        row = []        #Constraint
        #rowname=[]      #Name of the constraints
 
        self.frac = 'C'
                        
        self.nodesDC = {}
        for u in nodes:
            if(nodes[u][0]>0):
                self.nodesDC[u] = nodes[u]
            
        
        #And we create the variables for isUse
        #isUse = Omega in the paper
        for u in self.nodesDC:
            self.rowVnfUsed[u] = {}
            for f in self.nodesDC[u][1]:
                self.rowVnfUsed[u][f] = {}
                colname.append("isUse,{},{}".format(u,f))
                obj.append(beta)
                ub.append(cplex.infinity)
                types.append(self.frac)
                self.numColToChangeUB.append(self.numcol)
                self.numcol += 1
        self.lastColUsed = self.numcol
        
        self.initialPath = {}                
        #Variables for the paths used
        for s in listSfc:
            self.initialPath[s.id] = []
            self.rowOnePath[s.id] = []
            self.allPath[s.id] = []
            for t in range(self.nbEtapes+1):
                self.allPath[s.id].append([])
                self.initialPath[s.id].append([])
                for p in dictPath[s.id]:
                    #we create  the variable for the first path
                    colname.append("p,{},{},{}".format(s.id,p.num, t))
                    if t == self.nbEtapes:
                        tmp = 0
                        for l in p.nbLinks:
                            tmp += p.nbLinks[l]
                        for f in functions:
                            if f in s.functions:
                                self.rowVnfUsed[u][f][s.id] = -1
                        obj.append(tmp * s.bd)
                    else:
                        obj.append(0)
                    self.allPath[s.id][t].append((p, self.numcol))
                    self.initialPath[s.id][t].append(self.numcol)
                    
                    
                    ub.append(cplex.infinity)
                    types.append(self.frac)
                    self.numColToChangeUB.append(self.numcol)
                    self.numcol += 1
                    
        #Variables integrity between time step
        for s in listSfc:
            for t in range(1, self.nbEtapes+1):
                for p in dictPath[s.id]:
                    #we create  the variable for the first path
                    colname.append("y_p,{},{},{}".format(s.id,p.num, t))
                    obj.append(0)
                    ub.append(cplex.infinity)
                    types.append(self.frac)
                    self.numColToChangeUB.append(self.numcol)
                    self.numcol += 1

        #Constraints for the initial state
        for s in listSfc:
            #if (s != newSfc):
            for i in range (len(dictPath[s.id])-1):
                row.append([["p,{},{},{}".format(s.id,dictPath[s.id][i].num, 0)],[1]])
                #rowname.append("Ini_{}".format(self.numrow))
                self.numrow+=1
                sense.append('E')
                rhs.append(1)
                

        #Constraints for integrity between time step
        #Constraint number 3 in the paper
        for s in listSfc:
            for p in dictPath[s.id]:
                for t in range(1, self.nbEtapes+1):
                    row.append([["y_p,{},{},{}".format(s.id,p.num, t),"p,{},{},{}".format(s.id,p.num, t)], [1,-1]])
                    #rowname.append("YT_{}".format(self.numrow))
                    self.numrow+=1
                    sense.append('G')
                    rhs.append(0)
                    row.append([["y_p,{},{},{}".format(s.id,p.num, t),"p,{},{},{}".format(s.id,p.num, t-1)], [1,-1]])
                    #rowname.append("YT-1_{}".format(self.numrow))
                    self.numrow+=1
                    sense.append('G')
                    rhs.append(0)
                    
        #Constraints for links capacity
        #Constraint number 5 in the paper
        for (u,v) in links:
            self.rowLinkCapacity[(u,v)] = []
            for t in range(1, self.nbEtapes+1):
                listVar = []
                listVal = []
                for s in listSfc:
                    for p in dictPath[s.id]:
                        if((u,v) in p.nbLinks):
                                listVar.append("y_p,{},{},{}".format(s.id,p.num, t))
                                listVal.append(p.nbLinks[(u,v)]*s.bd)
                row.append([listVar, listVal])
                #rowname.append("LCapa_{}".format(self.numrow))    
                self.rowLinkCapacity[(u,v)].append(self.numrow)  
                #rowname.append("c{}".format(numrow))    
                self.numrow+=1
                sense.append('L')
                rhs.append(links[(u,v)][0])       

        #Only one path by sfc
        #Constraint number 2 in the paper
        for s in listSfc:
            for t in range(self.nbEtapes+1):
                listVar = []
                listVal = []
                for p in dictPath[s.id]:
                    listVar.append("p,{},{},{}".format(s.id,p.num,t))
                    listVal.append(1)
                row.append([listVar, listVal])
                #rowname.append("OnePAth_{}".format(self.numrow)) 
                self.rowOnePath[s.id].append(self.numrow)
                #rowname.append("c{}".format(numrow))
                self.numrow+=1
                sense.append('E')
                rhs.append(1)
            
        #Constraints for nodes capacity
        #Constraint number 4 in the paper
        for u in self.nodesDC:
            self.rowNodeCapacity[u] = []
            for t in range(1, self.nbEtapes+1):
                listVar = []
                listVal = []
                for s in listSfc:
                    for p in dictPath[s.id]:
                        tmp = 0
                        for i in range(len(s.functions)):
                            if p.nodesUsed[i] == u:
                                tmp += functions[s.functions[i]]
                        if tmp > 0 :
                                listVar.append("y_p,{},{},{}".format(s.id,p.num, t))
                                listVal.append(s.bd*tmp)
                            
                row.append([listVar, listVal])
                #rowname.append("NCapa_{}".format(self.numrow)) 
                self.rowNodeCapacity[u].append(self.numrow)
                #rowname.append("c{}".format(numrow))
                self.numrow+=1
                sense.append('L')
                rhs.append(self.nodesDC[u][0])
        
        #Constraints for vnf Used
        #Constraint number 6 in the paper
        for u in self.nodesDC:    
            #For each vnf on the DC
            for f in self.nodesDC[u][1]:
                #For each sfc
                for s in listSfc:
                    index = []
                    for i in range(len(s.functions)):
                        #We save in wich layer the function is used by the sfc
                        if s.functions[i] == f:
                            index.append(i)
                    #If the function is used by the sfc
                    if not len(index) == 0:
                        for p in dictPath[s.id]:
                            ok = False
                            for i in index:
                                if p.nodesUsed[i] == u:
                                    ok = True
                            #If the path use the vnf
                            if ok:
                                row.append([["isUse,{},{}".format(u,f), "p,{},{},{}".format(s.id,p.num,self.nbEtapes)],[1,-1]])
                            else:
                                row.append([["isUse,{},{}".format(u,f)],[1]])
                            self.rowVnfUsed[u][f][s.id] = self.numrow
                            #rowname.append("isUse_{}".format(self.numrow)) 
                            self.numrow+=1
                            sense.append('G')
                            rhs.append(0)

        
        self.prob.variables.add(obj=obj, types=types, ub=ub, names=colname)
        self.prob.linear_constraints.add(lin_expr=row, senses=sense, rhs=rhs)   
          
            
    
    def solve(self, verbose = False):
        #Set the problem to be an LP, if not Cplex will do it as a MIP for unknowns reasons and we can't have the duals :'(
        self.prob.set_problem_type(0)
        self.prob.solve()
        #self.prob.write("master_{}.lp".format(self.nbIter))
        self.nbIter += 1
        
        #Optimal Infeasible
        if self.prob.solution.get_status() == 5:
            self.prob.solve()
            if self.prob.solution.get_status() != 1:
                infoError(self.prob.solution.get_status(), 2, self)
                print("Exit Master 2")
                exit()
        elif self.prob.solution.get_status() != 1:
            infoError(self.prob.solution.get_status(), 1, self)
            print("Exit Master 1")
            exit()
        
        if verbose:        
            print("        Master Reconf obj : {}".format(self.prob.solution.get_objective_value()))
                  
        return self.prob.solution.get_objective_value()   
    
        
    def solveOpt(self, timelimit = 1000):
        
            
        #Set the problem to be an ILP
        self.prob.set_problem_type(1)

        if self.integral:
           
            for i in range(self.prob.variables.get_num()):
                self.prob.variables.set_upper_bounds(i,1)
                self.prob.variables.set_types(i, 'B')
        else:
            for i in range(self.lastColUsed):
                self.prob.variables.set_types(i, 'B')
            for i in range(self.prob.variables.get_num()):
                self.prob.variables.set_upper_bounds(i,1)
                    
        
        self.prob.parameters.timelimit.set(timelimit)
        self.prob.parameters.mip.tolerances.mipgap.set(0.0001)
        self.prob.solve()
        print(self.prob.solution.get_objective_value())
    
    #addPath
    def addPath(self, path, sfc):     
        
        tmp = 0
        for l in path.nbLinks:
            tmp += path.nbLinks[l]
            
        numVarPath = []
        numVarPathY = []
               
        #We add the path variable and the Y_path variables
        for t in range(1,self.nbEtapes+1):
            self.allPath[sfc.id][t].append((path, self.numcol))
            
            if t < self.nbEtapes:
                self.prob.variables.add(obj=[0], types=[self.frac], ub=[cplex.infinity], names=["p,{},{},{}".format(sfc.id,path.num,t)])
            else:
                self.prob.variables.add(obj=[tmp * sfc.bd], types=[self.frac], ub=[cplex.infinity], names=["p,{},{},{}".format(sfc.id,path.num,t)])
            numVarPath.append(self.numcol)
            self.numColToChangeUB.append(self.numcol)
            self.numcol += 1
            self.prob.variables.add(obj=[0], types=[self.frac], ub=[cplex.infinity], names=["y_p,{},{},{}".format(sfc.id,path.num,t)])
            numVarPathY.append(self.numcol)
            self.numColToChangeUB.append(self.numcol)
            self.numcol += 1
                
        rhs = []        #Result for each constraint
        sense = []      #Comparator for each constraint
        row = []        #Constraint
                
        #We add constraints for integrity between time step
        #Constraint number 3 in the paper
        for t in range(1, self.nbEtapes+1):
            row.append([["y_p,{},{},{}".format(sfc.id,path.num, t),"p,{},{},{}".format(sfc.id,path.num, t)], [1,-1]])
            #rowname.append("YT_{}".format(self.numrow))
            self.numrow+=1
            sense.append('G')
            rhs.append(0)
            if t > 1:
                row.append([["y_p,{},{},{}".format(sfc.id,path.num, t),"p,{},{},{}".format(sfc.id,path.num, t-1)], [1,-1]])
                #rowname.append("YT-1_{}".format(self.numrow))
                self.numrow+=1
                sense.append('G')
                rhs.append(0)
            
        self.prob.linear_constraints.add(lin_expr=row, senses=sense, rhs=rhs)    
        

        #Updating the constraint for One path taken
        #Constraint number 2 in the paper
        for t in range(1,self.nbEtapes+1):
            self.prob.linear_constraints.set_coefficients(self.rowOnePath[sfc.id][t], numVarPath[t-1], 1)
        
        #Updating the constraint for links capacity
        #Constraint number 5 in the paper
        for (u,v) in path.nbLinks:
            for t in range(self.nbEtapes):
                self.prob.linear_constraints.set_coefficients(self.rowLinkCapacity[(u,v)][t], numVarPathY[t], (path.nbLinks[(u,v)]*sfc.bd))
        
        #Updating the constraint for nodes capacity and vnf deployment
        #Constraints number 4 and 6 in the paper
        dictTmpVnf = {}
        dictTmpCapa = {}
        for i in range(len(sfc.functions)):
            u = path.nodesUsed[i]
            f = sfc.functions[i]
            if u in dictTmpCapa:
                dictTmpCapa[u] += self.functions[f]
                dictTmpVnf[u].append(f)
            else:
                dictTmpCapa[u] = self.functions[f]
                dictTmpVnf[u] = [f]
        for u in dictTmpCapa:
            for t in range(self.nbEtapes):
                self.prob.linear_constraints.set_coefficients(self.rowNodeCapacity[u][t], numVarPathY[t], (dictTmpCapa[u]*sfc.bd))
            for f in dictTmpVnf[u]:
                self.prob.linear_constraints.set_coefficients(self.rowVnfUsed[u][f][sfc.id], numVarPath[self.nbEtapes-1], -1)

    
    def getDuals(self):
        duals = self.prob.solution.get_dual_values()
        
        return duals, self.rowOnePath, self.rowLinkCapacity, self.rowNodeCapacity, self.rowVnfUsed

    
    def getResult(self, checkSolution = False):
        
        pathUsed = {}
        dictPath = {}
        
        values = self.prob.solution.get_values()

        roundValue = 8
        if self.integral:
            roundValue = 0
            
        #CheckSolution is only used for testing
        if checkSolution :
            allocation = []
            for t in range(self.nbEtapes + 1):
                allocation.append({})
                for s in self.listSfc:
                    allocation[t][s.id] = {}
                    allocation[t][s.id]["link"] = []
                    allocation[t][s.id]["node"] = []
                    pathUsed[s.id] = []
                    dictPath[s.id] = []
                    
                    allocation[t][s.id]["link"].append({})
                    for i in range(len(s.functions)):
                        allocation[t][s.id]["link"].append({})
                        allocation[t][s.id]["node"].append({})
                        
                    for (path,num) in self.allPath[s.id][t]:
                        flow = round(values[num], roundValue)
                        if(flow > 0):
                            if t == self.nbEtapes :
                                pathUsed[s.id].append(path.num)
                                dictPath[s.id].append(path)
                            flow = round(values[num], roundValue)
                            for i in range(len(path.alloc["link"])):
                                for (u,v) in path.alloc["link"][i]:
                                    allocation[t][s.id]["link"][i][(u,v)] = allocation[t][s.id]["link"][i].get((u,v),0) + (path.alloc["link"][i][(u,v)]*flow)
                            for i in range(len(path.alloc["node"])):
                                for u in path.alloc["node"][i]:
                                    allocation[t][s.id]["node"][i][u] = allocation[t][s.id]["node"][i].get(u,0) + (path.alloc["node"][i][u]*flow)
            checkStepOfReconfiguration([self.listSfc], self.nodes, self.links, self.functions, allocation, self.nbEtapes)
            allocation = allocation[self.nbEtapes]

        else:
            allocation = {}
            for s in self.listSfc:
                allocation[s.id] = {}
                allocation[s.id]["link"] = []
                allocation[s.id]["node"] = []
                pathUsed[s.id] = []
                dictPath[s.id] = []
                
                allocation[s.id]["link"].append({})
                for i in range(len(s.functions)):
                    allocation[s.id]["link"].append({})
                    allocation[s.id]["node"].append({})
            
            
                for (path,num) in self.allPath[s.id][self.nbEtapes]:
                    flow = round(values[num], roundValue)
                    if(flow > 0):
                        #print(values[num])
                        #print(path.alloc)
                        pathUsed[s.id].append(path.num)
                        dictPath[s.id].append(path)
                        flow = round(values[num], roundValue)
                        for i in range(len(path.alloc["link"])):
                            for (u,v) in path.alloc["link"][i]:
                                allocation[s.id]["link"][i][(u,v)] = allocation[s.id]["link"][i].get((u,v),0) + (path.alloc["link"][i][(u,v)]*flow)
                        for i in range(len(path.alloc["node"])):
                            for u in path.alloc["node"][i]:
                                allocation[s.id]["node"][i][u] = allocation[s.id]["node"][i].get(u,0) + (path.alloc["node"][i][u]*flow)
        self.prob.end()
        return allocation, pathUsed, dictPath
        
def byTime(elem):
    return elem.timeUsed
def bySecond(elem):
    return elem[1]


def infoError(status, cas, master):
    print("No solution available for the master")
    print("Cas {}".format(cas))
    print("Status : {}".format(status))
    print("Initial")
    for s in master.listSfc:
        print("{}    {}".format(s.id, master.initialPath[s.id][master.nbEtapes]))
    print("All path")
    for s in master.listSfc:
        print("{}    {}".format(s.id, master.allPath[s.id][master.nbEtapes]))
    master.prob.write("prob.lp")
    
