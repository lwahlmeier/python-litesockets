import socket, select, ssl, sys, threading, time, logging
import hashlib, struct, random, errno
import Queue
from threadly import *

if not "EPOLLRDHUP" in dir(select):
  select.EPOLLRDHUP = 0x2000

class UdpSocket():
  def __init__(self, ip, port=None):
    self.TYPE = "UDP"
    self.log = logging.getLogger("root.litesockets.UdpSocket")
    self.ip = ip
    self.port = port
    self.onData = None

    self.MAXBUFFER = 0
    self.WriteLock = threading.Condition()
    self.writeBuffSize = 0
    self.writeBuff = list()

    self.ReadLock = threading.Condition()
    self.readBuffSize = 0
    self.readBuff = list()
    self.GP = SocketExecuter()

  def connect(self):
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if self.port != None:
      self.socket.bind((self.ip, self.port))
    self.GP.addClient(self)
    return True

  def gotRead(self):
    if self.onData != None:
      self.onData(self)

  def addWrite(self, data):
    try:
      if type(data) != list: 
        raise Exception("Bad Data, must be list!!")
      self.WriteLock.acquire()
      self.writeBuff.append(data)
      self.writeBuffSize+=len(data[1])
      if self.writeBuffSize > 0:
        self.GP.setWrite(self, on=True)
      while self.writeBuffSize > self.MAXBUFFER:
        self.WriteLock.wait()
      return len(data)
    finally:
      self.WriteLock.release()

  def getWrite(self):
    try:
      self.WriteLock.acquire()
      X = self.writeBuff.pop(0)
      self.writeBuffSize -= len(X[1])
      if self.writeBuffSize <= self.MAXBUFFER:
        self.WriteLock.notify()
      if self.writeBuffSize == 0:
        self.GP.setWrite(self, on=False)
      return X
    finally:
      self.WriteLock.release()

  def addRead(self, data):
    try:
      self.ReadLock.acquire()
      self.readBuffSize += len(data[1])
      self.readBuff.append(data)
      if self.readBuffSize > self.MAXBUFFER:
        self.GP.setRead(self, on=False)
    finally:
      self.ReadLock.release()

  def getRead(self):
    try:
      self.ReadLock.acquire()
      X = self.readBuff.pop(0)
      self.readBuffSize -= len(X[1])
      if self.readBuffSize <= self.MAXBUFFER:
        self.GP.setRead(self, on=True)
      return X
    finally:
      self.ReadLock.release()

  def __runRead(self):
    if self.onData != None:
      self.onData(self)


  def end(self):
    try:
      self.socket.shutdown(socket.SHUT_RDWR)
    except:
      pass



class TcpServer():
  def __init__(self, ip, port, do_ssl = False, certfile=None, keyfile=None):
    self.log = logging.getLogger("root.litesockets.TcpServer")
    self.ip = ip
    self.port = port
    self.do_ssl = do_ssl
    self.onConnect = None
    self.certfile = certfile
    self.keyfile = keyfile
    self.GP = SocketExecuter()
    self.GP.start()
    self.socket = None

  def start(self):
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.socket.bind((self.ip, self.port))
    self.socket.listen(500)
    self.GP.addServer(self)

  def end(self):
    try:
      self.socket.shutdown(socket.SHUT_RDWR)
    except:
      pass

