import threading, socket
import socketexecuter

class Client(object):

  def __init__(self, socketExecuter, TYPE, socket):
    """Default init"""
    self.MAXBUFFER = 16384
    self.__write_buff_list = list()
    self.__write_buff = ""
    self.__writeBuffSize = 0

    self.__read_buff_list = list()
    self.__readBuffSize = 0

    self.__reader = None
    self.__closers = list()
    self.__writelock = threading.Condition()
    self.__readlock = threading.Condition()
    self.__socketExecuter = socketExecuter
    self.__isClosed = False
    self.__TYPE = TYPE
    self.__socket = socket
    self.__fd = None
    if self.__socket != None:
      self.__fd = socket.fileno()
    
  def connect(self):
    raise Exception("Not Implemented!")
  
  def getFileDesc(self):
    """
    Returns the FileDescriptor number for this client.
    """
    return self.__fd
    
  def setReader(self, reader):
    """
    Sets the reader for this client. Only one can be set at a time for any client.
    
    `reader` the reader function to callback on reads.  The client object is passed in with this
    """
    self.__reader = reader
    if self.__readBuffSize > 0:
      self.runOnClientThread(self.__reader, args=(self,))

  def addCloseListener(self, closer):
    """
    Adds a CloseListener for this client.  As many of these can be added as you want.
    
    `closer` the function to call close on when the client is closed.  
    """
    self.__closers.append(closer)
    
  def getSocketExecuter(self):
    """
    Returns the socketExecuter for this Client.
    """
    return self.__socketExecuter
  
  def getWriteBufferSize(self):
    """
    Returns the currently buffered write size.  This is the amount of
    data that has not yet been written to the socket.
    """
    return self.__writeBuffSize
  
  def getReadBufferSize(self):
    """
    Returns the amount of data currently in the clients read buffer.
    """
    return self.__readBuffSize
  
  def getSocket(self):
    """
    Returns the socket object for this client.
    """
    return self.__socket
  
  def runOnClientThread(self, task, args=(), kwargs={}):
    """
    Runs set function on this clients Thread queue.
    """
    self.__socketExecuter.getScheduler().schedule(task, key=self, args=args, kwargs=kwargs)

  def getRead(self):
    """Called by whoever created the client to get the read... 
    this should only be called once per __doRead event.  
    This will return a string with data"""
    self.__readlock.acquire()
    try:
      data = ""
      l = 0
      if(self.__TYPE == "UDP"):
        data = self.__read_buff_list.pop(0)
        l = len(data)
      else:
        data = "".join(self.__read_buff_list)
        self.__read_buff_list = []
        l = len(data)
      self.__readBuffSize-=l
      if (self.__readBuffSize+l) >= self.MAXBUFFER and self.__readBuffSize < self.MAXBUFFER:
        self.__socketExecuter.updateClientOperations(self)
      return data
    finally:
      self.__readlock.release()

  def write(self, data):
    self.__writelock.acquire()
    self.__write_buff_list.append(data)
    self.__writeBuffSize+=len(data)
    self.__writelock.release()
    self.__socketExecuter.updateClientOperations(self)

  def close(self):
    """This closes the socket and should remove the client from the SocketExecuter"""
    if  not self.__isClosed:
      self.__readlock.acquire()
      try:
        if  not self.__isClosed:
          self.__isClosed = True
          socketexecuter.noExcept(self.__socket.shutdown, socket.SHUT_RDWR)
          socketexecuter.noExcept(self.__socket.close)
          for cl in self.__closers:
            self.runOnClientThread(cl, args=(self,))
      finally: 
        self.__readlock.acquire()
      self.getSocketExecuter().updateClientOperations(self)
      
  def isClosed(self):
    """
    Returns True if closed as been called on this client, False otherwise.
    """
    return self.__isClosed

  def _addRead(self, data):
    self.__readlock.acquire()
    try:
      self.__read_buff_list.append(data)
      self.__readBuffSize+=len(data)
      if self.__readBuffSize > self.MAXBUFFER:
        self.__socketExecuter.updateClientOperations(self)
      if len(self.__read_buff_list) == 1 or self.__TYPE == "UDP":
        if self.__reader != None:
          self.runOnClientThread(self.__reader, args=(self,))
    finally:
      self.__readlock.release()

    
  def _getWrite(self):
    """this is called by the SocektExecuter once addWrite has added data to write to the socket and the socket is ready to be written to.
     This does not remove any data from the writeBuffer as we will not know how much will be written yet (reduce write)"""
    #done need a lock here since we are not changing anything yet
    if self.__write_buff == "" and len(self.__write_buff_list) > 0:
      self.__writelock.acquire()
      try:
        self.__write_buff = "".join(self.__write_buff_list)
        self.__write_buff_list = []
      finally:
        self.__writelock.release()
    return self.__write_buff

  def _reduceWrite(self, size):
    """This is called by the SocketExecuter once data is written out to the socket to reduce the amount of data on the writeBuffer"""
    self.__writelock.acquire()
    try:
      self.__writeBuffSize -= size
      self.__write_buff = self.__write_buff[size:]
      if self.__writeBuffSize == 0:
        self.__socketExecuter.updateClientOperations(self)
    finally:
      self.__writelock.release()
      
  def _getType(self):
    return self.__TYPE
  
  