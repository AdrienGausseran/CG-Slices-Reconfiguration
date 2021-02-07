
#A pathGC is used by the column generation
class PathGC(object):

    def __init__(self, num, alloc, nbLinks, nodesUsed, key = None):
        self.num = num              #The number of the path
        self.alloc = alloc          #The allocation
        self.nbLinks = nbLinks      #Number of links used : dictionary for each link it's you have the number of times it is used (it can be used multiple times because it's an SFC
        self.nodesUsed = nodesUsed  #List of used nodes
        self.key = key              #A key identifier
        
    def __repr__(self):
        return self.key

def fromAllocTopathGC(alloc, num):
    nbLinks = {}
    nodesUsed = []  
    key = ""
    

    for i in range(len(alloc["node"])):
        listL = list(list(alloc["link"][i].keys()))
        listL.sort()
        tmp = list(alloc["node"][i].keys())[0]
        key +=str(tmp)
        for (u,v) in listL:
            nbLinks[(u,v)] = nbLinks.get((u,v),0) + 1
            key += u+"-"+v
        nodesUsed.append(tmp)
    listL = list(alloc["link"][len(alloc["link"])-1].keys())
    listL.sort()
    for (u,v) in listL:
        nbLinks[(u,v)] = nbLinks.get((u,v),0) + 1
        key += u+"-"+v
    
    return PathGC(num, alloc, nbLinks, nodesUsed, key)

        