# CG-Slices-Reconfiguration

Python 3.6 was used
Cplex is needed

In the src folder ther is :

	allocILP.py contains the ILP the allocation for a single slice on the residual capacities of the network or it can compute the allocation for all the slices.
		In the paper we use it to map the slices one by one in the dynamic scenario, but we also use it as "slice-wreck" (Break Befor Make reconfiguration) to compute the optimal allocation for all the slices
		The parameters name are self-explaining. For the parameter fractional, it only exist because we worked with flow in another project but in this paper we work with paths so fractional = False

	reconfigurationIntegralILP.py contains the ILP that compute the Make Before Break reconfiguration and we call it "slow-rescue" in the paper

	reconfController.py contains the controller for the column generation based reconfiguration

	master.py contains the master problem for the column generation based reconfiguration

	subProbILP.py contains one of the sub-problems (pricing problem) for the column generation based reconfiguration. This one is rescue-ILP in the paper
	subProbLP.py contains one of the sub-problems (pricing problem) for the column generation based reconfiguration. This one is rescue-LP in the paper
	Both subProbILP and subProbLP are in the allocation folder because they compute only allocation but they are used by the reconfiguration (see the paper)

	Util.py contains utility functions

	param.py contains some parameters

	SFC.py contains the class for SFCs

	pathGC.py contains the class used by the column generation to contain an allocation

	instanceLoader.py contains utility functions to load networks, network settings and instances



In the instances folder there is :

	function contains the VNFs description

	SliceDistrib_Real contains the different slice models as well as their distribution

	map contains the different networks (I gave pdh as an example)

	traffic_Real is the traffic matrix of the network

	pdh.txt is a network (it comes from SNDlib : http://sndlib.zib.de/coredata.download.action?format=native&compression=zip&problemName=pdh--D-B-E-N-C-A-N-S&objectType=problem)
		it's not exactly the same file, you can easily understand what was changed to create your own network
		for each link (u,v) in the file we create a link (v,u)
		The capacities in the file are not the one we used, we changed the capacities inside a function to work with our instances

	expe contains the instances
		for each timeStep you have a slice (multiple SFCs), it is just an example



Some explanations :

	beta : In the paper we talk about a beta of 0 or 1.
		When we used a beta of 1, the beta variable was not set to 1, what we meant was the cost of using vnf to be of the same order of magnitude as the cost of using links.
		Beta = 1 means beta = (cost of 100% links used) / (cost of 100% VNFs deployed)

	network description : the network is made of links and nodes
		links is a dictionary, and for each link we have a list with the capacity and the delay of the link. "links[(nodeId1, nodeId2)] = [capacity, delayMax]"
		nodes is a dictionary, and for each node we have a list that contains the capacity of the node and canother list that contains the list of VNF that can be deployed on this node
			"nodes[nodeId]= [capacity, [listFunction]]"
			If the node is not a datacenter : "nodes[nodeId]= [0, []]"

Here you need to understand the concept of layer graph used two map the SFCs
	See https://hal.inria.fr/hal-02416096/document pages 6 and 7 to understand 

	allocation : It contains the slices allocation and it's a dictionary
		for each sliceId we have another dictionary for the links and the nodes
		The dictionary for the links contains a list of dictionary. The number of dictionary is the number of VNFs needed by the SFC +1
			Each dictionary contains the links used on the layer and the amount of their use (it's always 1 so we could have used a list but because we used the same implementation in an other project that work with flows, we keep the dictionary)
		The dictionary for the nodes contains a list of dictionary. The number of dictionary is the number of VNFs needed by the SFC
			Each dictionary contains the node used on the layer and the amount of it's use (it's always 1 so we could have used a list but because we used the same implementation in an other project that work with flows, we keep the dictionary)
		An example :

		{'N9_N2_1': {'link': [{('N9', 'N2'): 1.0}, {}, {}, {}, {}, {}], 'node': [{'N2': 1.0}, {'N2': 1.0}, {'N2': 1.0}, {'N2': 1.0}, {'N2': 1.0}]}, 'N9_N11_2': {'link': [{('N11', 'N7'): 1.0, ('N9', 'N11'): 1.0}, {}, {}, {}, {}, {('N7', 'N11'): 1.0}], 'node': [{'N7': 1.0}, {'N7': 1.0}, {'N7': 1.0}, {'N7': 1.0}, {'N7': 1.0}]}}
		Here we have two slices : 'N9_N2_1' and 'N9_N11_2'
		The slice 'N9_N2_1' use the link ('N9', 'N2') on the first layer and no other link in the other layer. All 5 VNFs are deployed on the node 'N2'
		The slice 'N9_N11_2' use the links ('N9', 'N11') and ('N11', 'N7') on the first layer and ('N7', 'N11') on the sixth layer. All 5 VNFs are deployed on the node 'N7'



With this you can easily create a main file to load the network, change his capacities, load an instance and try the allocation and the different reconfigurations
