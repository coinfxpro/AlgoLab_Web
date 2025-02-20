# Algolab Trading Dashboard

Algolab.com.tr API'sini kullanarak geliştirilmiş bir web trading uygulaması.

## Özellikler

- Kullanıcı girişi ve SMS doğrulama
- Canlı borsa verilerini görüntüleme
- Mum grafiği (Candlestick chart)
- Hacim grafiği
- Portföy görüntüleme
- Alım/Satım işlemleri
- Emir takibi

## Kurulum

1. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

## Kullanım

1. Uygulamayı başlatın:
```bash
python3 app.py
```

2. Tarayıcınızda http://127.0.0.1:5000 adresine gidin (veya localhost:5000)

Not: Eğer 5000 portu kullanımdaysa, `app.py` dosyasında port numarasını değiştirebilirsiniz:
```python
if __name__ == '__main__':
    app.run(debug=True, port=5000)  # Port numarasını değiştirin
```

### Port Kullanım Sorunu ve Çözümü

Eğer "Port 5000 is in use by another program" hatası alırsanız, aşağıdaki adımları izleyebilirsiniz:

1. Portu kullanan işlemi bulun:
```bash
lsof -i :5000
```

2. İşlemi sonlandırın (PID, yukarıdaki komuttan alınan işlem ID'sidir):
```bash
kill -9 <PID>
```

3. Veya tek komutla:
```bash
kill -9 $(lsof -t -i:5000)
```

4. Uygulamayı yeniden başlatın:
```bash
python3 app.py
```

3. Giriş ekranında:
   - API Anahtarı: Algolab'den aldığınız API anahtarı (API-XXXXX formatında)
   - TC Kimlik No / Kullanıcı Adı: Denizbank kullanıcı adınız
   - Şifre: Denizbank internet bankacılığı şifreniz

4. SMS doğrulama kodunu girin

## Sunucuya Deploy Etme

1. Heroku:
```bash
git push heroku main
```

2. DigitalOcean, AWS veya başka bir sunucuda:
```bash
gunicorn app:app
```

## Webhook Kullanımı

### TradingView Webhook Entegrasyonu

Uygulama, TradingView'den gelen sinyalleri otomatik olarak emirlere dönüştürebilen bir webhook endpoint'i içerir.

#### Webhook Endpoint Bilgileri

- **URL**: `http://your-server/webhook/tradingview`
- **Method**: `POST`
- **Headers**:
  - `Content-Type: application/json`
  - `X-Tradingview-Webhook-Signature: <HMAC-SHA256 signature>`

#### Request Body Formatı

```json
{
    "symbol": "GARAN",
    "side": "AL",        // "AL" veya "SAT"
    "quantity": "100",   // Lot miktarı
    "price": "20.50",    // Emir fiyatı
    "orderType": "Limit", // Opsiyonel, varsayılan: "Limit"
    "validity": "GUN"     // Opsiyonel, varsayılan: "GUN"
}
```

#### Webhook Güvenliği

1. Webhook güvenliği için HMAC-SHA256 imzalama kullanılmaktadır
2. `WEBHOOK_SECRET` environment variable'ı ile secret key belirleyebilirsiniz:
   ```bash
   export WEBHOOK_SECRET=your-secret-key
   ```
3. TradingView'de alert oluştururken webhook URL'sine ek olarak bu secret key ile imzalanmış bir header eklemeniz gerekir

#### TradingView'de Alert Oluşturma

1. TradingView'de bir indikatör veya strateji oluşturun
2. Alerts sekmesine gidin
3. "Create Alert" butonuna tıklayın
4. "Webhook URL" alanına webhook endpoint'inizi girin
5. "Message" alanına yukarıdaki JSON formatında bir mesaj girin
6. Alert'i kaydedin

#### Webhook Emirlerini İzleme

Webhook üzerinden gönderilen emirleri ve durumlarını `/webhook/orders` sayfasından takip edebilirsiniz. Bu sayfada:

- Emir tarih ve saati
- İşlem yapılan sembol
- İşlem yönü (AL/SAT)
- Miktar ve fiyat bilgileri
- Emir durumu
- Emir ID
- Sinyal kaynağı

bilgilerini görebilirsiniz. Sayfa her 30 saniyede bir otomatik olarak güncellenir.

#### Test Etme

Webhook'u test etmek için cURL kullanabilirsiniz:

```bash
# HMAC-SHA256 imzası oluştur
SIGNATURE=$(echo -n '{"symbol":"GARAN","side":"AL","quantity":"100","price":"20.50"}' | openssl dgst -sha256 -hmac "your-secret-key" -hex | cut -d' ' -f2)

# Webhook'u test et
curl -X POST http://localhost:5000/webhook/tradingview \
  -H "Content-Type: application/json" \
  -H "X-Tradingview-Webhook-Signature: $SIGNATURE" \
  -d '{"symbol":"GARAN","side":"AL","quantity":"100","price":"20.50"}'
```

## Lisans

MIT
