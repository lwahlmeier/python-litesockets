import unittest, time, hashlib, logging
import litesockets
from utils import testClass
from utils import waitTill
import operator
import os

DIRNAME = os.path.dirname(__file__)

TEST_STRING = "TEST"*100

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
log = logging.getLogger("root")
log.setLevel(logging.DEBUG)

class TestTcp(unittest.TestCase):
  def setUp(self):
    self.__socketExecuter = litesockets.SocketExecuter()

  def tearDown(self):
    self.__socketExecuter.stop()
    self.__socketExecuter.Executor.shutdown()

  def test_SimpleSSLSendTest(self):
    GSE = litesockets.GlobalSocketExecuter()
    GSE2 = litesockets.GlobalSocketExecuter()
    self.assertEquals(GSE, GSE2)
    ta = testClass(GSE)
    server = litesockets.SSLServer("localhost", 0, certfile="%s/tmp.crt"%(DIRNAME), keyfile="%s/tmp.key"%(DIRNAME))
    server.onNew = ta.accept
    server.connect()
    PORT = server.socket.getsockname()[1]
    GSE.startServer(server)
    client = litesockets.SSLClient("localhost", PORT)
    test_client = testClass(GSE)
    client.__reader = test_client.read
    client.connect()
    GSE.addClient(client)
    client.addWrite(TEST_STRING)

    waitTill(lambda X: ta.read_len < X, len(TEST_STRING) , 500)

    self.assertEquals(ta.reads[0], TEST_STRING)
    ta.reads.pop(0)
    ta.clients[0].addWrite(TEST_STRING)

    waitTill(lambda X: test_client.read_len <= X, 0, 500)

    self.assertEquals(test_client.reads[0], TEST_STRING)

    client.end()
    server.end()
    waitTill(lambda X: len(GSE.clients) > X, 0, 500)
    waitTill(lambda X: len(GSE.servers) > X, 0, 500)
    self.assertEquals(len(GSE.clients), 0)
    self.assertEquals(len(GSE.servers), 0)


  def test_TCPsendLots(self):
    LOOPS = 50
    STR_SIZE = len(TEST_STRING)
    BYTES = STR_SIZE*LOOPS
    test = testClass(self.__socketExecuter)
    server = litesockets.SSLServer("localhost", 0, certfile="%s/tmp.crt"%(DIRNAME), keyfile="%s/tmp.key"%(DIRNAME))
    server.onNew = test.accept
    server.connect()
    PORT = server.socket.getsockname()[1]
    self.__socketExecuter.startServer(server)
    client = litesockets.SSLClient("localhost", PORT)
    test_client = testClass(self.__socketExecuter)
    client.__reader = test_client.read
    client.connect()
    self.__socketExecuter.addClient(client)
    baseSha = hashlib.sha256()
    for i in xrange(0, LOOPS):
      baseSha.update(TEST_STRING)
      client.addWrite(TEST_STRING)
    newSha = baseSha.hexdigest()

    waitTill(lambda X: test.read_len < X, BYTES, 500)

    self.assertEquals(test.read_len, BYTES)
    self.assertEquals(hashlib.sha256("".join(test.reads)).hexdigest(), newSha)
    test.clients[0].addWrite("".join(test.reads))

    waitTill(lambda X: test_client.read_len < X, BYTES, 500)

    self.assertEquals(test.read_len, BYTES)
    self.assertEquals(hashlib.sha256("".join(test_client.reads)).hexdigest(), newSha)

    


