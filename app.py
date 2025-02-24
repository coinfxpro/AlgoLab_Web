from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
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
from models import db, UserCredentials
import threading
import time
from session_manager import session_manager
from algolab_api import AlgolabAPI

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///algolab.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

app.secret_key = os.urandom(24)  # Session için gerekli

# API nesnesi için global değişken
api_instance = None
last_login_time = None

# Oturum yenileme fonksiyonu
def refresh_session():
    global api_instance
    while True:
        time.sleep(600)  # 10 dakika bekle
        if api_instance:
            try:
                api_instance.RefreshSession()  # Oturum yenileme metodunu çağır
                app.logger.info("Oturum başarıyla yenilendi.")
            except Exception as e:
                app.logger.error(f"Oturum yenileme hatası: {str(e)}")

# Oturum yenileme thread'ini başlat
session_refresh_thread = threading.Thread(target=refresh_session, daemon=True)
session_refresh_thread.start()

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

# User sınıfını güncelle
class User(UserMixin):
    def __init__(self, username, apikey=None, password=None, token=None, hash=None):
        self.id = username
        self.username = username
        self.apikey = apikey
        self.password = password
        self.token = token
        self.hash = hash

# Login manager'ı ayarla
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    if user_id in session:
        return User(
            username=user_id,
            apikey=session.get('apikey'),
            password=session.get('password'),
            token=session.get('token'),
            hash=session.get('hash')
        )
    return None

@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    global api_instance, last_login_time
    
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
            
            # Login zamanını kaydet
            last_login_time = datetime.now()
            
            # Session'a bilgileri kaydet
            session['api_key'] = api_key
            session['username'] = username
            session['password'] = password
            session['logged_in'] = True
            
            # SMS doğrulama sayfasına yönlendir
            return redirect(url_for('verify_sms'))
            
        except Exception as e:
            flash(f'Giriş hatası: {str(e)}', 'error')
            
    return render_template('login.html')

