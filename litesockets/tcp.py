import socket, logging, struct, ssl
import client
import server

class TCPClient(client.Client):
  def __init__(self, host, port, socketExecuter, use_socket = None):
    self.__host = host
    self.__port = port
    if use_socket == None:
      self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
      self.__socket = use_socket
    self.__SUPER = super(TCPClient, self)
    self.__SUPER.__init__(socketExecuter, "TCP", self.__socket)
    self.__log = logging.getLogger("root.litesockets.TCPClient:"+self.__host+":"+str(self.__port))
    self.__connected = False
    self.__sslEnabled = False
    self.__sslArgs = ((), {});
    self.__plainSocket = self.__socket

  def connect(self):
    self.__log.debug("connecting %s:%d"%(self.__host, self.__port))
    self.__socket.connect((self.__host, self.__port))
    self.__socket.setblocking(0)
    self.__socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 0, 10))
    self.__log.debug("Client Connected")
    self.__connected = True
    if self.__sslEnabled:
      self.startSSL()
    
  def enableSSL(self, args=(), kwargs={}):
    self.__sslEnabled = True
    self.__sslArgs = (args, kwargs)
    if self.__connected:
      self.startSSL()
    
  def startSSL(self):
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
    
  def addClient(self, client):
    if self.getOnClient() != None:
      tcp_client = TCPClient(client.getpeername()[0], client.getpeername()[1], self.getSocketExecuter(), set_socket = client)
      self.getSocketExecuter().getScheduler().schedule(self.getOnClient(), args=(tcp_client,))

