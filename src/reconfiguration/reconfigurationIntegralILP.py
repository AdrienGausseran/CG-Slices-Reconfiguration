import collections

from Util import Util

import cplex


#Compute the differents state of a Basic reconfiguration
#	nodes : nodes of the network
#	arcs : links of the network
#	listSlice : the list of the slices to reconfigure
#	functions : the list of VNFs
#	nbEtapes means number of steps : it's the number of step we want for our reconfiguration : more step = potentially better performances but more time to compute
#	etapeIntitiale means Initial step : it's the current allocation that we need to reconfigure
#	beta : price of the VNFs (see the paper and the readme for explanation)
#	optimalNeeded : Boolean, if True, will return the optimal reconfiguration if it's possible in the given time. It's better to used False with a short timeLimit
#	timeLimit : limit in seconds
#	checkSolution : used for testing. If True the reconfiguration will be check to be sure there is no bug
def reconfigure(nodes, arcs, listSlice, functions, nbEtapes, etapeIntitiale, beta, verbose = False, optimalNeeded = True, timeLimit = 1000, checkSolution = False):
    
    prob = cplex.Cplex()
    prob.parameters.read.datacheck.set(0)
    prob.objective.set_sense(prob.objective.sense.minimize)
    prob.set_results_stream(None)
    
    ub = []         #Upper Bound
    obj = []        #Objective
    rhs = []        #Result for each constraint
    sense = []      #Comparator for each constraint
    colname = []    #Name of the variables
    types = []      #type of the variables
    row = []        #Constraint
    rowname=[]      #Name of the constraints
    numrow = 1

                    
    nodesDC = collections.OrderedDict()
    for u in nodes:
        if(nodes[u][0]>0):
            nodesDC[u] = nodes[u]
                    

    #We create a matrix to know which option a node can have
    #And we create the variables for isUse
    for u in nodesDC:
        for f in functions:
            colname.append("isUse,{},{}".format(u,f))
            obj.append(beta)
            ub.append(1)
            types.append('B')
                
    #print("A {}".format(numrow))
    #For each slice
    for slice in listSlice:
        for s in slice:
            #For each steps
            for t in range(nbEtapes+1):
                #Omega variable, to know if the allocation has changed between two time steps
                if t > 0:
                    colname.append("om,{},{}".format(s.id, t))
                    ub.append(1)
                    types.append('B')
                    obj.append(0)
                #For each layer of the slice
                for i in range(len(s.functions)+1):
                    #for each nodes
                    for u in nodesDC:
                        if(nodes[u][0]>0):
                            if(not i == len(s.functions)):
                                if(s.functions[i] in nodes[u][1]):
                                    #We create a variable to know if we use a node for an option
                                    colname.append("use,{},{},{},{}".format(s.id, t, i, u))
                                    ub.append(1)
                                    types.append("I")
                                    obj.append(0)
                                    if t > 0:
                                        colname.append("ruse,{},{},{},{}".format(s.id, t, i, u))
                                        ub.append(2)
                                        types.append("I")
                                        obj.append(0)
                
                    #for each arc we create a lp variable
                    for (u,v) in arcs:
                        colname.append("x,{},{},{},{},{}".format(s.id, t, i, u, v))
                        ub.append(1)
                        types.append("B")
                        #If it's the last step, the bandwidth is part of the objective
                        if(t == nbEtapes):
                            obj.append(s.bd)
                        else:
                            obj.append(0)
                        if t > 0:
                            colname.append("y,{},{},{},{},{}".format(s.id, t, i, u, v))
                            ub.append(2)
                            types.append("I")
                            obj.append(0)

                        
    #print("B {}".format(numrow))
    #Constraints for the initial  state
    for slice in listSlice:
        for s in slice:
            #For each layer of the slice
            for i in range(len(s.functions)+1):
                if(not i == len(s.functions)):
                    for u in nodesDC:
                        if(s.functions[i] in nodes[u][1]):
                            row.append([["use,{},{},{},{}".format(s.id, 0, i, u)],[1]])
                            rowname.append("c{}".format(numrow))
                            numrow+=1
                            sense.append('E')
                            rhs.append(etapeIntitiale[s.id]["node"][i].get(u,0))
                for (u,v) in arcs:
                    row.append([["x,{},{},{},{},{}".format(s.id, 0, i, u, v)], [1]])
                    rowname.append("c{}".format(numrow))
                    numrow+=1
                    sense.append('E')
                    rhs.append(etapeIntitiale[s.id]["link"][i].get((u,v),0))
                    
    #print("C {}".format(numrow))
    #Constraints of y, ruse and omega
    for slice in listSlice:
        for s in slice:
            for t in range(1, nbEtapes+1):
                #For each layer of the slice
                for i in range(len(s.functions)+1):
                    for (u,v) in arcs:
                        row.append([["y,{},{},{},{},{}".format(s.id, t, i, u, v),"x,{},{},{},{},{}".format(s.id, t, i, u, v)], [1,-1]])
                        rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('G')
                        rhs.append(0)
                        row.append([["y,{},{},{},{},{}".format(s.id, t, i, u, v),"x,{},{},{},{},{}".format(s.id, t-1, i, u, v)], [1,-1]])
                        rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('G')
                        rhs.append(0)
                        row.append([["y,{},{},{},{},{}".format(s.id, t, i, u, v),"x,{},{},{},{},{}".format(s.id, t-1, i, u, v),"x,{},{},{},{},{}".format(s.id, t, i, u, v), "om,{},{}".format(s.id, t)], [1,-1,-1,1]])
                        rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('G')
                        rhs.append(0)
                        
                        #Omega take 1 if there is no change, 0 otherwise
                        row.append([["om,{},{}".format(s.id, t),"x,{},{},{},{},{}".format(s.id, t-1, i, u, v),"x,{},{},{},{},{}".format(s.id, t, i, u, v)], [1,1,-1]])
                        rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('L')
                        rhs.append(1)
                        row.append([["om,{},{}".format(s.id, t),"x,{},{},{},{},{}".format(s.id, t-1, i, u, v),"x,{},{},{},{},{}".format(s.id, t, i, u, v)], [1,-1,1]])
                        rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('L')
                        rhs.append(1)
                        
                for i in range(len(s.functions)):
                    for u in nodesDC:
                        if(s.functions[i] in nodes[u][1]):
                            row.append([["ruse,{},{},{},{}".format(s.id, t, i, u),"use,{},{},{},{}".format(s.id, t, i, u)], [1,-1]])
                            rowname.append("c{}".format(numrow))
                            numrow+=1
                            sense.append('G')
                            rhs.append(0)
                            row.append([["ruse,{},{},{},{}".format(s.id, t, i, u),"use,{},{},{},{}".format(s.id, t-1, i, u)], [1,-1]])
                            rowname.append("c{}".format(numrow))
                            numrow+=1
                            sense.append('G')
                            rhs.append(0)
                            row.append([["ruse,{},{},{},{}".format(s.id, t, i, u),"use,{},{},{},{}".format(s.id, t-1, i, u),"use,{},{},{},{}".format(s.id, t, i, u), "om,{},{}".format(s.id, t)], [1,-1,-1,1]])
                            rowname.append("c{}".format(numrow))
                            numrow+=1
                            sense.append('G')
                            rhs.append(0)
                            
                            #Omega take 1 if there is no change, 0 otherwise
                            row.append([["om,{},{}".format(s.id, t),"use,{},{},{},{}".format(s.id, t-1, i, u),"use,{},{},{},{}".format(s.id, t, i, u)], [1,1,-1]])
                            rowname.append("c{}".format(numrow))
                            numrow+=1
                            sense.append('L')
                            rhs.append(1)
                            row.append([["om,{},{}".format(s.id, t),"use,{},{},{},{}".format(s.id, t-1, i, u),"use,{},{},{},{}".format(s.id, t, i, u)], [1,-1,1]])
                            rowname.append("c{}".format(numrow))
                            numrow+=1
                            sense.append('L')
                            rhs.append(1)

    #print("D {}".format(numrow))
    #Flow conservation constraints
    for slice in listSlice:
        for s in slice:
            for t in range(0, nbEtapes+1):
                for i in range(len(s.functions)+1):
                    for u in nodes:
                        listVar = []
                        listVal = []
                        
                        #If the node is a datacenter
                        if(nodes[u][0]>0):    
                            #If it's the source layer        self.nodes = nodes
                            if(i==0):
                                if(s.functions[i] in nodes[u][1]):
                                    listVar.append("use,{},{},{},{}".format(s.id, t, i, u))
                                    listVal.append(1)
                                for (n,v) in arcs :
                                    if(n==u):
                                        listVar.append("x,{},{},{},{},{}".format(s.id, t, i, u, v))
                                        listVal.append(1)
                                for (v,n) in arcs :
                                    if(n==u):
                                        listVar.append("x,{},{},{},{},{}".format(s.id, t, i, v, u))
                                        listVal.append(-1)
                                row.append([listVar, listVal])
                                rowname.append("c{}".format(numrow))
                                numrow+=1
                                sense.append('E')
                                #If u is the source node
                                if (u==s.src):
                                    rhs.append(1)
                                else:
                                    rhs.append(0)
                                
                            #If it's the last layer
                            elif(i==(len(s.functions))):
                                if(s.functions[i-1] in nodes[u][1]):
                                    listVar.append("use,{},{},{},{}".format(s.id, t, i-1, u))
                                    listVal.append(-1)
                                for (n,v) in arcs :
                                    if(n==u):
                                        listVar.append("x,{},{},{},{},{}".format(s.id, t, i, u, v))
                                        listVal.append(1)
                                for (v,n) in arcs :
                                    if(n==u):
                                        listVar.append("x,{},{},{},{},{}".format(s.id, t, i, v, u))
                                        listVal.append(-1)
                                row.append([listVar, listVal])
                                rowname.append("c{}".format(numrow))
                                numrow+=1
                                sense.append('E')
                                #If u is the destination node
                                if (u==s.dst):
                                    rhs.append(-1)
                                else:
                                    rhs.append(0)
                                    
                            #If it's in a middle layer
                            else :
                                if(s.functions[i] in nodes[u][1]):
                                    listVar.append("use,{},{},{},{}".format(s.id, t, i, u))
                                    listVal.append(1)
                                if(s.functions[i-1] in nodes[u][1]):
                                    listVar.append("use,{},{},{},{}".format(s.id, t, i-1, u))
                                    listVal.append(-1)
                                for (n,v) in arcs :
                                    if(n==u):
                                        listVar.append("x,{},{},{},{},{}".format(s.id, t, i, u, v))
                                        listVal.append(1)
                                for (v,n) in arcs :
                                    if(n==u):
                                        listVar.append("x,{},{},{},{},{}".format(s.id, t, i, v, u))
                                        listVal.append(-1)
                                row.append([listVar, listVal])
                                rowname.append("c{}".format(numrow))
                                numrow+=1
                                sense.append('E')
                                rhs.append(0)
                                
                        #If the node is not a datacenter
                        else :
                            #If it's the source layer
                            if(i==0):
                                for (n,v) in arcs :
                                    if(n==u):
                                        listVar.append("x,{},{},{},{},{}".format(s.id, t, i, u, v))
                                        listVal.append(1)
                                for (v,n) in arcs :
                                    if(n==u):
                                        listVar.append("x,{},{},{},{},{}".format(s.id, t, i, v, u))
                                        listVal.append(-1)
                                row.append([listVar, listVal])
                                rowname.append("c{}".format(numrow))
                                numrow+=1
                                sense.append('E')
                                #If u is the source node
                                if (u==s.src):
                                    rhs.append(1)
                                else:
                                    rhs.append(0)
                                
                            #If it's the last layer
                            elif(i==(len(s.functions))):
                                for (n,v) in arcs :
                                    if(n==u):
                                        listVar.append("x,{},{},{},{},{}".format(s.id, t, i, u, v))
                                        listVal.append(1)
                                for (v,n) in arcs :
                                    if(n==u):
                                        listVar.append("x,{},{},{},{},{}".format(s.id, t, i, v, u))
                                        listVal.append(-1)
                                row.append([listVar, listVal])
                                rowname.append("c{}".format(numrow))
                                numrow+=1
                                sense.append('E')
                                #If u is the destination node
                                if (u==s.dst):
                                    rhs.append(-1)
                                else:
                                    rhs.append(0)
                                    
                            #If it's in a middle layer
                            else :
                                for (n,v) in arcs :
                                    if(n==u):
                                        listVar.append("x,{},{},{},{},{}".format(s.id, t, i, u, v))
                                        listVal.append(1)
                                for (v,n) in arcs :
                                    if(n==u):
                                        listVar.append("x,{},{},{},{},{}".format(s.id, t, i, v, u))
                                        listVal.append(-1)
                                row.append([listVar, listVal])
                                rowname.append("c{}".format(numrow))
                                numrow+=1
                                sense.append('E')
                                rhs.append(0)

     
    #We start at 1 not 0 because the step 0 is a parameter
    for t in range(1, nbEtapes+1):   
                                                         
        #Constraints for links capacity
        for (u,v) in arcs:
            listVar = []
            listVal = []
            for slice in listSlice:
                for s in slice:
                    for i in range(len(s.functions)+1):
                        listVar.append("y,{},{},{},{},{}".format(s.id, t, i, u, v))
                        listVal.append(s.bd)
            row.append([listVar, listVal])
            rowname.append("c{}".format(numrow))
            numrow+=1
            sense.append('L')
            rhs.append(arcs[(u,v)][0])
            
        for slice in listSlice:
            for s in slice:
                #Only one node can be use as a function by slice, by layer
                for i in range(len(s.functions)):
                    listVar = []
                    listVal = []
                    for u in nodesDC:
                        if(s.functions[i] in nodes[u][1]):
                            listVar.append("use,{},{},{},{}".format(s.id, t, i, u))
                            listVal.append(1)
                    row.append([listVar, listVal])
                    rowname.append("c{}".format(numrow))
                    numrow+=1
                    sense.append('E')
                    rhs.append(1)
                    
                listVar = []
                listVal = []
                #Latency constraint
                for i in range(len(s.functions)+1):
                    for (u,v) in arcs:
                        listVar.append("x,{},{},{},{},{}".format(s.id, t, i, u, v))
                        listVal.append(arcs[(u,v)][1])
                row.append([listVar, listVal])
                rowname.append("c{}".format(numrow))
                numrow+=1
                sense.append('L')
                rhs.append(s.latencyMax)
                
        
        #Constraints for nodes capacity
        for u in nodesDC:
            listVar = []
            listVal = []
            
            for slice in listSlice:
                for s in slice:
                    for i in range(len(s.functions)):
                        if(s.functions[i] in nodes[u][1]):
                            listVar.append("ruse,{},{},{},{}".format(s.id, t, i, u))
                            val = s.bd*functions[s.functions[i]]
                            listVal.append(val)
            row.append([listVar, listVal])
            rowname.append("c{}".format(numrow))
            numrow+=1
            sense.append('L')
            rhs.append(nodes[u][0])       
            
    #print("F {}".format(numrow)) 
    #The constraint for isUse  
    for u in nodesDC:
        for f in functions:
            for slice in listSlice:
                for s in slice:
                    for i in range(len(s.functions)):
                        if(s.functions[i] == f):
                            if(f in nodes[u][1]):
                                row.append([["isUse,{},{}".format(u,f), "use,{},{},{},{}".format(s.id,nbEtapes,i,u)], [1, -1]])
                                rowname.append("c{}".format(numrow))
                                numrow+=1
                                sense.append('G')
                                rhs.append(0)  
            

    #print("{} constraints".format(numrow))
    prob.variables.add(obj=obj, types=types, ub=ub, names=colname)
    prob.linear_constraints.add(lin_expr=row, senses=sense, rhs=rhs, names=rowname)
    
    prob.parameters.timelimit.set(timeLimit)
    prob.parameters.mip.tolerances.mipgap.set(0.0001)

    allocation = collections.OrderedDict()
    
    try:
        prob.solve() 
        
    except :
        prob.end()
        # infeasible
        return False, {}, allocation
    
    if prob.solution.get_status() != 101 and prob.solution.get_status() != 102:
        #print("No solution available")
        prob.end()
        return False, {}
    #TimeLimit
    if optimalNeeded and prob.solution.get_status() == 107:
        #print("No solution available")
        prob.end()
        return False, {}
    
    valsVar = prob.solution.get_values()
    namesVar = prob.variables.get_names()

    #CheckSolution is only used for testing
    if checkSolution:
        allocation = Util.recreateAllocAllSteps(nodes, arcs, listSlice, namesVar, valsVar, False, nbEtapes)
        Util.checkStepOfReconfiguration(listSlice, nodes, arcs, functions, allocation, nbEtapes)
        allocation = allocation[nbEtapes]
    else:
        #The allocation returned is the allocation at the final step (nbEtapes)
        allocation = Util.recreateAllocLastStep(nodes, arcs, listSlice, namesVar, valsVar, False, nbEtapes)
        
    prob.end()
    return True, allocation

