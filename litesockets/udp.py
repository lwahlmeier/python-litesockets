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
    #self.__socket.setblocking(1)
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

  def write(self, data):
    self.__socket.sendto(data[1], data[0])

  def _getWrite(self):
    pass

  def _reduceWrite(self, size):
    pass

  def _addRead(self, data):
    ipp = data[0]
    if ipp not in self.__clients:
      udpc = UDPClient(self, ipp[0], ipp[1], self.getSocketExecuter())
      self.__clients[ipp] = udpc
      if self.__acceptor != None: 
        self.getSocketExecuter().getScheduler().execute(self.__acceptor, args=(udpc,))
    udpc = self.__clients[ipp]
    if udpc.getReadBufferSize() < udpc.MAXBUFFER:
      udpc._addRead(data[1])

  def getRead(self):
    pass

  def removeUDPClient(self, client):
    del self.__clients[client.getAddress()]

  def createUDPClient(self, host, port):
    client = UDPClient(self, host, port)
    self.__clients[(client.host, client.port)] = client
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
    #noop
    pass

  def write(self, data):
    self.__server.write([(self.__host, self.__port), data])

  def _reduceWrite(self, size):
    pass

  def _getWrite(self):
    pass
  
  def getAddress(self):
    return (self.__host, self.__port)

  def close(self):
    self.__server.removeUDPClient(self)
    self.__SUPER.close()

