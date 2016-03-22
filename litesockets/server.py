import socket

class Server(object):

  def __init__(self, socketExecuter, socket, TYPE):
    self.__socketExecuter = socketExecuter
    self.__TYPE = TYPE
    self.__socket = socket
    self.__closed = False;
    self.__closers = list()
    self.__acceptor = None
    
  def setOnClient(self, acceptor):
    self.__acceptor = acceptor
    
  def getType(self):
    return self.__TYPE
  
  def getSocket(self):
    return self.__socket

  def getSocketExecuter(self):
    return self.__socketExecuter

  def start(self):
    self.__socketExecuter.startServer(self)
    
  def stop(self):
    self.__socketExecuter.stopServer(self)
    
  def getOnClient(self):
    return self.__acceptor

  def close(self):
    if not self.__closed:
      self.__closed = True
      try:
        self.__socketExecuter.stopServer(self)
        self.__socket.shutdown(socket.SHUT_RDWR)
        for cl in self.__closers:
          self.__socketExecuter.getScheduler(cl, args=(self,))
      except:
        pass
      
  def addClient(self, client):
    pass
