import unittest, time, hashlib, logging
import litesockets
from utils import testClass
from utils import waitTill
import operator


TEST_STRING = "TEST"*100

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
log = logging.getLogger("root")
log.setLevel(logging.DEBUG)




class TestTcp(unittest.TestCase):
  def setUp(self):
    self.socketExecuter = litesockets.SocketExecuter()

  def tearDown(self):
    self.socketExecuter.stop()

  def test_SimpleTcpSendTest(self):
    test = testClass(self.socketExecuter)
    server = self.socketExecuter.createTCPServer("localhost", 0)
    server.setOnClient(test.accept)
    server.start()
    PORT = server.getSocket().getsockname()[1]

    client = self.socketExecuter.createTCPClient("localhost", PORT)
    test_client = testClass(self.socketExecuter)
    client.setReader(test_client.read)
    client.connect()
    self.socketExecuter.addClient(client)
    client.write(TEST_STRING)

    waitTill(lambda X: test.read_len < X, len(TEST_STRING) , 500)

    self.assertEquals(test.reads[0], TEST_STRING)
    test.reads.pop(0)
    test.clients[0].write(TEST_STRING)

    waitTill(lambda X: test_client.read_len <= X, 0, 500)

    self.assertEquals(test_client.reads[0], TEST_STRING)
    client.close()
    server.close()

    waitTill(lambda X: len(self.socketExecuter.getClients()) > X, 0, 500)
    waitTill(lambda X: len(self.socketExecuter.getServers()) > X, 0, 500)

    self.assertEquals(len(self.socketExecuter.getClients()), 0)
    self.assertEquals(len(self.socketExecuter.getServers()), 0)


  def test_TCPsendLots(self):
    LOOPS = 50
    STR_SIZE = len(TEST_STRING)
    BYTES = STR_SIZE*LOOPS
    test = testClass(self.socketExecuter)
    server = self.socketExecuter.createTCPServer("localhost", 0)
    server.setOnClient(test.accept)
    server.start()
    PORT = server.getSocket().getsockname()[1]

    client = self.socketExecuter.createTCPClient("localhost", PORT)
    test_client = testClass(self.socketExecuter)
    client.setReader(test_client.read)
    client.connect()
    self.socketExecuter.addClient(client)
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

    


