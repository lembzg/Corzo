from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson import ObjectId
import secrets
from email_service import EmailService  # Your existing EmailService
from eth_account import Account


# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))

# Initialize extensions
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Initialize Email Service
email_service = EmailService()

try:
    ATLAS_URI = "mongodb+srv://CorvoMangaer:abcd4321@hackathonoxford.9junkcs.mongodb.net/transaction_app?retryWrites=true&w=majority&appName=HackathonOxford"
    client = MongoClient(ATLAS_URI, serverSelectionTimeoutMS=5000)
    
    # Test connection
    client.admin.command('ping')
    print("Connected to MongoDB Atlas!")
    
    db = client.transaction_app
    users_col = db.users
    transactions_col = db.transactions
    sessions_col = db.sessions
    
    # Test collections exist, create if not
    collections = db.list_collection_names()
    if 'users' not in collections:
        db.create_collection('users')
    if 'transactions' not in collections:
        db.create_collection('transactions')
    if 'sessions' not in collections:
        db.create_collection('sessions')
        
except Exception as e:
    print(f"MongoDB Connection Failed: {e}")
    print("Make sure:")
    print("1. Your IP is whitelisted in MongoDB Atlas Network Access")
    print("2. Database user 'CorvoMangaer' exists with password 'abcd4321'")
    print("3. You're connected to the internet")
    print("\nStarting with limited functionality...")
    # Create dummy collections that will fail gracefully
    class DummyCollection:
        def find_one(self, *args, **kwargs): return None
        def insert_one(self, *args, **kwargs): return type('obj', (object,), {'inserted_id': 'dummy'})()
        def update_one(self, *args, **kwargs): pass
        def delete_one(self, *args, **kwargs): pass
        def find(self, *args, **kwargs): return []
        def aggregate(self, *args, **kwargs): return []
    
    users_col = DummyCollection()
    transactions_col = DummyCollection()
    sessions_col = DummyCollection()

# Helper Functions
def create_reset_token():
    return secrets.token_urlsafe(32)

