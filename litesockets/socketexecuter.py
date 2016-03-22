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
    self.DEFAULT = select.EPOLLIN|select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR
    self.clients = dict()
    self.servers = dict()
    self.Reader = select.epoll()
    self.Writer = select.epoll()
    self.Acceptor = select.epoll()
    if executor == None:
      self.Executor = Scheduler(threads)
    else:
      self.Executor = executor
    self.SCH = self.Executor.schedule
    self.log = logging.getLogger("root.litesockets.SocketExecuter")
    self.stats = dict()
    self.stats['RB'] = 0
    self.stats['SB'] = 0
    self.running = False
    self.start()

  def getScheduler(self):
    return self.Executor

  def start(self):
    if not self.running:
      self.running = True
      self.log.info("Start Reader")
      T = threading.Thread(target= self._doThread, args=(self.doReads,))
      T.daemon = True
      T.start()
      self.log.info("Start Writer")
      T = threading.Thread(target= self._doThread, args=(self.doWrites,))
      T.daemon = True
      T.start()
      self.log.info("Start Acceptor")
      T = threading.Thread(target= self._doThread, args=(self.doAcceptor,))
      T.daemon = True
      T.start()
    else:
      self.log.debug("groupPoll already started")

  def stop(self):
    self.running = False

  def _doThread(self, t):
    while self.running:
      try:
        t()
      except Exception as e:
        self.log.error("GP Socket Exception: %s: %s"%(t, sys.exc_info()[0]))
        self.log.error(e)
        
  def createTCPServer(self, host, port):
    s = TCPServer(self, host, port)
    self.servers[s.getSocket().fileno()] = s
    return s

  def startServer(self, server):
    if server.getSocket().fileno() in self.servers:
      self.Acceptor.register(server.getSocket().fileno(), select.EPOLLIN)      
      self.log.info("Added New Server")

  def stopServer(self, server):
    if server.getSocket().fileno() in self.servers:
      self.Acceptor.unregister(server.getSocket().fileno())

  def addClient(self, client):
    if not issubclass(type(client), Client):
      return
    try:
      FN = client.getSocket().fileno()
      self.clients[FN] = client
      self.setRead(client)
      self.log.debug("Added Client")
      self.log.debug("%d"%FN)
    except Exception as e:
      print e
      self.rmClient(client)
      return False
    return True

  def rmClient(self, client, FN=None):
    try:
      FN = client.getSocket().fileno()
    except:
      return
    try:
      del self.clients[FN]
    except:
      pass
    try:
      self.Reader.unregister(FN)
    except:
      pass
    try:
      self.Writer.unregister(FN)
    except:
      pass

  def setRead(self, client, on=True):
    try:
      if client.getSocket().fileno() not in self.clients:
        return
    except:
      return
    try:
      if on:
        try:
          print "register read", client
          self.Reader.register(client.getSocket().fileno(), select.EPOLLIN | select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR)
        except:
          print "register read", client
          self.Reader.modify(client.getSocket().fileno(), select.EPOLLIN | select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR)
      else:
        print "unregister read", client
        self.Reader.unregister(client.getSocket().fileno())
    except Exception as e:
      self.log.error("Problem adding Reader for client %s %s"%(e, on))

  def setWrite(self, client, on=True):
    try:
      if client.getSocket().fileno() not in self.clients:
        return
    except:
      return
    try:
      if on:
        try:
          self.Writer.register(client.getSocket().fileno(), select.EPOLLOUT)
        except:
          self.Writer.modify(client.getSocket().fileno(), select.EPOLLOUT)
      else:
        self.Writer.modify(client.getSocket().fileno(), 0)
    except Exception as e:
      self.log.error("Problem adding Writer %s"%(e))



  def doReads(self):
    events = self.Reader.poll(10000)
    for fileno, event in events:
      read_client = self.clients[fileno]
      print "read", read_client
      dlen = 0
      if event & select.EPOLLIN:
        dlen = self.clientRead(read_client)
      if dlen == 0 and (event & select.EPOLLRDHUP or event & select.EPOLLHUP or event & select.EPOLLERR):
        self.clientErrors(read_client, fileno)

  def clientRead(self, read_client):
    data = ""
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
      self.stats['RB'] += len(data)
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


  def doWrites(self):
    events = self.Writer.poll(10000)
    for fileno, event in events:
      if event & select.EPOLLOUT:
        CLIENT = self.clients[fileno]
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
          elif self.clients[fileno].TYPE == "CUSTOM":
            l = self.clients[fileno].WRITER()
          self.stats['SB'] += l
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

  def doAcceptor(self):
    events = self.Acceptor.poll(10000)
    for fileno, event in events:
      SERVER = self.servers[fileno]
      if event & select.EPOLLRDHUP or event & select.EPOLLHUP or event & select.EPOLLERR:
        self.serverErrors(SERVER, fileno)
      elif fileno in self.servers:
        self.log.debug("New Connection")
        conn, addr = SERVER.getSocket().accept()
        SERVER.addClient(conn)
