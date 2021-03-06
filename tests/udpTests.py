from __future__ import print_function
import unittest, time, hashlib, logging
import litesockets
from .utils import testClass, waitTill

try:
    xrange(1)
except:
    xrange = range



TEST_STRING = b"TEST"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
log = logging.getLogger("root")
log.setLevel(logging.DEBUG)

class TestUdp(unittest.TestCase):

  def setUp(self):
    self.SE = litesockets.SocketExecuter()

  def tearDown(self):
    self.SE.stop()

  def test_SimpleUdpSendTest(self):
    ta = testClass(self.SE)
    server = self.SE.createUDPServer("localhost", 0)
    server.setOnClient(ta.accept)
    server.start()
    PORT = server.getSocket().getsockname()[1]
    client = self.SE.createUDPServer("localhost", 0)
    cta = testClass(self.SE, name="OTHER")
    client.setOnClient(cta.accept)
    client.start()
    client.write([("localhost", PORT), TEST_STRING])
    c = 0
    while ta.read_len < len(TEST_STRING) and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(ta.reads[0], TEST_STRING)
    self.assertEquals(len(ta.clients), 1)
    ta.clients[0].write(ta.reads[0])
    c = 0
    while cta.read_len < len(TEST_STRING) and c < 100:
      time.sleep(.01)
      c+=1
    self.assertEquals(cta.reads[0], TEST_STRING)
    client.close()
    server.close()
    c = 0
    while len(self.SE.getClients()) > 0 and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(0, len(self.SE.getClients()))
    

  def test_UdpSendLots(self):
    LTEST_STRING = TEST_STRING*10
    LOOPS = 1000
    STR_SIZE = len(LTEST_STRING)
    BYTES = STR_SIZE*LOOPS
    ta = testClass(self.SE)
    server = self.SE.createUDPServer("localhost", 0)
    server.setOnClient(ta.accept)
    server.start()
    server.stop()
    server.start()
    PORT = server.getSocket().getsockname()[1]
    
    client = self.SE.createUDPServer("localhost", 0)
    cta = testClass(self.SE)
    client.setOnClient(cta.accept)
    #client.addCloseListener(cta.accept)
    client.start()
    
    cclient = client.createUDPClient("127.0.0.1", PORT)
    cclient.MAXBUFFER = BYTES*10
    cclient.setReader(cta.read)
    
    
    sclient = server.createUDPClient("127.0.0.1", client.getSocket().getsockname()[1])
    sclient.MAXBUFFER = BYTES*10
    sclient.setReader(ta.read)
    
    baseSha = hashlib.sha256()
    for i in xrange(0, LOOPS):
      baseSha.update(LTEST_STRING)
      cclient.write(LTEST_STRING)
      time.sleep(.001)
    newSha = baseSha.hexdigest()


    waitTill(lambda X: ta.read_len < X, BYTES, 500)

    #print("WAIT", ta.read_len, BYTES)
    #print(ta.reads[0], cclient.getWriteBufferSize(), sclient.getReadBufferSize(), server.getClients())
    
    self.assertEquals(hashlib.sha256(b"".join(ta.reads)).hexdigest(), newSha)
    self.assertEquals(ta.read_len, BYTES)
    X = b"".join(ta.reads)
    
    i=0
    while len(X) > 0:
      sclient.write(X[:1000])
      X=X[1000:]
      i+=1
      
    waitTill(lambda X: cta.read_len < X, BYTES, 500)
    
    #print("WAIT", cta.read_len, BYTES)
    #print (cta.reads[0], cclient.getReadBufferSize(), cclient.getWriteBufferSize())
    
    self.assertEquals(hashlib.sha256(b"".join(cta.reads)).hexdigest(), newSha)
    client.close()
    server.close()
    c = 0
    while len(self.SE.getClients()) > 0 and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(len(self.SE.getClients()), 0)

class TestUdpSelect(TestUdp):

  def setUp(self):
    self.SE = litesockets.SocketExecuter(forcePlatform="win")

  def tearDown(self):
    self.SE.stop()
