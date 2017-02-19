import select, logging, threading, sys, ssl, errno, socket, platform
from threadly import Scheduler, Clock
from .client import Client
from .server import Server
from .tcp import TCPClient, TCPServer
from .udp import UDPServer

if not "EPOLLRDHUP" in dir(select):
  select.EPOLLRDHUP = 0x2000

EMPTY_STRING = ""

class SelectSelector():
  def __init__(self, readCallback, writeCallback, acceptCallback, errorCallback):
    self.__log = logging.getLogger("root.litesockets.SelectSelector")
    self.__log.info("Creating basic select selector for: {}".format(platform.system()))
    self.__readCallback = readCallback
    self.__writeCallback = writeCallback
    self.__acceptCallback = acceptCallback
    self.__errorCallback = errorCallback
    
    self.__readClients = set()
    self.__writeClients = set()
    self.__acceptServers = set()
    
    self.__nb_readClients = set()
    self.__nb_writeClients = set()
    self.__nb_acceptServers = set()
    
    self.__writeLock = threading.Condition()
    self.__readLock = threading.Condition()
    self.__acceptLock = threading.Condition()
    self.__nbLock = threading.Condition()
    
    self.__localExecuter = Scheduler(5) #need 5 thread, all can be blocked at once
    self.__running = True
    self.__localExecuter.execute(self.__doReads)
    self.__localExecuter.execute(self.__doWrites)
    self.__localExecuter.execute(self.__doAcceptor)
    
    
  def stop(self):
    self.__running = False
    
  def addServer(self, fileno):
    self.__acceptLock.acquire()
    self.__acceptServers.add(FileNoWrapper(fileno))
    self.__acceptLock.release()
      
  def removeServer(self, fileno):
    now = FileNoWrapper(fileno)
    if now in self.__acceptServers:
      self.__acceptServers.remove(now)
    
  def addReader(self, fileno):
    now = FileNoWrapper(fileno)
    if now in self.__readClients or now in self.__nb_readClients:
      return
    if self.__readLock.acquire(blocking=False):
      self.__readClients.add(now)
      self.__readLock.release()
    else:
      self.__nb_readClients.add(now)
      self.__localExecuter.schedule(self.__tmpClientSelect, delay=0, recurring=False, key="SimpleKey")
      self.__localExecuter.schedule(self.__update_from_nb_selector, key="UpdateTask")
      
  def removeReader(self, fileno):
    now = FileNoWrapper(fileno)
    if now in self.__readClients:
      self.__readClients.remove(now)
    if now in self.__nb_readClients:
      self.__nb_readClients.remove(now)
    
  def addWriter(self, fileno):
    now = FileNoWrapper(fileno)
    if now in self.__writeClients or now in self.__nb_writeClients:
      return
    if self.__writeLock.acquire(blocking=False):
      self.__writeClients.add(now)
      self.__writeLock.release()
    else:
      self.__nb_writeClients.add(now)
      self.__localExecuter.schedule(self.__tmpClientSelect, key="SimpleKey")
      self.__localExecuter.schedule(self.__update_from_nb_selector, key="UpdateTask")
      
  def removeWriter(self, fileno):
    now = FileNoWrapper(fileno)
    if now in self.__writeClients:
      self.__writeClients.remove(now)
    if now in self.__nb_writeClients:
      self.__nb_writeClients.remove(now)
    
  def __doThread(self, t):
    while self.__running:
      try:
        t()
      except Exception as e:
        self.__log.error("GP Socket Exception: %s: %s"%(t, sys.exc_info()[0]))
        self.__log.error(e)
        
  def __update_from_nb_selector(self):
    if len(self.__nb_readClients) + len(self.__nb_writeClients) == 0:
      return
    else:
      self.__readLock.acquire()
      self.__nbLock.acquire()
      for r in self.__nb_readClients:
        self.__readClients.add(r)
      self.__nb_readClients.clear()
      self.__nbLock.release()
      self.__readLock.release()
      
      self.__writeLock.acquire()
      self.__nbLock.acquire()
      for r in self.__nb_writeClients:
        self.__writeClients.add(r)
      self.__nb_writeClients.clear()
      
      self.__nbLock.release()
      self.__writeLock.release()
      
  def __tmpClientSelect(self):
    if len(self.__nb_readClients) + len(self.__nb_writeClients) == 0:
      return
    self.__nbLock.acquire()
    rlist, wlist, xlist = select.select(self.__nb_readClients, self.__nb_writeClients, self.__readClients, 0.001)
    for rdy in rlist:
      try:
        self.__readCallback(rdy.fileno())
      except Exception as e:
        self.__log.debug("nbRead Error: %s"%(sys.exc_info()[0]))
        self.__log.debug(e)
        
    for rdy in wlist:
      try:
        self.__writeCallback(rdy.fileno())
      except Exception as e:
        self.__log.debug("nbWrite Error: %s"%(sys.exc_info()[0]))
        self.__log.debug(e)
        
    for bad in xlist:
      try:
        self.__errorCallback(bad.fileno())
      except:
        self.__log.debug("nberrorCB Error: %s"%(sys.exc_info()[0]))
        self.__log.debug(e)
        
    self.__nbLock.release()
    if len(self.__nb_readClients) + len(self.__nb_writeClients) > 0:
      self.__localExecuter.schedule(self.__tmpClientSelect, key="SimpleKey")
      
        
  def __doReads(self):
    rlist = []
    wlist = []
    xlist = []
    self.__readLock.acquire()
    if len(self.__readClients) > 0:
      rlist, wlist, xlist = select.select(self.__readClients, [], self.__readClients, .1)
    self.__readLock.release()
    
    for rdy in rlist:
      try:
        if rdy in self.__readClients:
          self.__readCallback(rdy.fileno())
      except Exception as e:
        self.__log.debug("Read Error: %s"%(sys.exc_info()[0]))
        self.__log.debug(e)
        
    for bad in xlist:
      try:
        self.__errorCallback(bad.fileno())
      except:
        self.__log.debug("errorCB Error: %s"%(sys.exc_info()[0]))
        self.__log.debug(e)
    if self.__running:
      self.__localExecuter.execute(self.__doReads)
    
  def __doWrites(self):
    rlist = []
    wlist = []
    xlist = []
    self.__writeLock.acquire()
    if len(self.__writeClients) > 0:
      rlist, wlist, xlist = select.select([], self.__writeClients,[] , .1)
    self.__writeLock.release()
    for rdy in wlist:
      try:
        if rdy in self.__writeClients:
          self.__writeCallback(rdy.fileno())
      except Exception as e:
        self.__log.debug("Write Error: %s"%(sys.exc_info()[0]))
        self.__log.debug(e)
        self.__writeClients.remove(rdy)
    if self.__running:
      self.__localExecuter.execute(self.__doWrites)

  
  def __doAcceptor(self):
    rlist = []
    wlist = []
    xlist = []
    self.__acceptLock.acquire()
    if len(self.__acceptServers) > 0:
      rlist, wlist, xlist = select.select(self.__acceptServers, [], self.__acceptServers, .1)
    self.__acceptLock.release()
    for bad in xlist:
      try:
        self.__errorCallback(bad.fileno())
        self.__writeClients.remove(bad)
      except Exception as e:
        self.__log.debug("errorCB Error: %s"%(sys.exc_info()[0]))
        self.__log.debug(e)
        
    for rdy in rlist:
      try:
        if rdy in self.__acceptServers:
          self.__acceptCallback(rdy.fileno())
      except Exception as e:
        self.__log.debug("Accept Error: %s"%(sys.exc_info()[0]))
        self.__log.debug(e)
        self.__writeClients.remove(rdy)

    if self.__running:
      self.__localExecuter.execute(self.__doAcceptor)

    
