<<<<<<< HEAD
// api.js - Helper functions for API calls
const API_BASE_URL = 'http://localhost:5050/api';

// Store token in localStorage
function setAuthToken(token) {
    localStorage.setItem('token', token);
}

function getAuthToken() {
    return localStorage.getItem('token');
}

function clearAuth() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
}

// Generic fetch with auth
async function apiFetch(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    // Add authorization header if token exists
    const token = getAuthToken();
    if (token) {
        defaultOptions.headers['Authorization'] = `Bearer ${token}`;
    }
    
    const finalOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, finalOptions);
        
        // Handle 401 Unauthorized (token expired)
        if (response.status === 401) {
            clearAuth();
            window.location.href = 'login.html';
            return;
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'API request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// API functions
export const api = {
    // Auth
    async register(userData) {
        return await apiFetch('/register', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    },
    
    async login(credentials) {
        return await apiFetch('/login', {
            method: 'POST',
            body: JSON.stringify(credentials)
        });
    },
    
    async verifyEmail(code) {
        return await apiFetch('/verify-email', {
            method: 'POST',
            body: JSON.stringify({ code })
        });
    },
    
    async forgotPassword(email) {
        return await apiFetch('/forgot-password', {
            method: 'POST',
            body: JSON.stringify({ email })
        });
    },
    
    async resetPassword(token, password) {
        return await apiFetch('/reset-password', {
            method: 'POST',
            body: JSON.stringify({ token, password })
        });
    },
    
    async resendActivation() {
        return await apiFetch('/resend-activation', {
            method: 'POST'
        });
    },
    
    // Transactions
    async getTransactions(params = {}) {
        const query = new URLSearchParams(params).toString();
        return await apiFetch(`/transactions${query ? `?${query}` : ''}`);
    },
    
    async createTransaction(transactionData) {
        return await apiFetch('/transactions', {
            method: 'POST',
            body: JSON.stringify(transactionData)
        });
    },
    
    async deleteTransaction(id) {
        return await apiFetch(`/transactions/${id}`, {
            method: 'DELETE'
        });
    },
    
    // Dashboard
    async getDashboard() {
        return await apiFetch('/dashboard');
    },
    
    // Test
    async testConnection() {
        return await apiFetch('/test');
    }
};

// Export the setAuthToken for use in other files
export { setAuthToken, getAuthToken, clearAuth };
=======
const BASE_URL = "http://127.0.0.1:5050"; // where Flask runs

async function getWalletAddress(token) {
  const res = await fetch(`${BASE_URL}/api/wallet`, {
    method: "GET",
    headers: { "Authorization": `Bearer ${token}` }
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "get wallet failed");
  return data.address;
}
>>>>>>> 1ad07a1 (My changes)
