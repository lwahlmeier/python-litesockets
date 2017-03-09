from __future__ import print_function
import unittest, time, hashlib, logging
import litesockets
from . import utils
import operator
import struct

try:
  xrange(1)
except:
  xrange=range



TEST_STRING = ("TEST"*100).encode('utf-8')
TEST_BINARY = struct.pack("!BBBBBB", 255, 0, 0, 11, 127, 200) 

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
log = logging.getLogger("root")
log.setLevel(logging.DEBUG)




class TestTcp(unittest.TestCase):
  def setUp(self):
    self.socketExecuter = litesockets.SocketExecuter()

  def tearDown(self):
    self.socketExecuter.stop()

  def test_SimpleTcpSendTestbinary(self):
    test = utils.testClass(self.socketExecuter)
    server = self.socketExecuter.createTCPServer("localhost", 0)
    server.setOnClient(test.accept)
    server.start()
    PORT = server.getSocket().getsockname()[1]

    client = self.socketExecuter.createTCPClient("localhost", PORT)
    test_client = utils.testClass(self.socketExecuter)
    client.setReader(test_client.read)
    client.connect()
    client.write(TEST_BINARY)

    utils.waitTill(lambda X: test.read_len < X, len(TEST_BINARY) , 500)

    self.assertEquals(test.reads[0], TEST_BINARY)
    test.reads.pop(0)
    test.clients[0].write(TEST_BINARY)

    utils.waitTill(lambda X: test_client.read_len <= X, 0, 500)

    self.assertEquals(test_client.reads[0], TEST_BINARY)
    self.assertEquals(len(self.socketExecuter.getClients()), 2)

    print("Closing!")
    client.close()
    server.close()

    print("{}".format(len(self.socketExecuter.getClients())))
    utils.waitTill(lambda X: len(self.socketExecuter.getClients()) > X, 0, 500)
    utils.waitTill(lambda X: len(self.socketExecuter.getServers()) > X, 0, 500)

    self.assertEquals(len(self.socketExecuter.getClients()), 0)
    self.assertEquals(len(self.socketExecuter.getServers()), 0)

  def test_SimpleTcpSendTest(self):
    test = utils.testClass(self.socketExecuter)
    server = self.socketExecuter.createTCPServer("localhost", 0)
    server.setOnClient(test.accept)
    server.start()
    PORT = server.getSocket().getsockname()[1]

    client = self.socketExecuter.createTCPClient("localhost", PORT)
    test_client = utils.testClass(self.socketExecuter)
    client.setReader(test_client.read)
    client.connect()
    client.write(TEST_STRING)

    utils.waitTill(lambda X: test.read_len < X, len(TEST_STRING) , 500)

    self.assertEquals(test.reads[0], TEST_STRING)
    test.reads.pop(0)
    test.clients[0].write(TEST_STRING)

    utils.waitTill(lambda X: test_client.read_len <= X, 0, 500)

    self.assertEquals(test_client.reads[0], TEST_STRING)
    self.assertEquals(len(self.socketExecuter.getClients()), 2)

    print("Closing!")
    client.close()
    server.close()

    print("{}".format(len(self.socketExecuter.getClients())))
    utils.waitTill(lambda X: len(self.socketExecuter.getClients()) > X, 0, 500)
    utils.waitTill(lambda X: len(self.socketExecuter.getServers()) > X, 0, 500)

    self.assertEquals(len(self.socketExecuter.getClients()), 0)
    self.assertEquals(len(self.socketExecuter.getServers()), 0)


  def test_TCPsendLots(self):
    LOOPS = 500
    STR_SIZE = len(TEST_STRING)
    BYTES = STR_SIZE*LOOPS
    test = utils.testClass(self.socketExecuter)
    server = self.socketExecuter.createTCPServer("localhost", 0)
    server.setOnClient(test.accept)
    server.start()
    PORT = server.getSocket().getsockname()[1]

    client = self.socketExecuter.createTCPClient("localhost", PORT)
    test_client = utils.testClass(self.socketExecuter)
    client.setReader(test_client.read)
    client.connect()

    baseSha = hashlib.sha256()
    for i in xrange(0, LOOPS):
      baseSha.update(TEST_STRING)
      client.write(TEST_STRING)
    newSha = baseSha.hexdigest()

    utils.waitTill(lambda X: test.read_len < X, BYTES, 500)

    self.assertEquals(test.read_len, BYTES)
    self.assertEquals(hashlib.sha256(b''.join(test.reads)).hexdigest(), newSha)
    test.clients[0].write(b''.join(test.reads))

    utils.waitTill(lambda X: test_client.read_len < X, BYTES, 500)

    self.assertEquals(test.read_len, BYTES)
    self.assertEquals(hashlib.sha256(b''.join(test_client.reads)).hexdigest(), newSha)
    
    self.assertEqual(BYTES*2, self.socketExecuter.getStats().getTotalRead())
    self.assertEqual(BYTES*2, self.socketExecuter.getStats().getTotalWrite())
    self.assertEqual(BYTES, client.getStats().getTotalRead())
    self.assertEqual(BYTES, client.getStats().getTotalWrite())
    self.assertEqual(BYTES, test.clients[0].getStats().getTotalRead())
    self.assertEqual(BYTES, test.clients[0].getStats().getTotalWrite())
    time.sleep(.5)
    self.assertTrue(test.clients[0].getStats().getReadRate() > 0.0)
    self.assertTrue(test.clients[0].getStats().getWriteRate() > 0.0)
    
class TestTcpSelect(TestTcp):
  def setUp(self):
    self.socketExecuter = litesockets.SocketExecuter(forcePlatform="win")

  def tearDown(self):
    self.socketExecuter.stop()

