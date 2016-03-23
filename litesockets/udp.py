import socket, logging
from .client import Client


class UDPServer(Client):
  def __init__(self, host, port, socketExecuter):
    self.__log = logging.getLogger("root.litesockets.UDPServer:"+host+":"+str(port))
    self.__host = host
    self.__port = port
    self.__clients = dict()
    self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.__socket.bind((self.ip, self.port))
    self.__SUPER = super(UDPServer, self, self.__socket)
    self.__SUPER.__init__(socketExecuter, "UDP", self.__socket);
    self.addCloseListener(self.__closeClients)

  def start(self):
    self.__socketExecuter.startServer(self)
    
  def stop(self):
    self.__socketExecuter.stopServer(self)

  def write(self, data):
    self.__socket.sendto(data[1], data[0])

  def getWrite(self):
    pass

  def reduceWrite(self, size):
    pass

  def addRead(self, data):
    ipp = data[0]
    if ipp not in self.__clients:
      udpc = UDPClient(self, self.__ip, self.__port, self.__socketExecuter)
      self.__clients[ipp] = udpc
      if self.__acceptor != None: 
        self.__socketExecuter.getSocketExecuter().execute(self.__acceptor, args=(udpc,))
    udpc = self.__clients[ipp]
    if udpc.getReadBufferSize() < udpc.MAXBUFFER:
      udpc.addRead(data[1])

  def getRead(self):
    pass

  def removeUDPClient(self, client):
    del self.__clients[client.getAddress()]

  def createUDPClient(self, host, port):
    client = UDPClient(self, host, port)
    self.__clients[(client.host, client.port)] = client
    return client
    
  def __closeClients(self):
    for client in self.__clients:
      client.close()
    


class UDPClient(Client):
  def __init__(self, udpServer, host, port, socketExecuter):
    self.__host = socket.gethostbyname(host)
    self.__port = port
    self.__server = udpServer
    self.__server.__clients[(self.host, self.port)] = self
    self.__log = logging.getLogger("root.litesockets.UDPClient"+self.__host+":"+self.__port)
    self.__SUPER = super(UDPClient, self)
    self.__SUPER.__init__(socketExecuter, "UDP")

  def connect(self):
    #noop
    pass

  def write(self, data):
    self.server.addWrite([(self.host, self.port), data])

  def reduceWrite(self, size):
    pass

  def getWrite(self):
    pass
  
  def getAddress(self):
    return (self.__host, self.__port)

  def close(self):
    self.__server.removeUDPClient(self)