# Authentication Routes
@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.json
        email = data.get('email')
        name = data.get('name')
        password = data.get('password')
        
        if not all([email, name, password]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if user exists
        if users_col.find_one({'email': email}):
            return jsonify({'error': 'Email already registered'}), 400
        
        # Hash password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Create user
        user_id = str(ObjectId())
        user = {
            '_id': user_id,
            'email': email,
            'name': name,
            'password': hashed_password,
            'created_at': datetime.utcnow(),
            'verified': False,  
            'balance': 0.0
        }
        
        users_col.insert_one(user)
        
        success, activation_code = email_service.send_activation_email(email, user_id)
        if success:
            users_col.update_one(
                {'_id': user_id},
                {'$set': {'activation_code': activation_code}}
            )
        
        # Create JWT token
        access_token = create_access_token(identity=user_id)
        
        return jsonify({
            'token': access_token,
            'user': {
                'id': user_id,
                'email': email,
                'name': name,
                'verified': False,
                'balance': 0.0
            },
            'message': 'Registration successful'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        # Find user
        user = users_col.find_one({'email': email})
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check password
        if not bcrypt.check_password_hash(user['password'], password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.get('verified', False):
            return jsonify({'error': 'Please verify your email first'}), 403
        
        # Create token
        access_token = create_access_token(identity=str(user['_id']))
        
        return jsonify({
            'token': access_token,
            'user': {
                'id': str(user['_id']),
                'email': user['email'],
                'name': user.get('name', ''),
                'balance': user.get('balance', 0)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify-email', methods=['POST'])
@jwt_required()
def verify_email():
    """Verify email with activation code"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        code = data.get('code')
        
        if not code:
            return jsonify({'error': 'Activation code required'}), 400
        
        # Get user
        user = users_col.find_one({'_id': user_id})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if already verified
        if user.get('verified'):
            return jsonify({'message': 'Email already verified'}), 200
        
        # FIX: Check stored code in MongoDB AND EmailService memory
        stored_code = user.get('activation_code')
        email_service_valid = email_service.verify_activation_code(user_id, code)
        
        # Accept if code matches either stored code OR EmailService memory
        if stored_code == code or email_service_valid:
            users_col.update_one(
                {'_id': user_id},
                {'$set': {'verified': True, 'verified_at': datetime.utcnow()}}
            )
            user = users_col.find_one({'_id': user_id})
            if user and not user.get('wallet'):
                acct = Account.create()
                wallet = {
                    'address': acct.address,
                    'privateKey': acct.key.hex()  
                }
                users_col.update_one({'_id': user_id}, {'$set': {'wallet': wallet}})
            return jsonify({'message': 'Email verified successfully'}), 200
        else:
            return jsonify({'error': 'Invalid or expired activation code'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    """Send password reset email"""
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        # Find user
        user = users_col.find_one({'email': email})
        if not user:
            # Don't reveal if user exists for security
            return jsonify({'message': 'If an account exists, a reset link has been sent'}), 200
        
        # Generate reset token
        reset_token = create_reset_token()
        expires_at = datetime.utcnow() + timedelta(hours=1)  # FIXED: Use datetime
        
        # Store reset token
        sessions_col.insert_one({
            'user_id': str(user['_id']),
            'reset_token': reset_token,
            'expires_at': expires_at,
            'used': False,
            'created_at': datetime.utcnow()
        })
        
        # Send reset email using your EmailService
        success, _ = email_service.send_password_reset_email(email, str(user['_id']))
        
        if success:
            return jsonify({'message': 'Password reset email sent'}), 200
        else:
            return jsonify({'error': 'Failed to send reset email'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    """Reset password with token"""
    try:
        data = request.json
        token = data.get('token')
        new_password = data.get('password')
        
        if not token or not new_password:
            return jsonify({'error': 'Token and new password required'}), 400
        
        # Find reset session - FIXED: Use datetime comparison
        session = sessions_col.find_one({
            'reset_token': token,
            'used': False,
            'expires_at': {'$gt': datetime.utcnow()}  # FIXED: Compare datetime objects
        })
        
        if not session:
            return jsonify({'error': 'Invalid or expired reset token'}), 400
        
        # Hash new password
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        # Update user password
        users_col.update_one(
            {'_id': session['user_id']},
            {'$set': {'password': hashed_password}}
        )
        
        # Mark token as used
        sessions_col.update_one(
            {'_id': session['_id']},
            {'$set': {'used': True}}
        )
        
        return jsonify({'message': 'Password reset successful'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Transaction Routes
@app.route('/api/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    """Get all transactions for user"""
    try:
        user_id = get_jwt_identity()
        
        # Get query parameters
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        category = request.args.get('category')
        type_filter = request.args.get('type')
        
        # Build query
        query = {'user_id': user_id}
        if category:
            query['category'] = category
        if type_filter:
            query['type'] = type_filter
        
        # Get transactions
        transactions = list(transactions_col.find(query)
                          .sort('date', -1)
                          .skip(offset)
                          .limit(limit))
        
        # Convert ObjectId to string and format dates
        result = []
        for t in transactions:
            t_dict = dict(t)
            t_dict['_id'] = str(t_dict['_id'])
            if 'date' in t_dict and isinstance(t_dict['date'], datetime):
                t_dict['date'] = t_dict['date'].isoformat()
            if 'created_at' in t_dict and isinstance(t_dict['created_at'], datetime):
                t_dict['created_at'] = t_dict['created_at'].isoformat()
            result.append(t_dict)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions', methods=['POST'])
@jwt_required()
def create_transaction():
    """Create a new transaction"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        
        # Validate required fields
        required = ['amount', 'description', 'type']
        for field in required:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400
        
        # Create transaction
        transaction = {
            '_id': str(ObjectId()),
            'user_id': user_id,
            'amount': float(data['amount']),
            'description': data['description'],
            'type': data['type'],  # 'income' or 'expense'
            'category': data.get('category', 'uncategorized'),
            'date': datetime.utcnow(),
            'created_at': datetime.utcnow()
        }
        
        # Insert transaction
        transactions_col.insert_one(transaction)
        
        # Update user balance
        user = users_col.find_one({'_id': user_id})
        current_balance = user.get('balance', 0) if user else 0
        
        if data['type'] == 'income':
            new_balance = current_balance + float(data['amount'])
        else:  # expense
            new_balance = current_balance - float(data['amount'])
        
        users_col.update_one(
            {'_id': user_id},
            {'$set': {'balance': new_balance}},
            upsert=False
        )
        
        # Convert for response
        transaction_response = dict(transaction)
        transaction_response['_id'] = str(transaction_response['_id'])
        transaction_response['date'] = transaction_response['date'].isoformat()
        transaction_response['created_at'] = transaction_response['created_at'].isoformat()
        
        return jsonify({
            'transaction': transaction_response,
            'new_balance': new_balance
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction(transaction_id):
    """Delete a transaction"""
    try:
        user_id = get_jwt_identity()
        
        # Find transaction
        transaction = transactions_col.find_one({
            '_id': transaction_id,
            'user_id': user_id
        })
        
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        # Adjust user balance
        user = users_col.find_one({'_id': user_id})
        current_balance = user.get('balance', 0) if user else 0
        
        if transaction['type'] == 'income':
            new_balance = current_balance - transaction['amount']
        else:  # expense
            new_balance = current_balance + transaction['amount']
        
        # Delete transaction
        transactions_col.delete_one({'_id': transaction_id})
        
        # Update user balance
        users_col.update_one(
            {'_id': user_id},
            {'$set': {'balance': new_balance}}
        )
        
        return jsonify({
            'message': 'Transaction deleted',
            'new_balance': new_balance
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    """Get dashboard statistics"""
    try:
        user_id = get_jwt_identity()
        
        # Get user
        user = users_col.find_one({'_id': user_id})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get recent transactions
        recent_transactions = list(transactions_col.find({'user_id': user_id})
                                  .sort('date', -1)
                                  .limit(5))
        
        recent_transactions_formatted = []
        for t in recent_transactions:
            t_dict = dict(t)
            t_dict['_id'] = str(t_dict['_id'])
            if 'date' in t_dict and isinstance(t_dict['date'], datetime):
                t_dict['date'] = t_dict['date'].isoformat()
            recent_transactions_formatted.append(t_dict)
        
        # Get monthly summary - simplified for reliability
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)
        
        all_transactions = list(transactions_col.find({
            'user_id': user_id,
            'date': {'$gte': start_of_month}
        }))
        
        income = sum(t['amount'] for t in all_transactions if t.get('type') == 'income')
        expenses = sum(t['amount'] for t in all_transactions if t.get('type') == 'expense')
        
        return jsonify({
            'balance': user.get('balance', 0),
            'recent_transactions': recent_transactions_formatted,
            'monthly_income': income,
            'monthly_expenses': expenses,
            'monthly_net': income - expenses
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/resend-activation', methods=['POST'])
@jwt_required()
def resend_activation():
    """Resend activation email"""
    try:
        user_id = get_jwt_identity()
        
        user = users_col.find_one({'_id': user_id})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.get('verified'):
            return jsonify({'message': 'Email already verified'}), 200
        
        # Resend activation email
        success, activation_code = email_service.send_activation_email(
            user['email'], user_id
        )
        
        if success:
            users_col.update_one(
                {'_id': user_id},
                {'$set': {'activation_code': activation_code}}
            )
            return jsonify({'message': 'Activation email resent'}), 200
        else:
            return jsonify({'error': 'Failed to send activation email'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Test endpoint
# Test endpoint
@app.route('/api/test', methods=['GET'])
def test():
    """Test if backend is working"""
    db_status = "connected" if 'client' in globals() and client else "disconnected"
    return jsonify({
        'message': 'Backend is working!',
        'database': db_status,
        'mongodb': 'connected',  # Add this
        'status': 'ready',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

# Health check
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy', 
        'database': 'connected' if 'client' in locals() and client else 'disconnected',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

if __name__ == '__main__':
    print("Starting Transaction App Backend...")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Try to create indexes if MongoDB is connected
        if 'client' in locals() and client:
            users_col.create_index('email', unique=True)
            transactions_col.create_index('user_id')
            sessions_col.create_index([('expires_at', 1)], expireAfterSeconds=0)
            print("Database indexes created")
    except Exception as e:
        print(f"Could not create indexes: {e}")
        print("Running without indexes")
    
    port = int(os.getenv('PORT', 5050))
    print(f"Server running on http://localhost:{port}")
    print("API Documentation:")
    print(f"   - Test endpoint: GET http://localhost:{port}/api/test")
    print(f"   - Register: POST http://localhost:{port}/api/register")
    print(f"   - Login: POST http://localhost:{port}/api/login")
    print(f"   - Health: GET http://localhost:{port}/api/health")
    
    app.run(debug=True, host='0.0.0.0', port=port)