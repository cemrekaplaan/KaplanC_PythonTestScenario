import base64
from io import BytesIO
import pandas as pd
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from flask_migrate import Migrate
import openpyxl
from sqlalchemy.orm import class_mapper


app = Flask(__name__)
db = SQLAlchemy()
migrate = Migrate(app, db)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Cemre.2001@127.0.0.1/task_api'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key' 
db.init_app(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
migrate = Migrate(app, db)

# User Class'ı 
class User(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# Customer Class'ı
class Customer(db.Model):
 
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    surname = db.Column(db.String(255))
    gsm = db.Column(db.String(20), unique=True)
    gender = db.Column(db.String(10))
    birthday = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# Token Class'ı 
class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(500), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# Purchase Class'ı 
class Purchase(db.Model):
   
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    purchase_date = db.Column(db.DateTime, nullable=False)
    listing_price = db.Column(db.Float, nullable=False)
    sale_price = db.Column(db.Float, nullable=False)
    discount_percentage = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

with app.app_context():
    db.create_all()

# Manuel olarak db'de yaptım: 
""" @app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
   
    # 400 - Bad Request 
    if not username or not password:
        return jsonify({'success': False, 'unsuccess_reason': 'Username, password are required!'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = User(username=username, password=hashed_password)
    
    db.session.add(new_user)
    db.session.commit()

    # 201 - Created
    return jsonify({'success': True, 'message': 'User registered successfully!'}), 201 """

@app.route('/login', methods=['POST'])
async def login():
    data = request.json

    username = data.get('username')
    password = data.get('password')

    # 400 - Bad Request
    if not username or not password:
        return jsonify({'success': False, 'unsuccess_reason': 'Username and password are required!'}), 400

    user = User.query.filter_by(username=username).first()

    if user and bcrypt.check_password_hash(user.password, password):

        # Token oluşturmak için: 
        expires_at = datetime.utcnow() + timedelta(minutes=15)
        access_token = create_access_token(identity=user.id, expires_delta=timedelta(minutes=15))

        # Token'ı Tokens tablosuna kaydetmek için: 
        new_token = Token(user_id=user.id, token=access_token, expires_at=expires_at)
        db.session.add(new_token)
        db.session.commit()

        # 200 - OK , 401 - Invalid, Unautorized 
        return jsonify({'success': True, 'user_id': user.id, 'access_token': access_token}), 200
    else:
        return jsonify({'success': False, 'unsuccess_reason': 'Invalid username or password.'}), 401

@app.route('/customer', methods=['POST'])
@jwt_required()
async def create_customer():
    data = request.json
    
    name = data.get('name')
    surname = data.get('surname')
    gsm = data.get('gsm')
    gender = data.get('gender')
    birthday = data.get('birthday')

    # 400 - Bad Request
    if not name or not surname or not gsm:
        return jsonify({'success': False, 'unsuccess_reason': 'Name, Surname, and Gsm are required!'}), 400

    # Gsm numarasına ait müşteriyi kontrol etmek için: 
    existing_customer = Customer.query.get(gsm)
    existing_customer = Customer.query.filter_by(gsm=gsm).first()

    # 400 - Bad Request
    if existing_customer:
        return jsonify({'success': False, 'unsuccess_reason': 'Customer with the given Gsm are already exist!'}), 400

    new_customer = Customer(name=name, surname=surname, gsm=gsm, gender=gender, birthday=birthday)
    db.session.add(new_customer)
    db.session.commit()

    # 201 - Created
    return jsonify({'success': True, 'customer_id': new_customer.id}), 201


@app.route('/purchase', methods=['POST'])
@jwt_required()
async def create_purchase():
    data = request.json

    customer_id = data.get('customer_id')
    purchase_date = data.get('purchase_date')
    listing_price = data.get('listing_price')
    sale_price = data.get('sale_price')
    discount_percentage = data.get('discount_percentage')

    # Parametreleri kontrol etmek için: 
    if not customer_id or not purchase_date or not listing_price or not sale_price:
        return jsonify({'success': False, 'unsuccess_reason': 'CustomerId, PurchaseDate, ListingPrice, and SalePrice are required!'}), 400

    # Alışverişi gerçekleştiren müşteriyi kontrol etmek için: 
    customer = Customer.query.get(customer_id)

    if not customer:
        return jsonify({'success': False, 'unsuccess_reason': 'Customer with the given CustomerId doesnt exist!'}), 400

    # Alışveriş tarihini datetime objesine çevirmek için: 
    purchase_date_str = purchase_date
    try:
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'success': False, 'unsuccess_reason': 'Invalid format for PurchaseDate! Use %Y-%m-%d format.'}), 400

    # Gelen verileri uygun tiplere dönüştürmek için:
    try:
        listing_price = float(listing_price)
        sale_price = float(sale_price)
        discount_percentage = float(discount_percentage)
    except ValueError:
        return jsonify({'success': False, 'unsuccess_reason': 'Invalid numeric value for prices or discount!'}), 400

    # Önceden yapılmış alışveriş kontrolünü sağlamak için: 
    current_date = datetime.utcnow()
    if purchase_date > current_date:
        return jsonify({'success': False, 'unsuccess_reason': 'PurchaseDate cannot be in the future!'}), 400
    
    # İndirim oranını kontrol etmek için: 
    if discount_percentage < 0.0 or discount_percentage > 100.0:
        return jsonify({'success': False, 'unsuccess_reason': 'DiscountPercentage must be between 0.0 and 100.0!'}), 400
    discounted_sale_price = sale_price * (1 - discount_percentage / 100)

    new_purchase = Purchase(customer_id=customer_id, purchase_date=purchase_date,
                            listing_price=listing_price, sale_price=discounted_sale_price, discount_percentage=discount_percentage)
    db.session.add(new_purchase)
    db.session.commit()

    # 201 - Created
    return jsonify({'success': True, 'purchase_id': new_purchase.id}), 201

