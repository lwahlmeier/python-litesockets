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
    X = self.getRead()
    if self.onNew == None:
      return
    if X[0] not in self.clients:
      client = UdpClient(self, X[0][0], X[0][1])
      self.onNew(client)
      self.clients[X[0]] = client
    self.clients[X[0]].addRead(X[1])
    self.SE.Executor.schedule(self.clients[X[0]].runRead, key=self.clients[X[0]])

  def addWrite(self, data):
    self.socket.sendto(data[1], data[0])

  def writeTry(self, data):
    self.socket.sendto(data[1], data[0])

  def writeBlocking(self, data):
    self.socket.sendto(data[1], data[0])

  def writeForce(self, data):
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
    self.readlock.acquire()
    try:
      data = self.read_buff.pop(0)
      l = len(data[1])
      self.readBuffSize-=l
      if (self.readBuffSize+l) >= self.MAXBUFFER and self.readBuffSize < self.MAXBUFFER:
        self.SE.setRead(self, on=True)
      return data
    finally:
      self.readlock.release()

  def end(self):
    try:
      self.socket.shutdown(socket.SHUT_RDWR)
    except:
      pass

  def mkUdpClient(self, host, port):
      client = UdpClient(self, host, port)
      self.clients[(client.host, client.port)] = client
      return client
    


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

  def writeTry(self, data):
    self.server.addWrite([(self.host, self.port), data])

  def writeBlocking(self, data):
    self.server.addWrite([(self.host, self.port), data])

  def writeForce(self, data):
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

