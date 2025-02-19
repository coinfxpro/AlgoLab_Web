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

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Session için gerekli

# API nesnesi için global değişken
api_instance = None

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
                        
                        # Kar/zarar yüzdesi hesapla
                        total_cost = cost * total_stock if total_stock > 0 else 0
                        kar_zarar_yuzde = (profit / total_cost * 100) if total_cost > 0 else 0
                        
                        portfolio.append({
                            'symbol': code,
                            'lot': total_stock,
                            'alis_maliyeti': cost,
                            'guncel_fiyat': unit_price,
                            'toplam_maliyet': total_cost,
                            'toplam_deger': total_amount,
                            'kar_zarar': profit,
                            'kar_zarar_yuzde': round(kar_zarar_yuzde, 2)
                        })
                except Exception as e:
                    print(f"Error processing position: {str(e)}")
                    continue
        
        # Emir geçmişi ve son işlemler
        print("Getting order history and recent transactions...")
        orders = {
            'bekleyen': [],
            'gerceklesen': [],
            'iptal': [],
            'son_islemler': []
        }
        
        try:
            # Emir geçmişi al
            order_history = api_instance.GetEquityOrderHistory(id="", subAccount="")
            print(f"Order history received: {order_history}")
            
            if order_history and isinstance(order_history, list):
                for order in order_history:
                    if isinstance(order, dict):
                        # Tarih bilgisini düzenle
                        try:
                            order['date'] = datetime.strptime(order.get('date', ''), '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M:%S')
                        except:
                            order['date'] = order.get('date', '')
                            
                        status = str(order.get('status', '')).lower()
                        if status == 'bekleyen':
                            orders['bekleyen'].append(order)
                        elif status in ['gerçekleşen', 'gerceklesen']:
                            orders['gerceklesen'].append(order)
                        elif status == 'iptal':
                            orders['iptal'].append(order)
            
            # Günlük işlemleri al
            today_transactions = api_instance.TodaysTransaction(subAccount="")
            print(f"Today's transactions received: {today_transactions}")
            
            if today_transactions and isinstance(today_transactions, list):
                for transaction in today_transactions:
                    if isinstance(transaction, dict):
                        # API'den gelen veriyi template'in beklediği formata dönüştür
                        formatted_transaction = {
                            'id': transaction.get('atpref', '-'),
                            'symbol': transaction.get('ticker', '-'),
                            'direction': transaction.get('buysell', '-'),
                            'price': transaction.get('price', '0'),
                            'quantity': transaction.get('ordersize', '0'),
                            'status': transaction.get('description', '-'),
                            'date': transaction.get('timetransaction', '-')
                        }
                        orders['son_islemler'].append(formatted_transaction)
            
            # Son işlemleri tarihe göre sırala (en yeniden en eskiye)
            orders['son_islemler'] = sorted(
                orders['son_islemler'],
                key=lambda x: datetime.strptime(x.get('date', '1900-01-01 00:00:00'), '%d.%m.%Y %H:%M:%S' if '.' in x.get('date', '') else '%Y-%m-%d %H:%M:%S'),
                reverse=True
            )
            
        except Exception as e:
            print(f"Emir geçmişi alınamadı: {str(e)}")
        
        # Son işlemler
        print("Getting today's transactions...")
        transactions = []
        try:
            trans_data = api_instance.GetTodaysTransaction(sub_account="")
            print(f"Transaction data received: {trans_data}")
            
            if trans_data and isinstance(trans_data, list):
                transactions = trans_data
        except Exception as e:
            print(f"Son işlemler alınamadı: {str(e)}")
        
        return render_template('dashboard.html', 
                             portfolio=portfolio,
                             orders=orders,
                             transactions=transactions)
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

if __name__ == '__main__':
    app.run(debug=True)
