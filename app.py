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
                        total_stock = float(position.get('totalstock', 0))
                        cost = float(position.get('cost', 0))
                        unit_price = float(position.get('unitprice', 0))
                        total_amount = float(position.get('tlamaount', 0))
                        profit = float(position.get('profit', 0))
                        
                        # Kar/zarar yüzdesi hesapla
                        total_cost = cost * total_stock
                        kar_zarar_yuzde = (profit / total_cost * 100) if total_cost > 0 else 0
                        
                        portfolio.append({
                            'symbol': code,
                            'lot': total_stock,
                            'alis_maliyeti': cost,
                            'guncel_fiyat': unit_price,
                            'toplam_maliyet': total_cost,
                            'toplam_deger': total_amount,
                            'kar_zarar': profit,
                            'kar_zarar_yuzde': kar_zarar_yuzde
                        })
                except Exception as e:
                    print(f"Error processing position: {str(e)}")
                    continue
        
        # Emir geçmişi
        print("Getting order history...")
        orders = {
            'bekleyen': [],
            'gerceklesen': [],
            'iptal': []
        }
        
        try:
            order_history = api_instance.GetEquityOrderHistory(id="", subAccount="")
            print(f"Order history received: {order_history}")
            
            if order_history and isinstance(order_history, list):
                for order in order_history:
                    if isinstance(order, dict):
                        status = str(order.get('status', '')).lower()
                        if status == 'bekleyen':
                            orders['bekleyen'].append(order)
                        elif status == 'gerçekleşen':
                            orders['gerceklesen'].append(order)
                        elif status == 'iptal':
                            orders['iptal'].append(order)
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

@app.route('/islem')
@login_required
def trading():
    try:
        # Bekleyen emirleri al
        orders = api_instance.GetEquityOrderHistory(id="", subAccount="")
        if isinstance(orders, str):
            orders = []
        elif isinstance(orders, dict):
            orders = [orders]
            
        # Sembol listesini al
        symbols = api_instance.GetEquityInfo("")
        if isinstance(symbols, str):
            symbols = []
        elif isinstance(symbols, dict):
            symbols = [symbols]
            
        return render_template('trading.html', orders=orders, symbols=symbols)
    except Exception as e:
        print(f"Trading page error: {str(e)}")
        flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

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

@app.route('/api/send_order', methods=['POST'])
@login_required
def send_order():
    try:
        data = request.get_json()
        print(f"Received order data: {data}")
        
        # Verileri al ve doğrula
        symbol = data.get('symbol', '').upper()
        direction = data.get('direction', '')  # 'Buy' veya 'Sell'
        price_type = data.get('priceType', '')  # 'limit' veya 'piyasa'
        price = data.get('price', '')
        quantity = data.get('quantity', '')
        
        print(f"Parsed order data: symbol={symbol}, direction={direction}, price_type={price_type}, price={price}, quantity={quantity}")
        
        if not all([symbol, direction, price_type, quantity]):
            missing = []
            if not symbol: missing.append('symbol')
            if not direction: missing.append('direction')
            if not price_type: missing.append('priceType')
            if not quantity: missing.append('quantity')
            if price_type == 'limit' and not price: missing.append('price')
            error_msg = f'Eksik alanlar: {", ".join(missing)}'
            print(f"Validation error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg})
        
        # Piyasa emri için fiyat 0 olacak
        if price_type == 'piyasa':
            price = '0'
        
        # API'ye emir gönder
        print(f"Sending order to API: symbol={symbol}, direction={direction}, price_type={price_type}, price={price}, quantity={quantity}")
        result = api_instance.SendOrder(
            symbol=symbol,
            direction=direction,
            pricetype=price_type,
            price=price,
            lot=quantity,
            sms=True,
            email=False,
            sub_account=""
        )
        
        print(f"API response: {result}")
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        error_msg = str(e)
        print(f"Send order error: {error_msg}")
        return jsonify({'success': False, 'error': error_msg})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