class FileNoWrapper():
  def __init__(self, fileno):
    self.__fileno = fileno
    
  def __hash__(self):
    return self.__fileno;
  
  def __eq__(self, obj):
    if isinstance(obj, FileNoWrapper):
      return self.fileno() == obj.fileno();
    else:
      return False
    
  def fileno(self):
    return self.__fileno

class EpollSelector():
  def __init__(self, readCallback, writeCallback, acceptCallback, errorCallback):
    self.__log = logging.getLogger("root.litesockets.EpollSelector")
    self.__log.info("Creating epoll selector for: {}".format(platform.system()))
    self.__DEFAULT_READ_POLLS = select.EPOLLIN|select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR
    self.__DEFAULT_ACCEPT_POLLS = select.EPOLLIN|select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR
    self.__readCallback = readCallback
    self.__writeCallback = writeCallback
    self.__acceptCallback = acceptCallback
    self.__errorCallback = errorCallback
    
    self.__ReadSelector = select.epoll()
    self.__WriteSelector = select.epoll()
    self.__AcceptorSelector = select.epoll()
    self.__running = True
    self.__localExecuter = Scheduler(3)
    
    self.__localExecuter.execute(self.__doReads)
    self.__localExecuter.execute(self.__doWrites)
    self.__localExecuter.execute(self.__doAcceptor)

    
  def stop(self):
    self.__running = False
    
  def addServer(self, fileno):
    try:
      self.__AcceptorSelector.register(fileno, self.__DEFAULT_ACCEPT_POLLS)
    except:
      noExcept(self.__AcceptorSelector.modify, fileno, self.__DEFAULT_ACCEPT_POLLS)
      
  def removeServer(self, fileno):
    noExcept(self.__AcceptorSelector.unregister, fileno)
    
  def addReader(self, fileno):
    try:
      self.__ReadSelector.register(fileno, self.__DEFAULT_READ_POLLS)
    except:
      noExcept(self.__ReadSelector.modify, fileno, self.__DEFAULT_READ_POLLS)
      
  def removeReader(self, fileno):
    noExcept(self.__ReadSelector.unregister, fileno)
    
  def addWriter(self, fileno):
    try:
      self.__WriteSelector.register(fileno, select.EPOLLOUT)
    except:
      noExcept(self.__WriteSelector.modify, fileno, select.EPOLLOUT)
      
  def removeWriter(self, fileno):
    noExcept(self.__WriteSelector.unregister, fileno)
    
  def __doThread(self, t):
    while self.__running:
      try:
        t()
      except Exception as e:
        self.__log.error("GP Socket Exception: %s: %s"%(t, sys.exc_info()[0]))
        self.__log.error(e)
        
  
  def __doReads(self):
    events = self.__ReadSelector.poll(1)
    for fileno, event in events:
      try:
        if event & select.EPOLLIN:
          self.__readCallback(fileno)
        if (event & select.EPOLLRDHUP or event & select.EPOLLHUP or event & select.EPOLLERR):
          self.__errorCallback(fileno)
          noExcept(self.__ReadSelector.unregister, fileno)
      except Exception as e:
        self.__log.debug("Read Error: %s"%(sys.exc_info()[0]))
        self.__log.debug(e)
    if self.__running:
      self.__localExecuter.execute(self.__doReads)
        
  def __doWrites(self):
    events = self.__WriteSelector.poll(1)
    for fileno, event in events:
      try:
        if event & select.EPOLLOUT:
          self.__writeCallback(fileno)
        else:
          self.__errorCallback(fileno)
          noExcept(self.__WriteSelector.unregister, fileno)
      except Exception as e:
        self.__log.debug("Write Error: %s"%(sys.exc_info()[0]))
        self.__log.debug(e)
    if self.__running:
      self.__localExecuter.execute(self.__doWrites)
          

  def __doAcceptor(self):
    events = self.__AcceptorSelector.poll(1)
    for fileno, event in events:
      try:
        if event & select.EPOLLIN:
          self.__acceptCallback(fileno)
        else:
          self.__errorCallback(fileno)
          noExcept(self.__WriteSelector.unregister, fileno)
      except Exception as e:
        self.__log.debug("Accept Error: %s"%(sys.exc_info()[0]))
        self.__log.debug(e)
    if self.__running:
      self.__localExecuter.execute(self.__doAcceptor)
        
  


