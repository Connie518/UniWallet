import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from models import db, User, UserCategory, UserItem, UserCurrency, Record
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

frontend_origins = os.environ.get('FRONTEND_URL').split(',')
CORS(app, resources={r"/api/*": {"origins": frontend_origins}}, supports_credentials=True)

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

DEFAULT_RATES = {'TWD': 1.00}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 未登入時的處理（覆蓋原本的預設跳轉，改回傳 JSON）
@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'status': 'error', 'message': '請先登入'}), 401

# --- 初始化幣別 ---
def init_user_default_currencies(user_id):
    exists = UserCurrency.query.filter_by(user_id=user_id).first()
    if not exists:        
        for name, rate in DEFAULT_RATES.items():
            new_cur = UserCurrency(name=name, rate=rate, user_id=user_id)
            db.session.add(new_cur)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"初始化幣別失敗: {e}")

# ==================== 認證 API ====================

# --- 註冊 ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
                        
    if not username or not password:
        return jsonify({'status': 'error', 'message': '帳號與密碼不能為空'}), 400

    user_exists = User.query.filter_by(username=username).first()
    if user_exists:
        return jsonify({'status': 'error', 'message': '此帳號已被註冊，請換一個試試！'}), 400
        
    if password != confirm_password:
        return jsonify({'status': 'error', 'message': '兩次輸入的密碼不一致，請重新檢查！'}), 400

    hashed_password = generate_password_hash(password, method='scrypt')
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'status': 'success', 'message': '註冊成功！歡迎使用，請登入！'}), 201

# --- 登入 ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username', '')
    password = data.get('password', '')
    
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({'status': 'error', 'message': '此帳號不存在，請先註冊！'}), 404
    elif check_password_hash(user.password, password):
        login_user(user)
        return jsonify({
            'status': 'success', 
            'message': '登入成功',
            'user': {'id': user.id, 'username': user.username}
        }), 200
    else:
        return jsonify({'status': 'error', 'message': '帳號或密碼錯誤！'}), 401

# --- 登出 ---
@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'status': 'success', 'message': '已成功登出'}), 200

# --- 獲取當前使用者資訊 ---
@app.route('/api/user/me', methods=['GET'])
def get_current_user():
    if current_user.is_authenticated:
        return jsonify({
            'is_authenticated': True,
            'user': {'id': current_user.id, 'username': current_user.username}
        }), 200
    return jsonify({'is_authenticated': False}), 200

# ==================== 資料 API ====================

# --- 獲取所有初始化/選單/錢包資料 ---
@app.route('/api/wallet/data', methods=['GET'])
@login_required
def get_wallet_data():
    user_records = Record.query.filter_by(user_id=current_user.id).all()
    user_categories = UserCategory.query.filter_by(user_id=current_user.id).all()
    user_items = UserItem.query.filter_by(user_id=current_user.id).all()
    user_currencies = UserCurrency.query.filter_by(user_id=current_user.id).all()
    if not user_currencies:
        init_user_default_currencies(current_user.id)
        user_currencies = UserCurrency.query.filter_by(user_id=current_user.id).all()

    return jsonify({
        'status': 'success',
        'username': current_user.username,
        'records': [r.to_dict() for r in user_records],
        'categories': [{'id': c.id, 'name': c.name} for c in user_categories],
        'items': [{'id': i.id, 'name': i.name, 'category_id': i.category_id} for i in user_items],
        'currencies': [{'id': c.id, 'name': c.name, 'rate': c.rate} for c in user_currencies]
    }), 200

# --- 新增類別 ---
@app.route('/api/category', methods=['POST'])
@login_required
def add_category():
    data = request.get_json() or {}
    name = data.get('name', '').strip()

    if not name:
        return jsonify({'status': 'error', 'message': '請輸入類別'}), 400
    
    exists = UserCategory.query.filter_by(name=name, user_id=current_user.id).first()
    if exists:
        return jsonify({'status': 'error', 'message': '類別已存在'}), 409
    
    new_cat = UserCategory(name=name, user_id=current_user.id)
    db.session.add(new_cat)
    db.session.commit()
    return jsonify({'status': 'success', 'id': new_cat.id}), 201    

