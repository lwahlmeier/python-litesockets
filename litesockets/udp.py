import socket, logging, struct, ssl
from litesockets import client


class UdpServer(client.Client):
  def __init__(self, ip, port):
    self.TYPE = "UDP"
    self.log = logging.getLogger("root.litesockets.UdpServer")
    self.ip = ip
    self.port = port
    self.server = self
    self.SUPER = super(UdpServer, self)
    self.SUPER.__init__();
    self.clients = dict()
    self.onNew = None

  def connect(self):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((self.ip, self.port))
    self.SUPER.connect(sock, self.TYPE)

  def runRead(self):
    X = self.read_buff.pop(0)
    if self.onNew == None:
      return
    if X[0] not in self.clients:
      client = UdpClient(self, X[0][0], X[0][1])
      self.onNew(client)
      self.clients[X[0]] = client
    self.clients[X[0]].addRead(X[1])
    self.clients[X[0]].runRead()

  def addWrite(self, data):
    self.socket.sendto(data[1], data[0])

  def getWrite(self):
    pass

  def reduceWrite(self, size):
    pass

  def addRead(self, data):
    try:
      self.readlock.acquire()
      self.readBuffSize += len(data[1])
      self.read_buff.append(data)
      if self.readBuffSize > self.MAXBUFFER:
        self.SE.setRead(self, on=False)
    finally:
      self.readlock.release()

  def getRead(self):
    return self.SUPER.getRead()

  def end(self):
    try:
      self.socket.shutdown(socket.SHUT_RDWR)
    except:
      pass

  def mkUdpClient(host, port):
      client = UdpClient(host, port, self)
      self.clients[X[0]] = client
    


class UdpClient(client.Client):
  def __init__(self, udpServer, host, port):
    self.TYPE = "UDP"
    self.host = socket.gethostbyname(host)
    self.port = port
    self.server = udpServer
    self.server.clients[(self.host, self.port)] = self
    self.log = logging.getLogger("root.litesockets.UdpClient")
    self.SUPER = super(UdpClient, self)
    self.SUPER.__init__()

  def connect(self):
    self.SUPER.connect(None, self.TYPE)

  def runRead(self):
    self.SUPER.runRead()

  def addWrite(self, data):
    self.server.addWrite([(self.host, self.port), data])

  def reduceWrite(self, size):
    pass

  def getWrite(self):
    pass

  def addRead(self, data):
    self.SUPER.addRead(data)

  def getRead(self):
    return self.SUPER.getRead()

  def end(self):
    if self.created_server:
      self.server.end()
    else:
      del self.server.clients[(self.host, self.port)]

