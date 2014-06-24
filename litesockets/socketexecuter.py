import select, logging, threading, sys, ssl, errno, socket
from threadly import Executor
from litesockets.client import Client
from litesockets.server import Server

if not "EPOLLRDHUP" in dir(select):
  select.EPOLLRDHUP = 0x2000

EMPTY = ""

class SocketExecuter():
  def __init__(self, threads=5, executor=None):
    self.DEFAULT = select.EPOLLIN|select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR
    self.clients = dict()
    self.servers = dict()
    self.Reader = select.epoll()
    self.Writer = select.epoll()
    self.Acceptor = select.epoll()
    if executor == None:
      self.Executor = Executor(threads)
    else:
      self.Executor = executor
    self.SCH = self.Executor.schedule
    self.log = logging.getLogger("root.litesockets.SocketExecuter")
    self.stats = dict()
    self.stats['RB'] = 0
    self.stats['SB'] = 0
    self.running = False
    self.start()

  def start(self):
    if self.running == False:
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

  def addServer(self, server):
    if not issubclass(type(server), Server) and not issubclass(type(server), Client):
      return
    elif issubclass(type(server), Client):
      self.addClient(server)
      return
    try:
      FN = server.socket.fileno()
      if FN in self.servers:
        self.log.error("Duplicate server Add!!")
        return
      self.servers[FN] = server
      server._setSocketExecuter(self)
      self.Acceptor.register(FN, select.EPOLLIN)
      self.log.info("Added New Server")
    except Exception as e:
      self.log.info("Problem adding Server: %s"%(e))
      self.rmServer(server)

  def rmServer(self, server):
    if not issubclass(type(server), Server) and not issubclass(type(server), Client):
      return
    elif issubclass(type(server), Client):
      self.rmClient(server)
      return
    try:
      FN = server.socket.fileno()
    except:
      return
    if FN in self.servers:
      del self.servers[FN]
      self.log.info("Removing Server")
      try:
        self.Acceptor.unregister(FN)
      except:
        pass

  def addClient(self, client):
    if not issubclass(type(client), Client):
      return
    try:
      FN = client.socket.fileno()
      if FN in self.clients:
        self.log.error("Duplicate client Add!!")
        return False
      self.clients[FN] = client
      client._setSocketExecuter(self)
      self.setRead(client)
      self.log.debug("Added Client")
      self.log.debug("%d"%FN)
    except Exception as e:
      self.rmClient(client)
      return False
    return True

  def rmClient(self, client, FN=None):
    try:
      FN = client.socket.fileno()
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
      if client.socket.fileno() not in self.clients:
        return
    except:
      return
    try:
      client.readlock.acquire()
      if on:
        try:
          self.Reader.register(client.socket.fileno(), select.EPOLLIN | select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR)
        except:
          self.Reader.modify(client.socket.fileno(), select.EPOLLIN | select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR)
      else:
        self.Reader.unregister(client.socket.fileno())
    except Exception as e:
      self.log.error("Problem adding Reader for client %s %s"%(e, on))
    finally:
      client.readlock.release()

  def setWrite(self, client, on=True):
    try:
      if client.socket.fileno() not in self.clients:
        return
    except:
      return
    try:
      client.writelock.acquire()
      if on:
        try:
          self.Writer.register(client.socket.fileno(), select.EPOLLOUT)
        except:
          self.Writer.modify(client.socket.fileno(), select.EPOLLOUT)
      else:
        self.Writer.modify(client.socket.fileno(), 0)
    except Exception as e:
      self.log.error("Problem adding Writer %s"%(e))
    finally:
      client.writelock.release()


  def doReads(self):
    events = self.Reader.poll(10000)
    for fileno, event in events:
      read_client = self.clients[fileno]
      dlen = 0
      if event & select.EPOLLIN:
        dlen = self.clientRead(read_client)
      if dlen == 0 and (event & select.EPOLLRDHUP or event & select.EPOLLHUP or event & select.EPOLLERR):
        self.clientErrors(read_client, fileno)

  def clientRead(self, read_client):
    data = ""
    try:
      if read_client.TYPE == "CUSTOM":
        data = read_client.READER()
        if data != EMPTY:
          read_client.addRead(data)
          self.SCH(read_client.runRead, key=read_client)
      elif read_client.socket.type == socket.SOCK_STREAM:
        data = read_client.socket.recv(65536)
        if data != EMPTY:
          read_client.addRead(data)
          self.SCH(read_client.runRead, key=read_client)
      elif read_client.socket.type == socket.SOCK_DGRAM:
        data, addr = read_client.socket.recvfrom(65536)
        if data != EMPTY:
          read_client.addRead([addr, data])
          self.SCH(read_client.runRead, key=read_client)
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
        l = 0
        try:
          if CLIENT.TYPE == "UDP":
            d = CLIENT.getWrite()
            l = CLIENT.socket.sendto(d[1], d[0])
          elif CLIENT.TYPE == "TCP":
            #we only write 4k at a time because of some ssl problems with:
            # error:1409F07F:SSL routines:SSL3_WRITE_PENDING:bad write retry
            l = CLIENT.socket.send(str(self.clients[fileno].getWrite())[:4096])
            CLIENT.reduceWrite(l)
          elif self.clients[fileno].TYPE == "CUSTOM":
            l = self.clients[fileno].WRITER()
          self.stats['SB'] += l
        except Exception as e:
          self.log.debug("Write Error: %s"%(sys.exc_info()[0]))
          self.log.debug(e)

  def serverErrors(self, server, fileno):
    self.log.debug("Removeing Server %d "%(fileno))
    self.rmServer(server)


  def clientErrors(self, client, fileno):
    self.log.debug("Removeing client %d "%(fileno))
    self.rmClient(client)
    if client.closer != None:
      client.closer(client)

  def doAcceptor(self):
    events = self.Acceptor.poll(10000)
    for fileno, event in events:
      SERVER = self.servers[fileno]
      if event & select.EPOLLRDHUP or event & select.EPOLLHUP or event & select.EPOLLERR:
        self.serverErrors(SERVER, fileno)
      elif fileno in self.servers:
        self.log.debug("New Connection")
        conn, addr = SERVER.socket.accept()
        SERVER.addClient(conn)
        if SERVER.onConnect != None:
          self.Executor.schedule(SERVER.onConnect, key=SERVER)

