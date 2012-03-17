import networkx as nx
import matplotlib.pyplot as plt
from socket import socket as sock, AF_INET, SOCK_DGRAM 
from select import select

POLL = 0
READ_SIZE = 4096
HDR_LEN = 24 
REC_LEN = 52
NUM_FLOWS = 1

class Filter: 
   def __init__(self, host="", port=6969):
      self.host = host
      self.port = port
      self.listener = sock(AF_INET, SOCK_DGRAM, 0)
      self.listener.bind((host, port))
      self.flowGraph = nx.Graph()
      self.data = {}
      self.nodeNames = ["---"]
      self.nodeData = ["Select a node."]
      self.avgByteGraph = []
      self.avgLenGraph = []
      self.numFlowsGraph = []
      self.buffer = ""
      self.lastTwentyRecords = []
      self.lastTwentyHeaders = []
                
   def updateNetworkGraph(self):
      pos=nx.spring_layout(self.flowGraph)
      nx.draw(self.flowGraph, pos, fontsize=10)
      plt.axis('off')
      plt.savefig("graph.png")
  
   def addFlowToGraph(self, routerSrc, dst, nextHop):
      if nextHop == "0.0.0.0":
         self.flowGraph.add_edge(routerSrc, dst)
      else:
         self.flowGraph.add_edge(routerSrc, nextHop)

   def getAvgBytes(self):
      totalBytesNow = 0
      for (key, value) in self.data.items():
         totalBytesNow += value[L3_BYTES]
      self.avgByteGraph.append(totalBytesNow / len(self.data))    
      if len(self.avgByteGraph) > 50:
         self.avgByteGraph = self.avgByteGraph[-50:0]
        
      return self.avgByteGraph 
      
   def getAvgFlowLength(self):
      totalLength = 0
      for (key, value) in self.data.items():
         totalLength += (value[END] - value[START])
      self.avgLenGraph.append(totalLength / len(self.data))
      if len(self.avgLenGraph) > 50:
         self.avgLenGraph = self.avgLenGraph[-50:0]
      return self.avgLenGraph
      
   def generateGraphs(self):
      return [ self.getAvgBytes(), self.getAvgFlowLength(), self.numFlowsGraph ]

   def getKey(self, recPayload):
      srcIP = recPayload[0]
      dstIP = recPayload[1]
      srcPort = recPayload[9]
      dstPort = recPayload[10]
      ipType = recPayload[13]
      tos = recPayload[14]
      return (srcIP, dstIP, srcPort, dstPort, ipType, tos)    

   def update(self, nodeIndex):
     
      while select([self.listener], [], [], POLL)[0]:
         self.buffer += self.listener.recv(READ_SIZE)
      
      while self.buffer != "":
         hdrPayload = list(unpack("!HHLLLLBBH", self.buffer[:HDR_LEN])) 
         self.lastTwentyHeaders.append(hdrPayload)
         if len(self.lastTwentyHeaders) > 20:
            self.lastTwentyHeaders = self.lastTwentyHeaders[-20:]
         
         for idx in range(hdrPayload[NUM_FLOWS]):
            start = HDR_LEN + (idx * REC_LEN)
            end = start + REC_LEN
            recPayload = list(unpack("!LLLHHLLLLHHBBBBHHBBHL", self.buffer[start:end]))
            self.updateMetrics(self.getKey(recPayload), recPayload)
            self.lastTwentyRecords.append(recPayload)
            if len(self.lastTwentyRecords) > 20:
               self.lastTwentyRecords = self.lastTwentyRecords[-20:]          
         
      return [ self.generateGraphs(), self.getNewNodes(), self.nodeData[nodeIndex] ]
       
   def updateMetrics(self, unique, record): 
    #Check if the flow record is already in the dictionary
      if unique in self.data:
         flowRecord = self.data[unique]
         # Check if start times are the same
         if flowRecord[START] == record[START]:
            self.data[unique][L3_BYTES] += record[L3_BYTES]
            self.data[unique][END] = record[END]
      else: 
         self.data[unique] = record           
     