class TcpClient():
  def __init__(self):
    self.TYPE = "TCP"
    self.log = logging.getLogger("root.litesockets.TcpClient")
    self.ip = None
    self.port = None
    self.socket = None 
    self.MAXBUFFER = 4096*4
    self.write_buff = bytearray()
    self.last_write_buff = ""
    self.writeBuffSize = 0
    self.recv_buff = list()
    self.recvBuffSize = 0
    self.ciphers=[]
    self.lastBytes = None

    self.onData = None
    self.onClose = None
    self.onEmpty = None

    self.plainSock = None
    self.WriteLock = threading.Condition()
    self.ReadLock = threading.Condition()
    self.GP = SocketExecuter()

  def connect(self, ip, port, do_ssl=False):
    self.ip = ip
    self.port = port
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if do_ssl == True:
      self.log.debug("Doing SSL")
      self.do_ssl()
    self.log.debug("connecting %s:%d"%(ip, port))
    self.socket.connect((ip, port))
    self.init_conn()
    self.GP.addClient(self)    
    self.log.debug("Client Connected")

  def init_conn(self):
    self.socket.setblocking(0)
    self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 0, 10))

  def do_ssl(self, server=False, certfile=None, keyfile=None):
    self.plainSock = self.socket
    if server == False:
      if len(self.ciphers) > 0:
        self.socket = ssl.wrap_socket(self.socket, ciphers=":".join(self.ciphers))
      else:
        self.socket = ssl.wrap_socket(self.socket)
    else:
      self.socket = ssl.wrap_socket(self.socket, server_side=True, certfile=certfile, keyfile=keyfile)

  def gotRead(self):
    if self.onData != None:
      self.onData(self)

  def getRead(self):
    self.ReadLock.acquire()
    X = self.recv_buff.pop(0)
    l = len(X)
    self.recvBuffSize -= l
    #if self.recvBuffSize == 0:
    if (self.recvBuffSize+l) >= self.MAXBUFFER and self.recvBuffSize < self.MAXBUFFER:
      self.GP.setRead(self, on=True)
    self.ReadLock.release()
    return X

  def addRead(self, data):
    self.ReadLock.acquire()
    self.recv_buff.append(data)
    self.recvBuffSize += len(data)
    if self.recvBuffSize > self.MAXBUFFER:
      self.GP.setRead(self, on=False)
    self.ReadLock.release()
  
  def getWrite(self):
#    if len(self.last_write_buff) == 0:
#      self.last_write_buff = str(self.write_buff[:4096])
    return self.write_buff

  def reduceWrite(self, red):
    try:
      self.WriteLock.acquire()
      del self.write_buff[:red]
      self.last_write_buff = self.last_write_buff[red:]
      self.writeBuffSize -= red
      if self.writeBuffSize == 0:
        self.GP.setWrite(self, on=False)
      if self.writeBuffSize < self.MAXBUFFER:
        self.WriteLock.notify()
    finally:
      self.WriteLock.release()

  def addWrite(self, data):
    try:
      self.WriteLock.acquire()
      self.write_buff.extend(data)
      self.writeBuffSize+=len(data)
      if self.writeBuffSize > 0:
        self.GP.setWrite(self, True)
      while self.writeBuffSize >= self.MAXBUFFER:
        self.WriteLock.wait()
      return len(data)
    finally:
      self.WriteLock.release()
      

  def end(self):
    try:
      self.socket.shutdown(socket.SHUT_RDWR)
      self.socket.close()
    except:
      pass

