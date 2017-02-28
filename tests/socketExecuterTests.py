from __future__ import print_function
import unittest, time, hashlib, logging, platform
import litesockets
from threadly import Scheduler
from .utils import testClass, waitTill

try:
    xrange(1)
except:
    xrange = range

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
log = logging.getLogger("root")
log.setLevel(logging.DEBUG)

class TestSE(unittest.TestCase):
  
  def setUp(self):
    self.SCH = Scheduler(10)
    self.SE = litesockets.SocketExecuter(scheduler=self.SCH)
    
  def tearDown(self):
    self.SE.stop()
    self.SCH.shutdown_now()

  def test_SE_ServerStartMany(self):
    SE1 = litesockets.SocketExecuter()
    self.assertTrue(self.SE.isRunning(), "SE not running")
    self.assertTrue(SE1.isRunning(), "SE1 not running")
    self.SE.stop()
    SE1.stop()
    self.assertFalse(self.SE.isRunning(), "SE not running")
    self.assertFalse(SE1.isRunning(), "SE1 not running")
    self.SCH.shutdown_now()

  def test_SE_ClientAddRemove(self):
    CLIENT_NUM = 1
    ta = testClass(self.SE)
    server = self.SE.createTCPServer("localhost", 0)
    server.setOnClient(ta.accept)
    PORT = server.getSocket().getsockname()[1]
    server.start()
    clients = list()

    for i in xrange(CLIENT_NUM):
      client = self.SE.createTCPClient("localhost", PORT)
      client.connect()
      for i in xrange(500):
        if(len(self.SE.getClients()) == (len(clients)*2)+2):
          break
        else:
          time.sleep(.01)
      self.assertEqual(len(self.SE.getClients()), (len(clients)*2)+2)
      clients.append(client)
      self.assertEqual(len(self.SE.getClients()), len(clients)*2)
      
#     for i in xrange(CLIENT_NUM):
#       clients[i].write("TEST")

    for i in xrange(CLIENT_NUM):
      clients[i].close()
      for Q in xrange(500):
        if len(self.SE.getClients()) == (CLIENT_NUM*2)-((i+1)*2):
          break
        else:
          time.sleep(.1)
          
      self.assertEqual(len(self.SE.getClients()), (CLIENT_NUM*2)-((i+1)*2))
    self.assertEqual(len(self.SE.getClients()), 0)

    server.stop()
    server.close()

    self.SE.stop()


  def test_SE_ServerAddRemove(self):
    SERVER_NUM = 5
    testA = list()
    servers = list()
    for i in xrange(SERVER_NUM):
      ta = testClass(self.SE)
      server = self.SE.createTCPServer("localhost", 0)
      server.setOnClient(ta.accept)
      server.start()
      testA.append(ta)
      servers.append(server)
      self.assertEqual(len(self.SE.getServers()), i+1)

    for i in xrange(SERVER_NUM):
      servers[i].close()
      c = 0
      while len(self.SE.getServers()) > len(servers)-(i+1) or c > 500:
        time.sleep(.01)
        c+=1
      self.assertEqual(len(self.SE.getServers()), len(servers)-(i+1))

    c = 0
    while len(self.SE.getServers()) > 0 or c > 500:
      time.sleep(.01)
      c+=1
    self.assertEqual(len(self.SE.getServers()), 0)
    self.SE.startServer("TEST")
    self.assertEqual(len(self.SE.getServers()), 0)

    self.SE.stop()

  def test_SE_Stats(self):
    ta = testClass(self.SE)
    server = self.SE.createTCPServer("localhost", 0)
    server.setOnClient(ta.accept)
    server.start()
    PORT = server.getSocket().getsockname()[1]
    client = self.SE.createTCPClient("localhost", PORT)
    cta = testClass(self.SE)
    client.setReader(cta.read)
    client.connect()
    waitTill(lambda X: len(ta.clients) < X, 1, 500)
    client.write("X"*1000)
    waitTill(lambda X: ta.read_len < X, 1000, 500)
    self.assertEqual(1000, ta.read_len)
    self.assertEqual(1000, self.SE.getStats().getTotalRead())
    self.assertEqual(1000, self.SE.getStats().getTotalWrite())
    self.assertTrue(1000, self.SE.getStats().getReadRate() > 0.0)
    self.assertTrue(1000, self.SE.getStats().getWriteRate() > 0.0)
    server.close()
    client.close()
    

  def test_SE_ClientMaxReads(self):
    ta = testClass(self.SE)
    server = self.SE.createTCPServer("localhost", 0)
    server.setOnClient(ta.accept)
    server.start()
    PORT = server.getSocket().getsockname()[1]
    client = self.SE.createTCPClient("localhost", PORT)
    client.MAXBUFFER = 1
    cta = testClass(self.SE)
    client.setReader(cta.read)
    client.connect()

    c = 0
    while len(ta.clients) <= 0 and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEqual(len(ta.clients), 1)
    ta.clients[0].MAXBUFFER=20
    for i in xrange(20):
      ta.clients[0].write("T"*10)
    c = 0
    while cta.read_len < 200 and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEqual(cta.read_len, 200)
    self.SE.stop()

class TestSESelect(TestSE):
  def setUp(self):
    self.SCH = Scheduler(10)
    self.SE = litesockets.SocketExecuter(scheduler=self.SCH, forcePlatform="win")

  def tearDown(self):
    self.SE.stop()
    self.SCH.shutdown_now()
 

if __name__ == '__main__':
  unittest.main()
