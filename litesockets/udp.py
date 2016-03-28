import socket, logging
import client


class UDPServer(client.Client):
  def __init__(self, host, port, socketExecuter):
    self.__host = host
    self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.__socket.bind((self.__host, port))
    self.__port = self.__socket.getsockname()[1]
    self.__log = logging.getLogger("root.litesockets.UDPServer:"+self.__host+":"+str(self.__port))
    self.__clients = dict()
    self.__socket.setblocking(0)
    self.__SUPER = super(UDPServer, self)
    self.__SUPER.__init__(socketExecuter, "UDP", self.__socket);
    self.__acceptor = None
    self.addCloseListener(self.__closeClients)

  def start(self):
    self.getSocketExecuter().updateClientOperations(self)
    
  def stop(self):
    self.getSocketExecuter().updateClientOperations(self)
    
  def setOnClient(self, acceptor):
    self.__acceptor = acceptor
    
  def connect(self):
    pass
 
  def _addRead(self, data):
    ipp = data[0]
    if ipp not in self.__clients:
      udpc = self.createUDPClient(ipp[0], ipp[1])
      self.__clients[ipp] = udpc
      if self.__acceptor != None: 
        self.getSocketExecuter().getScheduler().execute(self.__acceptor, args=(udpc,))
    udpc = self.__clients[ipp]
    if udpc.getReadBufferSize() < udpc.MAXBUFFER:
      udpc.runOnClientThread(udpc._addRead, args=(data[1],))
    else:
      print "DROPPED!"
    #X = self.getStats()._addRead(len(data))

  def getClients(self):
    return list(self.__clients)

  def getRead(self):
    pass

  def removeUDPClient(self, client):
    del self.__clients[client.getAddress()]

  def createUDPClient(self, host, port):
    client = UDPClient(self, host, port, self.getSocketExecuter())
    self.__clients[(host, port)] = client
    return client
    
  def __closeClients(self, us):
    ld = self.__clients.copy()
    for client in ld:
      ld[client].close()
    


class UDPClient(client.Client):
  def __init__(self, udpServer, host, port, socketExecuter):
    self.__host = socket.gethostbyname(host)
    self.__port = port
    self.__server = udpServer
    self.__log = logging.getLogger("root.litesockets.UDPClient"+self.__host+":"+str(self.__port))
    self.__SUPER = super(UDPClient, self)
    self.__SUPER.__init__(socketExecuter, "UDP", None)

  def connect(self):
    pass

  def write(self, data):
    self.__server.write([(self.__host, self.__port), data])
    self.getStats()._addWrite(len(data))

  def _reduceWrite(self, size):
    pass

  def _getWrite(self):
    pass
  
  def getAddress(self):
    return (self.__host, self.__port)

  def close(self):
    self.__server.removeUDPClient(self)
    self.__SUPER.close()

