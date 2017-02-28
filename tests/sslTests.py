from __future__ import print_function
import unittest, hashlib, logging
import litesockets, time
from . import utils
import os

try:
  xrange(1)
except:
  xrange=range

DIRNAME = os.path.dirname(__file__)

TEST_STRING = ("TEST"*100).encode('utf-8')

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
log = logging.getLogger("root")
log.setLevel(logging.DEBUG)

class TestSSL(unittest.TestCase):
  def setUp(self):
    self.SE = litesockets.SocketExecuter()

  def tearDown(self):
    self.SE.stop()

  def test_SimpleSSLSendTest(self):
    ta = utils.testClass(self.SE)
    server = self.SE.createTCPServer("localhost", 0)
    server.setSSLInfo(certfile="%s/tmp.crt"%(DIRNAME), keyfile="%s/tmp.key"%(DIRNAME), do_handshake_on_connect=True)
    server.setOnClient(ta.accept)
    server.start()
    PORT = server.getSocket().getsockname()[1]

    client = self.SE.createTCPClient("localhost", PORT)
    test_client = utils.testClass(self.SE)
    client.setReader(test_client.read)
    client.enableSSL()
    client.startSSL()
    client.connect()
    client.write(TEST_STRING)
    utils.waitTill(lambda X: ta.read_len < X, len(TEST_STRING) , 500)

    self.assertEquals(ta.reads[0], TEST_STRING)
    ta.reads.pop(0)
    ta.clients[0].write(TEST_STRING)

    utils.waitTill(lambda X: test_client.read_len <= X, 0, 500)

    self.assertEquals(test_client.reads[0], TEST_STRING)
    print("Done Read")
    time.sleep(1)
    
    client.close()
    print("{}".format(client))
    server.close()

    utils.waitTill(lambda X: len(self.SE.getClients()) > X, 0, 5000)
    utils.waitTill(lambda X: len(self.SE.getServers()) > X, 0, 5000)
    print("Done Waiting")
    self.assertEquals(0, len(self.SE.getClients()))
    self.assertEquals(0, len(self.SE.getServers()))

  def test_SSLsendLots(self):
    LOOPS = 500
    STR_SIZE = len(TEST_STRING)
    BYTES = STR_SIZE*LOOPS
    test = utils.testClass(self.SE)
    server = self.SE.createTCPServer("localhost", 0)
    server.setSSLInfo(certfile="%s/tmp.crt"%(DIRNAME), keyfile="%s/tmp.key"%(DIRNAME), do_handshake_on_connect=True)
    server.setOnClient(test.accept)
    server.start()
    PORT = server.getSocket().getsockname()[1]

    client = self.SE.createTCPClient("localhost", PORT)
    test_client = utils.testClass(self.SE)
    client.setReader(test_client.read)
    client.enableSSL()
    client.connect()
    client.startSSL()
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

    
class TestSSLSelect(TestSSL):
  def setUp(self):
    self.SE = litesockets.SocketExecuter(forcePlatform="win")

  def tearDown(self):
    self.SE.stop()
  

