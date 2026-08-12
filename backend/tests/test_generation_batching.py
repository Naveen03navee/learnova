import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.generation.orchestrator import _calculate_batches
from app.core.config import settings

class TestGenerationBatchingLogic(unittest.TestCase):
    def setUp(self):
        self.original_batch_size = settings.GENERATION_BATCH_SIZE
        settings.GENERATION_BATCH_SIZE = 5

    def tearDown(self):
        settings.GENERATION_BATCH_SIZE = self.original_batch_size

    def test_calculate_batches_exact_multiple(self):
        # 20 requested, batch size 5 -> [5, 5, 5, 5]
        batches = _calculate_batches(20, 5)
        self.assertEqual(batches, [5, 5, 5, 5])

    def test_calculate_batches_remainder(self):
        # 12 requested, batch size 5 -> [5, 5, 2]
        batches = _calculate_batches(12, 5)
        self.assertEqual(batches, [5, 5, 2])

    def test_calculate_batches_less_than_batch(self):
        # 3 requested, batch size 5 -> [3]
        batches = _calculate_batches(3, 5)
        self.assertEqual(batches, [3])
        
    def test_calculate_batches_single_batch(self):
        # 5 requested, batch size 5 -> [5]
        batches = _calculate_batches(5, 5)
        self.assertEqual(batches, [5])

if __name__ == '__main__':
    unittest.main()
