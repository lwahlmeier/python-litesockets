import unittest, hashlib, logging
import litesockets
from utils import testClass
from utils import waitTill
import os

DIRNAME = os.path.dirname(__file__)

TEST_STRING = "TEST"*100

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
log = logging.getLogger("root")
log.setLevel(logging.DEBUG)

class TestSSL(unittest.TestCase):
  def setUp(self):
    self.__socketExecuter = litesockets.SocketExecuter()

  def tearDown(self):
    self.__socketExecuter.stop()

  def test_SimpleSSLSendTest(self):
    ta = testClass(self.__socketExecuter)
    server = self.__socketExecuter.createTCPServer("localhost", 0)
    server.setSSLInfo("%s/tmp.crt"%(DIRNAME), "%s/tmp.key"%(DIRNAME))
    server.setOnClient(ta.accept)
    server.start()
    PORT = server.getSocket().getsockname()[1]

    client = self.__socketExecuter.createTCPClient("localhost", PORT)
    test_client = testClass(self.__socketExecuter)
    client.setReader(test_client.read)
    client.enableSSL(start=True)
    client.connect()

    client.write(TEST_STRING)

    waitTill(lambda X: ta.read_len < X, len(TEST_STRING) , 500)

    self.assertEquals(ta.reads[0], TEST_STRING)
    ta.reads.pop(0)
    ta.clients[0].write(TEST_STRING)

    waitTill(lambda X: test_client.read_len <= X, 0, 500)

    self.assertEquals(test_client.reads[0], TEST_STRING)
    
    
    client.close()
    server.close()

    waitTill(lambda X: len(self.__socketExecuter.getClients()) > X, 0, 500)
    waitTill(lambda X: len(self.__socketExecuter.getServers()) > X, 0, 500)
    self.assertEquals(0, len(self.__socketExecuter.getClients()))
    self.assertEquals(0, len(self.__socketExecuter.getServers()))


  def test_SSLsendLots(self):
    LOOPS = 500
    STR_SIZE = len(TEST_STRING)
    BYTES = STR_SIZE*LOOPS
    test = testClass(self.__socketExecuter)
    server = self.__socketExecuter.createTCPServer("localhost", 0)
    server.setSSLInfo("%s/tmp.crt"%(DIRNAME), "%s/tmp.key"%(DIRNAME))
    server.setOnClient(test.accept)
    server.start()
    PORT = server.getSocket().getsockname()[1]

    client = self.__socketExecuter.createTCPClient("localhost", PORT)
    test_client = testClass(self.__socketExecuter)
    client.setReader(test_client.read)
    client.enableSSL(start=True)
    client.connect()
    baseSha = hashlib.sha256()
    for i in xrange(0, LOOPS):
      baseSha.update(TEST_STRING)
      client.write(TEST_STRING)
    newSha = baseSha.hexdigest()

    waitTill(lambda X: test.read_len < X, BYTES, 500)

    self.assertEquals(test.read_len, BYTES)
    self.assertEquals(hashlib.sha256("".join(test.reads)).hexdigest(), newSha)
    test.clients[0].write("".join(test.reads))

    waitTill(lambda X: test_client.read_len < X, BYTES, 500)

    self.assertEquals(test.read_len, BYTES)
    self.assertEquals(hashlib.sha256("".join(test_client.reads)).hexdigest(), newSha)

    


