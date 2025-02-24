import threading
import time
from datetime import datetime, timedelta
from algolab_api import AlgolabAPI

class SessionManager:
    def __init__(self):
        self._sessions = {}  # {user_id: (api_instance, last_refresh_time)}
        self._lock = threading.Lock()
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._running = False
    
    def start(self):
        self._running = True
        self._refresh_thread.start()
    
    def add_session(self, user_id, api_instance):
        with self._lock:
            self._sessions[user_id] = (api_instance, datetime.now())
    
    def get_session(self, user_id):
        with self._lock:
            if user_id in self._sessions:
                return self._sessions[user_id][0]
        return None
    
    def _refresh_loop(self):
        while self._running:
            try:
                self._refresh_all_sessions()
            except Exception as e:
                print(f"Error in refresh loop: {e}")
            time.sleep(300)  # 5 dakika bekle
    
    def _refresh_all_sessions(self):
        with self._lock:
            current_time = datetime.now()
            for user_id, (api, last_refresh) in list(self._sessions.items()):
                if current_time - last_refresh > timedelta(minutes=8):
                    try:
                        # Token yenileme işlemi
                        api.refresh_token()
                        self._sessions[user_id] = (api, current_time)
                        print(f"Session refreshed for user {user_id}")
                    except Exception as e:
                        print(f"Failed to refresh session for user {user_id}: {e}")
                        # Başarısız olursa session'ı kaldır
                        self._sessions.pop(user_id, None)

session_manager = SessionManager()
