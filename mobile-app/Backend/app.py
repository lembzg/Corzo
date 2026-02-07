# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import os
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import secrets
from email_service import EmailService  # Your existing EmailService

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
app.config['MONGO_URI'] = os.getenv('MONGO_URI', 'mongodb://localhost:27017')

# Initialize extensions
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Initialize Email Service
email_service = EmailService()

# MongoDB Connection
client = MongoClient(app.config['MONGO_URI'])
db = client.transaction_app

# Collections
users_col = db.users
transactions_col = db.transactions
sessions_col = db.sessions  # For password reset tokens

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
        
        # Send activation email
        success, activation_code = email_service.send_activation_email(email, user_id)
        if success:
            # Store activation code in database
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
                'verified': False
            },
            'message': 'Registration successful. Check your email for activation code.'
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
        
        # Find user
        user = users_col.find_one({'email': email})
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check password
        if not bcrypt.check_password_hash(user['password'], password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check if verified
        if not user.get('verified', True):  # Change to False for strict verification
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
        
        # Get user
        user = users_col.find_one({'_id': user_id})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if already verified
        if user.get('verified'):
            return jsonify({'message': 'Email already verified'}), 200
        
        # Verify code (using your EmailService)
        if email_service.verify_activation_code(user_id, code):
            users_col.update_one(
                {'_id': user_id},
                {'$set': {'verified': True, 'verified_at': datetime.utcnow()}}
            )
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
        
        # Find user
        user = users_col.find_one({'email': email})
        if not user:
            # Don't reveal if user exists for security
            return jsonify({'message': 'If an account exists, a reset link has been sent'}), 200
        
        # Generate reset token
        reset_token = create_reset_token()
        expires_at = datetime.utcnow().timestamp() + 3600  # 1 hour
        
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
        
        # Find reset session
        session = sessions_col.find_one({
            'reset_token': token,
            'used': False,
            'expires_at': {'$gt': datetime.utcnow().timestamp()}
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
        
        # Convert ObjectId to string
        for t in transactions:
            t['_id'] = str(t['_id'])
            t['date'] = t['date'].isoformat() if isinstance(t['date'], datetime) else t['date']
        
        return jsonify(transactions), 200
        
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
        current_balance = user.get('balance', 0)
        
        if data['type'] == 'income':
            new_balance = current_balance + float(data['amount'])
        else:  # expense
            new_balance = current_balance - float(data['amount'])
        
        users_col.update_one(
            {'_id': user_id},
            {'$set': {'balance': new_balance}}
        )
        
        # Convert for response
        transaction['_id'] = str(transaction['_id'])
        transaction['date'] = transaction['date'].isoformat()
        
        return jsonify({
            'transaction': transaction,
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
        current_balance = user.get('balance', 0)
        
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
        
        # Get recent transactions
        recent_transactions = list(transactions_col.find({'user_id': user_id})
                                  .sort('date', -1)
                                  .limit(5))
        
        for t in recent_transactions:
            t['_id'] = str(t['_id'])
            t['date'] = t['date'].isoformat() if isinstance(t['date'], datetime) else t['date']
        
        # Get monthly summary
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)
        
        pipeline = [
            {'$match': {
                'user_id': user_id,
                'date': {'$gte': start_of_month}
            }},
            {'$group': {
                '_id': '$type',
                'total': {'$sum': '$amount'}
            }}
        ]
        
        monthly_summary = list(transactions_col.aggregate(pipeline))
        
        income = next((item['total'] for item in monthly_summary if item['_id'] == 'income'), 0)
        expenses = next((item['total'] for item in monthly_summary if item['_id'] == 'expense'), 0)
        
        return jsonify({
            'balance': user.get('balance', 0),
            'recent_transactions': recent_transactions,
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

# Health check
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200

if __name__ == '__main__':
    # Create indexes
    users_col.create_index('email', unique=True)
    transactions_col.create_index('user_id')
    transactions_col.create_index([('user_id', 1), ('date', -1)])
    sessions_col.create_index('reset_token', unique=True)
    sessions_col.create_index('expires_at', expireAfterSeconds=3600)
    
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)