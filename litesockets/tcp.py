import client, socket, logging, struct, ssl
import server

class TcpClient(client.Client):
  def __init__(self, host, port):
    self.host = host
    self.port = port
    self.SUPER = super(TcpClient, self)
    self.SUPER.__init__()
    self.log = logging.getLogger("root.litesockets.TcpClient")
    self.TYPE = "TCP"

  def connect(self):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.log.debug("connecting %s:%d"%(self.host, self.port))
    sock.connect((self.host, self.port))
    self.init_conn(sock)
    self.SUPER.connect(sock, self.TYPE)
    self.log.debug("Client Connected")

  def init_conn(self, sock):
    sock.setblocking(0)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 0, 10))

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


class TcpServer(server.Server):
  def __init__(self, ip, port):
    self.SUPER = super(TcpServer, self)
    self.SUPER.__init__()
    self.log = logging.getLogger("root.litesockets.TcpServer")
    self.ip = ip
    self.port = port

  def connect(self):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((self.ip, self.port))
    sock.listen(500)
    self.SUPER.connect(sock)

  def addClient(self, client):
    t = TcpClient(client.getpeername()[0], client.getpeername()[1])
    t.socket = client
    self.SUPER.addClient(t)

  def onConnect(self):
    self.SUPER.onConnect()

  def end(self):
    self.SUPER.end()

