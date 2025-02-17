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

2. Tarayıcınızda http://127.0.0.1:5001 adresine gidin

Not: Eğer 5001 portu kullanımdaysa, `app.py` dosyasında port numarasını değiştirebilirsiniz:
```python
if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Port numarasını değiştirin
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

## Lisans

MIT
