import unittest, time, hashlib, logging
import litesockets
from utils import testClass

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
log = logging.getLogger("root")
log.setLevel(logging.DEBUG)


class TestSE(unittest.TestCase):

  def test_SE_ServerStartMany(self):
    SE = litesockets.SocketExecuter()
    SE.start()
    SE1 = litesockets.SocketExecuter()
    SE.stop()
    __socketExecuter.Executor.shutdown()
    SE1.stop()
    SE1.Executor.shutdown()

  def test_SE_ClientAddRemove(self):
    CLIENT_NUM = 5
    SE = litesockets.SocketExecuter()
    ta = testClass(SE)
    server = litesockets.TcpServer("localhost", 0)
    server.onNew = ta.accept
    server.connect()
    PORT = server.socket.getsockname()[1]
    SE.startServer(server)
    clients = list()

    for i in xrange(CLIENT_NUM):
      client = litesockets.TcpClient("localhost", PORT)
      client.connect()
      time.sleep(.1)
      self.assertEquals(len(SE.clients), (i+1)+len(clients))
      SE.addClient(client)
      clients.append(client)
      self.assertEquals(len(SE.clients), len(clients)*2)

    for i in xrange(CLIENT_NUM):
      SE.rmClient(clients[i])
      self.assertEquals(len(SE.clients), (len(clients)*2)-(i+1))

    for i in xrange(CLIENT_NUM):
      SE.rmClient(clients[i])
      self.assertEquals(len(SE.clients), (CLIENT_NUM))

    for i in xrange(CLIENT_NUM):
      SE.addClient(clients[i])
      self.assertEquals(len(SE.clients), (CLIENT_NUM)+(i+1))

    for i in xrange(CLIENT_NUM):
      SE.addClient(clients[i])
      self.assertEquals(len(SE.clients), (CLIENT_NUM*2))

    for i in xrange(CLIENT_NUM):
      clients[i].end()
      while len(SE.clients) > (CLIENT_NUM*2)-((i+1)*2):
        time.sleep(.01)
      self.assertEquals(len(SE.clients), (CLIENT_NUM*2)-((i+1)*2))
    self.assertEquals(len(SE.clients), 0)

    for i in xrange(CLIENT_NUM):
      SE.addClient(clients[i])
      self.assertEquals(len(SE.clients), 0)

    SE.addClient("TEST")
    self.assertEquals(len(SE.clients), 0)
    SE.stop()
    __socketExecuter.Executor.shutdown()


  def test_SE_ServerAddRemove(self):
    SERVER_NUM = 5
    SE = litesockets.SocketExecuter()
    testA = list()
    servers = list()
    for i in xrange(SERVER_NUM):
      ta = testClass(SE)
      server = litesockets.TcpServer("localhost", 0)
      server.onNew = ta.accept
      server.connect()
      SE.startServer(server)
      testA.append(ta)
      servers.append(server)
      self.assertEquals(len(SE.servers), i+1)

    for i in xrange(SERVER_NUM):
      SE.stopServer(servers[i])
      self.assertEquals(len(SE.servers), len(servers)-(i+1))

    for i in xrange(SERVER_NUM):
      SE.stopServer(servers[i])
      self.assertEquals(len(SE.servers), 0)

    for i in xrange(SERVER_NUM):
      SE.startServer(servers[i])
      self.assertEquals(len(SE.servers), i+1)
    
    for i in xrange(SERVER_NUM):
      SE.startServer(servers[i])
      self.assertEquals(len(SE.servers), len(servers))

    for i in xrange(SERVER_NUM):
      servers[i].end()
      c = 0
      while len(SE.servers) > len(servers)-(i+1) or c > 500:
        time.sleep(.01)
        c+=1
      self.assertEquals(len(SE.servers), len(servers)-(i+1))

    for i in xrange(SERVER_NUM):
      SE.startServer(servers[i])
    c = 0
    while len(SE.servers) > 0 or c > 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(len(SE.servers), 0)

    SE.startServer("TEST")
    self.assertEquals(len(SE.servers), 0)
    SE.stop()
    __socketExecuter.Executor.shutdown()


  def test_SE_ClientMaxReads(self):
    SE = litesockets.SocketExecuter()
    ta = testClass(SE)
    server = litesockets.TcpServer("localhost", 0)
    server.onNew = ta.accept
    server.connect()
    PORT = server.socket.getsockname()[1]
    SE.startServer(server)
    client = litesockets.TcpClient("localhost", PORT)
    client.MAXBUFFER = 1
    cta = testClass(SE)
    client.__reader = cta.read
    client.connect()
    SE.addClient(client)
    c = 0
    while len(ta.clients) <= 0 and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(len(ta.clients), 1)
    ta.clients[0].MAXBUFFER=20
    for i in xrange(20):
      print "write", 1
      ta.clients[0].addWrite("T"*10)
    c = 0
    while cta.read_len < 200 and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(cta.read_len, 200)
    SE.stop()
    __socketExecuter.Executor.shutdown()

if __name__ == '__main__':
  unittest.main()

