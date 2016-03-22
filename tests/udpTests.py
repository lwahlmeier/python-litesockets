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
    self.__socketExecuter.Executor.shutdown()

  def test_SimpleUdpSendTest(self):
    ta = testClass(self.__socketExecuter)
    server = litesockets.UdpServer("localhost", 0)
    server.onNew = ta.accept
    server.connect()
    PORT = server.socket.getsockname()[1]
    self.__socketExecuter.addClient(server)
    client = litesockets.UdpServer("localhost", 0)
    cta = testClass(self.__socketExecuter)
    client.onNew = cta.accept
    client.connect()
    self.__socketExecuter.addClient(client)
    client.addWrite([("localhost", PORT), TEST_STRING])
    c = 0
    while ta.read_len < len(TEST_STRING) and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(ta.reads[0], TEST_STRING)
    self.assertEquals(len(ta.clients), 1)
    ta.clients[0].addWrite(ta.reads[0])
    c = 0
    while cta.read_len < len(TEST_STRING) and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(cta.reads[0], TEST_STRING)
    client.end()
    server.end()
    c = 0
    while len(self.__socketExecuter.clients) > 0 and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(len(self.__socketExecuter.clients), 0)
    

  def test_UdpSendLots(self):
    LOOPS = 500
    STR_SIZE = len(TEST_STRING)
    BYTES = STR_SIZE*LOOPS
    ta = testClass(self.__socketExecuter)
    server = litesockets.UdpServer("localhost", 0)
    server.onNew = ta.accept
    server.connect()
    PORT = server.socket.getsockname()[1]
    self.__socketExecuter.addClient(server)
    client = litesockets.UdpServer("localhost", 0)
    cta = testClass(self.__socketExecuter)
    client.onNew = cta.accept
    client.connect()
    self.__socketExecuter.addClient(client)
    baseSha = hashlib.sha256()
    for i in xrange(0, LOOPS):
      baseSha.update(TEST_STRING)
      client.addWrite([("localhost", PORT), TEST_STRING])
    newSha = baseSha.hexdigest()
    c = 0
    while ta.read_len < BYTES and c < 500:
      time.sleep(.01)
      c+=1
    print "WAIT", ta.read_len, c
    self.assertEquals(hashlib.sha256("".join(ta.reads)).hexdigest(), newSha)
    self.assertEquals(ta.read_len, BYTES)
    X = "".join(ta.reads)
    while len(X) > 0:
      ta.clients[0].addWrite(X[:1000])
      X=X[1000:]
    c = 0
    while cta.read_len < BYTES and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(hashlib.sha256("".join(cta.reads)).hexdigest(), newSha)
    client.end()
    server.end()
    c = 0
    while len(self.__socketExecuter.clients) > 0 and c < 500:
      time.sleep(.01)
      c+=1
    self.assertEquals(len(self.__socketExecuter.clients), 0)
    

