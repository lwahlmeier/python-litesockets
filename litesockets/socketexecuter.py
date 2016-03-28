import select, logging, threading, sys, ssl, errno, socket
from threadly import Scheduler
from .client import Client
from .server import Server
from .tcp import TCPClient, TCPServer
from .udp import UDPServer

if not "EPOLLRDHUP" in dir(select):
  select.EPOLLRDHUP = 0x2000

EMPTY_STRING = ""

class SocketExecuter():
  """
  The main SocketExecuter for litesockets.  

  The SocketExecuter is what processes all socket operations.  Doing the writes, reads, and accepting new connections.  
  It also does all the callbacks when a read or new socket connects.  Having a SocketExecuter is required for all litesockets 
  Connections, and in general only 1 should be needed per process.
  """
  def __init__(self, threads=5, scheduler=None):
    """
    Constructs a new SocketExecuter
    
    `threads` used to set the number of threads used when creating a Scheduler when no Scheduler is provided.
    
    `scheduler` this scheduler will be used with the SocketExecuters client/server callbacks. 
    """
    
    self.__log = logging.getLogger("root.litesockets.SocketExecuter")
    self.__DEFAULT_READ_POLLS = select.EPOLLIN|select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR
    self.__DEFAULT_ACCEPT_POLLS = select.EPOLLIN|select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR
    self.__clients = dict()
    self.__servers = dict()
    self.__ReadSelector = select.epoll()
    self.__WriteSelector = select.epoll()
    self.__AcceptorSelector = select.epoll()
    self.__internalExec = None
    if scheduler == None:
      self.__executor = Scheduler(threads)
      self.__internalExec = self.__executor 
    else:
      self.__executor = scheduler
    self.__stats = dict()
    self.__stats['RB'] = 0
    self.__stats['SB'] = 0
    self.__running = False
    self.__start()

  def getScheduler(self):
    """
    Returns the scheduler that is set for this SocketExecuter.
    """
    
    return self.__executor

  def __start(self):
    if not self.__running:
      self.__running = True
      self.__log.info("Start __ReadSelector")
      T = threading.Thread(target= self.__doThread, args=(self.__doReads,))
      T.daemon = True
      T.start()
      self.__log.info("Start __WriteSelector")
      T = threading.Thread(target= self.__doThread, args=(self.__doWrites,))
      T.daemon = True
      T.start()
      self.__log.info("Start __AcceptorSelector")
      T = threading.Thread(target= self.__doThread, args=(self.__doAcceptor,))
      T.daemon = True
      T.start()
    else:
      self.__log.debug("groupPoll already started")

  def stop(self):
    """
    Stops the SocketExecuter, this will close all clients/servers created from it.
    """
    
    self.__running = False
    if self.__internalExec != None:
      self.__internalExec.shutdown_now()
      
  def isRunning(self):
    """
    Returns True if the SocketExecuter is running or False if it was shutdown.
    """
    
    return self.__running
  
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

  def __doThread(self, t):
    while self.__running:
      try:
        t()
      except Exception as e:
        self.__log.error("GP Socket Exception: %s: %s"%(t, sys.exc_info()[0]))
        self.__log.error(e)

  def startServer(self, server):
    """
    Generally this is not called except through Server.start() you can do that manually if wanted.
    
    `server` the server to start listening on.
    """
    
    if isinstance(server, Server) and server.getSocket().fileno() in self.__servers:
      self.__AcceptorSelector.register(server.getSocket().fileno(), self.__DEFAULT_ACCEPT_POLLS)      
      self.__log.info("Added New Server")

  def stopServer(self, server):
    """
    Generally this is not called except through Server.stop() you can do that manually if wanted.
    
    `server` the server to start listening on.
    """
    if isinstance(server, Server) and server.getSocket().fileno() in self.__servers:
      noExcept(self.__AcceptorSelector.unregister, server.getSocket().fileno())
      
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
        noExcept(self.__ReadSelector.unregister, FN)
        noExcept(self.__WriteSelector.unregister, FN)
        del self.__clients[FN]
        return
      
      if client.getReadBufferSize() >= client.MAXBUFFER or disable:
        noExcept(self.__ReadSelector.unregister, FN)
      else:
        try:
          self.__ReadSelector.register(FN, self.__DEFAULT_READ_POLLS)
        except:
          noExcept(self.__ReadSelector.modify, FN, self.__DEFAULT_READ_POLLS)
      if client.getWriteBufferSize() == 0  or disable:
        noExcept(self.__WriteSelector.unregister, FN)
      else:
        try:
          self.__WriteSelector.register(FN, select.EPOLLOUT)
        except:
          noExcept(self.__WriteSelector.modify, FN, select.EPOLLOUT)


  def __doReads(self):
    events = self.__ReadSelector.poll(1)
    for fileno, event in events:
      if fileno not in self.__clients:
        noExcept(self.__ReadSelector.unregister, fileno)
        continue
      read_client = self.__clients[fileno]
      
      dlen = 0
      if event & select.EPOLLIN:
        dlen = self.__clientRead(read_client)
      if dlen == 0 and (event & select.EPOLLRDHUP or event & select.EPOLLHUP or event & select.EPOLLERR):
        self.__clientErrors(read_client, fileno)

  def __clientRead(self, read_client):
    data = EMPTY_STRING
    try:
      if read_client._getType() == "CUSTOM":
        data = read_client.READER()
        if data != EMPTY_STRING:
          read_client._addRead(data)
      elif read_client.getSocket().type == socket.SOCK_STREAM:
        data = read_client.getSocket().recv(655360)
        if data != EMPTY_STRING:
          read_client._addRead(data)
      elif read_client.getSocket().type == socket.SOCK_DGRAM:
        data, addr = read_client.getSocket().recvfrom(65536)
        if data != EMPTY_STRING:
          read_client._addRead([addr, data])
      self.__stats['RB'] += len(data)
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


  def __doWrites(self):
    events = self.__WriteSelector.poll(1)
    for fileno, event in events:
      if event & select.EPOLLOUT:
        CLIENT = self.__clients[fileno]
        l = 0
        try:
          if CLIENT._getType() == "UDP":
            d = CLIENT._getWrite()
            l = CLIENT.getSocket().sendto(d[1], d[0])
          elif CLIENT._getType() == "TCP":
            w = CLIENT._getWrite()
            l = CLIENT.getSocket().send(w)
            CLIENT._reduceWrite(l)
          elif self.__clients[fileno].TYPE == "CUSTOM":
            l = self.__clients[fileno].WRITER()
          self.__stats['SB'] += l
        except Exception as e:
          self.__log.debug("Write Error: %s"%(sys.exc_info()[0]))
          self.__log.debug(e)

  def __serverErrors(self, server, fileno):
    self.__log.debug("Removeing Server %d "%(fileno))
    self.__AcceptorSelector.unregister(fileno)
    server.close()
    
  def __clientErrors(self, client, fileno):
    self.__log.debug("Removeing client %d "%(fileno))
    noExcept(self.__ReadSelector.unregister, fileno)
    noExcept(self.__WriteSelector.unregister, fileno)
    client.close()

  def __doAcceptor(self):
    events = self.__AcceptorSelector.poll(1)
    for fileno, event in events:
      SERVER = self.__servers[fileno]
      if event & select.EPOLLRDHUP or event & select.EPOLLHUP or event & select.EPOLLERR:
        self.__serverErrors(SERVER, fileno)
      elif fileno in self.__servers:
        self.__log.debug("New Connection")
        conn, addr = SERVER.getSocket().accept()
        SERVER.addClient(conn)
  
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
  except:
    pass
