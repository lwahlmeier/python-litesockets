import socket, logging, ssl
from . import client
from . import server
from .stats import noExcept

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
    self.__sslEnabled = False
    self.__startSSL = False
    self.__sslArgs = ((), {});
    self.__plainSocket = self.__socket
    self.__log = logging.getLogger("root.litesockets.{}".format(self))
    if self.__connected:
      self.__log.info("Created new Connected Client")
    else:
      self.__log.info("Created new unconnected Client")


  def __str__(self):
    return "TCPClient:{}:{},{}".format(self.__host,self.__port,self.getFileDesc())

  def connect(self):
    if not self.__connected:
      self.__connected = True
      self.__log.debug("Connecting Client")
      self.__socket.connect((self.__host, self.__port))
      if self.__sslEnabled and self.__startSSL:
        self.startSSL()
      self.__socket.setblocking(0)
      self.__log.debug("Client is Connected")
    self.getSocketExecuter().updateClientOperations(self)

      
  def getSocket(self):
    return self.__socket

    
  def enableSSL(self, **kwargs):
    if not self.__sslEnabled:
      self.__sslEnabled = True
      self.__sslArgs = (kwargs)
      if "do_handshake_on_connect" in kwargs:
        self.__startSSL = kwargs["do_handshake_on_connect"]
      else:
        self.__startSSL = False
      #we always set this to true because when we wrap we want it to start
      self.__sslArgs["do_handshake_on_connect"] = True
      if self.__startSSL and self.__connected:
        self.startSSL()
    else:
      raise Exception("cant set ssl again on socket!")
    
  def startSSL(self):
    self.__startSSL = True
    if self.__connected:
      self.getSocketExecuter().updateClientOperations(self, disable=True)
      self.__socket.setblocking(1)
      tmpSocket = ssl.wrap_socket(self.__plainSocket, **self.__sslArgs)
      self.__socket = tmpSocket
      self.__socket.setblocking(0)
      self.getSocketExecuter().updateClientOperations(self)

  def close(self):
    if not self.isClosed():
      noExcept(self.__socket.close)
      self.__SUPER.close()

class TCPServer(server.Server):
  """
  A TCPServer instance. Notifiying you when new TCPClients connect.
  """
  def __init__(self, socketExecuter, host, port):
    """
    Constructs a new TCPServer.  This should never be created manually instead use createTCPServer
    on a started SocketExecuter object. 
    """
    self.__host = host
    self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.__socket.bind((self.__host, port))
    self.__socket.listen(500)
    self.__port = self.__socket.getsockname()[1]
    self.__SUPER = super(TCPServer, self)
    self.__SUPER.__init__(socketExecuter, self.__socket, "TCP")
    self.__ssl_info = None
    self.__logString = "root.litesockets.TCPServer:{}".format(self)
    self.__log = logging.getLogger(self.__logString)
    self.__log.info("New Server Created")

  def __str__(self):
    return "TCPServer:{}:{},{}".format(self.__host,self.__port,self.getFileDesc())

    
  def setSSLInfo(self, **kwargs):
    """
    Sets ssl information for this socket. Takes the same arguments used in wrap_socket.  If do_handshake_on_connect is set to true
    we will do the handshake on the TCPClient immediately otherwise startSSL() will have to be called on the TCPClient to start.
    """
    kwargs['server_side'] = True
    self.__ssl_info = {}
    self.__ssl_info.update(kwargs)
    
    
  def addClient(self, client):
    if self.getOnClient() != None:
      tcp_client = self.getSocketExecuter().createTCPClient(client.getpeername()[0], client.getpeername()[1], use_socket = client)
      if self.__ssl_info != None:
        tcp_client.enableSSL(**self.__ssl_info)
      self.getSocketExecuter().updateClientOperations(tcp_client)
      self.getSocketExecuter().getScheduler().schedule(self.getOnClient(), args=(tcp_client,))

