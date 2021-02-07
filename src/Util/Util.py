import collections

import copy


#Return the objective of an allocation (the cost of the links and the cost of the vnf)
def objective(nodes, listSlice, allocation, beta):
    #Variables initialization
    vnf = {}
    objBW = 0
    objVNF = 0
    for u in nodes:
        vnf[u] = {}
    #For each slice
    for j in range(len(listSlice)):
        slice = listSlice[j]
        #For each sfc
        for s in slice:
            #Bandwidth cost
            for i in range (len(allocation[s.id]["link"])):
                for (u,v) in allocation[s.id]["link"][i]:
                    objBW+=allocation[s.id]["link"][i][(u,v)]*s.bd
            #Node utilization
            for i in range (len(allocation[s.id]["node"])):
                for u in allocation[s.id]["node"][i]:
                    if(allocation[s.id]["node"][i][u]>0):
                        vnf[u][s.functions[i]] = 1
    #VNF cost using the node utilization
    for n in nodes:
        for f in vnf[n]:
            objVNF+=vnf[n][f]
    return (objBW + objVNF * beta), objBW, objVNF


#Return if the alloc (alloc of only ONE sfc) is composed of a single path
#It is used by subProbLP to know if the allocation is correct or if we need to compute the ILP formulation of the subproblem
def isSinglePath(alloc):
    adj = {}
    for i in range(len(alloc["link"])):
        for (u,v) in alloc["link"][i]:
            if (u, i) in adj:
                return False
            else:
                adj[(u, i)] = [(v, i)]
    for i in range(len(alloc["node"])):
        if(len(alloc["node"][i]))>1:
            return False
        for u in alloc["node"][i]:
            if (u, i) in adj:
                return False
            else:
                adj[(u, i)] = [(u, i+1)]       
    return True


#Test function
#Used to know if the reconfiguration is correct and if there is no bugs
#Not used in the final version
def checkStepOfReconfiguration(listSlice, nodes, links, functions, allocations, nbSteps):    
    errorDetected = False
    for t in range(nbSteps) :
        culmulStep = {}
        for slice in listSlice:
            for s in slice:
                culmulStep[s.id] = copy.deepcopy(allocations[t][s.id])
                if not sameAlloc(allocations[t][s.id], allocations[t+1][s.id]):
                    for i in range(len(s.functions)):
                        for l in allocations[t+1][s.id]['link'][i]:
                            if not l in culmulStep[s.id]['link'][i]:
                                culmulStep[s.id]['link'][i][l] = allocations[t+1][s.id]['link'][i][l]
                            else:
                                culmulStep[s.id]['link'][i][l] += allocations[t+1][s.id]['link'][i][l]
                        for n in allocations[t+1][s.id]['node'][i]:
                            if not n in culmulStep[s.id]['node'][i]:
                                culmulStep[s.id]['node'][i][n] = allocations[t+1][s.id]['node'][i][n]
                            else:
                                culmulStep[s.id]['node'][i][n] += allocations[t+1][s.id]['node'][i][n]
                    for l in allocations[t+1][s.id]['link'][len(s.functions)]:
                        if not l in culmulStep[s.id]['link'][len(s.functions)]:
                            culmulStep[s.id]['link'][len(s.functions)][l] = allocations[t+1][s.id]['link'][len(s.functions)][l]
                        else:
                            culmulStep[s.id]['link'][len(s.functions)][l] += allocations[t+1][s.id]['link'][len(s.functions)][l]
                    
        lRes, nRes = residual(links, nodes, functions, listSlice, culmulStep)
        for l in lRes:
            if lRes[l][0] < -1:
                print("Error between etape {} and {} : {} {} on {}".format(t, t+1, l, lRes[l][0], links[l][0]))
                errorDetected = True
        for n in nRes:
            if nRes[n][0] < -1:
                print("Error between etape {} and {} : {} {} on {}".format(t, t+1, n, nRes[n][0], nodes[n][0]))
                errorDetected = True
    return errorDetected


