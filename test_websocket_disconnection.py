import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from james.api.server import ConnectionManager

class TestConnectionManager(unittest.IsolatedAsyncioTestCase):
    async def test_broadcast_websocket_disconnection(self):
        manager = ConnectionManager()

        # Create mocked WebSockets
        ws1 = MagicMock()
        ws1.send_text = AsyncMock()

        ws2 = MagicMock()
        ws2.send_text = AsyncMock(side_effect=Exception("Connection closed"))

        ws3 = MagicMock()
        ws3.send_text = AsyncMock()

        manager.active = [ws1, ws2, ws3]

        message = {"test": "data"}
        await manager.broadcast(message)

        # ws1 and ws3 should still be active, ws2 removed
        self.assertEqual(len(manager.active), 2)
        self.assertIn(ws1, manager.active)
        self.assertNotIn(ws2, manager.active)
        self.assertIn(ws3, manager.active)

        import json
        expected_data = json.dumps(message)
        ws1.send_text.assert_called_once_with(expected_data)
        ws2.send_text.assert_called_once_with(expected_data)
        ws3.send_text.assert_called_once_with(expected_data)

if __name__ == '__main__':
    unittest.main()
