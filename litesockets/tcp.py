import socket, logging, ssl
import client
import server

class TCPClient(client.Client):

  def __init__(self, host, port, socketExecuter, use_socket = None):
    self.__host = host
    self.__port = port
    if use_socket == None:
      self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.__connected = False
    else:
      self.__socket = use_socket
      self.__socket.setblocking(0)
      self.__connected = True
    self.__SUPER = super(TCPClient, self)
    self.__SUPER.__init__(socketExecuter, "TCP", self.__socket)
    self.__log = logging.getLogger("root.litesockets.TCPClient:"+self.__host+":"+str(self.__port))
    self.__sslEnabled = False
    self.__startSSL = False
    self.__sslArgs = ((), {});
    self.__plainSocket = self.__socket

  def connect(self):
    if not self.__connected:
      self.__connected = True
      self.__log.debug("connecting %s:%d"%(self.__host, self.__port))
      self.__socket.connect((self.__host, self.__port))
      if self.__sslEnabled and self.__startSSL:
        self.startSSL()
      self.__socket.setblocking(0)
      self.__log.debug("Client Connected")
    self.getSocketExecuter().updateClientOperations(self)

      
  def getSocket(self):
    return self.__socket

    
  def enableSSL(self, start=False, *args, **kwargs):
    if not self.__sslEnabled:
      self.__sslEnabled = True
      self.__sslArgs = (args, kwargs)
      self.__startSSL = start
      self.__sslArgs[1]["do_handshake_on_connect"] = True
      if start and self.__connected:
        self.startSSL()
    else:
      raise Exception("cant set ssl again on socket!")
    
  def startSSL(self):
    self.__startSSL = True
    if self.__connected:
      self.getSocketExecuter().updateClientOperations(self, disable=True)
      self.__socket.setblocking(1)
      tmpSocket = ssl.wrap_socket(self.__plainSocket, *self.__sslArgs[0], **self.__sslArgs[1])
      self.__socket = tmpSocket
      self.__socket.setblocking(0)
      self.getSocketExecuter().updateClientOperations(self)

class TCPServer(server.Server):
  """
  A TCPServer instance. Notifiying you when new TCPClients connect.
  """
  def __init__(self, socketExecuter, host, port):
    """
    Constructs a new TCPServer.  This should never be created manually instead use createTCPServer
    on a started SocketExecuter object. 
    """
    self.__logString = "root.litesockets.TCPServer:"+host+":"+str(port)
    self.__log = logging.getLogger()
    self.__host = host
    self.__port = port
    self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.__socket.bind((self.__host, self.__port))
    self.__socket.listen(500)
    self.__SUPER = super(TCPServer, self)
    self.__SUPER.__init__(socketExecuter, self.__socket, "TCP")
    self.__ssl_info = None
    
  def setSSLInfo(self, **kwargs):
    """
    Sets ssl information for this socket. Takes the same arguments used in wrap_socket.  If do_handshake_on_connect is set to true
    we will do the handshake on the TCPClient immediately otherwise startSSL() will have to be called on the TCPClient to start.
    """
    self.__ssl_info = {}
    self.__ssl_info.update(kwargs)
    
    
  def addClient(self, client):
    if self.getOnClient() != None:
      tcp_client = self.getSocketExecuter().createTCPClient(client.getpeername()[0], client.getpeername()[1], use_socket = client)
      if self.__ssl_info != None:
        tcp_client.enableSSL(**self.__ssl_info)
      self.getSocketExecuter().updateClientOperations(tcp_client)
      self.getSocketExecuter().getScheduler().schedule(self.getOnClient(), args=(tcp_client,))

