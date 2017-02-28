import socket, logging
from . import client


class UDPServer(client.Client):
  """
  A UDPServer instance.  This acts basically like a TCP listen port.  Notifiying you 
  when new UDPClients "connect (send data)"
  """
  def __init__(self, host, port, socketExecuter):
    """
    Constructs a new UDPServer.  This should never be created manually instead use createUDPServer
    on a started SocketExecuter object. 
    """
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
    """
    Starts actively listening on the set UDP port.
    """
    self.getSocketExecuter().updateClientOperations(self)
    
  def stop(self):
    """
    Stops actively listening on the set UDP port, it will still be bound to that port though.
    """
    self.getSocketExecuter().updateClientOperations(self)
    
  def setOnClient(self, acceptor):
    """
    Sets the onClient listener callback.  This will be called any time a new UDP endpoint sends data
    to this server.  It will create a UDPClient which will then be sent the data.
    """
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
      pass
    #X = self.getStats()._addRead(len(data))

  def getClients(self):
    """
    Returns a list of "connected" UDPClients.
    """
    return list(self.__clients)

  def getRead(self):
    pass

  def removeUDPClient(self, client):
    """
    Removed a UDPClient from the server.  If more data is sent to this client
    onClient will fire again with a new UDPClient for that endpoint.
    """
    del self.__clients[client.getAddress()]

  def createUDPClient(self, host, port):
    """
    Creates a UDPClient to send data to set host and port.
    """
    client = UDPClient(self, host, port, self.getSocketExecuter())
    self.__clients[(host, port)] = client
    return client
    
  def __closeClients(self, us):
    ld = self.__clients.copy()
    for client in ld:
      ld[client].close()
    


class UDPClient(client.Client):
  """
  A UDPClient object.  This acts like a TCPClient only allowing sending and reciving of data
  to/from one endpoint.  It is technically a mocked client as all read/write operations happen through
  the UDPServer's udp socket.
  """
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
    """
    Writes data to the hard set end point for this client. (see getAddress).
    """
    self.__server.write([(self.__host, self.__port), data])
    self.getStats()._addWrite(len(data))

  def _reduceWrite(self, size):
    pass

  def _getWrite(self):
    pass
  
  def getAddress(self):
    """
    Returns the host/port tuple that this UDPClient is connected to. 
    """
    return (self.__host, self.__port)

  def close(self):
    """
    Closes this UDPClient.
    """
    self.__server.removeUDPClient(self)
    self.__SUPER.close()

