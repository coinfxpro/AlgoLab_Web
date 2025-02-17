from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from algolab import API
import pandas as pd
import json
from functools import wraps
import plotly
import plotly.graph_objs as go
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Session için gerekli

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
    if request.method == 'POST':
        api_key = request.form.get('api_key')
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            # API bağlantısı
            api = API(api_key=api_key, username=username, password=password, auto_login=True)
            
            # Session'a API nesnesini kaydet
            session['api_key'] = api_key
            session['username'] = username
            session['password'] = password
            session['logged_in'] = True
            
            flash('Başarıyla giriş yaptınız!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Giriş hatası: {str(e)}', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Çıkış yaptınız.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # API bağlantısı
        api = API(api_key=session['api_key'], username=session['username'], 
                 password=session['password'], auto_login=True)
        
        # Portföy bilgisi
        portfolio = api.get_instant_position()
        
        # Sembol listesi
        symbols = api.get_equity_info()
        
        return render_template('dashboard.html', 
                             portfolio=portfolio,
                             symbols=symbols)
    except Exception as e:
        flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/market_data')
@login_required
def market_data():
    try:
        api = API(api_key=session['api_key'], username=session['username'], 
                 password=session['password'], auto_login=True)
        
        # Tüm semboller
        symbols = api.get_equity_info()
        
        return render_template('market_data.html', symbols=symbols)
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
        
        api = API(api_key=session['api_key'], username=session['username'], 
                 password=session['password'], auto_login=True)
        
        data = api.get_candle_data(symbol=symbol, period=period, interval=interval)
        
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
        api = API(api_key=session['api_key'], username=session['username'], 
                 password=session['password'], auto_login=True)
        
        # Sembol listesi
        symbols = api.get_equity_info()
        
        # Açık emirler
        orders = api.get_equity_order_history()
        
        return render_template('trading.html', 
                             symbols=symbols,
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
        
        api = API(api_key=session['api_key'], username=session['username'], 
                 password=session['password'], auto_login=True)
        
        result = api.send_order(
            symbol=symbol,
            direction=direction,
            price_type=price_type,
            price=price,
            quantity=quantity
        )
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
