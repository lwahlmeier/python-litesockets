import logging, socket
import abc

class Server():
  __metaclass__ = abc.ABCMeta
  log = logging.getLogger("root.litesockets.Server")

  def __init__(self):
    self.log = logging.getLogger("root.litesockets.TcpServer")
    self.TYPE = None
    self.onNew = None
    self.SE = None
    self.socket = None
    self.clients = list()

  def _setSocketExecuter(self, SE):
    self.SE = SE

  @abc.abstractmethod
  def connect(self, socket):
    self.socket = socket

  @abc.abstractmethod
  def addClient(self, client):
    self.clients.append(client)

  @abc.abstractmethod
  def onConnect(self):
    if self.onNew != None:
      self.onNew(self.clients.pop(0))

  @abc.abstractmethod
  def end(self):
    try:
      self.socket.shutdown(socket.SHUT_RDWR)
      self.SE.rmServer(self)
    except:
      pass

