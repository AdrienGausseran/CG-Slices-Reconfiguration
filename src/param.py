stableStopGC = True	#StableStop : if the improvement is less than 0.1% over a number (stableCycle) iterations we stop
stableCycle = 15
verbose = False
checkSolution = False	#checkSolution : used for testing. If True the reconfiguration will be check to be sure there is no bug
IntegralFlow = True	#Always True : False if you want a flow based allocation, True if you want paths (we used paths in this paper)

