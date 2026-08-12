import unittest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.generation.orchestrator import _calculate_batches

class TestBatchCalculation(unittest.TestCase):
    def test_calculate_batches(self):
        self.assertEqual(_calculate_batches(5, 5), [5])
        self.assertEqual(_calculate_batches(12, 5), [5, 5, 2])
        self.assertEqual(_calculate_batches(20, 5), [5, 5, 5, 5])
        self.assertEqual(_calculate_batches(3, 5), [3])

if __name__ == '__main__':
    unittest.main()
