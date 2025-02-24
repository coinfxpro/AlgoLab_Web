from rq import Worker, Queue, Connection
import redis

# Redis bağlantısı
redis_conn = redis.Redis()

# Worker fonksiyonu
def process_order(order_data):
    print(f"Processing order: {order_data}")
    # Burada emir işleme kodları yer alacak

# Worker'ı başlatma
if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker([Queue('orders')])
        worker.work()
