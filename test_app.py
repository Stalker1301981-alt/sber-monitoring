import unittest, sys, os, threading, time
sys.path.insert(0, os.path.dirname(__file__))
from calc import SberMonitoringWebsite, APP_VERSION
from http.server import HTTPServer

class TestApp(unittest.TestCase):
    def test_version_exists(self):
        self.assertTrue(len(APP_VERSION) > 0)

    def test_class_exists(self):
        self.assertTrue(issubclass(SberMonitoringWebsite, object))

if __name__ == '__main__':
    unittest.main()