#Recreate the allocations of a list of slices using "namesVar and valsVar" which are given by cplex
#Fractional was an option in a former project, now everything is integral. Fractional = False
def recreateAlloc(nodes, arcs, listSlices, namesVar, valsVar, fractional):
    allocation = {}
    for slice in listSlices:
        for s in slice:
            allocation[s.id] = {}
            allocation[s.id]["link"]=[]
            allocation[s.id]["node"]=[]
            for i in range(len(s.functions)+1):
                allocation[s.id]["link"].append({})
                if(not i == len(s.functions)):
                    allocation[s.id]["node"].append({})
                     
    for i in range(len(namesVar)) :
        if namesVar[i][0]=='x':
            tmp = namesVar[i].split(",")
            id = tmp[1]
            layer = int(float(tmp[2]))
            src = tmp[3]
            dst = tmp[4]
            
            if(fractional):
                if(round(valsVar[i], 7)) > 0:
                    allocation[id]["link"][layer][(src,dst)] = round(valsVar[i], 8)
            else :
                if(round(valsVar[i],1)>0):
                    allocation[id]["link"][layer][(src,dst)] = round(valsVar[i],1)
        elif namesVar[i][0]=='u':
            tmp = namesVar[i].split(",")
            id = tmp[1]
            layer = int(float(tmp[2]))
            src = tmp[3]
            if(fractional):
                if(round(valsVar[i], 7)) > 0:
                    allocation[id]["node"][layer][src] = round(valsVar[i], 8)
            else :
                if(round(valsVar[i],1)>0):
                    allocation[id]["node"][layer][src] = round(valsVar[i],1)
    return allocation


#Recupere les variables et les valeurs pour recrer l'allocation d'une sfc
def recreateOneAllocGC(nodes, arcs, sfc, namesVar, valsVar):
    allocation = {}
    
    allocation["link"]=[]
    allocation["node"]=[]
    for i in range(len(sfc.functions)+1):
        allocation["link"].append({})
        if(not i == len(sfc.functions)):
            allocation["node"].append({})
                     
    for i in range(len(namesVar)) :
        if round(valsVar[i], 7) > 0:
            if namesVar[i][0]=='x':
                tmp = namesVar[i].split(",")
                layer = int(float(tmp[1]))
                src = tmp[2]
                dst = tmp[3]
                allocation["link"][layer][(src,dst)] = 1
                
            elif namesVar[i][0]=='u':
                tmp = namesVar[i].split(",")
                layer = int(float(tmp[1]))
                src = tmp[2]
                allocation["node"][layer][src] = 1
                
    return allocation


#Recreate the allocations of a list of slices using "namesVar and valsVar" which are given by cplex
#Fractional was an option in a former project, now everything is integral. Fractional = False
#
#It is used by renconfigurationIntegralILP (slow-rescue in the paper)
#It will give the allocation of the slices at the last step (nbEtapes)
def recreateAllocLastStep(nodes, arcs, listSlice, namesVar, valsVar, fractional, nbEtapes):
    allocation = collections.OrderedDict()


    for slice in listSlice:
        for s in slice:
            allocation[s.id] = collections.OrderedDict()
            allocation[s.id]["link"]=[]
            allocation[s.id]["node"]=[]
            for i in range(len(s.functions)+1):
                allocation[s.id]["link"].append(collections.OrderedDict())
                if(not i == len(s.functions)):
                    allocation[s.id]["node"].append(collections.OrderedDict())
    
       
    for i in range(len(namesVar)) :
        if namesVar[i][0]=='x':
            tmp = namesVar[i].split(",")
            id = tmp[1]
            step = int(float(tmp[2]))
            layer = int(float(tmp[3]))
            src = tmp[4]
            dst = tmp[5]
            if(step==nbEtapes):
                if(fractional):
                    allocation[id]["link"][layer][(src,dst)] = round(valsVar[i], 9)
                else :
                    allocation[id]["link"][layer][(src,dst)] = round(valsVar[i],1)
        elif namesVar[i][0]=='u':
            tmp = namesVar[i].split(",")
            id = tmp[1]
            step = int(float(tmp[2]))
            layer = int(float(tmp[3]))
            src = tmp[4]
            if(step==nbEtapes):
                if(fractional):
                    allocation[id]["node"][layer][src] = round(valsVar[i], 9)
                else :
                    allocation[id]["node"][layer][src] = round(valsVar[i],1)
    return allocation