# # --- 刪除類別 ---
@app.route('/api/category/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    cat = UserCategory.query.filter_by(id=category_id, user_id=current_user.id).first()
    if not cat:
        return jsonify({'status': 'error', 'message': '找不到該類別'}), 404
    
    try:
        UserItem.query.filter_by(category_id=cat.id).delete()
        db.session.delete(cat)
        db.session.commit()
        return jsonify({'status': 'success', 'message': '類別及其所有品項接刪除'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': '刪除失敗'}), 500

# --- 新增品項 ---
@app.route('/api/item', methods=['POST'])
@login_required
def add_item():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    category_name = data.get('category_name', '')

    if not name or not category_name:
        return jsonify({'status': 'error', 'message': '請輸入品項'}), 400
    
    cat = UserCategory.query.filter_by(name=category_name, user_id=current_user.id).first()
    if not cat:
        return jsonify({'status': 'error', 'message': '該類別不存在'}), 404
    
    exists = UserItem.query.filter_by(name=name, category_id=cat.id, user_id=current_user.id).first()
    if exists:
        return jsonify({'status': 'error', 'message': '品項已存在'}), 409
    
    new_item = UserItem(name=name, category_id=cat.id, user_id=current_user.id)
    db.session.add(new_item)
    db.session.commit()
    return jsonify({'status': 'success', 'id': new_item.id, 'name':new_item.name}), 201

# # --- 刪除品項 ---
@app.route('/api/item/<int:item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    item = UserItem.query.filter_by(id=item_id, user_id=current_user.id).first()

    if not item:
        return jsonify({'status': 'error', 'message': '該品項不存在'}), 404
    
    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({'status': 'success', 'message': '品相已刪除'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': '刪除失敗'}), 500

# --- 新增幣別 ---
@app.route('/api/currency', methods=['POST'])
@login_required
def add_currency():
    data = request.get_json() or {}
    name = data.get('name', '').strip().upper()
    rate_input = data.get('rate')

    if not name:
        return jsonify({'status': 'error', 'message': '請輸入幣別'}), 400
    
    exists = UserCurrency.query.filter_by(name=name, user_id=current_user.id).first()
    if exists:
        return jsonify({'status': 'error', 'message': '幣別已存在'}), 409
    
    final_rate = None
    if rate_input is not None and str(rate_input).strip() != "":
        try:
            final_rate = float(rate_input)
        except ValueError:
            return jsonify({'status': 'error', 'message': '輸入的匯率格式不正確'}), 400
    else:
        try:
            response = requests.get("https://accessibility.cathaybk.com.tw/exchange-rate-search.aspx", verify=False)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            found = False
            rows = soup.find('table', {'summary': '無障礙公開外幣即時匯率查詢'}).find('tbody').find_all('tr')
            for row in rows:
                tds = row.find_all('td')
                currency_text = tds[0].text.strip()
                if 'Cash' not in currency_text and name in currency_text:
                    final_rate = "Realtime"
                    found = True
                    break
            if not found:
                return jsonify({'status': 'error', 'message': f'網站上找不到 {name} 的即時匯率，請手動填寫匯率！'}), 404
        except Exception:
            return jsonify({'status': 'error', 'message': f'目前無法獲取 {name} 的即時匯率，請確認網路連線或至「編輯選單」手動新增匯率！'}), 500
    
    new_cur = UserCurrency(name=name, rate=final_rate, user_id=current_user.id)
    db.session.add(new_cur)
    db.session.commit()
    return jsonify({'status': 'success', 'id': new_cur.id, 'name': new_cur.name, 'rate': final_rate}), 201

# --- 刪除幣別 ---
@app.route('/api/currency/<int:currency_id>', methods=['DELETE'])
@login_required
def delete_currency(currency_id):
    cur = UserCurrency.query.filter_by(id=currency_id, user_id=current_user.id).first()
    if not cur:
        return jsonify({'status': 'error', 'message': '該幣別不存在'}), 404
    
    try:
        db.session.delete(cur)
        db.session.commit()
        return jsonify({'status': 'success', 'message': '幣別已刪除'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': '刪除失敗'}), 500

# --- 新增消費紀錄 ---
@app.route('/api/record', methods=['POST'])
@login_required
def add_record():
    data = request.get_json() or {}
    category = data.get('category')
    item = data.get('item')
    currency_name = data.get('currency_name')
    price = data.get('price')

    if not all([category, item, currency_name, price]):
        return jsonify({'status': 'error', 'message': '請填寫完整的消費紀錄資訊'}), 400

    try:
        price = float(data.get('price'))
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'message': '金額格式錯誤'}), 400
        
    user_cur = UserCurrency.query.filter_by(name=currency_name, user_id=current_user.id).first()

    if not user_cur:
        return jsonify({'status': 'error', 'message': '找不到對應的幣別匯率設定'}), 404
    currency_rate = user_cur.rate

    if str(currency_rate).strip() != "Realtime" and str(currency_rate).strip() != '':
        try:
            twd = round(price * float(currency_rate), 2)
        except ValueError:
            return jsonify({'status': 'error', 'message': '匯率格式輸入錯誤'}), 400
        
    else:
        try:
            response = requests.get("https://accessibility.cathaybk.com.tw/exchange-rate-search.aspx", verify=False)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            target_td = soup.find('td', string=lambda s: s and currency_name in s and "Cash" not in s)
            sell_rate = float(target_td.parent.find_all('td')[2].text.strip())
            twd = round(price * sell_rate, 2)
        except Exception:
            return jsonify({'status': 'error', 'message': f"目前無法獲取 {currency_name} 的即時匯率，請確認網路連線或至「編輯選單」手動新增匯率！"}), 500
        
    new_record = Record(category=category, item=item, currency=currency_name, price=price, twd=twd, user_id=current_user.id)
    db.session.add(new_record)
    db.session.commit()
    return jsonify({
        'status': 'success',
        'record': {
            'id': new_record.id,
            'category': new_record.category,
            'item': new_record.item,
            'currency': new_record.currency,
            'price': new_record.price,
            'twd': new_record.twd
        }
    }), 201

# --- 刪除消費紀錄 ---
@app.route('/api/record/<int:record_id>', methods=['DELETE'])
@login_required
def delete_record(record_id):
    record = db.session.get(Record, record_id)
    if not record:
        return jsonify({'status': 'error', 'message': '該紀錄不存在'}), 404
    
    if record.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': '無權限刪除'}), 404
    
    db.session.delete(record)
    db.session.commit()
    return jsonify({'status': 'success', 'message': '紀錄已刪除'}), 200
                

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    port_num = int(os.environ.get('PORT', 8000))
    is_debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port_num, debug=is_debug)