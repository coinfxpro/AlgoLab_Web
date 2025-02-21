# AlgoLab Web Trading Platform

Algolab.com.tr API'sini kullanarak geliştirilmiş web tabanlı trading platformu.

## Özellikler

- Kullanıcı girişi ve SMS doğrulama
- Canlı borsa verileri ve grafikler
- Portföy yönetimi
- Alım/Satım işlemleri
- Emir takibi
- TradingView webhook entegrasyonu

## Kurulum

1. Repo'yu klonlayın:
```bash
git clone https://github.com/coinfxpro/AlgoLab_Web.git
cd AlgoLab_Web
```

2. Virtual environment oluşturun (opsiyonel ama önerilen):
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
.\venv\Scripts\activate  # Windows
```

3. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

4. SQLite veritabanını oluşturun:
```bash
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

## Kullanım

1. Uygulamayı başlatın:
```bash
python app.py
```

2. Tarayıcınızda `http://127.0.0.1:5001` adresine gidin

3. Giriş yapın:
   - API Anahtarı: Algolab'den aldığınız API anahtarı
   - Kullanıcı Adı: Denizbank kullanıcı adınız
   - Şifre: Denizbank şifreniz

4. SMS doğrulama kodunu girin

## TradingView Webhook Entegrasyonu

### Webhook Ayarları

1. Uygulamada "Webhook Ayarları" sayfasına gidin
2. Size özel webhook secret key'inizi görüntüleyin veya yenisini oluşturun
3. Bu secret key'i TradingView alert'lerinizde kullanacaksınız

### TradingView Alert Formatı

TradingView'de alert oluştururken aşağıdaki JSON formatını kullanın:

```json
{
    "secret": "your_webhook_secret_key",
    "symbol": "SASA",
    "side": "BUY",        // BUY veya SELL
    "type": "MARKET",     // MARKET veya LIMIT
    "price": "3.55",      // LIMIT emirler için fiyat
    "quantity": "1"       // Lot miktarı
}
```

### Emir Tipleri

1. **Market (Piyasa) Emirleri**
   ```json
   {
       "secret": "your_secret",
       "symbol": "SASA",
       "side": "BUY",
       "type": "MARKET",
       "quantity": "1"
   }
   ```
   - Market emirlerinde `price` belirtmeyin
   - Emir anında piyasa fiyatından gerçekleşir

2. **Limit Emirleri**
   ```json
   {
       "secret": "your_secret",
       "symbol": "SASA",
       "side": "BUY",
       "type": "LIMIT",
       "price": "3.55",
       "quantity": "1"
   }
   ```
   - Limit emirlerde mutlaka `price` belirtin
   - Emir belirtilen fiyattan gerçekleşir

### TradingView'de Alert Oluşturma

1. TradingView'de bir indikatör veya strateji seçin
2. "Alerts" sekmesine gidin
3. "Create Alert" butonuna tıklayın
4. "Webhook URL" alanına:
   ```
   http://your-server:5001/webhook/tradingview
   ```
5. "Message" alanına yukarıdaki JSON formatında mesajınızı yazın
6. "Save" ile alert'i kaydedin

### Test Etme

Webhook'u test etmek için cURL kullanabilirsiniz:

```bash
# Market Emri Testi
curl -X POST http://localhost:5001/webhook/tradingview \
  -H "Content-Type: application/json" \
  -d '{"secret":"your_secret","symbol":"SASA","side":"BUY","type":"MARKET","quantity":"1"}'

# Limit Emri Testi
curl -X POST http://localhost:5001/webhook/tradingview \
  -H "Content-Type: application/json" \
  -d '{"secret":"your_secret","symbol":"SASA","side":"BUY","type":"LIMIT","price":"3.55","quantity":"1"}'
```

## Notlar

- Market emirleri anında piyasa fiyatından gerçekleşir
- Limit emirler belirtilen fiyata gelene kadar bekler
- Her kullanıcının kendine özel webhook secret key'i vardır
- Webhook üzerinden gelen emirler "Webhook Emirleri" sayfasında görüntülenir

## Güvenlik

- Her webhook isteği için secret key kontrolü yapılır
- Secret key'ler veritabanında güvenli şekilde saklanır
- Her kullanıcı sadece kendi emirlerini görüntüleyebilir

## Sorun Giderme

**Port 5001 kullanımda hatası:**
```bash
# Portu kullanan işlemi bulun
lsof -i :5001

# İşlemi sonlandırın
kill -9 <PID>

# Veya tek komutla
kill -9 $(lsof -t -i:5001)
```

## Lisans

MIT