#Testing function
#Recreate the allocations of a list of slices using "namesVar and valsVar" which are given by cplex
#Fractional was an option in a former project, now everything is integral. Fractional = False
#
#It is used by renconfigurationIntegralILP (slow-rescue in the paper)
#It will give the allocation of the slices at all the steps
#thoses allocation will be used by checkStepOfReconfiguration for testing
def recreateAllocAllSteps(nodes, arcs, listSlice, namesVar, valsVar, fractional, nbEtapes):
    allocation = []

    for t in range(nbEtapes+1) :   
        allocation.append({})
        for slice in listSlice:
            for s in slice:
                allocation[t][s.id] = collections.OrderedDict()
                allocation[t][s.id]["link"]=[]
                allocation[t][s.id]["node"]=[]
                for i in range(len(s.functions)+1):
                    allocation[t][s.id]["link"].append(collections.OrderedDict())
                    if(not i == len(s.functions)):
                        allocation[t][s.id]["node"].append(collections.OrderedDict())
    
       
    for i in range(len(namesVar)) :
        if namesVar[i][0]=='x':
            tmp = namesVar[i].split(",")
            id = tmp[1]
            step = int(float(tmp[2]))
            layer = int(float(tmp[3]))
            src = tmp[4]
            dst = tmp[5]
            if(fractional):
                allocation[step][id]["link"][layer][(src,dst)] = round(valsVar[i], 9)
            else :
                allocation[step][id]["link"][layer][(src,dst)] = round(valsVar[i],1)
        elif namesVar[i][0]=='u':
            tmp = namesVar[i].split(",")
            id = tmp[1]
            step = int(float(tmp[2]))
            layer = int(float(tmp[3]))
            src = tmp[4]
            if(fractional):
                allocation[step][id]["node"][layer][src] = round(valsVar[i], 9)
            else :
                allocation[step][id]["node"][layer][src] = round(valsVar[i],1)
    return allocation




































#Verify if two alloc are the same
#Return if the two allocation are equal
def sameAlloc(alloc1, alloc2):
    #Verify that the links are the same
    for i in range(len(alloc2["link"])):
        keys1 = alloc1["link"][i].keys()
        sorted(keys1)
        keys2 = alloc2["link"][i].keys()
        sorted(keys2)
        if(keys1 != keys2):
            return False
        else:
            for k in keys2:
                if(alloc1["link"][i][k] != alloc2["link"][i][k]):
                    return False
    #Verify that the nodes are the same
    for i in range(len(alloc2["node"])):
        keys1 = alloc1["node"][i].keys()
        sorted(keys1)
        keys2 = alloc2["node"][i].keys()
        sorted(keys2)
        if(keys1 != keys2):
            return False
        else:
            for k in keys2:
                if(alloc1["node"][i][k] != alloc2["node"][i][k]):
                    return False
    return True
    

#Return the residual capacities of links and nodes
def residual(links, nodes, functions, listSlice, allocations):
    #We copy the links in links residual and the nodes in nodes residual
    linksResidual = copy.deepcopy(links)
    nodesResidual = copy.deepcopy(nodes)
    
    #We decreased the residual capacity of the links and the nodes
    for slice in listSlice:
        for s in slice:
            for i in range(len(s.functions)+1):
                for (u,v) in allocations[s.id]["link"][i] :
                    linksResidual[(u,v)][0]-= s.bd*allocations[s.id]["link"][i][(u,v)]
            for i in range(len(s.functions)):
                for u in allocations[s.id]["node"][i]:
                    nodesResidual[u][0] -= s.bd*functions[s.functions[i]]*allocations[s.id]["node"][i][u]
            
    return linksResidual, nodesResidual


