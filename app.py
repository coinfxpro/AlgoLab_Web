from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from algolab import API
from config import URL_LOGIN_CONTROL  # URL'yi config'den al
import pandas as pd
import json
from functools import wraps
import plotly
import plotly.graph_objs as go
from datetime import datetime, timedelta
import os
import hmac
import hashlib

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Session için gerekli

# API nesnesi için global değişken
api_instance = None

# Webhook emirlerini saklamak için global liste
webhook_orders = []

# Tüm sembolleri almak için yardımcı fonksiyon
def get_all_symbols():
    try:
        # Önce boş sembol ile çağırarak tüm sembolleri al
        result = api_instance.GetEquityInfo("")
        if isinstance(result, list):
            return [item.get('symbol') for item in result if item.get('symbol')]
        return []
    except Exception as e:
        print(f"Sembol listesi alınamadı: {str(e)}")
        return []

# Login gerektiren sayfalar için decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Bu sayfayı görüntülemek için giriş yapmalısınız.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    global api_instance
    
    if request.method == 'POST':
        api_key = request.form.get('api_key')
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            # API bağlantısı
            api_instance = API(api_key=api_key, username=username, password=password, auto_login=False)
            
            # İlk login işlemi
            if not api_instance.LoginUser():
                raise Exception("Login başarısız")
            
            # Session'a bilgileri kaydet
            session['api_key'] = api_key
            session['username'] = username
            session['password'] = password
            
            # SMS doğrulama sayfasına yönlendir
            return redirect(url_for('verify_sms'))
            
        except Exception as e:
            flash(f'Giriş hatası: {str(e)}', 'error')
            
    return render_template('login.html')

