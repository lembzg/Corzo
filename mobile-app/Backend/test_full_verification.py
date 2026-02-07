# test_full_verification.py
import requests
import json
import time

BASE_URL = "http://localhost:5050/api"
TEST_EMAIL = "testverify@example.com"

print("Testing Full Email Verification Flow...")

# 1. Register (will send activation email)
print("\n1. Registering user...")
register_data = {
    "email": TEST_EMAIL,
    "name": "Verify Test",
    "password": "test123"
}

resp = requests.post(f"{BASE_URL}/register", json=register_data)
print(f"   Status: {resp.status_code}")
print(f"   Response: {resp.text}")

if resp.status_code == 201:
    data = resp.json()
    token = data.get('token')
    user_id = data.get('user', {}).get('id')
    
    print(f"   User ID: {user_id}")
    print(f"   Token: {token[:20]}...")
    print(f"   Verified: {data.get('user', {}).get('verified')}")  # Should be False
    
    # 2. Try to login (should fail - not verified)
    print("\n2. Trying to login (should fail)...")
    login_data = {
        "email": TEST_EMAIL,
        "password": "test123"
    }
    resp2 = requests.post(f"{BASE_URL}/login", json=login_data)
    print(f"   Status: {resp2.status_code}")
    print(f"   Response: {resp2.text}")
    
    # 3. Check server console for activation code
    print("\n3. Check server terminal for activation code!")
    print("   Look for: 'Password reset email to testverify@example.com: ...'")
    print("   The 6-digit code will be in the email content")
    
    # 4. Manually verify with code (you'll need to get code from console)
    print("\n4. To verify, run:")
    print(f"   curl -X POST http://localhost:5050/api/verify-email \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -H 'Authorization: Bearer {token}' \\")
    print(f"     -d '{{\"code\": \"ACTIVATION_CODE_FROM_CONSOLE\"}}'")
    
    # 5. Test resend activation
    print("\n5. Testing resend activation...")
    resp3 = requests.post(
        f"{BASE_URL}/resend-activation",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"   Status: {resp3.status_code}")
    print(f"   Response: {resp3.text}")
    
else:
    print("Registration failed!")