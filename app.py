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
        # Portföy bilgisi
        portfolio_data = api_instance.GetInstantPosition()
        
        # Portföy verisini düzenle
        portfolio = []
        if isinstance(portfolio_data, (list, dict)):
            if isinstance(portfolio_data, dict):
                portfolio_data = [portfolio_data]
            
            for position in portfolio_data:
                if isinstance(position, dict):
                    # Pozisyon verilerini güvenli bir şekilde al
                    symbol = position.get('symbol', '')
                    quantity = position.get('quantity', 0)
                    cost = position.get('cost', 0)
                    last_price = position.get('last_price', 0)
                    
                    # Kar/zarar hesapla
                    try:
                        kar_zarar = (last_price - cost) * quantity
                    except:
                        kar_zarar = 0
                    
                    portfolio.append({
                        'symbol': symbol,
                        'quantity': quantity,
                        'cost': cost,
                        'last_price': last_price,
                        'kar_zarar': kar_zarar
                    })
        
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
        
        return render_template('dashboard.html', 
                             portfolio=portfolio,
                             symbols=symbol_details)
    except Exception as e:
        flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('login'))

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

@app.route('/trading')
@login_required
def trading():
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
        
        # Açık emirler
        orders = api_instance.GetEquityOrderHistory("")
        
        return render_template('trading.html', 
                             symbols=symbol_details,
                             orders=orders)
    except Exception as e:
        flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/api/send_order', methods=['POST'])
@login_required
def send_order():
    try:
        data = request.json
        symbol = data.get('symbol')
        direction = data.get('direction')  # 'Buy' veya 'Sell'
        price_type = data.get('price_type')  # 'limit' veya 'piyasa'
        price = data.get('price')
        quantity = data.get('quantity')
        
        if not all([symbol, direction, price_type, quantity]):
            return jsonify({'success': False, 'error': 'Eksik parametre'})
        
        result = api_instance.SendOrder(
            symbol=symbol,
            direction=direction,
            pricetype=price_type,
            price=price if price_type == 'limit' else None,
            lot=quantity,
            sms=True,
            email=False,
            subAccount=""
        )
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
