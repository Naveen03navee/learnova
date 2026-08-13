import unittest
import sys
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.generation.deduplicator import check_duplicate

class TestSemanticDeduplicator(unittest.IsolatedAsyncioTestCase):
    @patch('app.services.generation.deduplicator.asyncio.to_thread')
    async def test_deduplicator_queries_generated_and_permanent(self, mock_embed):
        mock_embed.return_value = [0.1] * 384
        
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.execute = AsyncMock()
        
        # Simulate no duplicates found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        is_dup = await check_duplicate(mock_db, "Test text", "exam1", "sub1")
        self.assertFalse(is_dup)
        
        # Verify db.execute was called twice: once for GeneratedQuestion, once for Question
        self.assertEqual(mock_db.execute.call_count, 2)
        
    @patch('app.services.generation.deduplicator.asyncio.to_thread')
    async def test_deduplicator_returns_true_if_found_in_generated(self, mock_embed):
        mock_embed.return_value = [0.1] * 384
        
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.execute = AsyncMock()
        
        # Simulate found in GeneratedQuestion
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "some_id"
        mock_db.execute.return_value = mock_result
        
        is_dup = await check_duplicate(mock_db, "Test text", "exam1", "sub1")
        self.assertTrue(is_dup)
        
        # Verify db.execute was called only once (short-circuits)
        self.assertEqual(mock_db.execute.call_count, 1)

if __name__ == '__main__':
    unittest.main()