class SocketExecuter():
  """
  The main SocketExecuter for litesockets.  

  The SocketExecuter is what processes all socket operations.  Doing the writes, reads, and accepting new connections.  
  It also does all the callbacks when a read or new socket connects.  Having a SocketExecuter is required for all litesockets 
  Connections, and in general only 1 should be needed per process.
  """
  def __init__(self, threads=5, scheduler=None, forcePlatform=None):
    """
    Constructs a new SocketExecuter
    
    `threads` used to set the number of threads used when creating a Scheduler when no Scheduler is provided.
    
    `scheduler` this scheduler will be used with the SocketExecuters client/server callbacks. 
    
    `forcePlatform` this sets the detected platform, this can be used to switch the selector object made.
    """
    self.__log = logging.getLogger("root.litesockets.SocketExecuter")
    self.__clients = dict()
    self.__servers = dict()
    self.__internalExec = None
    if scheduler == None:
      self.__executor = Scheduler(threads)
      self.__internalExec = self.__executor 
    else:
      self.__executor = scheduler
    self.__stats = Stats()
    if forcePlatform == None:
      forcePlatform = platform.system()
    if forcePlatform.lower().find("linux") > -1:
      self.__selector = EpollSelector(self.__clientRead, self.__clientWrite, self.__serverAccept, self.__socketerrors)
    else:
      self.__selector = SelectSelector(self.__clientRead, self.__clientWrite, self.__serverAccept, self.__socketerrors)
    self.__running = True

  def getScheduler(self):
    """
    Returns the scheduler that is set for this SocketExecuter.
    """
    return self.__executor

  def stop(self):
    """
    Stops the SocketExecuter, this will close all clients/servers created from it.
    """
    self.__selector.stop()
    self.__running = False
    if self.__internalExec != None:
      self.__internalExec.shutdown_now()
      
  def isRunning(self):
    """
    Returns True if the SocketExecuter is running or False if it was shutdown.
    """
    
    return self.__running

  def updateClientOperations(self, client, disable=False):
    """
    This is called to detect what operations to check the client for.  This will decide if
    the client need to check to writes and/or reads and then takes the appropriate actions.
    
    `client` the client to check for operations on.
    
    `disable` if this is set to True it will force the client to be removed from both reads and writes.
    """
    if not isinstance(client, Client):
      return
    FN = client.getFileDesc()
    if FN in self.__clients:
      if client.isClosed():
        self.__selector.removeReader(FN)
        self.__selector.removeWriter(FN)
        del self.__clients[FN]
        return
      if client.getReadBufferSize() >= client.MAXBUFFER or disable:
        self.__selector.removeReader(FN)
      else:
        self.__selector.addReader(FN)
      if client.getWriteBufferSize() == 0  or disable:
        self.__selector.removeWriter(FN)
      else:
        self.__selector.addWriter(FN)
          
  
  def createUDPServer(self, host, port):
    """
    Returns a UDPServer
    
    `host` the host or IP address open the listen port on.
    
    `port` the port to open up.
    """
    us = UDPServer(host, port, self)
    FN = us.getFileDesc()
    self.__clients[FN] = us
    us.addCloseListener(self.__closeClient)
    return us
  
  def createTCPClient(self, host, port, use_socket = None):
    """
    Returns a TCPClient
    
    `host` the host or IP to connect the client to.
    
    `port` the port on that host to connect to.
    """
    
    c = TCPClient(host, port, self, use_socket=use_socket)
    self.__clients[c.getSocket().fileno()] = c
    c.addCloseListener(self.__closeClient)
    return c
        
  def createTCPServer(self, host, port):
    """
    Returns a TCPServer
    
    `host` the host or IP address open the listen port on.
    
    `port` the port to open up.
    """
    
    s = TCPServer(self, host, port)
    self.__servers[s.getSocket().fileno()] = s
    s.addCloseListener(self.__closeServer)
    return s
  
  def getClients(self):
    """
    Returns a list of all the Clients still open and associated with this SocketExecuter.
    """
    
    return list(self.__clients.values())
  
  def getServers(self):
    """
    Returns a list of all Servers still open and associated with this SocketExecuter.
    """
    return list(self.__servers.values())
  
  def getStats(self):
    return self.__stats

  def startServer(self, server):
    """
    Generally this is not called except through Server.start() you can do that manually if wanted.
    
    `server` the server to start listening on.
    """
    
    if isinstance(server, Server) and server.getSocket().fileno() in self.__servers:
      self.__selector.addServer(server.getSocket().fileno())
      self.__log.info("Added New Server")

  def stopServer(self, server):
    """
    Generally this is not called except through Server.stop() you can do that manually if wanted.
    
    `server` the server to start listening on.
    """
    if isinstance(server, Server) and server.getSocket().fileno() in self.__servers:
      self.__selector.removeServer(server.getSocket().fileno())

  def __socketerrors(self, fileno):
    if fileno in self.__clients:
      self.__clientErrors(self.__clients[fileno], fileno)
    elif fileno in self.__servers:
      self.__serverErrors(self.__servers[fileno], fileno)
      
  def __serverAccept(self, fileno):
    if fileno not in self.__servers:
      self.__selector.removeServer(fileno)
      return
    SERVER = self.__servers[fileno]
    self.__log.debug("New Connection")
    conn, addr = SERVER.getSocket().accept()
    SERVER.addClient(conn)
    

  def __clientRead(self, fileno):
    if fileno not in self.__clients:
      self.__selector.removeReader(fileno)
      return
    
    read_client = self.__clients[fileno]
    data_read = 0
    try:
      if read_client._getType() == "CUSTOM":
        data = read_client.READER()
        if data != EMPTY_STRING:
          read_client._addRead(data)
          data_read += len(data)
      elif read_client.getSocket().type == socket.SOCK_STREAM:
        data = read_client.getSocket().recv(655360)
        if data != EMPTY_STRING:
          read_client._addRead(data)
          data_read += len(data)
        else:
          read_client.close()
      elif read_client.getSocket().type == socket.SOCK_DGRAM:
        data = EMPTY_STRING
        try:
          data, addr = read_client.getSocket().recvfrom(65536)
        except socket.error, e:
          print data, e
          if e.args[0] != errno.EWOULDBLOCK:
            raise e
        if data != EMPTY_STRING:
          read_client.runOnClientThread(read_client._addRead, args=([addr, data],))
          data_read+=len(data)
      self.__stats._addRead(data_read)
      return len(data)
    except ssl.SSLError as err:
      pass
    except KeyError as e:
      self.__log.debug("client removed on read")
    except IOError as e:
      if e.errno != errno.EAGAIN:
        self.__log.error("Read Error: %s"%(sys.exc_info()[0]))
        self.__log.error(e)
    except Exception as e:
      self.__log.error("Read Error: %s"%(sys.exc_info()[0]))
      self.__log.error(e)
      self.__log.error(errno.EAGAIN)
    return 0

  def __clientWrite(self, fileno):
    if fileno not in self.__clients:
      self.__selector.removeWriter(fileno)
      return
    CLIENT = self.__clients[fileno]
    l = 0
    try:
      if CLIENT._getType() == "UDP":
        d = CLIENT._getWrite()
        l = CLIENT.getSocket().sendto(d[1], d[0])
        CLIENT._reduceWrite(l)
      elif CLIENT._getType() == "TCP":
        w = CLIENT._getWrite()
        l = CLIENT.getSocket().send(w)
        CLIENT._reduceWrite(l)
      elif self.__clients[fileno].TYPE == "CUSTOM":
        l = self.__clients[fileno].WRITER()
      self.__stats._addWrite(l)
    except Exception as e:
      self.__log.debug("clientWrite Error: %s"%(sys.exc_info()[0]))
      self.__log.debug(e)

  def __serverErrors(self, server, fileno):
    self.__log.debug("Removing Server %d "%(fileno))
    self.__selector.removeServer(fileno)
    server.close()
    
  def __clientErrors(self, client, fileno):
    self.__log.debug("Removing client %d "%(fileno))
    self.__selector.removeReader(fileno)
    self.__selector.removeWriter(fileno)
    client.close()
  
  def __closeClient(self, client):
    client.close()
        
  def __closeServer(self, server):
    self.stopServer(server)
    del self.__servers[server.getSocket().fileno()]
    
    
def noExcept(task, *args, **kwargs):
  """
  Helper function that helps swallow exceptions.
  """
  try:
    task(*args, **kwargs)
  except Exception as e:
    pass

class Stats(object):
  def __init__(self):
    self.__clock = Clock()
    self.__startTime = self.__clock.accurate_time()
    self.__totalRead = 0
    self.__totalWrite = 0
  
  def getTotalRead(self):
    """
    Returns the total bytes read.
    """
    return self.__totalRead
  
  def getTotalWrite(self):
    """
    Returns the total bytes writen.
    """
    return self.__totalWrite
  
  def getReadRate(self):
    """
    Returns the bytes read per second.
    """
    X = round(self.__totalRead/(self.__clock.accurate_time() - self.__startTime), 4)
    if X > 0:
      return X
    else:
      return 0 
  
  def getWriteRate(self):
    """
    Returns the bytes written per second.
    """
    X = round(self.__totalWrite/(self.__clock.accurate_time() - self.__startTime), 4)
    if X > 0:
      return X
    else:
      return 0
  
  def _addRead(self, size):
    self.__totalRead += size
    
  def _addWrite(self, size):
    self.__totalWrite += size
    
    
    
    
