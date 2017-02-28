import socket

class Server(object):
  def __init__(self, socketExecuter, socket, TYPE):
    self.__socketExecuter = socketExecuter
    self.__TYPE = TYPE
    self.__socket = socket
    self.__closed = False;
    self.__closers = list()
    self.__acceptor = None
    self.__fd = None
    if self.__socket != None:
      self.__fd = socket.fileno()

  def setOnClient(self, acceptor):
    """
    Sets the onClient callback.  Should be a function pointer taking 1 argument for the 
    new Client object created by this Server.
    """
    self.__acceptor = acceptor

  def getFileDesc(self):
    """
    Returns the FileDescriptor number for this client.
    """
    return self.__fd

    
  def _getType(self):
    return self.__TYPE
  
  def getSocket(self):
    """
    Returns the raw socket object associated with this server.
    """
    return self.__socket

  def getSocketExecuter(self):
    """
    Returns the SocketExecuter object associated with this Server.
    """
    return self.__socketExecuter

  def start(self):
    """
    Starts Listening with this Server Instance.
    """
    if not self.__closed:
      self.__socketExecuter.startServer(self)
    
  def stop(self):
    """
    Stops Listening with this Server Instance.
    """
    if not self.__closed:
      self.__socketExecuter.stopServer(self)
    
  def addCloseListener(self, closer):
    """
    Adds a close listener callback function. This function must take 1 argument
    which will be the server that is being closed.  You can have as many close listeners 
    added as you want.
    """
    self.__closers.append(closer)
    
  def getOnClient(self):
    """
    Returns the onClient listener callback.
    """
    return self.__acceptor

  def close(self):
    """
    Closes this server.  Once this is called the server will no longer be bound to its listen port 
    and can no longer be started.
    """
    if not self.__closed:
      self.__closed = True
      try:
        self.__socket.close()
        #self.__socket.shutdown(socket.SHUT_RDWR)
        #try:
        #except Exception as e:
        #  pass
 
      except Exception as e:
        pass
      for cl in self.__closers:
        self.__socketExecuter.getScheduler().execute(cl, args=(self,))
      
  def addClient(self, client):
    pass