def serialize(model):
    columns = [column.key for column in class_mapper(model.__class__).columns]
    return {column: getattr(model, column) for column in columns}

@app.route('/export_purchase/<int:customer_id>', methods=['GET'])
def export_purchase(customer_id):
    purchases = Purchase.query.filter_by(customer_id=customer_id).all()
    purchases_dict_list = [serialize(purchase) for purchase in purchases]

    return jsonify({'success': True, 'purchases': purchases_dict_list}), 200

# Protected endpoint: 
@app.route('/protected_endpoint', methods=['GET'])
@jwt_required()
def protected_endpoint():
    current_user_id = get_jwt_identity()
   
    return jsonify({'success': True, 'user_id': current_user_id}), 200


@app.route('/purchase_summary', methods=['GET'])
@jwt_required()
async def purchase_summary():

    # Gerekli parametreler(get methodu ile):
    beginning_date_str = request.args.get('beginning_date')
    ending_date_str = request.args.get('ending_date')

    # Parametreleri kontrol etmek için: 
    if not beginning_date_str or not ending_date_str:
        return jsonify({'success': False, 'unsuccess_reason': 'BeginningDate and EndingDate are required!'}), 400

    # Tarihleri datetime objelerine çevirmek için(strptime methodu ile): 
    try:
        beginning_date = datetime.strptime(beginning_date_str, '%Y-%m-%d')
        ending_date = datetime.strptime(ending_date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'success': False, 'unsuccess_reason': 'Invalid value for BeginningDate or EndingDate!'}), 400

    # Alışveriş bilgilerini filtrelemek için: 
    purchases = Purchase.query.filter(Purchase.purchase_date.between(beginning_date, ending_date)).all()

    # Analiz için gerekli parametreleri hesaplamak:
    total_purchase_count = len(purchases)
    unique_customer_count = len(set(purchase.customer_id for purchase in purchases))
    total_revenue = sum(purchase.sale_price for purchase in purchases)
    total_discount_amount = sum(purchase.listing_price - purchase.sale_price for purchase in purchases)

    customer_info = {customer.id: {'birthday': customer.birthday, 'gender': customer.gender} for customer in Customer.query.filter(Customer.id.in_([purchase.customer_id for purchase in purchases])).all()}

    # Excel dokümanı oluşturmak için: 
    df = pd.DataFrame([
    {
        'Customer ID': purchase.customer_id,
        'Customer Birtdate': customer_info[purchase.customer_id]['birthday'].strftime('%Y-%m-%d') if purchase.customer_id in customer_info else '',
        'Customer Gender': customer_info[purchase.customer_id]['gender'] if purchase.customer_id in customer_info else '',
        'Purchase Date': purchase.purchase_date.strftime('%Y-%m-%d %H:%M:%S'),
        'Purchase Listing Price': purchase.listing_price,
        'Purchase Sale Price': purchase.sale_price,
        'Purchase Discount Amount': purchase.listing_price - purchase.sale_price,
        'Purchase Discount Percentage': (purchase.listing_price - purchase.sale_price) / purchase.listing_price * 100
    } for purchase in purchases
])

    # Satırları alışveriş tarihine göre sıralamak için(sort_values methodu): 
    df.sort_values(by='Purchase Date', ascending=False, inplace=True)

    # Excel dokümanını Base64'e çevirmek için: 
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    excel_base64 = base64.b64encode(excel_buffer.read()).decode('utf-8')
    decoded_excel = base64.b64decode(excel_base64)

    # Excel dosyasına kaydetmek için: 
    with open('saved_excel.xlsx', 'wb') as file:
        file.write(decoded_excel)

    return jsonify({
        'success': True,
        'total_purchase_count': total_purchase_count,
        'unique_customer_count': unique_customer_count,
        'total_revenue': total_revenue,
        'total_discount_amount': total_discount_amount,
        'excel_document': excel_base64
    }), 200

@app.route('/')
async def home():
    return jsonify({'message': 'Welcome to the Task API!'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
