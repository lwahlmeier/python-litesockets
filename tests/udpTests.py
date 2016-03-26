import unittest, time, hashlib, logging
import litesockets
from utils import testClass



TEST_STRING = "TEST"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
log = logging.getLogger("root")
log.setLevel(logging.DEBUG)

class TestUdp(unittest.TestCase):

  def setUp(self):
    self.__socketExecuter = litesockets.SocketExecuter()

  def tearDown(self):
    self.__socketExecuter.stop()

  def test_SimpleUdpSendTest(self):
    ta = testClass(self.__socketExecuter)
    server = self.__socketExecuter.createUDPServer("localhost", 0)
    server.setOnClient(ta.accept)
    server.start()
    PORT = server.getSocket().getsockname()[1]
    client = self.__socketExecuter.createUDPServer("localhost", 0)
    cta = testClass(self.__socketExecuter, name="OTHER")
    client.setOnClient(cta.accept)
    client.start()
    client.write([("localhost", PORT), TEST_STRING])
    c = 0
    while ta.read_len < len(TEST_STRING) and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(ta.reads[0], TEST_STRING)
    self.assertEquals(len(ta.clients), 1)
    print "----------clients:", ta.clients
    ta.clients[0].write(ta.reads[0])
    c = 0
    while cta.read_len < len(TEST_STRING) and c < 100:
      print cta.read_len
      time.sleep(.01)
      c+=1
    print "--------other Read"
    self.assertEquals(cta.reads[0], TEST_STRING)
    client.close()
    server.close()
    print "--------Close Called!"
    c = 0
    while len(self.__socketExecuter.getClients()) > 0 and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(0, len(self.__socketExecuter.getClients()))
    

  def test_UdpSendLots(self):
    LOOPS = 200
    STR_SIZE = len(TEST_STRING)
    BYTES = STR_SIZE*LOOPS
    ta = testClass(self.__socketExecuter)
    server = self.__socketExecuter.createUDPServer("localhost", 0)
    server.setOnClient(ta.accept)
    server.start()
    server.stop()
    server.start()
    PORT = server.getSocket().getsockname()[1]
    
    client = self.__socketExecuter.createUDPServer("localhost", 0)
    cta = testClass(self.__socketExecuter)
    client.setOnClient(cta.accept)
    #client.addCloseListener(cta.accept)
    client.start()
    
    baseSha = hashlib.sha256()
    for i in xrange(0, LOOPS):
      baseSha.update(TEST_STRING)
      client.write([("localhost", PORT), TEST_STRING])
      if i%10 == 0:
        time.sleep(.1)
    newSha = baseSha.hexdigest()
    c = 0
    
    while ta.read_len < BYTES and c < 500:
      time.sleep(.01)
      c+=1
    print "WAIT", ta.read_len, BYTES
    
    
    self.assertEquals(hashlib.sha256("".join(ta.reads)).hexdigest(), newSha)
    self.assertEquals(ta.read_len, BYTES)
    X = "".join(ta.reads)
    
    i=0
    while len(X) > 0:
      ta.clients[0].write(X[:1000])
      X=X[1000:]
      time.sleep(.1)
      i+=1
      
      
    c = 0
    while cta.read_len < BYTES and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(hashlib.sha256("".join(cta.reads)).hexdigest(), newSha)
    client.close()
    server.close()
    c = 0
    while len(self.__socketExecuter.getClients()) > 0 and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(len(self.__socketExecuter.getClients()), 0)
    