@singleton
class SocketExecuter():
  def __init__(self, threads=5):
    self.DEFAULT = select.EPOLLIN|select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR
    self.clients = dict()
    self.servers = dict()
    self.sendBuffer = list()
    self.epoll = select.epoll()
    self.Reader = select.epoll()
    self.Writer = select.epoll()
    self.Errors = select.epoll()
    self.Acceptor = select.epoll()
    self.Executor = Executor(threads)
    self.log = logging.getLogger("root.litesockets.SocketExecuter")
    self.ST = None # Socket Thread
    self.stats = dict()
    self.stats['RB'] = 0
    self.stats['SB'] = 0
    self.started = False
    self.start()

  def start(self):
    if self.started == False:
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
      self.started = True
    else:
      self.log.debug("groupPoll already started")

  def pool(self, q):
    while True:
      try:
        (client, call) = self.Queues[q].get()
        call(client)
      except Exception as e:
        self.log.error("Thread Exception %d", q)
        self.log.error("Thread Exception %s", sys.exc_info()[0])
        self.log.error(e)

  def _doThread(self, t):
    while True:
      try:
        t()
      except Exception as e:
        self.log.error("GP Socket Exception: %s: %s"%(t, sys.exc_info()[0]))
        self.log.error(e)

  def addServer(self, server):
    try:
      FN = server.socket.fileno()
      if FN in self.servers:
        self.log.error("Duplicate server Add!!")
        return False
      self.servers[FN] = server
      self.Errors.register(FN, select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR)
      self.Acceptor.register(FN, select.EPOLLIN)
      self.log.info("Added New Server")
    except Exception as e:
      self.log.info("Problem adding Server: %s"%(e))
      self.rmServer(server)
      return False
    return True

  def rmServer(self, server):
    try:
      FN = server.socket.fileno()
    except:
      return
    if FN in self.servers:
      del self.servers[FN]
      self.log.info("Removing Server")
      try:
        self.Errors.unregister(FN)
      except:
        pass
      try:
        self.Acceptor.unregister(FN)
      except:
        pass

  def addClient(self, client):
    try:
      FN = client.socket.fileno()
      if FN in self.clients:
        self.log.error("Duplicate client Add!!")
        return False
      self.clients[FN] = client
      client.epollRead = self.Reader
      client.epollWrite = self.Writer
      #self.Errors.register(FN, select.EPOLLRDHUP|select.EPOLLHUP|select.EPOLLERR)
      self.setRead(client)
      self.log.debug("Added Client")
      self.log.debug("%d"%FN)
    except:
      self.rmClient()
      return False
    return True

  def rmClient(self, client, FN=None):
    if FN==None:
      try:
        FN = client.socket.fileno()
      except:
        return
    del self.clients[FN]
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
      client.ReadLock.acquire()
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
      client.ReadLock.release()

  def setWrite(self, client, on=True):
    try:
      if client.socket.fileno() not in self.clients:
        return
    except:
      return
    try:
      client.WriteLock.acquire()
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
      client.WriteLock.release()

  def doReads(self):
    events = self.Reader.poll(10000)
    for fileno, event in events:
      read_client = self.clients[fileno]
      if event & select.EPOLLIN:
        self.clientRead(read_client)
      if event & select.EPOLLRDHUP or event & select.EPOLLHUP or event & select.EPOLLERR:
        self.clientErrors(read_client, fileno)

  def clientRead(self, read_client):
    data = ""
    try:
      if read_client.TYPE == "UDP":
        data, addr = read_client.socket.recvfrom(65536)
        if read_client.onData != None:
          read_client.addRead([addr, data])
          self.Executor.schedule(read_client.gotRead, key=read_client)
      elif read_client.TYPE == "TCP":
        data = read_client.socket.recv(65536)
        if len(data) > 0 and read_client.onData != None: 
          read_client.addRead(data)
          self.Executor.schedule(read_client.gotRead, key=read_client)
      elif read_client.TYPE == "CUSTOM":
        data = read_client.READER()
        if len(data) > 0 and read_client.onData != None: 
          read_client.addRead(data)
          self.Executor.schedule(read_client.gotRead, key=read_client)
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

  def clientErrors(self, client, fileno):
    self.log.debug("Removeing Socket %d "%(fileno))
    self.rmClient(client)
    if client.onClose != None:
      client.onClose(fileno)
  
  def doAcceptor(self):
    events = self.Acceptor.poll(10000)
    for fileno, event in events:
      if fileno in self.servers:
        SERVER = self.servers[fileno]
        self.log.debug("New Connection")
        t = TcpClient()
        if SERVER.onConnect != None:
          SERVER.onConnect(t)
        conn, addr = SERVER.socket.accept()
        t.socket = conn
        if SERVER.do_ssl == True:
          t.do_ssl(server=True, certfile=SERVER.certfile, keyfile=SERVER.keyfile)
        t.init_conn()
        self.addClient(t)

