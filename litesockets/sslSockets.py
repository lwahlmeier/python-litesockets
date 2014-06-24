import client, socket, logging, struct, ssl
import server

class SSLClient(client.Client):
  def __init__(self, host, port, certfile=None, keyfile=None, ciphers=None, server=False, socket=None):
    self.host = host
    self.port = port
    self.certfile = certfile
    self.keyfile = keyfile
    self.ciphers = ciphers
    self.server = server
    self.plainSock = socket
    self.socket = socket
    self.SUPER = super(SSLClient, self)
    self.SUPER.__init__()
    self.log = logging.getLogger("root.litesockets.SSLClient")
    self.TYPE = "TCP"

  def connect(self):
    if self.plainSock == None and self.server == False:
      self.plainSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.log.debug("connecting %s:%d"%(self.host, self.port))
      self.plainSock.connect((self.host, self.port))
    self.socket = self.do_ssl()
    self.init_conn(self.socket)
    self.SUPER.connect(self.socket, self.TYPE)
    self.log.debug("Client Connected")

  def init_conn(self, sock):
    sock.setblocking(0)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 0, 10))

  def do_ssl(self):
    self.socket = ssl.wrap_socket(self.plainSock, server_side=self.server, certfile=self.certfile, keyfile=self.keyfile, ciphers=self.ciphers)
    return self.socket

  def runRead(self):
    self.SUPER.runRead()

  def getRead(self):
    return self.SUPER.getRead()

  def addRead(self, data):
    self.SUPER.addRead(data)

  def addWrite(self, data):
    self.SUPER.addWrite(data)

  def getWrite(self):
    return self.SUPER.getWrite()

  def reduceWrite(self, size):
    self.SUPER.reduceWrite(size)

  def end(self):
    self.SUPER.end()
    self.plainSock.close()


class SSLServer(server.Server):
  def __init__(self, ip, port, certfile, keyfile):
    self.SUPER = super(SSLServer, self)
    self.SUPER.__init__()
    self.log = logging.getLogger("root.litesockets.TcpServer")
    self.ip = ip
    self.port = port
    self.certfile = certfile
    self.keyfile = keyfile

  def connect(self):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((self.ip, self.port))
    sock.listen(500)
    self.SUPER.connect(sock)

  def addClient(self, client):
    t = SSLClient(client.getpeername()[0], client.getpeername()[1], certfile=self.certfile, keyfile=self.keyfile, server=True, socket = client)
    t.do_ssl()
    self.SUPER.addClient(t)

  def onConnect(self):
    self.SUPER.onConnect()

  def end(self):
    self.SUPER.end()

