import abc, logging, threading

class Client(object):
  __metaclass__ = abc.ABCMeta
  log = logging.getLogger("root.litesockets.Client")

  def __init__(self):
    """Default init"""
    self.MAXBUFFER = 16384
    self.write_buff = list()
    self.writeBuffSize = 0

    self.read_buff = list()
    self.readBuffSize = 0

    self.reader = None
    self.closer = None
    self.writelock = threading.Condition()
    self.readlock = threading.Condition()
    self.SE = None

  @abc.abstractmethod
  def connect(self, socket, socketType):
    self.TYPE = socketType
    self.socket = socket

    return

  @abc.abstractmethod
  def runRead(self):
    """Called by the socket executer to complete an action once a read with data comes in"""
    if self.reader != None:
      self.reader(self)
    return

  @abc.abstractmethod    
  def getRead(self):
    """Called by whoever created the client to get the read... 
    this should only be called once per __doRead event.  
    This will return a string with data"""
    self.readlock.acquire()
    try:
      data = self.read_buff.pop(0)
      l = len(data)
      self.readBuffSize-=l
      if (self.readBuffSize+l) >= self.MAXBUFFER and self.readBuffSize < self.MAXBUFFER:
        self.SE.setRead(self, on=True)
      return data
    finally:
      self.readlock.release()

  def _setSocketExecuter(self, SE):
    self.SE = SE

  @abc.abstractmethod
  def addRead(self, data):
    """This is called by the SocketExecuter once data is read off the socket"""
    self.readlock.acquire()
    try:
      self.read_buff.append(data)
      self.readBuffSize+=len(data)
      if self.readBuffSize > self.MAXBUFFER:
        self.SE.setRead(self, on=False)
    finally:
      self.readlock.release()

  @abc.abstractmethod
  def addWrite(self, data):
    """This will add data to be written on the socket.  Make sure this is called once with all needed data or single threaded, otherwise data might get written out of order.
    This function will block if you are writting to fast.  It should be safe to call with the Thread you get a Read on Even if your talking to yourself (unless the SocketExecuter is limited to 1 thread)"""
    self.writelock.acquire()
    try:
      self.write_buff.extend(data)
      self.writeBuffSize+=len(data)
      if self.writeBuffSize > 0:
        self.SE.setWrite(self, True)
      while self.writeBuffSize >= self.MAXBUFFER:
        self.writelock.wait()
    finally:
      self.writelock.release()

  @abc.abstractmethod
  def getWrite(self):
    """this is called by the SocektExecuter once addWrite has added data to write to the socket and the socket is ready to be written to.
     This does not remove any data from the writeBuffer as we will not know how much will be written yet (reduce write)"""
    #done need a lock here since we are not changing anything yet
    return "".join(self.write_buff)

  @abc.abstractmethod
  def reduceWrite(self, size):
    """This is called by the SocketExecuter once data is written out to the socket to reduce the amount of data on the writeBuffer"""
    self.writelock.acquire()
    try:
      self.writeBuffSize -= size
      while size > 0:
        l = len(self.write_buff[0])
        if l <= size:
          self.write_buff.pop(0)
          size-=l
        else:
          self.write_buff[0] = self.write_buff[0][size:]
          size = 0

      if self.writeBuffSize == 0:
        self.SE.setWrite(self, on=False)
      if self.writeBuffSize < self.MAXBUFFER:
        self.writelock.notify()
    finally:
      self.writelock.release()


  @abc.abstractmethod
  def end(self):
    """This closes the socket and should remove the client from the SocketExecuter"""
    self.SE.rmClient(self)
    self.socket.close()
  
