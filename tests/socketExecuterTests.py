import unittest, time, hashlib, logging
import litesockets
from threadly import Scheduler
from utils import testClass

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
log = logging.getLogger("root")
log.setLevel(logging.DEBUG)


class TestSE(unittest.TestCase):

  def test_SE_ServerStartMany(self):
    sch = Scheduler(10)
    SE = litesockets.SocketExecuter(scheduler=sch)
    SE1 = litesockets.SocketExecuter()
    self.assertTrue(SE.isRunning(), "SE not running")
    self.assertTrue(SE1.isRunning(), "SE1 not running")
    SE.stop()
    SE1.stop()
    self.assertFalse(SE.isRunning(), "SE not running")
    self.assertFalse(SE1.isRunning(), "SE1 not running")
    sch.shutdown_now()

  def test_SE_ClientAddRemove(self):
    CLIENT_NUM = 5
    SE = litesockets.SocketExecuter()
    ta = testClass(SE)
    server = SE.createTCPServer("localhost", 0)
    server.setOnClient(ta.accept)
    PORT = server.getSocket().getsockname()[1]
    server.start()
    clients = list()

    for i in xrange(CLIENT_NUM):
      print PORT, type(PORT)
      client = SE.createTCPClient("localhost", PORT)
      client.connect()
      for i in xrange(500):
        if(len(SE.getClients()) == (len(clients)*2)+2):
          break
        else:
          time.sleep(.01)
      self.assertEquals(len(SE.getClients()), (len(clients)*2)+2)
      clients.append(client)
      self.assertEquals(len(SE.getClients()), len(clients)*2)

    for i in xrange(CLIENT_NUM):
      clients[i].close()
      for Q in xrange(500):
        print len(SE.getClients()), (CLIENT_NUM*2)-((i+1)*2)
        if len(SE.getClients()) == (CLIENT_NUM*2)-((i+1)*2):
          break
        else:
          time.sleep(.1)
          
      self.assertEquals(len(SE.getClients()), (CLIENT_NUM*2)-((i+1)*2))
    self.assertEquals(len(SE.getClients()), 0)

    SE.stop()


  def test_SE_ServerAddRemove(self):
    SERVER_NUM = 5
    SE = litesockets.SocketExecuter()
    testA = list()
    servers = list()
    for i in xrange(SERVER_NUM):
      ta = testClass(SE)
      server = SE.createTCPServer("localhost", 0)
      server.setOnClient(ta.accept)
      server.start()
      testA.append(ta)
      servers.append(server)
      self.assertEquals(len(SE.getServers()), i+1)

    for i in xrange(SERVER_NUM):
      servers[i].close()
      c = 0
      while len(SE.getServers()) > len(servers)-(i+1) or c > 500:
        print len(SE.getServers()), len(servers)-(i+1)
        time.sleep(.01)
        c+=1
      self.assertEquals(len(SE.getServers()), len(servers)-(i+1))

    c = 0
    while len(SE.getServers()) > 0 or c > 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(len(SE.getServers()), 0)
    SE.startServer("TEST")
    self.assertEquals(len(SE.getServers()), 0)
    SE.stop()


  def test_SE_ClientMaxReads(self):
    SE = litesockets.SocketExecuter()
    ta = testClass(SE)
    server = SE.createTCPServer("localhost", 0)
    server.setOnClient(ta.accept)
    server.start()
    PORT = server.getSocket().getsockname()[1]
    client = SE.createTCPClient("localhost", PORT)
    client.MAXBUFFER = 1
    cta = testClass(SE)
    client.setReader(cta.read)
    client.connect()

    c = 0
    while len(ta.clients) <= 0 and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(len(ta.clients), 1)
    ta.clients[0].MAXBUFFER=20
    for i in xrange(20):
      print "write", 1
      ta.clients[0].write("T"*10)
    c = 0
    while cta.read_len < 200 and c < 500:
      print "waiting", cta.read_len
      time.sleep(.01)
      c+=1
    self.assertEquals(cta.read_len, 200)
    SE.stop()


if __name__ == '__main__':
  unittest.main()

