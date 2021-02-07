import collections

from Util import pathGC
from Util import Util

import cplex


#If ObjBandwitch the objective will be to minimize to bandwdith, if false it will be to minimize the delay
#	nodes : nodes of the network
#	arcs : links of the network
#	listSlice : the list of the slices to reconfigure
#	functions : the list of VNFs
#	nodeFunction : if != empty it's the Function that are already used on some nodes (if used with the residual network)
#	beta : price of the VNFs (see the paper and the readme for explanation)
#	fractional : True if you want a flow based allocation, False if you want paths (we used paths in this paper)
#	timeLimit : limit in seconds
#	optimalNeeded : Boolean, if True, will return the optimal reconfiguration if it's possible in the given time. It's better to used False with a short timeLimit
def findAllocation(nodes, arcs, listSlices, functions, nodeFunction, beta, fractional, timeLimit = 1000, verbose=False, optimalNeeded = True):
    
    prob = cplex.Cplex()
    prob.parameters.read.datacheck.set(0)
    
    prob.objective.set_sense(prob.objective.sense.minimize)
    prob.set_results_stream(None)
    
    #    ---------- ---------- ---------- First we build the model
    
    obj = []        #Objective
    ub = []         #Upper Bound
    rhs = []        #Result for each constraint
    sense = []      #Comparator for each constraint
    colname = []    #Name of the variables
    types = []      #type of the variables
    row = []        #Constraint
    rowname=[]      #Name of the constraints
    numrow = 1

    if(not fractional):
        frac = 'B'
    else:
        frac = 'C'
        
                    
    nodesDC = collections.OrderedDict()
    for u in nodes:
        if(nodes[u][0]>0):
            nodesDC[u] = nodes[u]
                 
    #We create a matrix to know which Function a node can have
    #And we create the variables for isUse
    for u in nodesDC:
        for f in functions:
            colname.append("isUse,{},{}".format(u,f))
            obj.append(beta)
            ub.append(1)
            types.append('B')
            if u in nodeFunction.keys():
                if f in nodeFunction[u].keys():
                    row.append([["isUse,{},{}".format(u,f)], [1]])
                    rowname.append("c{}".format(numrow))
                    numrow+=1
                    rhs.append(nodeFunction[u][f])
                    sense.append("E")
    
    #For each slice
    for slice in listSlices:
        for s in slice:
            #For each layer of the slice
            for i in range(len(s.functions)+1):
                #for each nodes
                for u in nodesDC:
                    if(not i == len(s.functions)):
                        if(s.functions[i] in nodes[u][1]):
                            #We create a variable to know if we use a node for an option
                            colname.append("use,{},{},{}".format(s.id,i,u))
                            obj.append(0)
                            ub.append(1)
                            types.append(frac)
        
                #for each arc we create a lp variable
                for (u,v) in arcs:
                    colname.append("x,{},{},{},{}".format(s.id,i,u,v))
                    obj.append(s.bd)
                    ub.append(1)
                    types.append(frac)
                
    #Flow conservation constraints
    for slice in listSlices:
        for s in slice:
            for i in range(len(s.functions)+1):
                for u in nodes:
                    listVar = []
                    listVal = []
                    #If the node is a datacenter
                    if(nodes[u][0]>0):
                        #If it's the source layer
                        if(i==0):
                            if(s.functions[i] in nodes[u][1]):
                                listVar.append("use,{},{},{}".format(s.id,i,u))
                                listVal.append(1)
                            for (n,v) in arcs :
                                if(n==u):
                                    listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                                    listVal.append(1)
                            for (v,n) in arcs :
                                if(n==u):
                                    listVar.append("x,{},{},{},{}".format(s.id,i,v,u))
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
                                listVar.append("use,{},{},{}".format(s.id,i-1,u))
                                listVal.append(-1)
                            for (n,v) in arcs :
                                if(n==u):
                                    listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                                    listVal.append(1)
                            for (v,n) in arcs :
                                if(n==u):
                                    listVar.append("x,{},{},{},{}".format(s.id,i,v,u))
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
                                listVar.append("use,{},{},{}".format(s.id,i,u))
                                listVal.append(1)
                            if(s.functions[i-1] in nodes[u][1]):
                                listVar.append("use,{},{},{}".format(s.id,i-1,u))
                                listVal.append(-1)
                            for (n,v) in arcs :
                                if(n==u):
                                    listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                                    listVal.append(1)
                            for (v,n) in arcs :
                                if(n==u):
                                    listVar.append("x,{},{},{},{}".format(s.id,i,v,u))
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
                                    listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                                    listVal.append(1)
                            for (v,n) in arcs :
                                if(n==u):
                                    listVar.append("x,{},{},{},{}".format(s.id,i,v,u))
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
                                    listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                                    listVal.append(1)
                            for (v,n) in arcs :
                                if(n==u):
                                    listVar.append("x,{},{},{},{}".format(s.id,i,v,u))
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
                                    listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                                    listVal.append(1)
                            for (v,n) in arcs :
                                if(n==u):
                                    listVar.append("x,{},{},{},{}".format(s.id,i,v,u))
                                    listVal.append(-1)
                            row.append([listVar, listVal])
                            rowname.append("c{}".format(numrow))
                            numrow+=1
                            sense.append('E')
                            rhs.append(0)
                                                   
    #Constraints for links capacity
    for (u,v) in arcs:
        listVar = []
        listVal = []
        for slice in listSlices:
            for s in slice:
                for i in range(len(s.functions)+1):
                    listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                    listVal.append(s.bd)
        row.append([listVar, listVal])
        rowname.append("c{}".format(numrow))
        numrow+=1
        sense.append('L')
        rhs.append(arcs[(u,v)][0])
            
        
    for slice in listSlices:
        for s in slice:
            #Only one node can be use as a function by slice, by layer
            for i in range(len(s.functions)):
                listVar = []
                listVal = []
                for u in nodesDC:
                    if(s.functions[i] in nodes[u][1]):
                        listVar.append("use,{},{},{}".format(s.id,i,u))
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
                    listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
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
        
        for slice in listSlices:
            for s in slice:
                for i in range(len(s.functions)):
                    if(s.functions[i] in nodes[u][1]):
                        listVar.append("use,{},{},{}".format(s.id,i,u))
                        val = s.bd*functions[s.functions[i]]
                        listVal.append(val)
        row.append([listVar, listVal])
        rowname.append("c{}".format(numrow))
        numrow+=1
        sense.append('L')
        rhs.append(nodes[u][0])
        
        #The constraint for isUse
        for f in functions:
            for slice in listSlices:
                for s in slice:
                    for i in range(len(s.functions)):
                        if(s.functions[i] == f):
                            if(f in nodes[u][1]):
                                row.append([["isUse,{},{}".format(u,f), "use,{},{},{}".format(s.id,i,u)], [1, -1]])
                                rowname.append("c{}".format(numrow))
                                numrow+=1
                                sense.append('G')
                                rhs.append(0)   
    
    
    prob.variables.add(obj=obj, types=types, ub=ub, names=colname)
    prob.linear_constraints.add(lin_expr=row, senses=sense, rhs=rhs, names=rowname)
    
    prob.parameters.timelimit.set(timeLimit)
    prob.parameters.mip.tolerances.mipgap.set(0.0001)
    
    allocation = {}

    try:
        prob.solve() 
        
    except :
        prob.end()
        # infeasible
        return False, {}, allocation
    
    if prob.solution.get_status() != 101 and prob.solution.get_status() != 102:
        #print("No solution available")
        prob.end()
        return False, {}, {}
    #TimeLimit
    if optimalNeeded and prob.solution.get_status() == 107:
        #print("No solution available")
        prob.end()
        return False, {}, {}
    
    valsVar = prob.solution.get_values()
    namesVar = prob.variables.get_names()

    allocation = Util.recreateAlloc(nodes, arcs, listSlices, namesVar, valsVar, fractional)
    dictPath = {}
    for slice in listSlices:
        for s in slice:
            path = pathGC.fromAllocTopathGC(allocation[s.id], 0)
            dictPath[s.id] = [path]
        
    prob.end()
    return True, dictPath, allocation
    
        
