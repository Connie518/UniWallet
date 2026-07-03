import json
import pytest
from unittest.mock import patch, MagicMock

# --- Test Register API ---
@pytest.mark.parametrize("payload, excepted_message", [
    ({
        "username": "",
        "password": "password123",
        "confirm_password": "password123"
    }, "帳號與密碼不能為空"),
    ({
        "username": "testuser",
        "password": "",
        "confirm_password": ""
    }, "帳號與密碼不能為空"),
    ({
        "username": "",
        "password": "",
        "confirm_password": ""
    }, "帳號與密碼不能為空")
])

def test_register_empty_fields(client, payload, excepted_message):
    response = client.post('/api/register', data=json.dumps(payload), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['message'] == excepted_message
    assert response.status_code == 400

def test_register_duplicate_username(client):
    payload = {
        "username": "testuser",
        "password": "password123",
        "confirm_password": "password123"
    }
    client.post('/api/register', data=json.dumps(payload), content_type='application/json')
    response = client.post('/api/register', data=json.dumps(payload), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['message'] == '此帳號已被註冊，請換一個試試！'
    assert response.status_code == 400

def test_register_password_mismatch(client):
    payload = {
        "username": "testuser",
        "password": "password123",
        "confirm_password": "password456"
    }
    response = client.post('/api/register', data=json.dumps(payload), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['message'] == '兩次輸入的密碼不一致，請重新檢查！'
    assert response.status_code == 400

def test_register_success(client):
    payload = {
        "username": "testuser",
        "password": "password123",
        "confirm_password": "password123"
    }
    response = client.post('/api/register', data=json.dumps(payload), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['message'] == '註冊成功！歡迎使用，請登入！'
    assert response.status_code == 201

# --- Test Login API ---
def test_login_user_not_found(client):
    payload = {
        "username": "testuser",
        "password": "password123"
    }
    response = client.post('/api/login', data=json.dumps(payload), content_type='application/json')
    data = response.get_json()    
    assert data['status'] == 'error'
    assert data['message'] == '此帳號不存在，請先註冊！'
    assert response.status_code == 404

def test_login_incorrect_password(client):
    register_payload = {
        "username": "testuser",
        "password": "password123",
        "confirm_password": "password123"
    }
    client.post('/api/register', data=json.dumps(register_payload), content_type='application/json')
    login_payload = {
        "username": "testuser",
        "password": "password456"
    }
    response = client.post('/api/login', data=json.dumps(login_payload), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['message'] == '帳號或密碼錯誤！'
    assert response.status_code == 401

def test_login_success(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    response = client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['message'] == '登入成功'
    assert data['user']['username'] == 'testuser'
    assert response.status_code == 200

# --- Test Logout API ---
def test_logout(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    response = client.post('/api/logout')
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['message'] == '已成功登出'
    assert response.status_code == 200
    subsequent_response = client.get('/api/wallet/data')
    assert subsequent_response.status_code == 401

# --- Test Get Current User API ---
def test_get_current_user_unauthenticated(client):
    response = client.get('/api/user/me')
    data = response.get_json()
    assert data['is_authenticated'] == False
    assert response.status_code == 200

def test_get_current_user_authenticated(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    response = client.get('/api/user/me')
    data = response.get_json()
    assert data['is_authenticated'] == True
    assert data['user']['username'] == 'testuser'
    assert response.status_code == 200

# --- Test Wallet Data API ---
def test_get_wallet_data_new_user(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    response = client.get('/api/wallet/data')
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['username'] == 'testuser'
    assert data['records'] == []
    assert data['categories'] == []
    assert data['items'] == []
    assert data['currencies'][0]['name'] == 'TWD'
    assert data['currencies'][0]['rate'] == '1.0'
    assert response.status_code == 200

def test_get_wallet_data_old_user(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    from app import db, User, Record
    from datetime import datetime
    with client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        test_record = Record(
            date=datetime.now(),
            category='飲食',
            item='早餐',
            currency='TWD',
            price=100,
            twd=100,
            user_id=user.id
        )
        db.session.add(test_record)
        db.session.commit()
    response = client.get('/api/wallet/data')
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['username'] == 'testuser'
    assert len(data['records']) == 1
    assert data['records'][0]['date'] == datetime.now().strftime('%Y/%m/%d')
    assert data['records'][0]['category'] == '飲食'
    assert data['records'][0]['item'] == '早餐'
    assert data['records'][0]['currency'] == 'TWD'
    assert data['records'][0]['price'] == 100
    assert data['records'][0]['twd'] == 100
    assert response.status_code == 200

# --- Test Add/Delete Category API ---
def test_add_category_success(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    response = client.post('/api/category', data=json.dumps({"name": "飲食"}), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'id' in data
    assert response.status_code == 201

def test_add_dulicate_category(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    client.post('/api/category', data=json.dumps({"name": "飲食"}), content_type='application/json')
    response = client.post('/api/category', data=json.dumps({"name": "飲食"}), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['message'] == '類別已存在'
    assert response.status_code == 409

def test_add_empty_category(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    response = client.post('/api/category', data=json.dumps({"name": ""}), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['message'] == '請輸入類別'
    assert response.status_code == 400

def test_delete_category(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    from app import db, User, UserCategory, UserItem
    with client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        category = UserCategory(name='飲食', user_id=user.id)
        db.session.add(category)
        db.session.commit()
        item = UserItem(name='早餐', user_id=user.id, category_id=category.id)
        db.session.add(item)
        db.session.commit()
        category_id = category.id
    response = client.delete(f'/api/category/{category_id}')
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['message'] == '類別及其所有品項接刪除'
    assert response.status_code == 200
    with client.application.app_context():
        assert db.session.get(UserCategory, category_id) is None
        item = UserItem.query.filter_by(category_id=category_id).count()
        assert item == 0

# --- Test Add/Delete Item API ---
def test_add_item_success(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    client.post('/api/category', data=json.dumps({"name": "飲食"}), content_type='application/json')
    response = client.post('/api/item', data=json.dumps({"name": "早餐", "category_name": "飲食"}), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['name'] == '早餐'
    assert 'id' in data
    assert response.status_code == 201

def test_add_duplicate_item(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    client.post('/api/category', data=json.dumps({"name": "飲食"}), content_type='application/json')
    client.post('/api/item', data=json.dumps({"name": "早餐", "category_name": "飲食"}), content_type='application/json')
    response = client.post('/api/item', data=json.dumps({"name": "早餐", "category_name": "飲食"}), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['message'] == '品項已存在'
    assert response.status_code == 409

def test_add_item_cat_not_found(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    client.post('/api/category', data=json.dumps({"name": "飲食"}), content_type='application/json')
    response = client.post('/api/item', data=json.dumps({"name": "飛機", "category_name": "交通"}), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['message'] == '該類別不存在'
    assert response.status_code == 404

def test_add_empty_item(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    client.post('/api/category', data=json.dumps({"name": "飲食"}), content_type='application/json')
    response = client.post('/api/item', data=json.dumps({"name": "", "category_name": "飲食"}), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['message'] == '請輸入品項'
    assert response.status_code == 400

def test_delete_item(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    from app import db, User, UserCategory, UserItem
    with client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        category = UserCategory(name='飲食', user_id=user.id)
        db.session.add(category)
        db.session.commit()
        item = UserItem(name='早餐', user_id=user.id, category_id=category.id)
        db.session.add(item)
        db.session.commit()
        item_id = item.id
    response = client.delete(f'/api/item/{item_id}')
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['message'] == '品相已刪除'
    assert response.status_code == 200
    with client.application.app_context():
        assert db.session.get(UserItem, item_id) is None

# --- Test Add/Delete Currency API ---
def test_add_currency_manual_success(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    response = client.post('/api/currency', data=json.dumps({"name": "krw", "rate": "0.021"}), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['name'] == 'KRW'
    assert data['rate'] == 0.021
    assert response.status_code == 201

def test_add_empty_currency_manual(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    response = client.post('/api/currency', data=json.dumps({"name": "", "rate": ""}), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['message'] == '請輸入幣別'
    assert response.status_code == 400

def test_add_duplicate_currency_manual(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    client.post('/api/currency', data=json.dumps({"name": "krw", "rate": "0.021"}), content_type='application/json')
    response = client.post('/api/currency', data=json.dumps({"name": "krw", "rate": "0.021"}), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['message'] == '幣別已存在'
    assert response.status_code == 409

def test_add_invalid_currency_rate_manual(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    response = client.post('/api/currency', data=json.dumps({"name": "abc", "rate": "2#-"}), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['message'] == '輸入的匯率格式不正確'
    assert response.status_code == 400

@patch('requests.get')
def test_add_currency_auto(mock_get, client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    mock_html = """
    <table class="table_style_1" summary="無障礙公開外幣即時匯率查詢">
        <tbody>
            <tr>
                <td class="td">美元(USD)</td>
                <td class="td">31.8500</td>
                <td class="td">32.0500</td>
            </tr>
        </tbody>
    </table>
    """
    mock_response = MagicMock()
    mock_response.text = mock_html
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    res_success = client.post('/api/currency', data=json.dumps({"name": "usd", "rate": ""}), content_type='application/json')
    assert res_success.get_json()['status'] == 'success'
    assert res_success.get_json()['name'] == 'USD'
    assert res_success.get_json()['rate'] == 'Realtime'
    assert res_success.status_code == 201
    res_fall = client.post('/api/currency', data=json.dumps({"name": "abc", "rate": ""}), content_type='application/json')
    assert res_fall.get_json()['status'] == 'error'
    assert res_fall.get_json()['message'] == '網站上找不到 ABC 的即時匯率，請手動填寫匯率！'
    assert res_fall.status_code == 404

def test_delete_currency(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    from app import db, User, UserCurrency
    with client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        currency = UserCurrency(name="KRW", rate=0.021, user_id=user.id)
        db.session.add(currency)
        db.session.commit()
        currency_id = currency.id
    response = client.delete(f'/api/currency/{currency_id}')
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['message'] == '幣別已刪除'
    assert response.status_code == 200
    with client.application.app_context():
        assert db.session.get(UserCurrency, currency_id) is None

# --- Test Add/Delete Record API ---
def test_add_record_manual_rate(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    client.get('/api/wallet/data')
    payload = {
        "category": "飲食",
        "item": "早餐",
        "currency_name": "TWD",
        "price": 100
    }
    response = client.post('/api/record', data=json.dumps(payload), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['record']['item'] == '早餐'
    assert data['record']['price'] == 100
    assert data['record']['twd'] == 100
    assert response.status_code == 201

def test_add_record_empty_price(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    client.get('/api/wallet/data')
    payload = {
        "category": "飲食",
        "item": "早餐",
        "currency_name": "TWD"
    }
    response = client.post('/api/record', data=json.dumps(payload), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['message'] == '請填寫完整的消費紀錄資訊'
    assert response.status_code == 400

def test_add_record_invalid_price(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    client.get('/api/wallet/data')
    payload = {
        "category": "飲食",
        "item": "早餐",
        "currency_name": "TWD",
        "price": "2#-"
    }
    response = client.post('/api/record', data=json.dumps(payload), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'error'
    assert data['message'] == '金額格式錯誤'
    assert response.status_code == 400

@patch('requests.get')
def test_add_record_realtime_rate(mock_get, client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    from app import db, User, UserCurrency
    with client.application.app_context():
        user = User.query.filter_by(username="testuser").first()
        usd_cur = UserCurrency(name="USD", rate="Realtime", user_id=user.id)
        db.session.add(usd_cur)
        db.session.commit()
    mock_html = """
    <table class="table_style_1" summary="無障礙公開外幣即時匯率查詢">
        <tbody>
            <tr>
                <td class="td">美元(USD)</td>
                <td class="td">31.8500</td>
                <td class="td">32.0500</td>
            </tr>
        </tbody>
    </table>
    """
    mock_response = MagicMock()
    mock_response.text = mock_html
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    payload = {
        "category": "購物",
        "item": "衣服",
        "currency_name": "USD",
        "price": 100
    }
    response = client.post('/api/record', data=json.dumps(payload), content_type='application/json')
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['record']['twd'] == 3205
    assert response.status_code == 201

def test_delete_record_success(client):
    user_info = {
        "username": "testuser",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user_info, "confirm_password": user_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user_info), content_type='application/json')
    from datetime import datetime
    from app import db, User, Record
    with client.application.app_context():
        user = User.query.filter_by(username='testuser').first()
        record = Record(date=datetime.now(), category='娛樂', item='電影', currency='TWD', price=300, twd=300, user_id=user.id)
        db.session.add(record)
        db.session.commit()
        record_id = record.id
    response = client.delete(f'/api/record/{record_id}')
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['message'] == '紀錄已刪除'
    assert response.status_code == 200
    with client.application.app_context():
        assert db.session.get(Record, record_id) is None

def test_delete_other_user_record_denied(client):
    user1_info = {
        "username": "testuser1",
        "password": "password123"
    }
    client.post('/api/register', data=json.dumps({**user1_info, "confirm_password": user1_info["password"]}), content_type='application/json')
    from datetime import datetime
    from app import db, User, Record
    with client.application.app_context():
        user1 = User.query.filter_by(username='testuser1').first()
        record1 = Record(date=datetime.now(), category='飲食', item='晚餐', currency='TWD', price=150, twd=150, user_id=user1.id)
        db.session.add(record1)
        db.session.commit()
        record1_id = record1.id
    user2_info = {
        "username": "testuser2",
        "password": "password456"
    }
    client.post('/api/register', data=json.dumps({**user2_info, "confirm_password": user2_info["password"]}), content_type='application/json')
    client.post('/api/login', data=json.dumps(user2_info), content_type='application/json')
    response = client.delete(f'/api/record/{record1_id}')
    assert response.get_json()['status'] == 'error'
    assert response.get_json()['message'] == '無權限刪除'
    assert response.status_code == 404
    with client.application.app_context():
        assert db.session.get(Record, record1_id) is not None
    