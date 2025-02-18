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
        
        if portfolio_data is None:
            print("Portfolio data is None")
        elif isinstance(portfolio_data, str):
            print(f"Portfolio data is string: {portfolio_data}")
        elif isinstance(portfolio_data, dict):
            print(f"Portfolio data is dict with keys: {portfolio_data.keys()}")
        elif isinstance(portfolio_data, list):
            print(f"Portfolio data is list with {len(portfolio_data)} items")
            if portfolio_data:
                print(f"First item keys: {portfolio_data[0].keys() if isinstance(portfolio_data[0], dict) else 'Not a dict'}")
        else:
            print(f"Portfolio data is of type: {type(portfolio_data)}")
        
        # Portföy verisini düzenle
        portfolio = []
        if portfolio_data:  # None kontrolü
            # String kontrolü
            if isinstance(portfolio_data, str):
                print(f"Portfolio data is string: {portfolio_data}")
                portfolio_data = []
            # Liste kontrolü
            elif isinstance(portfolio_data, dict):
                portfolio_data = [portfolio_data]
            elif not isinstance(portfolio_data, list):
                print(f"Unexpected portfolio data type: {type(portfolio_data)}")
                portfolio_data = []
            
            # Her pozisyon için veriyi düzenle
            for position in portfolio_data:
                try:
                    if isinstance(position, dict):
                        print(f"Processing position: {position}")
                        # Pozisyon verilerini güvenli bir şekilde al
                        symbol = position.get('Symbol', '')
                        quantity = float(position.get('Quantity', 0))
                        cost = float(position.get('AveragePrice', 0))
                        last_price = float(position.get('LastPrice', 0))
                        
                        # Hesaplamalar
                        total_cost = cost * quantity
                        total_value = last_price * quantity
                        kar_zarar = total_value - total_cost
                        kar_zarar_yuzde = (kar_zarar / total_cost * 100) if total_cost > 0 else 0
                        
                        portfolio.append({
                            'symbol': symbol,
                            'quantity': quantity,
                            'cost': cost,
                            'last_price': last_price,
                            'total_cost': total_cost,
                            'total_value': total_value,
                            'kar_zarar': kar_zarar,
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
            
            if order_history:
                if isinstance(order_history, str):
                    print(f"Order history is string: {order_history}")
                    order_history = []
                elif isinstance(order_history, dict):
                    order_history = [order_history]
                
                if isinstance(order_history, list):
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
            
            if trans_data:
                if isinstance(trans_data, str):
                    print(f"Transaction data is string: {trans_data}")
                    trans_data = []
                elif isinstance(trans_data, dict):
                    trans_data = [trans_data]
                
                if isinstance(trans_data, list):
                    transactions = trans_data
        except Exception as e:
            print(f"Son işlemler alınamadı: {str(e)}")
        
        # Sembol listesi (sadece portföydeki semboller için fiyat bilgisi al)
        portfolio_symbols = {pos['symbol'] for pos in portfolio if pos.get('symbol')}
        symbol_details = []
        
        print("Getting symbol details...")
        for symbol in portfolio_symbols:
            try:
                details = api_instance.GetEquityInfo(symbol)
                print(f"Symbol details for {symbol}: {details}")
                
                if details:
                    if isinstance(details, str):
                        print(f"Symbol details is string for {symbol}: {details}")
                        continue
                    symbol_details.append(details[0] if isinstance(details, list) else details)
            except Exception as e:
                print(f"Sembol bilgisi alınamadı ({symbol}): {str(e)}")
        
        return render_template('dashboard.html', 
                             portfolio=portfolio,
                             symbols=symbol_details,
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
        direction = data.get('direction', '')  # "Buy" veya "Sell"
        price_type = data.get('priceType', '')  # "limit" veya "piyasa"
        price = data.get('price', '')  # Piyasa emirleri için boş string
        quantity = data.get('quantity', '')

        # Normalize numeric formats: replace comma with dot if any
        if price:
            price = price.replace(',', '.').strip()
        if quantity:
            quantity = str(quantity).strip()

        print(f"Parsed order data: symbol={symbol}, direction={direction}, price_type={price_type}, price={price}, quantity={quantity}")

        # Validasyon
        if not all([symbol, direction in ['Buy', 'Sell'], price_type in ['limit', 'piyasa'], quantity]):
            missing = []
            if not symbol: missing.append('symbol')
            if direction not in ['Buy', 'Sell']: missing.append('direction')
            if price_type not in ['limit', 'piyasa']: missing.append('priceType')
            if not quantity: missing.append('quantity')
            if price_type == 'limit' and not price: missing.append('price')

            error_msg = f'Geçersiz veya eksik alanlar: {", ".join(missing)}'
            print(f"Validation error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg})

        # API'ye emir gönder
        try:
            print(f"Sending order to API: symbol={symbol}, direction={direction}, price_type={price_type}, price={price}, quantity={quantity}")
            
            # Parametrelerin sırası örnek koddaki gibi olmalı
            result = api_instance.SendOrder(
                symbol=symbol, 
                direction=direction, 
                pricetype=price_type, 
                price=price, 
                lot=quantity, 
                sms=False, 
                email=False, 
                subAccount=""
            )
            
            print(f"API response: {result}")
            
            if isinstance(result, dict):
                if result.get('success'):
                    content = result.get('content', '')
                    return jsonify({'success': True, 'data': content})
                else:
                    error_msg = result.get('message', 'API yanıtı başarısız')
                    return jsonify({'success': False, 'error': error_msg})
            else:
                return jsonify({'success': False, 'error': 'API yanıtı geçersiz format'})
                
        except Exception as e:
            error_msg = f"API çağrısı sırasında hata: {str(e)}"
            print(error_msg)
            return jsonify({'success': False, 'error': error_msg})
            
    except Exception as e:
        error_msg = f"İstek işlenirken hata: {str(e)}"
        print(error_msg)
        return jsonify({'success': False, 'error': error_msg})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
