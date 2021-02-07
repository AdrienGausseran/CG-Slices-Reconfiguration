import time
from multiprocessing import Process, Manager
from random import shuffle
from copy import copy
from collections import deque

from reconfiguration import master as reconfMaster
from allocation import subProbLP as subLP
from allocation import subProbILP as subILP
from Util import Util
import param

class reconfController(object):
    
    def __init__(self, links, nodes, functions, listSlice, nbEtapes, beta, useLP, stableStop, timeLimit = 1000, maxIteration = 150):
        
        self.maxIteration = maxIteration	#The maximum number of iterations we want to compute before stopping
        self.verbose = param.verbose
        self.checkSolution = param.checkSolution
        
        self.IntegralFlow = param.IntegralFlow	#False if you want a flow based allocation, True if you want paths (we used paths in this paper)
        
        self.links = links	#links of the network
        self.nodes = nodes	#nodes of the network
        self.functions = functions	#the list of VNFs
        self.listSfc = []
        for slice in listSlice:
            for s in slice:
                self.listSfc.append(s)
        self.beta = beta	#Price of the VNFs (see the paper and the readme for explanation)
        self.nbEtapes = nbEtapes    #Number of time steps of the reconf
        self.useLP = useLP	#If true it will use subLP as subproblems (rescue-LP in the paper), if false it will use subILP as subproblems (rescue-ILP in the paper)
        self.stableStop = stableStop    #StableStop : if the improvement is less than 0.1% over a number (stableCycle) iteration we stop and compute the master (ILP) problem
        
        self.timeLimit = timeLimit	#limit in seconds to compute the
        
        self.nbIteration = 0
        self.nbColumn = 0
        
        self.timeTotal = 0
        self.timeSubs = 0
        self.timeMaster = 0
        self.timeOptimal = 0
        
        self.objRelax = 0
        self.obj = 0
        self.bwUsed = 0
        self.vnfUsed = 0
        
        self.subs = []
        self.master = None
        
        self.oldObj = deque()
        
    #Initialization of the controller
    #Must be called before solve
    def initialise(self, dictPath):
        tStart = time.time()
        #Creation of the subproblems
        #One subproblem by sfc
        #Each sub will be compute "nbEtapes" times
        if self.useLP:
            for s in self.listSfc:
                self.subs.append(subLP.SubProb(self.nodes, self.links, self.functions, s, self.beta, self.nbEtapes))
        else:
            self.subs = [subILP.SubProb(self.nodes, self.links, self.functions, s, self.beta, self.nbEtapes) for s in self.listSfc] 
        #For each sub problem we add their first path (the path they already use before the reconfiguration
        for sub in self.subs:
            sub.addPath(dictPath[sub.sfc.id])
            
        self.timeSubs += time.time() - tStart
        
        #Creation of the master problem
        self.master = reconfMaster.Master(self.nodes, self.links, self.functions, None, self.listSfc, self.nbEtapes, self.beta, dictPath, self.IntegralFlow)
        self.timeTotal += time.time() - tStart
        
        
    
    def solve(self, nbThread = 1):
        
        if nbThread > 1:
            return self.solveMultiThread(nbThread)
        
        tStart = time.time()
        
        opt = False
        #We do multiple iterations until there is no more improvement or there is no more time or if we have done to much iterations
        while not opt:
            self.nbIteration += 1
            opt = True
            t = time.time()
            #We solve the relaxed master problem
            self.objRelax = self.master.solve(self.verbose)
            
            #Here we have a limit to do solve the pricing problems
            #The limit here is a maximum number of iteration, and 80% of the time limit (20% are kept to do the integral optimization
            if self.nbIteration == self.maxIteration or (time.time()-tStart) > (self.timeLimit*0.80):
                break
            #We get the duals values of the constraints of the master
            duals, constraintOnePath, constraintLinkCapacity, constraintNodeCapacity, constraintVnfUsed = self.master.getDuals()
            self.timeMaster += time.time() - t
    
            t = time.time()
            for sub in self.subs:
                listPath = []
                for step in range(self.nbEtapes, 0, -1):
                    #We update the objective of the sub using the duals of the master
                    sub.updateObjective(duals, constraintOnePath[sub.sfc.id][step], constraintLinkCapacity, constraintNodeCapacity, constraintVnfUsed, step)
                    #We solve the subproblem
                    reduceCost, path = sub.solve(step)
                    #If the reduce cost of the sub is < 0, we add the path created to the master
                    if reduceCost < 0:
                        listPath.append(path)
                        self.nbColumn +=1
                        opt = False
                        #print(path.alloc)
                for path in listPath :
                    self.master.addPath(path, sub.sfc)
            self.timeSubs += time.time() - t
            #StableStop : if the improvement is less than 0.1% over a number (stableCycle) iteration we stop
            if self.stableStop :
                stableCycle = param.stableCycle
                self.oldObj.append(self.objRelax)
                if len(self.oldObj) > stableCycle:
                    oldObj = self.oldObj.popleft()
                    if (oldObj- self.objRelax)/float(oldObj)*100 < 0.1:
                        opt = True
                
                
        t = time.time()

        #We use the time left
        limit = max(self.timeLimit*0.2, self.timeLimit - (time.time()-tStart))
        
        #We solve the master problem (ILP, not relaxed) using all the path created by the subs
        self.master.solveOpt(limit)
        self.timeOptimal = time.time() - t
        self.timeTotal += time.time() - tStart
        #We get the result
        res_Reconf, NumPathUsed_Reconf, pathUsed_Reconf = self.master.getResult(checkSolution=self.checkSolution)
        self.obj, self.bwUsed, self.vnfUsed = Util.objective(self.nodes, [self.listSfc], res_Reconf, self.beta)
        for sub in self.subs:
            sub.end()
        
        
        return res_Reconf, pathUsed_Reconf
    
    
    #Solve function called if you wand to do the computation in parallel
    #The librairy multiprocessing is used (does not work on windows)
    def solveMultiThread(self, nbThreadSub):

        #The thread's job
        def doYourJobYouUselessThread(listSub, duals, constraintOnePath, constraintLinkCapacity, constraintNodeCapacity, constraintVnfUsed, nbEtapes, dictPath):
            for sub in listSub:
                listPath = []
                for step in range(nbEtapes, 0, -1):
                    #We update the objective of the sub using the duals of the master
                    sub.updateObjective(duals, constraintOnePath[sub.sfc.id][step], constraintLinkCapacity, constraintNodeCapacity, constraintVnfUsed, step)
                    #We solve the subproblem
                    reduceCost, path = sub.solve(step)
                    #If the reduce cost of the sub is < 0, we add the path created to the master
                    if reduceCost < 0:
                        listPath.append(path)
                dictPath[sub.sfc.id] = listPath

        tStart = time.time()
        
        #Creation of lists to share the subproblems among the threads 
        listSubThread = [[] for i in range(nbThreadSub)]
        listSubTmp = copy(self.subs)
        shuffle(listSubTmp)
        nbSubByHtread = len(listSubTmp)//nbThreadSub
        dictSubThread = Manager().dict()
        it = 0
        
        #We fill the lists
        #We put the same amount of sub in each thread
        for i in range(nbSubByHtread):
            for subThread in listSubThread:
                subThread.append(listSubTmp[it])
                dictSubThread[listSubTmp[it].sfc.id] = []
                it += 1
        for i in range(len(listSubTmp) % len(listSubThread)):
            listSubThread[i].append(listSubTmp[it])
            dictSubThread[listSubTmp[it].sfc.id] = []
            it += 1

        
        opt = False
        #We do multiple iteration until there is no more improvement or there is no more time or if we have done to much iterations
        while not opt:
            self.nbIteration += 1
            opt = True
            t = time.time()
            #We solve the relaxed master problem
            self.objRelax = self.master.solve(self.verbose)
            
            #Here we have a limit to do solve the pricing problems
            #The limit here is a maximum number of iteration, and 80% of the time limit (20% are kept to do the integral optimization
            if self.nbIteration == self.maxIteration or (time.time()-tStart) > (self.timeLimit*0.80):
                break
            #We get the duals values of the constraints of the master
            duals, constraintOnePath, constraintLinkCapacity, constraintNodeCapacity, constraintVnfUsed = self.master.getDuals()
            self.timeMaster += time.time() - t
    
            t = time.time()
            
            #We launch all the threads
            listProcess = []
            for listSub in listSubThread:
                p = Process(target=doYourJobYouUselessThread, args=(listSub, duals, constraintOnePath, constraintLinkCapacity, constraintNodeCapacity, constraintVnfUsed, self.nbEtapes, dictSubThread))
                p.start()
                listProcess.append(p)
                
            #print("reconfController {}    C".format(self.nbIteration))
            #We wait for the ends of the threads
            for p in listProcess:
                p.join()
            #We add the new paths
            for sub in self.subs:
                listPath = dictSubThread[sub.sfc.id]
                if len(listPath) > 0 :
                    opt = False
                    self.nbColumn += len(listPath)
                    for path in listPath :
                        self.master.addPath(path, sub.sfc)
            self.timeSubs += time.time() - t
            
            for p in listProcess:
                p.terminate()

            #StableStop : if the improvement is less than 0.1% over a number (stableCycle) iteration we stop
            if self.stableStop :
                stableCycle = param.stableCycle
                self.oldObj.append(self.objRelax)
                if len(self.oldObj) > stableCycle:
                    oldObj = self.oldObj.popleft()
                    if (oldObj- self.objRelax)/float(oldObj)*100 < 0.1:
                        opt = True
                
        print("Reconfiguration GC subs Ok")
        t = time.time()

        #We use the time left
        limit = max(self.timeLimit*0.2, self.timeLimit - (time.time()-tStart))
        #We solve the master problem (ILP, not relaxed) using all the path created by the subs
        self.master.solveOpt(limit)
        self.timeOptimal = time.time() - t
        self.timeTotal += time.time() - tStart
        #We get the result
        res_Reconf, NumPathUsed_Reconf, pathUsed_Reconf = self.master.getResult(checkSolution=self.checkSolution)
        self.obj, self.bwUsed, self.vnfUsed = Util.objective(self.nodes, [self.listSfc], res_Reconf, self.beta)
        
        for sub in self.subs:
            sub.end()
        
        return res_Reconf, pathUsed_Reconf
