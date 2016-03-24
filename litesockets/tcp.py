import socket, logging, struct, ssl
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
      self.__connected = True
    self.__SUPER = super(TCPClient, self)
    self.__SUPER.__init__(socketExecuter, "TCP", self.__socket)
    print self.__host, type(self.__host)
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
      self.__socket.setblocking(0)
      self.__socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
      self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 0, 10))
      self.__log.debug("Client Connected")
      if self.__sslEnabled and self.__startSSL:
        self.startSSL()
    
  def enableSSL(self, start=False, args=(), kwargs={}):
    if not self.__sslEnabled:
      self.__sslEnabled = True
      self.__sslArgs = (args, kwargs)
      self.__startSSL = start
      if start and self.__connected:
        self.startSSL()
    else:
      raise Exception("cant set ssl again on socket!")
    
  def startSSL(self):
    self.__startSSL = True
    if self.__connected:
      tmpSocket = ssl.wrap_socket(self.__plainSocket, *self.__sslArgs[0], **self.__sslArgs[1])
      self.__socket = tmpSocket

class TCPServer(server.Server):
  def __init__(self, socketExecuter, host, port):
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
    
  def setSSLInfo(self, certFile, keyFile, doHandshake=False, hostname=None, kwargs={}):
    self.__ssl_info = {"keyfile":keyFile, "certfile":certFile, "server_side":True, "do_handshake_on_connect":doHandshake}
    self.__ssl_info.update(kwargs)
    
    
  def addClient(self, client):
    if self.getOnClient() != None:
      tcp_client = self.getSocketExecuter().createTCPClient(client.getpeername()[0], client.getpeername()[1], use_socket = client)
      if self.__ssl_info != None:
        tcp_client.enableSSL(**self.__ssl_info)
      self.getSocketExecuter().getScheduler().schedule(self.getOnClient(), args=(tcp_client,))

