from __future__ import absolute_import, unicode_literals
import threading, socket
from .stats import Stats
from .stats import noExcept
import sys
if sys.version_info < (3,):
  def b(x):
    return x
else:
  import codecs
  def b(x):
    return codecs.latin_1_encode(x)[0]

try:
  xrange(1)
except:
  xrange=range


class Client(object):

  def __init__(self, socketExecuter, TYPE, socket):
    """Default init"""
    self.MAXBUFFER = 16384
    self.__write_buff_list = list()
    self.__write_buff = bytearray()
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
    self.__stats = Stats()
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
      if self.__TYPE == "TCP":
        self.runOnClientThread(self.__reader, args=(self,))
      elif self.__TYPE == "UDP":
        l = len(self.__read_buff_list)
        for i in xrange(l):
          self.runOnClientThread(self.__reader, args=(self,))

  def addCloseListener(self, closer):
    """
    Adds a CloseListener for this client.  As many of these can be added as you want.
    
    `closer` the function to call close on when the client is closed.  
    """
    self.__closers.append(closer)
    
  def getStats(self):
    return self.__stats
    
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
    """
    Returns the data read from this socket.
    
    This should be called on the client each time the the onRead callback is ran.
    """
    self.__readlock.acquire()
    try:
      data = ""
      l = 0
      if(self.__TYPE == "UDP"):
        data = self.__read_buff_list.pop(0)
        l = len(data)
      else:
        data = b''.join(self.__read_buff_list)
        self.__read_buff_list = []
        l = len(data)
      self.__readBuffSize-=l
    finally:
      self.__readlock.release()
    self.__socketExecuter.updateClientOperations(self)
    return data


  def write(self, data):
    """
    Writes provided data to the socket.  The data must be either a string or bytearray.
    
    `data` data to write to the socket.
    """
    if self.__TYPE == "TCP":
      if type(data) == str:
        data = b(data)
      size = len(data)
      data_list = []
      for i in xrange(0,size,1024*64):
        data_list.append(data[i:i+(1024*64)])
      try:
        self.__writelock.acquire()
        self.__write_buff_list.extend(data_list)
        self.__writeBuffSize+=size
      finally:
        self.__writelock.release()
      self.__socketExecuter.updateClientOperations(self)
    elif self.__TYPE == "UDP":
      if type(data[1]) is str:
        data[1] = b(data[1])
      try:
        self.__writelock.acquire()
        self.__write_buff_list.append(data)
        self.__writeBuffSize+=len(data[1])
      finally:
        self.__writelock.release()
      self.__socketExecuter.updateClientOperations(self)
      

  def close(self):
    """
    This closes the socket and should remove the client from the SocketExecuter
    """
    if  not self.__isClosed:
      self.getSocketExecuter().updateClientOperations(self, disable=True)
      self.__readlock.acquire()
      try:
        if  not self.__isClosed:
          self.__isClosed = True
          
          if self.__socket is not None:
            noExcept(self.__socket.shutdown, socket.SHUT_RDWR)
            noExcept(self.__socket.close)
          for cl in self.__closers:
            self.runOnClientThread(cl, args=(self,))
      finally: 
        self.__readlock.release()
      self.getSocketExecuter().updateClientOperations(self)
      
  def isClosed(self):
    """
    Returns True if closed as been called on this client, False otherwise.
    """
    return self.__isClosed

  def _addRead(self, data):
    self.__readlock.acquire()
    try:
      size = len(data)
      self.__read_buff_list.append(data)
      self.__stats._addRead(size)
      self.__readBuffSize+=size
      if self.__readBuffSize > self.MAXBUFFER:
        self.__socketExecuter.updateClientOperations(self)
      if len(self.__read_buff_list) == 1 or self.__TYPE == "UDP":
        if self.__reader != None:
          self.runOnClientThread(self.__reader, args=(self,))
    finally:
      self.__readlock.release()

    
  def _getWrite(self):
    """
    This is called by the SocektExecuter once the socket can write and data is pending from a write call in the Client
    
    This does not remove any data from the writeBuffer as we do not know how much will be written yet (see _reduceWrite)
    """
    self.__writelock.acquire()
    try:
      if len(self.__write_buff) == 0 and len(self.__write_buff_list) > 0:
        if self.__TYPE == "TCP":
          self.__write_buff = bytearray(b''.join(self.__write_buff_list))
          self.__write_buff_list = []
        if self.__TYPE == "UDP":
          self.__write_buff = self.__write_buff_list.pop(0)
    finally:
      self.__writelock.release()
    return self.__write_buff

  def _reduceWrite(self, size):
    """
    This is called by the SocketExecuter once data is written out to the socket to reduce the amount of data on the writeBuffer
    """
    try:
      self.__writelock.acquire()
      self.__writeBuffSize -= size
      if self.__TYPE == "TCP":
        del self.__write_buff[:size]
      elif self.__TYPE == "UDP":
        self.__write_buff = ""
      self.__stats._addWrite(size)
      if self.__writeBuffSize == 0:
        self.__socketExecuter.updateClientOperations(self)
    finally:
      self.__writelock.release()
      
  def _getType(self):
    return self.__TYPE

  
