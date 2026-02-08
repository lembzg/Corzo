// modules.js - Central module for all JavaScript functionality
import { api, setAuthToken, getAuthToken, clearAuth } from './api.js';

// Auth module
const AuthModule = {
    // Check if user is logged in
    checkAuth() {
        const token = getAuthToken();
        const user = localStorage.getItem('user');
        
        if (!token || !user) {
            return false;
        }
        
        try {
            return JSON.parse(user);
        } catch {
            return false;
        }
    },
    
    // Get current user
    getCurrentUser() {
        const user = localStorage.getItem('user');
        return user ? JSON.parse(user) : null;
    },
    
    // Logout
    logout() {
        clearAuth();
        window.location.href = 'index.html';
    },
    
    // Redirect if not logged in
    requireAuth(redirectTo = 'login.html') {
        if (!this.checkAuth()) {
            window.location.href = redirectTo;
        }
    },
    
    // Update user data in localStorage
    updateUser(userData) {
        const currentUser = this.getCurrentUser();
        const updatedUser = { ...currentUser, ...userData };
        localStorage.setItem('user', JSON.stringify(updatedUser));
    }
};

// Form handling module
const FormModule = {
    // Show loading state on button
    setLoading(button, isLoading, loadingText = 'Loading...') {
        if (isLoading) {
            button.dataset.originalText = button.textContent;
            button.disabled = true;
            button.textContent = loadingText;
        } else {
            button.disabled = false;
            button.textContent = button.dataset.originalText || button.textContent;
        }
    },
    
    // Show message to user
    showMessage(element, text, type = 'info') {
        if (!element) return;
        
        element.textContent = text;
        element.style.display = 'block';
        
        const colors = {
            success: '#4ade80',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };
        
        element.style.color = colors[type] || colors.info;
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            element.style.display = 'none';
        }, 5000);
    },
    
    // Collect all form data
    collectFormData(formId) {
        const form = document.getElementById(formId);
        if (!form) return {};
        
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        return data;
    }
};

// UI module for updating dashboard
const UIModule = {
    // Format currency
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    },
    
    // Format date
    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    },
    
    // Update dashboard with data
    updateDashboard(data) {
        // Update balance (placeholder; on-chain refresh happens in plasma.js)
        const balanceEl = document.querySelector('#totalBalance');
        if (balanceEl) {
            balanceEl.textContent = this.formatCurrency(data.balance);
        }
        
        // Update recent transactions
        if (data.recent_transactions && data.recent_transactions.length > 0) {
            this.updateTransactionList(data.recent_transactions);
        }
        
        // Update stats
        this.updateStats(data);
    },
    
    updateTransactionList(transactions) {
        const listEl = document.querySelector('.list');
        if (!listEl) return;
        
        listEl.innerHTML = '';
        
        transactions.forEach(transaction => {
            const li = document.createElement('li');
            li.innerHTML = `
                <div>
                    <p class="item-title">${transaction.description}</p>
                    <p class="item-sub">${this.formatDate(transaction.date)} · ${transaction.category}</p>
                </div>
                <span class="item-amount ${transaction.type === 'income' ? 'positive' : 'negative'}">
                    ${transaction.type === 'income' ? '+' : '-'} ${this.formatCurrency(transaction.amount)}
                </span>
            `;
            listEl.appendChild(li);
        });
    },
    
    updateStats(data) {
        // Update monthly stats if you have elements for them
        const statsContainer = document.querySelector('.pill-row');
        if (statsContainer) {
            statsContainer.innerHTML = `
                <span class="pill ${data.monthly_net >= 0 ? 'positive' : 'negative'}">
                    ${data.monthly_net >= 0 ? '▲' : '▼'} ${this.formatCurrency(Math.abs(data.monthly_net))} this month
                </span>
                <span class="pill">Balance: ${this.formatCurrency(data.balance)}</span>
            `;
        }
    }
};


// Initialize everything when DOM is loaded
function initApp() {
    // Initialize avatar menu
    
    // Check auth status
    const currentPage = window.location.pathname.split('/').pop();
    const protectedPages = ['main-page.html', 'send.html', 'invest.html', 'dashboard.html'];
    
    if (protectedPages.includes(currentPage)) {
        AuthModule.requireAuth();
        fetchAndRenderWalletBalance();
        loadDashboardData();
    }
    
  
    // Test backend connection
    testBackendConnection();
}

// Dashboard data loader
async function loadDashboardData() {
    try {
        const data = await api.getDashboard();
        UIModule.updateDashboard(data);
    } catch (error) {
        console.error('Failed to load dashboard:', error);
        // Keep showing demo data
    }
}

// Test backend
async function testBackendConnection() {
    try {
        const result = await api.testConnection();
        console.log('Backend status:', result);
    } catch (error) {
        console.warn('Backend not available:', error);
    }
}

// Export everything
export {
    api,
    AuthModule,
    FormModule,
    UIModule,
    initApp,
    loadDashboardData
};
