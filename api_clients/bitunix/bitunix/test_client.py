import unittest
from unittest.mock import patch, MagicMock
from client import BitUnixClient, Candlestick # Assuming client.py is in the same directory or accessible via PYTHONPATH
import requests

class TestBitUnixClient(unittest.TestCase):

    def setUp(self):
        # It's good practice to set up the client for each test if it holds state
        # or if environment variable loading needs to be consistent.
        # For now, we rely on python-dotenv in client.py for API keys if needed.
        self.client = BitUnixClient()

    @patch('requests.request')
    def test_get_historical_klines_success(self, mock_request):
        """Test successful retrieval of historical klines."""
        mock_response_data = {
            "code": 0,
            "msg": "Success",
            "data": [
                {
                    "time": 1672410780000,
                    "open": "60000.0",
                    "high": "60001.0",
                    "low": "59989.2",
                    "close": "60000.5",
                    "baseVol": "10.5",   # Corresponds to 'volume' in Candlestick
                    "quoteVol": "630000.0", # Corresponds to 'quote_volume'
                    "type": "LAST_PRICE"
                },
                {
                    "time": 1672410840000,
                    "open": "60000.5",
                    "high": "60002.0",
                    "low": "59990.0",
                    "close": "60001.0",
                    "baseVol": "12.3",
                    "quoteVol": "738000.0",
                    # "type" field might be missing, testing .get() behavior
                }
            ]
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock() # Ensure it doesn't raise for success
        mock_request.return_value = mock_response

        symbol = "BTCUSDT"
        interval = "1m"
        klines = self.client.get_historical_klines(symbol=symbol, interval=interval, limit=2)

        self.assertEqual(len(klines), 2)
        
        # Check first kline
        self.assertIsInstance(klines[0], Candlestick)
        self.assertEqual(klines[0].open_time, 1672410780000)
        self.assertEqual(klines[0].open_price, 60000.0)
        self.assertEqual(klines[0].high_price, 60001.0)
        self.assertEqual(klines[0].low_price, 59989.2)
        self.assertEqual(klines[0].close_price, 60000.5)
        self.assertEqual(klines[0].volume, 10.5)
        self.assertEqual(klines[0].quote_volume, 630000.0)
        self.assertEqual(klines[0].kline_type, "LAST_PRICE")

        # Check second kline (testing missing 'type')
        self.assertEqual(klines[1].open_time, 1672410840000)
        self.assertEqual(klines[1].close_price, 60001.0)
        self.assertEqual(klines[1].volume, 12.3)
        self.assertIsNone(klines[1].kline_type) # Should be None due to .get("type")

        # Verify that requests.request was called correctly
        expected_params = {
            "symbol": symbol,
            "interval": interval,
            "limit": 2
        }
        mock_request.assert_called_once_with(
            "GET",
            f"{self.client.BASE_URL}/api/v1/futures/market/kline",
            params=expected_params,
            json=None, # No json data for GET
            headers=self.client._get_headers() # Check if headers are passed
        )

    @patch('requests.request')
    def test_get_historical_klines_api_error(self, mock_request):
        """Test API error during kline retrieval (e.g., bad request, invalid symbol)."""
        mock_error_response_data = {
            "code": 10001, # Example error code
            "msg": "Invalid symbol",
            "data": None
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_error_response_data
        # For API errors where HTTP status might still be 200 but "code" is non-zero
        mock_response.raise_for_status = MagicMock() 
        mock_request.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError) as context:
            self.client.get_historical_klines(symbol="INVALIDPAIR", interval="1h")
        
        self.assertIn("API Error: Invalid symbol", str(context.exception))
        # Check that the original response was attached to the exception
        self.assertIs(context.exception.response, mock_response)


    @patch('requests.request')
    def test_get_historical_klines_http_error(self, mock_request):
        """Test HTTP error (e.g., 429 Too Many Requests, 500 Internal Server Error)."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Simulated HTTP 429", response=MagicMock(text="Rate limit exceeded"))
        mock_request.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError) as context:
            self.client.get_historical_klines(symbol="BTCUSDT", interval="1m")
        
        self.assertIn("Simulated HTTP 429", str(context.exception))

    @patch('requests.request')
    def test_get_historical_klines_network_error(self, mock_request):
        """Test network error (e.g., requests.exceptions.ConnectionError)."""
        mock_request.side_effect = requests.exceptions.ConnectionError("Simulated network problem")

        with self.assertRaises(requests.exceptions.ConnectionError) as context:
            self.client.get_historical_klines(symbol="BTCUSDT", interval="1m")
            
        self.assertIn("Simulated network problem", str(context.exception))

    @patch('requests.request')
    def test_get_historical_klines_empty_data(self, mock_request):
        """Test successful response but with empty data list."""
        mock_response_data = {
            "code": 0,
            "msg": "Success",
            "data": [] # Empty list of klines
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response

        klines = self.client.get_historical_klines(symbol="BTCUSDT", interval="1h", limit=5)
        self.assertEqual(len(klines), 0)
        self.assertEqual(klines, [])

if __name__ == '__main__':
    unittest.main() 