@app.route('/verify_sms', methods=['GET', 'POST'])
def verify_sms():
    global api_instance
    
    if request.method == 'POST':
        sms_code = request.form.get('sms_code')
        try:
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
            
            # Hash'i veritabanına kaydet
            user = UserCredentials.query.filter_by(username=session.get('username')).first()
            if user:
                user.hash_value = api_instance.hash
                db.session.commit()
            
            # Kullanıcı nesnesini oluştur ve giriş yap
            user = User(
                username=session.get('username'),
                apikey=session.get('api_key'),
                password=session.get('password'),
                token=api_instance.token,
                hash=api_instance.hash
            )
            login_user(user)
            
            # Session'a bilgileri kaydet
            session['token'] = api_instance.token
            session['hash'] = api_instance.hash
            session['logged_in'] = True
            
            flash('Başarıyla giriş yaptınız!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
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
        print("\n=== Dashboard Request Started ===")
        print("Getting portfolio data...")
        
        # Portföy bilgisi
        portfolio_data = api_instance.GetInstantPosition(sub_account="")
        print(f"Portfolio data received: {len(portfolio_data) if portfolio_data else 0} items")
        
        # Portföy özeti
        print("\nGetting portfolio summary...")
        portfolio_summary = None
        try:
            risk_data = api_instance.RiskSimulation()
            print(f"\nRisk data: {risk_data}")
            
            if risk_data and risk_data.get('success'):
                content = risk_data.get('content', {})
                print(f"\nContent type: {type(content)}")
                print(f"Content: {content}")
                
                if isinstance(content, dict):
                    def safe_float(value):
                        try:
                            if value and value != '-' and not isinstance(value, str):
                                return float(value)
                            if isinstance(value, str) and value.replace('.', '').isdigit():
                                return float(value)
                            return 0.0
                        except:
                            return 0.0
                    
                    portfolio_summary = {
                        't0_nakit': safe_float(content.get('t0')),
                        't1_nakit': safe_float(content.get('t1')),
                        't2_nakit': safe_float(content.get('t2')),
                        't0_hisse': safe_float(content.get('t0equity')),
                        't1_hisse': safe_float(content.get('t1equity')),
                        't2_hisse': safe_float(content.get('t2equity')),
                        't0_toplam': safe_float(content.get('t0overall')),
                        't1_toplam': safe_float(content.get('t1overall')),
                        't2_toplam': safe_float(content.get('t2overall')),
                        't0_ozkaynakoran': safe_float(content.get('t0capitalrate')),
                        't1_ozkaynakoran': safe_float(content.get('t1capitalrate')),
                        't2_ozkaynakoran': safe_float(content.get('t2capitalrate')),
                        'nakit_haric_toplam': safe_float(content.get('netoverall')),
                        'aciga_satis_limit': safe_float(content.get('shortfalllimit')),
                        'kredi_bakiye': safe_float(content.get('credit0'))
                    }
                    print("\nPortfolio summary created:", bool(portfolio_summary))
                    print("Portfolio summary values:")
                    for key, value in portfolio_summary.items():
                        print(f"  {key}: {value}")
                else:
                    print("\nRisk data content is not a dictionary")
        except Exception as e:
            print(f"\nError getting portfolio summary: {str(e)}")
            print("Error details:", e.__class__.__name__)
            import traceback
            print(traceback.format_exc())
        
        print(f"\nFinal portfolio_summary value: {portfolio_summary}")
        
        # Portföy verisini düzenle
        portfolio = []
        total_cost = 0
        total_value = 0
        total_profit_loss = 0
        total_try_amount = 0  # TRY bakiyesi için yeni değişken
        
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
                        
                        # TRY bakiyesi için özel durum
                        if code == 'TRY':
                            total_try_amount = abs(total_amount)  # TRY bakiyesini kaydet
                            profit = 0  # TRY için kar/zarar gösterme
                            continue  # TRY'yi portföy hesaplamalarına dahil etme
                        
                        # Toplam maliyet ve değer hesapla
                        position_cost = cost * total_stock if total_stock > 0 else 0
                        total_cost += position_cost
                        total_value += total_amount
                        total_profit_loss += profit
                        
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
            
            # TRY'yi en son ekle
            if total_try_amount > 0:
                portfolio.append({
                    'symbol': 'TRY',
                    'lot': 0,
                    'alis_maliyeti': 0,
                    'guncel_fiyat': 1,
                    'toplam_maliyet': 0,
                    'toplam_deger': total_try_amount,
                    'kar_zarar': 0,
                    'kar_zarar_yuzde': 0
                })
        
        return render_template('dashboard.html', 
                             portfolio=portfolio,
                             total_cost=total_cost,
                             total_value=total_value,
                             total_profit_loss=total_profit_loss,
                             total_try_amount=total_try_amount,
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

@app.route('/webhook-settings', methods=['GET', 'POST'])
@login_required
def webhook_settings():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        webhook_secret = request.form.get('webhook_secret')
        if webhook_secret:
            # Kullanıcı bilgilerini güncelle veya oluştur
            user_creds = UserCredentials.query.filter_by(username=session.get('username')).first()
            if not user_creds:
                user_creds = UserCredentials(
                    username=session.get('username'),
                    api_key=session.get('api_key'),
                    password=session.get('password'),
                    webhook_secret=webhook_secret
                )
                db.session.add(user_creds)
            else:
                user_creds.webhook_secret = webhook_secret
                user_creds.api_key = session.get('api_key')
                user_creds.password = session.get('password')
            
            db.session.commit()
            flash('Webhook secret key başarıyla kaydedildi!', 'success')
            return redirect(url_for('webhook_settings'))
    
    # Mevcut webhook secret'ı getir
    user_creds = UserCredentials.query.filter_by(username=session.get('username')).first()
    current_secret = user_creds.webhook_secret if user_creds else None
    
    return render_template('webhook_settings.html', current_secret=current_secret)

@app.route('/webhook/tradingview', methods=['POST'])
def tradingview_webhook():
    try:
        data = request.json
        print(f"Received webhook data: {data}")
        
        api_key = data.get('secret')
        if not api_key:
            print("Error: No API key provided")
            return jsonify({'error': 'No API key provided'}), 400
            
        if not api_key.startswith('API-'):
            print(f"Error: Invalid API key format: {api_key}")
            return jsonify({'error': 'Invalid API key format'}), 400

        # Session kontrolü ve otomatik login
        session = session_manager.get_session(api_key)
        if not session:
            try:
                print(f"No session found for {api_key}, creating new session...")
                # API key ile otomatik login
                algolab_api = AlgolabAPI(api_key)
                token_info = algolab_api.get_token()
                if token_info:
                    session_manager.create_session(
                        api_key,
                        token_info['token'],
                        token_info['refresh_token']
                    )
                    print(f"New session created for {api_key}")
                    session = session_manager.get_session(api_key)
            except Exception as e:
                print(f"Auto-login failed: {str(e)}")
                return jsonify({'error': f'Auto-login failed: {str(e)}'}), 401

        # Emir işleme
        try:
            algolab_api = AlgolabAPI(api_key)
            algolab_api.access_token = session['token']
            
            result = algolab_api.place_order(
                symbol=data.get('symbol'),
                side=data.get('side'),
                order_type=data.get('type'),
                price=data.get('price'),
                quantity=data.get('quantity')
            )
            print(f"Order placed successfully: {result}")
            return jsonify(result), 200
        except Exception as e:
            print(f"Order placement failed: {str(e)}")
            return jsonify({'error': f'Order placement failed: {str(e)}'}), 500

    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 400

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
    # Worker'ı başlatma komutu
    os.system('python worker.py &')
    app.run(debug=True, host='0.0.0.0', port=5001)

