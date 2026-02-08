// Add this function to update user info
function updateUserInfo() {
    try {
        // Get user data from localStorage (where modules.js stores it)
        const userData = localStorage.getItem('user');
        
        if (userData) {
            const user = JSON.parse(userData);
            
            // Update avatar initials
            const avatar = document.querySelector('.avatar');
            const avatarSmall = document.querySelector('.avatar-small');
            
            if (avatar && user.name) {
                avatar.textContent = user.name.charAt(0).toUpperCase();
            }
            if (avatarSmall && user.name) {
                avatarSmall.textContent = user.name.charAt(0).toUpperCase();
            }
            
            // Update user name and email
            const userName = document.querySelector('.user-name');
            const userEmail = document.querySelector('.user-email');
            
            if (userName) userName.textContent = user.name || 'User';
            if (userEmail) userEmail.textContent = user.email || 'No email';
            
            console.log('User info updated:', user.name, user.email);
        } else {
            console.log('No user data found in localStorage');
        }
    } catch (error) {
        console.error('Error updating user info:', error);
    }
}

// Update the logout function to clear data properly
function logout() {
    // Clear localStorage/session data
    localStorage.removeItem('userId');
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('email');
    localStorage.removeItem('username');

    // Reset visible balance immediately (if present)
    const bal = document.getElementById('totalBalance');
    if (bal) bal.textContent = '£0.00';

    // Redirect to login
    window.location.replace('index.html');
}

// Call updateUserInfo when page loads
document.addEventListener('DOMContentLoaded', function() {
    updateUserInfo();
});

// Your existing functions (keep these)
function toggleAvatarMenu() {
  const menu = document.getElementById('avatarMenu');
  if (menu) {
    if (menu.classList.contains('active')) {
      // Start fade out
      menu.classList.remove('active');
      menu.classList.add('fading-out');
      
      // Remove fading-out class after animation completes
      setTimeout(() => {
        menu.classList.remove('fading-out');
      }, 200);
    } else {
      // Remove any leftover classes
      menu.classList.remove('fading-out');
      // Start fade in
      menu.classList.add('active');
    }
  }
}

document.addEventListener('click', function(event) {
  const menu = document.getElementById('avatarMenu');
  const avatarBtn = document.querySelector('.avatar-btn');
  
  if (menu && menu.classList.contains('active')) {
    if (!menu.contains(event.target) && !avatarBtn.contains(event.target)) {
      // Start fade out when clicking outside
      menu.classList.remove('active');
      menu.classList.add('fading-out');
      
      setTimeout(() => {
        menu.classList.remove('fading-out');
      }, 200);
    }
  }
});

document.addEventListener('keydown', function(event) {
  if (event.key === 'Escape') {
    const menu = document.getElementById('avatarMenu');
    if (menu && menu.classList.contains('active')) {
      menu.classList.remove('active');
      menu.classList.add('fading-out');
      
      setTimeout(() => {
        menu.classList.remove('fading-out');
      }, 200);
    }
  }
});


async function refreshBalanceForCurrentUser() {
  // Prefer the on-chain balance helper exposed by plasma.js
  if (typeof window.fetchAndRenderWalletBalance === 'function') {
    await window.fetchAndRenderWalletBalance();
  } else if (typeof window.loadBalanceFromChain === 'function') {
    await window.loadBalanceFromChain();
  }
}

// Run on normal load and when returning from bfcache
window.addEventListener('pageshow', () => {
  refreshBalanceForCurrentUser();
});

// Refresh when tab regains focus
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) refreshBalanceForCurrentUser();
});
