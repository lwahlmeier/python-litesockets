import select, logging, threading, sys, ssl, errno, socket
from threadly import Scheduler
from .client import Client
from .server import Server
from .tcp import TCPClient, TCPServer

if not "EPOLLRDHUP" in dir(select):
  select.EPOLLRDHUP = 0x2000

EMPTY = ""

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
    self.__clients = dict()
    self.__servers = dict()
    self.__ReadSelector = select.epoll()
    self.__WriteSelector = select.epoll()
    self.__AcceptorSelector = select.epoll()
    if executor == None:
      self.__executor = Scheduler(threads)
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

  def __doThread(self, t):
    while self.__running:
      try:
        t()
      except Exception as e:
        self.log.error("GP Socket Exception: %s: %s"%(t, sys.exc_info()[0]))
        self.log.error(e)
  
  def createTCPClient(self, host, port, use_socket = None):
    c = TCPClient(self, host, port, use_socket=use_socket)
    self.__clients[c.getSocket().fileno()] = c
    return c
        
  def createTCPServer(self, host, port):
    s = TCPServer(self, host, port)
    self.__servers[s.getSocket().fileno()] = s
    return s

  def startServer(self, server):
    if server.getSocket().fileno() in self.__servers:
      self.__AcceptorSelector.register(server.getSocket().fileno(), select.EPOLLIN)      
      self.log.info("Added New Server")

  def stopServer(self, server):
    if server.getSocket().fileno() in self.__servers:
      self.__AcceptorSelector.unregister(server.getSocket().fileno())

  def addClient(self, client):
    if client.getSocket().fileno() in self.__clients:
      self.setRead(client)

  def rmClient(self, client):
    FN = client.getSocket().fileno()
    if FN in self.__clients:
      try:
        self.__ReadSelector.unregister(FN)
      except:
        pass
      try:
        self.__WriteSelector.unregister(FN)
      except:
        pass
      del self.__clients[FN]

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
          self.__ReadSelector.register(client.getSocket().fileno(), select.EPOLLIN | select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR)
        except:
          print "register read", client
          self.__ReadSelector.modify(client.getSocket().fileno(), select.EPOLLIN | select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR)
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
        self.clientErrors(read_client, fileno)

  def __clientRead(self, read_client):
    data = EMPTY
    try:
      if read_client.getType() == "CUSTOM":
        data = read_client.READER()
        if data != EMPTY:
          read_client.addRead(data)
      elif read_client.getSocket().type == socket.SOCK_STREAM:
        data = read_client.getSocket().recv(65536)
        if data != EMPTY:
          read_client.addRead(data)
      elif read_client.getSocket().type == socket.SOCK_DGRAM:
        data, addr = read_client.getSocket().recvfrom(65536)
        if data != EMPTY:
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

  def serverErrors(self, server, fileno):
    self.log.debug("Removeing Server %d "%(fileno))
    self.stopServer(server)


  def clientErrors(self, client, fileno):
    self.log.debug("Removeing client %d "%(fileno))
    self.rmClient(client)
    client.close()

  def __doAcceptor(self):
    events = self.__AcceptorSelector.poll(10000)
    for fileno, event in events:
      SERVER = self.__servers[fileno]
      if event & select.EPOLLRDHUP or event & select.EPOLLHUP or event & select.EPOLLERR:
        self.serverErrors(SERVER, fileno)
      elif fileno in self.__servers:
        self.log.debug("New Connection")
        conn, addr = SERVER.getSocket().accept()
        SERVER.addClient(conn)
