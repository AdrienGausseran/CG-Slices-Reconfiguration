import os.path
import collections


import SFC
import readWritter

#Function used to read the file describing the VNFs
#file : instances/function
def readFunctions(path):
    functions = {}
    fileToOpen = os.path.join(path, "instances")
    fileToOpen = os.path.join(fileToOpen, "function")
    with open(fileToOpen, "r") as f:
        for line in f :
            if(line[0] == "#"):
                continue
            tmp = line.replace("\n","")
            tmp = tmp.split(" ")
            functions[tmp[0]] = float(tmp[1])
    f.close()
    return functions


#Function used to read the file describing the distribution of SFCs
#file : instances/SliceDistrib_Real
def readSFC_Distrib(path, file):
    distrib = collections.OrderedDict()
    probaTotal = 0
    fileToOpen = os.path.join(path, "instances")
    fileToOpen = os.path.join(fileToOpen, file)
    with open(fileToOpen, "r") as f:
        for line in f :
            if(line[0] == "#"):
                continue
            tmp = line.replace("\n","")
            tmp = tmp.split(" ")
            sfcType = tmp[0]
            capacityDemand = float(tmp[2])
            nbDemand = float(tmp[3])
            latency = float(tmp[4])
            tmp = tmp[1].replace("[","")
            tmp = tmp.replace("]","")
            functions = tmp.split(",")
            probaTotal += nbDemand
            distrib[sfcType] = [functions, capacityDemand, probaTotal, latency]
    f.close()
    return distrib

#Function used to read the file describing the traffic matrix of a network
#file : instances/map/"networkName"/traffic_Real
def readTraffic(path, mapName, file = "traffic"):
    traffic = collections.OrderedDict()
    demandProbaTotal = 0
    fileToOpen = os.path.join(path, "instances")
    fileToOpen = os.path.join(fileToOpen, "map")
    fileToOpen = os.path.join(fileToOpen, mapName)
    fileToOpen = os.path.join(fileToOpen, file)
    with open(fileToOpen, "r") as f:
        for line in f :
            if(line[0] == "#"):
                continue
            tmp=line.replace("  ","")
            tmp = tmp.split(" ")
            src, dst, proba = tmp[2], tmp[3], tmp[6]
            demandProbaTotal += float(proba)
            traffic[tmp[0]] = [demandProbaTotal, (src, dst)]
    f.close()
    return traffic



#loadMap the graph and the demand from  a SNDLib file
#path : path of the file
#withTraffic : True if the demands of the file must been loadMap, False either
#The traffic can be load separately from a traffic file (in instance/map/"networkName"/"traffic_..." by the function readTraffic
#The capacity used in the project are not the one mention in the file but are tuned 
def loadMap(path, mapName, withTraffic = False, capacityInfiny = -1):
    fileToOpen = os.path.join(path, "instances")
    fileToOpen = os.path.join(fileToOpen, "map")
    fileToOpen = os.path.join(fileToOpen, mapName)
    fileToOpen = os.path.join(fileToOpen, "{}.txt".format(mapName))
    nodes = {}
    links = collections.OrderedDict()
    traffic = collections.OrderedDict()
    demandProbaTotal = 0
    
    demandPart = False
    nodePart = False
    linkPart = False
    
    with open(fileToOpen, "r") as f:
        for line in f :

            #We save the nodes
            if(nodePart):
                if(line==")\n"):
                    nodePart = False
                    continue
                line = line.replace("  ", "")
                nodeid=line[:line.find("(")-1]
                mySubString=line[line.find("(")+2:line.find(")")-1]
                #We collect the node
                nodes[nodeid] = []
                #We collect the capacity
                capacity = int(mySubString)
                if(capacity > 0 and capacityInfiny > -1):
                    nodes[nodeid].append(capacityInfiny)
                else:  
                    nodes[nodeid].append(int(mySubString))
                line=line[line.find("[")+2:line.find("]")-1]
                tmpOption = line.split(" ")
                #We collect the functions
                nodes[nodeid].append([])
                for i in range(len(tmpOption)):
                    if(tmpOption[i]!=''):
                        nodes[nodeid][1].append(tmpOption[i])
                        
            #We save the links
            elif(linkPart):
                if(line==")\n"):
                    linkPart = False
                    if(withTraffic):
                        continue
                    else :
                        break
                mySubString=line[line.find("(")+2:line.find(")")-1]
                #We save the source and the destination
                tmp=mySubString.split(" ")
                node1 = tmp[0]
                node2 = tmp[1]
                links[(node1, node2)]=[]
                #We save the capacity and the delay
                line = line[line.find(")")+1:]
                line = line.replace(' ( ','')
                line = line.replace(' )\n','')
                tmp=line.split(" ")
                if(capacityInfiny > -1):
                    capacity = capacityInfiny
                else:  
                    capacity = int(tmp[0])
                delay = float(tmp[1])
                links[(node1, node2)].append(capacity)
                links[(node1, node2)].append(delay)
                #We save the link in the other way
                links[(node2, node1)]=[]
                links[(node2, node1)].append(capacity)
                links[(node2, node1)].append(delay)
                
            elif(demandPart):
                if(line==")\n"):
                    break
                tmp=line.replace("  ","")
                tmp = tmp.split(" ")
                src, dst, proba = tmp[2], tmp[3], tmp[6]
                demandProbaTotal += float(proba)
                traffic[tmp[0]] = [demandProbaTotal, (src, dst)]
                
                
            else:
                if(line=="NODES (\n"):
                    nodePart = True
                elif(line=="LINKS (\n"):
                    linkPart = True
                elif(line=="DEMANDS (\n"):
                    demandPart = True
                else:
                    continue
            
    f.close()
    
    return nodes, links, traffic    


#Load all the sfc in the file "fileName" in the folder "map" in instances
def loadInstance(path, map, fileName):
    file_to_open = os.path.join(map, "expe")
    file_to_open = os.path.join(file_to_open, fileName)
    file_to_open = os.path.join("map", file_to_open)
    file_to_open = os.path.join("instances", file_to_open)
    file_to_open = os.path.join(path, file_to_open)
    listSlice = []
    listSfc = []
    with open(file_to_open+".txt") as f:
        for line in f :
            line = line.replace("\n", "")
            if line[0] == "(":
                listSfc = []
            elif line[0] == ")":
                listSlice.append(listSfc)
            else:
                line = line.replace("    ", "")
                tmp = line.split(":")
                id = tmp[0]
                tmp = tmp[1].split(" ")
                bd = int(float(tmp[0]))
                functions = tmp[2].split(",")
                maxLatency = float(tmp[3])
                timeOfDeath = int(float(tmp[4]))
                tmp = tmp[1].split(",")
                listSfc.append(SFC.SFC(id,bd,tmp[0],tmp[1],functions, maxLatency, timeOfDeath))
    f.close()
    return listSlice

    
    