import json
import time
import requests
import websocket
import threading
import schedule
from datetime import datetime

__all__ = ['AlgolabAPI']

class AlgolabAPI:
    def __init__(self, api_key=None):
        self.hostname = "www.algolab.com.tr"
        self.api_hostname = f"https://{self.hostname}"
        self.api_url = self.api_hostname
        self.socket_url = f"wss://{self.hostname}/api/ws"
        self.access_token = None
        self.refresh_token = None
        self.ws = None
        self.connected = False
        self.headers = {}
        if api_key:
            self.headers = {
                "APIKEY": api_key,
                "Content-Type": "application/json"
            }

    def refresh_token(self, refresh_token=None):
        """Refresh access token using refresh token"""
        try:
            if not refresh_token and not self.refresh_token:
                raise Exception("No refresh token available")
            
            url = f"{self.api_url}/api/RefreshToken"
            headers = self.headers.copy()
            
            if refresh_token:
                self.refresh_token = refresh_token
            
            data = {
                "refreshToken": self.refresh_token
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                self.access_token = result.get('token', '')
                self.refresh_token = result.get('refreshToken', '')
                return self.access_token
            else:
                raise Exception(result.get('message', 'Token refresh failed'))
        except Exception as e:
            raise Exception(f"Token refresh error: {str(e)}")

    def connect(self, username, password):
        """Login to Algolab API"""
        try:
            # First, get the API key if not already set
            if not self.headers:
                self.headers = {
                    "APIKEY": f"API-{username}",
                    "Content-Type": "application/json"
                }
            
            # Login request
            url = f"{self.api_url}/api/LoginUser"
            data = {
                "username": username,
                "password": password,
                "apiKey": self.headers.get("APIKEY")
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                self.access_token = result.get('token', '')
                self.refresh_token = result.get('refreshToken', '')  # Store refresh token
                return True
            else:
                raise Exception(result.get('message', 'Login failed'))
        except Exception as e:
            raise Exception(f"Login error: {str(e)}")

    def get_token(self):
        """Return current tokens"""
        return {
            'token': self.access_token,
            'refresh_token': self.refresh_token
        }

    def get_headers(self):
        """Get headers with access token"""
        headers = self.headers.copy()
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        return headers

    def get_symbols(self):
        """Get available symbols"""
        try:
            url = f"{self.api_url}/api/GetEquityInfo"
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                # Extract symbol names from the equity info
                symbols = [item.get('symbol') for item in result.get('data', [])]
                return symbols
            else:
                raise Exception(result.get('message', 'Failed to get symbols'))
        except Exception as e:
            raise Exception(f"Error getting symbols: {str(e)}")

    def get_history(self, symbol, period="1d", interval="1m"):
        """Get historical data for a symbol"""
        try:
            url = f"{self.api_url}/api/GetCandleData"
            params = {
                "symbol": symbol,
                "period": period,
                "interval": interval
            }
            response = requests.get(url, headers=self.get_headers(), params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                return result.get('data', [])
            else:
                raise Exception(result.get('message', 'Failed to get historical data'))
        except Exception as e:
            raise Exception(f"Error getting historical data: {str(e)}")

    def get_quote(self, symbol):
        """Get current quote for a symbol"""
        try:
            url = f"{self.api_url}/api/GetEquityInfo"
            params = {"symbol": symbol}
            response = requests.get(url, headers=self.get_headers(), params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                # Find the specific symbol in the response
                for item in result.get('data', []):
                    if item.get('symbol') == symbol:
                        return item
                raise Exception(f"Symbol {symbol} not found in response")
            else:
                raise Exception(result.get('message', 'Failed to get quote'))
        except Exception as e:
            raise Exception(f"Error getting quote: {str(e)}")

    def connect_websocket(self, on_message=None, on_error=None):
        """Connect to websocket for real-time data"""
        def on_ws_message(ws, message):
            if on_message:
                on_message(json.loads(message))

        def on_ws_error(ws, error):
            if on_error:
                on_error(error)
            else:
                print(f"WebSocket error: {error}")

        def on_ws_close(ws, close_status_code, close_msg):
            self.connected = False
            print("WebSocket connection closed")

        def on_ws_open(ws):
            self.connected = True
            print("WebSocket connection established")
            # Send authentication message
            auth_message = {
                "type": "auth",
                "token": self.access_token
            }
            ws.send(json.dumps(auth_message))

        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            self.socket_url,
            on_message=on_ws_message,
            on_error=on_ws_error,
            on_close=on_ws_close,
            on_open=on_ws_open
        )

        # Start WebSocket connection in a separate thread
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

    def subscribe(self, symbol, channels=None):
        """Subscribe to real-time data for a symbol"""
        if not self.connected or not self.ws:
            raise Exception("WebSocket is not connected")

        if channels is None:
            channels = ["trade", "quote", "orderbook"]

        subscribe_message = {
            "type": "subscribe",
            "symbol": symbol,
            "channels": channels
        }
        self.ws.send(json.dumps(subscribe_message))

    def unsubscribe(self, symbol, channels=None):
        """Unsubscribe from real-time data for a symbol"""
        if not self.connected or not self.ws:
            raise Exception("WebSocket is not connected")

        if channels is None:
            channels = ["trade", "quote", "orderbook"]

        unsubscribe_message = {
            "type": "unsubscribe",
            "symbol": symbol,
            "channels": channels
        }
        self.ws.send(json.dumps(unsubscribe_message))

    def close_websocket(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close()
            self.connected = False

    def place_order(self, symbol, side, order_type, price, quantity):
        """Place a new order"""
        try:
            url = f"{self.api_url}/api/SendOrder"
            headers = self.get_headers()

            data = {
                "symbol": symbol,
                "side": side.upper(),
                "type": order_type.upper(),
                "price": float(price) if price else 0,
                "quantity": float(quantity)
            }

            print(f"Sending order request: {data}")
            print(f"Using headers: {headers}")
            response = requests.post(url, headers=headers, json=data)
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")
            
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return result
            else:
                raise Exception(result.get('message', 'Order placement failed'))
        except Exception as e:
            raise Exception(f"Order placement error: {str(e)}")
