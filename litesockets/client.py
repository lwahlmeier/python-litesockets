import threading

class Client(object):

  def __init__(self, socketExecuter, TYPE):
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
    
  def setReader(self, reader):
    self.__reader = reader

  def addCloseListener(self, closer):
    self.__closers.append(closer)
  
  def getType(self):
    return self.__TYPE
    
  def getSocketExecuter(self):
    return self.__socketExecuter
  
  def getWriteBufferSize(self):
    return self.__writeBuffSize
  
  def getReadBufferSize(self):
    return self.__readBuffSize
  
  def getSocket(self):
    return None
  
  def runOnClientThread(self, task, args=(), kwargs={}):
    print "run", task
    self.__socketExecuter.getScheduler().schedule(task, key=self, args=args, kwargs=kwargs)

  def getRead(self):
    """Called by whoever created the client to get the read... 
    this should only be called once per __doRead event.  
    This will return a string with data"""
    self.__readlock.acquire()
    try:
      data = "".join(self.__read_buff_list)
      self.__read_buff_list = []
      l = len(data)
      self.__readBuffSize-=l
      if (self.__readBuffSize+l) >= self.MAXBUFFER and self.__readBuffSize < self.MAXBUFFER:
        self.__socketExecuter.setRead(self, on=True)
      return data
    finally:
      self.__readlock.release()

  def addRead(self, data):
    """This is called by the SocketExecuter once data is read off the socket"""
    self.__readlock.acquire()
    try:
      self.__read_buff_list.append(data)
      self.__readBuffSize+=len(data)
      if self.__readBuffSize > self.MAXBUFFER:
        self.__socketExecuter.setRead(self, on=False)
      if len(self.__read_buff_list) == 1:
        print "run Read"
        if self.__reader != None:
          self.runOnClientThread(self.__reader, args=(self,))
    finally:
      self.__readlock.release()

  def write(self, data):
    self.__writelock.acquire()
    self.__write_buff_list.append(data)
    self.__writeBuffSize+=len(data)
    self.__writelock.release()
    self.__socketExecuter.setWrite(self, True)

  def getWrite(self):
    """this is called by the SocektExecuter once addWrite has added data to write to the socket and the socket is ready to be written to.
     This does not remove any data from the writeBuffer as we will not know how much will be written yet (reduce write)"""
    #done need a lock here since we are not changing anything yet
    if self.__write_buff == "" and len(self.__write_buff_list) > 0:
      self.__writelock.acquire()
      try:
        
        self.__write_buff = "".join(self.__write_buff_list)
      finally:
        self.__writelock.release()
    return self.__write_buff

  def reduceWrite(self, size):
    """This is called by the SocketExecuter once data is written out to the socket to reduce the amount of data on the writeBuffer"""
    self.__writelock.acquire()
    try:
      print "reduce", size
      self.__writeBuffSize -= size
      self.__write_buff = self.__write_buff[size:]
      if self.__writeBuffSize == 0:
        self.__socketExecuter.setWrite(self, on=False)
      if self.__writeBuffSize < self.MAXBUFFER:
        self.__writelock.notify()
    finally:
      self.__writelock.release()


  def close(self):
    """This closes the socket and should remove the client from the SocketExecuter"""
    self.__readlock.acquire()
    try:
      if  not self.__isClosed:
        self.__isClosed = True
        try:
          self.__socket.close()
        except Exception:
          #We dont care at this point!
          pass
        finally:
          for cl in self.__closers:
            self.runOnClientThread(cl, args=(self,))
    finally: 
      self.__readlock.acquire()
