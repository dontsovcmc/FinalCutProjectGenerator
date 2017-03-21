# -*- coding: utf-8 -*-
__author__ = 'dontsov'
import unittest

from main import fc_duration, parse_keylogger_buf

class TestKeyLogger(unittest.TestCase):

    def test_fc_duration(self):
        self.assertEqual(fc_duration(0, 25),    '0s')
        self.assertEqual(fc_duration(1000, 25), '1s')
        self.assertEqual(fc_duration(2000, 25), '2s')

        self.assertEqual(fc_duration(1001, 25), '1s')
        self.assertEqual(fc_duration(1019, 25), '1s')
        self.assertEqual(fc_duration(1020, 25), '2600/2500s')
        self.assertEqual(fc_duration(1040, 25), '2600/2500s')
        self.assertEqual(fc_duration(40, 25),   '100/2500s')
        self.assertEqual(fc_duration(5040, 25), '12600/2500s')

    def test_parse_keylogger_lines(self):
        # slide index, offset in millisec, duration in millisec
        buf = '''2017-03-18 04:00:00.0	[Down]
2017-03-18 04:00:00.040	[Down]
2017-03-18 04:00:00.240	[Down]
2017-03-18 04:00:00.960	[Down]
2017-03-18 04:00:06.960	[Down]
2017-03-18 04:00:18.960	[Down]'''.split('\n')

        ts = parse_keylogger_buf(buf)
        self.assertEqual(len(ts), 7)
        self.assertEqual(ts[0], (0, 0, 10000))
        self.assertEqual(ts[1], (1, 10000, 40))
        self.assertEqual(ts[2], (2, 10040, 200))
        self.assertEqual(ts[3], (3, 10240, 720))
        self.assertEqual(ts[4], (4, 10960, 6000))
        self.assertEqual(ts[5], (5, 16960, 12000))
        self.assertEqual(ts[6], (6, 28960, 10000))


    def test_split(self):
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # check that s.split fails when the separator is not a string
        with self.assertRaises(TypeError):
            s.split(2)

if __name__ == '__main__':
    unittest.main()