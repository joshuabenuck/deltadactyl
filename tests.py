from deltadactyl import *
import unittest
DEBUG = True

"""
expected, actual
assertEqual
assertTrue
assertRaises
"""
class TestDeltaDactyl(unittest.TestCase):
  def setUp(self):
    pass

  def test_stepped_value_down(self):
    v = SteppedValue([5, 4, 2, 1], int, 3)
    self.assertEqual(3, v())
    v.down()
    self.assertEqual(2, v())

  def test_stepped_value_up(self):
    v = SteppedValue([5, 4, 2, 1], int, 3)
    self.assertEqual(3, v())
    v.up()
    self.assertEqual(4, v())

if __name__ == '__main__':
    unittest.main()

