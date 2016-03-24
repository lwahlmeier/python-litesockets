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

  The SocketExecuter is what processes all socket operations.  Doing the writes, reads, and accepts.  It will also do the callback
  when a read or accept happen.  Having a SocketExecuter is required for all litesockets Connections, and in general only 1 is need
  per process.
  """
  def __init__(self, threads=5, executor=None):
    self.log = logging.getLogger("root.litesockets.SocketExecuter")
    self.__DEFAULT_READ_POLLS = select.EPOLLIN|select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR
    self.__DEFAULT_ACCEPT_POLLS = select.EPOLLIN|select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR
    self.__clients = dict()
    self.__servers = dict()
    self.__ReadSelector = select.epoll()
    self.__WriteSelector = select.epoll()
    self.__AcceptorSelector = select.epoll()
    self.__internalExec = None
    if executor == None:
      self.__executor = Scheduler(threads)
      self.__internalExec = self.__executor 
    else:
      self.__executor = executor
    self.__stats = dict()
    self.__stats['RB'] = 0
    self.__stats['SB'] = 0
    self.__running = False
    self.__start()

  def getScheduler(self):
    return self.__executor

  def __start(self):
    if not self.__running:
      self.__running = True
      self.log.info("Start __ReadSelector")
      T = threading.Thread(target= self.__doThread, args=(self.__doReads,))
      T.daemon = True
      T.start()
      self.log.info("Start __WriteSelector")
      T = threading.Thread(target= self.__doThread, args=(self.__doWrites,))
      T.daemon = True
      T.start()
      self.log.info("Start __AcceptorSelector")
      T = threading.Thread(target= self.__doThread, args=(self.__doAcceptor,))
      T.daemon = True
      T.start()
    else:
      self.log.debug("groupPoll already started")

  def stop(self):
    self.__running = False
    if self.__internalExec != None:
      self.__internalExec.shutdown_now()
      
  def isRunning(self):
    return self.__running
  
  def getClients(self):
    return list(self.__clients.values())
  
  def getServers(self):
    return list(self.__servers.values())

  def __doThread(self, t):
    while self.__running:
      try:
        t()
      except Exception as e:
        self.log.error("GP Socket Exception: %s: %s"%(t, sys.exc_info()[0]))
        self.log.error(e)
        
  def createUDPServer(self, host, port):
    us = UDPServer(host, port, self)
    FN = us.getFileDesc()
    self.__clients[FN] = us
    us.addCloseListener(self.__closeClient)
    return us
  
  def createTCPClient(self, host, port, use_socket = None):
    c = TCPClient(host, port, self, use_socket=use_socket)
    self.__clients[c.getSocket().fileno()] = c
    c.addCloseListener(self.__closeClient)
    return c
        
  def createTCPServer(self, host, port):
    s = TCPServer(self, host, port)
    self.__servers[s.getSocket().fileno()] = s
    s.addCloseListener(self.__closeServer)
    return s

  def startServer(self, server):
    if isinstance(server, Server) and server.getSocket().fileno() in self.__servers:
      self.__AcceptorSelector.register(server.getSocket().fileno(), self.__DEFAULT_ACCEPT_POLLS)      
      self.log.info("Added New Server")

  def stopServer(self, server):
    if isinstance(server, Server) and server.getSocket().fileno() in self.__servers:
      try:
        self.__AcceptorSelector.unregister(server.getSocket().fileno())
      except:
        pass

  def addClient(self, client):
    if isinstance(client, Client) and client.getFileDesc() in self.__clients:
      self.setRead(client)

  def rmClient(self, client):
    if not isinstance(client, Client):
      return 
    FN = client.getFileDesc()
    if FN in self.__clients:
      try:
        self.__ReadSelector.unregister(FN)
      except:
        pass
      try:
        self.__WriteSelector.unregister(FN)
      except:
        pass

  def setRead(self, client, on=True):
    try:
      if client.getSocket().fileno() not in self.__clients:
        return
    except:
      return
    try:
      if on:
        try:
          print "register read", client
          self.__ReadSelector.register(client.getSocket().fileno(), self.__DEFAULT_READ_POLLS)
        except:
          print "register read", client
          self.__ReadSelector.modify(client.getSocket().fileno(), self.__DEFAULT_READ_POLLS)
      else:
        print "unregister read", client
        self.__ReadSelector.unregister(client.getSocket().fileno())
    except Exception as e:
      self.log.error("Problem adding __ReadSelector for client %s %s"%(e, on))

  def setWrite(self, client, on=True):
    try:
      if client.getSocket().fileno() not in self.__clients:
        return
    except:
      return
    try:
      if on:
        try:
          self.__WriteSelector.register(client.getSocket().fileno(), select.EPOLLOUT)
        except:
          self.__WriteSelector.modify(client.getSocket().fileno(), select.EPOLLOUT)
      else:
        self.__WriteSelector.modify(client.getSocket().fileno(), 0)
    except Exception as e:
      self.log.error("Problem adding __WriteSelector %s"%(e))



  def __doReads(self):
    events = self.__ReadSelector.poll(10000)
    for fileno, event in events:
      read_client = self.__clients[fileno]
      print "read", read_client
      dlen = 0
      if event & select.EPOLLIN:
        dlen = self.__clientRead(read_client)
      if dlen == 0 and (event & select.EPOLLRDHUP or event & select.EPOLLHUP or event & select.EPOLLERR):
        self.__clientErrors(read_client, fileno)

  def __clientRead(self, read_client):
    data = EMPTY_STRING
    try:
      if read_client.getType() == "CUSTOM":
        data = read_client.READER()
        if data != EMPTY_STRING:
          read_client.addRead(data)
      elif read_client.getSocket().type == socket.SOCK_STREAM:
        data = read_client.getSocket().recv(65536)
        if data != EMPTY_STRING:
          read_client.addRead(data)
      elif read_client.getSocket().type == socket.SOCK_DGRAM:
        data, addr = read_client.getSocket().recvfrom(65536)
        if data != EMPTY_STRING:
          read_client.addRead([addr, data])
      self.__stats['RB'] += len(data)
      return len(data)
    except ssl.SSLError as err:
      pass
    except KeyError as e:
      self.log.debug("client removed on read")
    except IOError as e:
      if e.errno != errno.EAGAIN:
        self.log.error("Read Error: %s"%(sys.exc_info()[0]))
        self.log.error(e)
    except Exception as e:
      self.log.error("Read Error: %s"%(sys.exc_info()[0]))
      self.log.error(e)
      self.log.error(errno.EAGAIN)
    return 0


  def __doWrites(self):
    events = self.__WriteSelector.poll(10000)
    for fileno, event in events:
      if event & select.EPOLLOUT:
        CLIENT = self.__clients[fileno]
        print "write:",CLIENT.getWriteBufferSize()
        l = 0
        try:
          if CLIENT.getType() == "UDP":
            d = CLIENT.getWrite()
            l = CLIENT.getSocket().sendto(d[1], d[0])
          elif CLIENT.getType() == "TCP":
            #we only write 4k at a time because of some ssl problems with:
            # error:1409F07F:SSL routines:SSL3_WRITE_PENDING:bad write retry
            w = CLIENT.getWrite()
            print "write:", w
            l = CLIENT.getSocket().send(w[:4096])
            CLIENT.reduceWrite(l)
          elif self.__clients[fileno].TYPE == "CUSTOM":
            l = self.__clients[fileno].WRITER()
          self.__stats['SB'] += l
        except Exception as e:
          self.log.debug("Write Error: %s"%(sys.exc_info()[0]))
          self.log.debug(e)

  def __serverErrors(self, server, fileno):
    self.log.debug("Removeing Server %d "%(fileno))
    self.__AcceptorSelector.unregister(fileno)
    server.close()
    
  def __clientErrors(self, client, fileno):
    self.log.debug("Removeing client %d "%(fileno))
    self.rmClient(client)
    client.close()

  def __doAcceptor(self):
    events = self.__AcceptorSelector.poll(10000)
    for fileno, event in events:
      SERVER = self.__servers[fileno]
      if event & select.EPOLLRDHUP or event & select.EPOLLHUP or event & select.EPOLLERR:
        self.__serverErrors(SERVER, fileno)
      elif fileno in self.__servers:
        self.log.debug("New Connection")
        conn, addr = SERVER.getSocket().accept()
        SERVER.addClient(conn)
  
  def __closeClient(self, client):
    #self.log("----GOT CLOSE: client" +""+str(client.getFileDesc())) 
    self.rmClient(client)
    if client.getFileDesc() in self.__clients:
      del self.__clients[client.getFileDesc()];
        
  def __closeServer(self, server):
    print "----GOT CLOSE"
    self.stopServer(server)
    del self.__servers[server.getSocket().fileno()];