@app.route('/verify_sms', methods=['GET', 'POST'])
def verify_sms():
    global api_instance
    
    if 'api_key' not in session or api_instance is None:
        flash('Oturum süresi doldu, lütfen tekrar giriş yapın.', 'error')
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        sms_code = request.form.get('sms_code')
        try:
            print(f"SMS Kodu alındı: {sms_code}")  # Debug log
            
            # Token ve SMS kodunu şifrele
            token = api_instance.encrypt(api_instance.token)
            sms = api_instance.encrypt(sms_code)
            
            # Login kontrolü için payload hazırla
            payload = {'token': token, 'password': sms}
            
            # Login kontrolü yap
            response = api_instance.post(URL_LOGIN_CONTROL, payload=payload, login=True)
            if not api_instance.error_check(response, "LoginUserControl"):
                raise Exception("SMS doğrulama başarısız")
                
            login_control = response.json()
            if not login_control.get("success"):
                raise Exception(login_control.get("message", "SMS doğrulama başarısız"))
                
            # Hash'i kaydet
            api_instance.hash = login_control["content"]["hash"]
            api_instance.save_settings()
            
            if not api_instance.is_alive:
                raise Exception("Oturum aktif değil")
            
            session['logged_in'] = True
            flash('Başarıyla giriş yaptınız!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            print(f"SMS doğrulama hatası: {str(e)}")  # Debug log
            flash(f'SMS doğrulama hatası: {str(e)}', 'error')
    
    return render_template('verify_sms.html')

@app.route('/logout')
def logout():
    global api_instance
    api_instance = None
    session.clear()
    flash('Çıkış yaptınız.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Debug için API çağrılarını logla
        print("Getting portfolio data...")
        
        # Portföy bilgisi
        portfolio_data = api_instance.GetInstantPosition(sub_account="")
        print(f"Portfolio data received (raw): {portfolio_data}")
        
        # Portföy verisini düzenle
        portfolio = []
        total_cost = 0
        total_value = 0
        
        if portfolio_data and isinstance(portfolio_data, list):
            # Her pozisyon için veriyi düzenle
            for position in portfolio_data:
                try:
                    if isinstance(position, dict):
                        print(f"Processing position: {position}")
                        # Pozisyon verilerini güvenli bir şekilde al
                        code = position.get('code', '')
                        
                        # Sayısal değerleri güvenli bir şekilde dönüştür
                        try:
                            total_stock = float(position.get('totalstock', '0').replace(',', ''))
                            cost = float(position.get('cost', '0').replace(',', ''))
                            unit_price = float(position.get('unitprice', '0').replace(',', ''))
                            total_amount = float(position.get('tlamaount', '0').replace(',', ''))
                            profit = float(position.get('profit', '0').replace(',', ''))
                        except (ValueError, TypeError):
                            print(f"Error converting numeric values for position: {code}")
                            continue
                        
                        # Toplam maliyet ve değer hesapla
                        position_cost = cost * total_stock if total_stock > 0 else 0
                        total_cost += position_cost
                        total_value += total_amount
                        
                        # Kar/zarar yüzdesi hesapla
                        kar_zarar_yuzde = (profit / position_cost * 100) if position_cost > 0 else 0
                        
                        portfolio.append({
                            'symbol': code,
                            'lot': total_stock,
                            'alis_maliyeti': cost,
                            'guncel_fiyat': unit_price,
                            'toplam_maliyet': position_cost,
                            'toplam_deger': total_amount,
                            'kar_zarar': profit,
                            'kar_zarar_yuzde': round(kar_zarar_yuzde, 2)
                        })
                except Exception as e:
                    print(f"Error processing position: {str(e)}")
                    continue
        
        # Portföy özeti
        print("Getting portfolio summary...")
        portfolio_summary = None
        try:
            risk_data = api_instance.RiskSimulation()
            if risk_data and risk_data.get('success'):
                content = risk_data.get('content', [{}])[0]
                portfolio_summary = {
                    't0_nakit': float(content.get('t0', '0')),
                    't1_nakit': float(content.get('t1', '0')),
                    't2_nakit': float(content.get('t2', '0')),
                    't0_hisse': float(content.get('t0equity', '0')),
                    't1_hisse': float(content.get('t1equity', '0')),
                    't2_hisse': float(content.get('t2equity', '0')),
                    't0_toplam': float(content.get('t0overall', '0')),
                    't1_toplam': float(content.get('t1overall', '0')),
                    't2_toplam': float(content.get('t2overall', '0')),
                    't0_ozkaynakoran': float(content.get('t0capitalrate', '0')),
                    't1_ozkaynakoran': float(content.get('t1capitalrate', '0')),
                    't2_ozkaynakoran': float(content.get('t2capitalrate', '0')),
                    'nakit_haric_toplam': float(content.get('netoverall', '0')),
                    'aciga_satis_limit': float(content.get('shortfalllimit', '0')),
                    'kredi_bakiye': float(content.get('credit0', '0'))
                }
        except Exception as e:
            print(f"Error getting portfolio summary: {str(e)}")
        
        return render_template('dashboard.html', 
                             portfolio=portfolio,
                             total_cost=total_cost,
                             total_value=total_value,
                             portfolio_summary=portfolio_summary)
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/trading')
@login_required
def trading():
    try:
        # Emir geçmişini al
        orders = api_instance.GetEquityOrderHistory(id="", subAccount="")
        print(f"Orders response: {orders}")
        
        if orders and isinstance(orders, list):
            # Sadece bekleyen emirleri filtrele
            orders = [order for order in orders if order.get('equityStatusDescription', '').upper() == 'WAITING']
        else:
            orders = []
            
        print(f"Filtered orders: {orders}")
        return render_template('trading.html', orders=orders)
    except Exception as e:
        print(f"Trading page error: {str(e)}")
        flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/send_order', methods=['POST'])
@login_required
def send_order():
    try:
        data = request.get_json()
        print(f"Received order data: {data}")
        
        # Verileri al ve doğrula
        symbol = data.get('symbol', '').upper()
        direction = data.get('direction', '').upper()  # API 'BUY' veya 'SELL' bekliyor
        price_type = data.get('priceType', '').lower()  # API 'limit' veya 'piyasa' bekliyor
        price = str(data.get('price', ''))  # API string bekliyor
        lot = str(data.get('quantity', ''))  # API string bekliyor
        
        print(f"Parsed order data: symbol={symbol}, direction={direction}, price_type={price_type}, price={price}, lot={lot}")
        
        # Gerekli alanları kontrol et
        if not all([symbol, direction, price_type, lot]):
            raise ValueError("Tüm alanlar doldurulmalıdır")
            
        if direction not in ['BUY', 'SELL']:
            raise ValueError("Geçersiz işlem yönü")
            
        if price_type not in ['limit', 'piyasa']:
            raise ValueError("Geçersiz emir tipi")
            
        # Piyasa emri için fiyat 0 olacak
        if price_type == 'piyasa':
            price = '0'
        elif not price:
            raise ValueError("Limit emir için fiyat girilmelidir")
            
        # API'ye gönderilecek payload'ı hazırla
        payload = {
            "symbol": symbol,
            "direction": direction,
            "pricetype": price_type,
            "price": price,
            "lot": lot,
            "sms": False,
            "email": False,
            "subAccount": ""  # Büyük S yerine küçük s
        }
        
        print(f"Sending order with payload: {payload}")
        
        # Emir gönder
        response = api_instance.SendOrder(**payload)
        print(f"Order response: {response}")
        
        if not response or not isinstance(response, dict):
            raise ValueError("Emir gönderilemedi")
            
        if not response.get('success', False):
            raise ValueError(response.get('message', 'Emir gönderilemedi'))
            
        # Başarılı cevabı döndür
        return jsonify({
            'success': True,
            'message': response.get('message', ''),
            'reference': response.get('content', '')
        })
        
    except Exception as e:
        print(f"Error sending order: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/cancel_order', methods=['POST'])
@login_required
def cancel_order():
    try:
        data = request.get_json()
        order_id = data.get('id')
        
        if not order_id:
            raise ValueError("Emir ID'si gerekli")
            
        # API'ye gönderilecek payload
        payload = {
            "id": order_id,
            "subAccount": ""
        }
        
        print(f"Canceling order with payload: {payload}")
        
        # Emri iptal et
        response = api_instance.DeleteOrder(**payload)
        print(f"Cancel order response: {response}")
        
        if not response or not isinstance(response, dict):
            raise ValueError("Emir iptal edilemedi")
            
        if not response.get('success', False):
            raise ValueError(response.get('message', 'Emir iptal edilemedi'))
            
        return jsonify({
            'success': True,
            'message': response.get('message', 'Emir başarıyla iptal edildi')
        })
        
    except Exception as e:
        print(f"Error canceling order: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/market_data')
@login_required
def market_data():
    try:
        # Sembol listesi
        symbols = get_all_symbols()
        
        # Her sembol için detaylı bilgi al
        symbol_details = []
        for symbol in symbols:
            try:
                details = api_instance.GetEquityInfo(symbol)
                if details:
                    symbol_details.append(details[0] if isinstance(details, list) else details)
            except Exception as e:
                print(f"Sembol bilgisi alınamadı ({symbol}): {str(e)}")
        
        return render_template('market_data.html', symbols=symbol_details)
    except Exception as e:
        flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/api/candle_data')
@login_required
def get_candle_data():
    try:
        symbol = request.args.get('symbol')
        period = request.args.get('period', '1d')
        interval = request.args.get('interval', '1m')
        
        if not symbol:
            return jsonify({'success': False, 'error': 'Sembol belirtilmedi'})
        
        data = api_instance.GetCandleData(symbol=symbol, period=period)
        
        if not data:
            return jsonify({'success': False, 'error': 'Veri bulunamadı'})
        
        # Mum grafiği için veriyi hazırla
        candlestick = go.Candlestick(
            x=[d['date'] for d in data],
            open=[d['open'] for d in data],
            high=[d['high'] for d in data],
            low=[d['low'] for d in data],
            close=[d['close'] for d in data]
        )
        
        layout = go.Layout(
            title=f'{symbol} Fiyat Grafiği',
            yaxis_title='Fiyat',
            xaxis_title='Tarih'
        )
        
        fig = go.Figure(data=[candlestick], layout=layout)
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        return jsonify({'success': True, 'chart': graphJSON, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/webhook/orders')
@login_required
def webhook_orders_page():
    return render_template('webhook_orders.html', webhook_orders=webhook_orders)

@app.route('/webhook/orders/data')
@login_required
def webhook_orders_data():
    # Emir durumlarını güncelle
    for order in webhook_orders:
        if order['status'] == 'waiting':
            try:
                # Emir durumunu kontrol et
                order_history = api_instance.GetEquityOrderHistory(id=order['order_id'], subAccount="")
                if order_history and isinstance(order_history, list):
                    for hist_order in order_history:
                        if hist_order.get('id') == order['order_id']:
                            order['status'] = hist_order.get('status', 'waiting')
                            break
            except Exception as e:
                print(f"Error updating order status: {str(e)}")
    
    return jsonify({'success': True, 'orders': webhook_orders})

# Webhook güvenliği için secret key
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'your-secret-key')  # Güvenli bir secret key kullanın

@app.route('/webhook/tradingview', methods=['POST'])
def tradingview_webhook():
    try:
        # Gelen veriyi al
        data = request.get_json()
        
        # Webhook imzasını kontrol et
        signature = request.headers.get('X-Tradingview-Webhook-Signature')
        if not verify_webhook_signature(request.get_data(), signature):
            return jsonify({'error': 'Invalid signature'}), 401
            
        print(f"Received webhook data: {data}")
        
        # Gerekli alanları kontrol et
        required_fields = ['symbol', 'side', 'quantity', 'price']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Emir tipini belirle (AL/SAT)
        side = data['side'].upper()
        if side not in ['AL', 'SAT']:
            return jsonify({'error': 'Invalid side. Must be AL or SAT'}), 400
            
        # Emir payload'ını hazırla
        payload = {
            'symbol': data['symbol'],
            'price': str(data['price']),
            'lot': str(data['quantity']),
            'side': side,
            'subAccount': '',  # Alt hesap belirtilmemişse boş bırak
            'orderType': data.get('orderType', 'Limit'),  # Varsayılan olarak Limit emir
            'validity': data.get('validity', 'GUN'),  # Varsayılan olarak günlük emir
        }
        
        # Emri gönder
        response = api_instance.SendOrder(**payload)
        print(f"Order response: {response}")
        
        if not response or not isinstance(response, dict):
            raise Exception("Invalid response from API")
            
        if not response.get('success', False):
            raise Exception(response.get('message', 'Order failed'))
            
        # Başarılı emri listeye ekle
        order_id = response.get('content', {}).get('id')
        webhook_orders.append({
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': data['symbol'],
            'side': side,
            'quantity': data['quantity'],
            'price': data['price'],
            'status': 'waiting',
            'order_id': order_id,
            'source': 'TradingView'
        })
            
        return jsonify({
            'success': True,
            'message': 'Order placed successfully',
            'order_id': order_id
        })
        
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def verify_webhook_signature(payload, signature):
    """Webhook imzasını doğrula"""
    try:
        if not signature:
            return False
            
        # HMAC-SHA256 ile imzayı hesapla
        expected_signature = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Hesaplanan imza ile gelen imzayı karşılaştır
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        print(f"Signature verification error: {str(e)}")
        return False

@app.route('/daily_transactions')
@login_required
def daily_transactions():
    try:
        # Günlük işlemleri al
        transactions = api_instance.GetTodaysTransactions()
        
        if transactions and transactions.get('success'):
            content = transactions.get('content', [])
            
            # İşlemleri formatla
            formatted_transactions = []
            for transaction in content:
                formatted_transactions.append({
                    'referans': transaction.get('atpref', '-'),
                    'hisse': transaction.get('ticker', '-'),
                    'islem_turu': transaction.get('buysell', '-'),
                    'miktar': transaction.get('ordersize', '0'),
                    'kalan': transaction.get('remainingsize', '0'),
                    'fiyat': transaction.get('price', '0'),
                    'tutar': transaction.get('amount', '0'),
                    'islem_zamani': transaction.get('timetransaction', '-'),
                    'durum': transaction.get('description', '-'),
                    'gerceklesen': transaction.get('fillunit', '0')
                })
            
            return render_template('daily_transactions.html', transactions=formatted_transactions)
            
    except Exception as e:
        flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
