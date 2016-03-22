import socket, logging, struct, ssl
from litesockets import client, socketexecuter


class UDPServer(client.Client):
  def __init__(self, ip, port):
    self.TYPE = "UDP"
    self.log = logging.getLogger("root.litesockets.UdpServer")
    self.ip = ip
    self.port = port
    self.server = self
    self.SUPER = super(UDPServer, self)
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
      client = UDPClient(self, X[0][0], X[0][1])
      self.onNew(client)
      self.clients[X[0]] = client
    self.clients[X[0]].addRead(X[1])
    self.__socketExecuter.Executor.schedule(self.clients[X[0]].runRead, key=self.clients[X[0]])

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
      self.__readlock.acquire()
      self.__readBuffSize += len(data[1])
      self.__read_buff_list.append(data)
      if self.__readBuffSize > self.MAXBUFFER:
        self.__socketExecuter.setRead(self, on=False)
    finally:
      self.__readlock.release()

  def getRead(self):
    self.__readlock.acquire()
    try:
      data = self.__read_buff_list.pop(0)
      l = len(data[1])
      self.__readBuffSize-=l
      if (self.__readBuffSize+l) >= self.MAXBUFFER and self.__readBuffSize < self.MAXBUFFER:
        self.__socketExecuter.setRead(self, on=True)
      return data
    finally:
      self.__readlock.release()

  def end(self):
    try:
      self.socket.shutdown(socket.SHUT_RDWR)
    except:
      pass

  def mkUDPClient(self, host, port):
      client = UDPClient(self, host, port)
      self.clients[(client.host, client.port)] = client
      return client
    


class UDPClient(client.Client):
  def __init__(self, udpServer, host, port, socketExecuter):
    self.__host = socket.gethostbyname(host)
    self.__port = port
    self.__server = udpServer
    self.__server.clients[(self.host, self.port)] = self
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

  def close(self):
    del self.__server.clients[(self.host, self.port)]

