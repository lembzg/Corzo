import smtplib
import os
import secrets
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS


class EmailService:
    """
    Email service for user authentication workflows.
    Handles sign-in verification emails and password reset emails.
    """
    
    def __init__(self):
        """
        Initialize the email service.   
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            sender_email: Email address to send from
            sender_password: Password for sender email
            app_name: Name of your application
            base_url: Base URL for your web app
        """
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email= "corzoapp@gmail.com"
        self.sender_password= "osexcuaehoztlcat"
        self.app_name = "CorzoApp"
        self.base_url = "http://localhost:5050"
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Store temporary activation codes (in production, use a database)
        self.activation_codes = {}
        self.reset_codes = {}
        
        # Default expiration times (in hours)
        self.activation_expiry_hours = 24
        self.reset_expiry_hours = 1
    
    def _create_activation_code(self, length: int = 6) -> str:
        """Generate a random activation code."""
        # Using digits only for simpler user experience
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    def _create_reset_token(self, length: int = 32) -> str:
        """Generate a secure reset token."""
        return secrets.token_urlsafe(length)
    def send_custom_email(self, recipient, subject, html_content, plain_text=None):
        """
        Send a custom email using your existing _send_email method.
        
        Args:
            recipient: Email address to send to
            subject: Email subject
            html_content: HTML content for the email
            plain_text: Plain text version (optional - auto-generated if None)
        
        Returns:
            bool: True if sent successfully
        """
        # Auto-generate plain text if not provided
        if plain_text is None:
            # Simple HTML to text conversion
            import re
            plain_text = re.sub(r'<[^>]+>', '', html_content)
            plain_text = re.sub(r'\s+', ' ', plain_text).strip()
        
        # Use the existing _send_email method
        return self._send_email(recipient, subject, html_content, plain_text)
    
    def _send_email(self, recipient: str, subject: str, html_body: str, text_body: str) -> bool:
        """
        Send an email with embedded image.
        
        Args:
            recipient: Recipient email address
            subject: Email subject
            html_body: HTML content
            text_body: Plain text content (for email clients that don't support HTML)
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create message container
            msg = MIMEMultipart('related')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = recipient
            
            # Create alternative part for HTML and plain text
            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)
            
            # Create plain text version
            text_part = MIMEText(text_body, 'plain')
            msg_alternative.attach(text_part)
            
            # Create HTML version
            html_part = MIMEText(html_body, 'html')
            msg_alternative.attach(html_part)
            
            # Embed image (logo or signature)
            image_path = self._get_embedded_image_path()
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as img_file:
                    img = MIMEImage(img_file.read())
                    img.add_header('Content-ID', '<embedded_logo>')
                    img.add_header('Content-Disposition', 'inline', filename='Corzo_Logo.jpeg')
                    msg.attach(img)
            else:
                # If no image file exists, we'll use a placeholder in the HTML
                self.logger.warning("Embedded image not found, using placeholder")
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            self.logger.info(f"Email sent successfully to {recipient}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email to {recipient}: {str(e)}")
            return False
    
    def _get_embedded_image_path(self) -> Optional[str]:
        """
        Get the path to the embedded image.
        Override this method to provide your own image path.
        
        Returns:
            str or None: Path to image file
        """
        # Default locations to check for logo
        possible_paths = [
            'static/images/Corzo_Logo.jpeg',
            'static/Corzo_Logo.jpeg',
            'Corzo_Logo.jpeg',
            os.path.join(os.path.dirname(__file__), 'Corzo_Logo.jpeg')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _get_email_template(self, template_name: str, context: Dict[str, Any]) -> tuple:
        """
        Get HTML and plain text templates for emails.
        
        Args:
            template_name: Name of the template
            context: Dictionary with template variables
            
        Returns:
            tuple: (html_template, text_template)
        """
        templates = {
            'activation': {
                'html': self._get_activation_html_template(context),
                'text': self._get_activation_text_template(context)
            },
            'reset': {
                'html': self._get_reset_html_template(context),
                'text': self._get_reset_text_template(context)
            }
        }
        
        if template_name in templates:
            return templates[template_name]['html'], templates[template_name]['text']
        
        raise ValueError(f"Template '{template_name}' not found")
    
    def _get_activation_html_template(self, context: Dict[str, Any]) -> str:
        """HTML template for activation email."""
        code = context.get('code', '')
        expiry_hours = context.get('expiry_hours', self.activation_expiry_hours)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    text-align: center;
                    padding: 20px 0;
                }}
                .logo {{
                    padding: 30px;
                    border-radius: 10px;
                    margin: 20px 0;
                    max-width: 600px;
                    height: auto;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border-radius: 10px;
                    margin: 20px 0;
                }}
                .code {{
                    display: inline-block;
                    background-color: #007bff;
                    color: white;
                    padding: 15px 30px;
                    font-size: 24px;
                    font-weight: bold;
                    letter-spacing: 5px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    color: #666;
                    font-size: 12px;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    color: #856404;
                    padding: 10px;
                    border-radius: 5px;
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <!-- Embedded logo -->
                <img src="cid:embedded_logo" alt="{self.app_name} Logo" class="logo">
                <h1>Welcome to {self.app_name}!</h1>
            </div>
            
            <div class="content">
                <h2>Activate Your Account</h2>
                <p>Thank you for signing up to {self.app_name}! To complete your registration, please use the activation code below:</p>
                
                <div class="code">{code}</div>
                
                <div class="warning">
                    <p><strong>Important:</strong> This code will expire in {expiry_hours} hours.</p>
                </div>
                
                <p>Enter this code on the activation page to verify your email address and activate your account.</p>
                
                <p>If you did not sign up for an account with {self.app_name}, please ignore this email.</p>
            </div>
            
            <div class="footer">
                <p>&copy; {datetime.now().year} {self.app_name}. All rights reserved.</p>
                <p>This email was sent to {context.get('email', '')}</p>
            </div>
        </body>
        </html>
        """
    
    def _get_activation_text_template(self, context: Dict[str, Any]) -> str:
        """Plain text template for activation email."""
        code = context.get('code', '')
        expiry_hours = context.get('expiry_hours', self.activation_expiry_hours)
        
        return f"""
        Welcome to {self.app_name}!
        
        ACTIVATE YOUR ACCOUNT
        
        Thank you for signing up to {self.app_name}! To complete your registration, please use the activation code below:
        
        Activation Code: {code}
        
        Important: This code will expire in {expiry_hours} hours.
        
        Enter this code on the activation page to verify your email address and activate your account.
        
        If you did not sign up for an account with {self.app_name}, please ignore this email.
        
        ---
        © {datetime.now().year} {self.app_name}. All rights reserved.
        This email was sent to {context.get('email', '')}
        """
    
    def _get_reset_html_template(self, context: Dict[str, Any]) -> str:
        """HTML template for password reset email."""
        reset_link = context.get('reset_link', '')
        expiry_hours = context.get('expiry_hours', self.reset_expiry_hours)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    text-align: center;
                    padding: 20px 0;
                }}
                .logo {{
                    max-width: 150px;
                    height: auto;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border-radius: 10px;
                    margin: 20px 0;
                }}
                .button {{
                    display: inline-block;
                    background-color: #dc3545;
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    color: #666;
                    font-size: 12px;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    color: #856404;
                    padding: 10px;
                    border-radius: 5px;
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <img src="cid:embedded_logo" alt="{self.app_name} Logo" class="logo">
                <h1>Password Reset Request</h1>
            </div>
            
            <div class="content">
                <h2>Reset Your Password</h2>
                <p>We received a request to reset your password for your {self.app_name} account.</p>
                
                <p>Click the button below to reset your password:</p>
                
                <p style="text-align: center;">
                    <a href="{reset_link}" class="button">Reset Password</a>
                </p>
                
                <p>Or copy and paste this link into your browser:</p>
                <p><code>{reset_link}</code></p>
                
                <div class="warning">
                    <p><strong>Important:</strong> This link will expire in {expiry_hours} hours.</p>
                    <p>If you did not request a password reset, please ignore this email or contact support if you're concerned about your account's security.</p>
                </div>
            </div>
            
            <div class="footer">
                <p>&copy; {datetime.now().year} {self.app_name}. All rights reserved.</p>
                <p>This email was sent to {context.get('email', '')}</p>
            </div>
        </body>
        </html>
        """
    
    def _get_reset_text_template(self, context: Dict[str, Any]) -> str:
        """Plain text template for password reset email."""
        reset_link = context.get('reset_link', '')
        expiry_hours = context.get('expiry_hours', self.reset_expiry_hours)
        
        return f"""
        Password Reset Request - {self.app_name}
        
        RESET YOUR PASSWORD
        
        We received a request to reset your password for your {self.app_name} account.
        
        Click the link below to reset your password:
        {reset_link}
        
        Important: This link will expire in {expiry_hours} hours.
        
        If you did not request a password reset, please ignore this email or contact support if you're concerned about your account's security.
        
        ---
        © {datetime.now().year} {self.app_name}. All rights reserved.
        This email was sent to {context.get('email', '')}
        """
    
    def send_activation_email(self, email: str, user_id: str) -> tuple:
        """
        Send activation email with verification code.
        
        Args:
            email: User's email address
            user_id: User's unique identifier
            
        Returns:
            tuple: (success, code) or (success, error_message)
        """
        try:
            # Generate activation code
            activation_code = self._create_activation_code()
            
            # Store code with expiration
            expiry_time = datetime.now() + timedelta(hours=self.activation_expiry_hours)
            self.activation_codes[user_id] = {
                'code': activation_code,
                'email': email,
                'expires_at': expiry_time,
                'used': False
            }
            
            # Prepare email context
            context = {
                'code': activation_code,
                'email': email,
                'app_name': self.app_name,
                'expiry_hours': self.activation_expiry_hours
            }
            
            # Get templates
            html_body, text_body = self._get_email_template('activation', context)
            
            # Send email
            subject = f"Activate Your {self.app_name} Account"
            success = self._send_email(email, subject, html_body, text_body)
            
            if success:
                return True, activation_code
            else:
                return False, "Failed to send activation email"
                
        except Exception as e:
            self.logger.error(f"Error sending activation email to {email}: {str(e)}")
            return False, str(e)
    
    def send_password_reset_email(self, email: str, user_id: str) -> tuple:
        """
        Send password reset email with reset link.
        
        Args:
            email: User's email address
            user_id: User's unique identifier
            
        Returns:
            tuple: (success, reset_token) or (success, error_message)
        """
        try:
            # Generate reset token
            reset_token = self._create_reset_token()
            
            # Store token with expiration
            expiry_time = datetime.now() + timedelta(hours=self.reset_expiry_hours)
            self.reset_codes[user_id] = {
                'token': reset_token,
                'email': email,
                'expires_at': expiry_time,
                'used': False
            }
            
            # Create reset link
            reset_link = f"{self.base_url}/reset-password?token={reset_token}&user_id={user_id}"
            
            # Prepare email context
            context = {
                'reset_link': reset_link,
                'email': email,
                'app_name': self.app_name,
                'expiry_hours': self.reset_expiry_hours
            }
            
            # Get templates
            html_body, text_body = self._get_email_template('reset', context)
            
            # Send email
            subject = f"Reset Your {self.app_name} Password"
            success = self._send_email(email, subject, html_body, text_body)
            
            if success:
                return True, reset_token
            else:
                return False, "Failed to send reset email"
                
        except Exception as e:
            self.logger.error(f"Error sending reset email to {email}: {str(e)}")
            return False, str(e)
    
    def verify_activation_code(self, user_id: str, code: str) -> bool:
        """
        Verify if activation code is valid.
        
        Args:
            user_id: User's unique identifier
            code: Activation code to verify
            
        Returns:
            bool: True if code is valid, False otherwise
        """
        if user_id not in self.activation_codes:
            return False
        
        data = self.activation_codes[user_id]
        
        # Check if code matches and is not expired
        if (data['code'] == code and 
            not data['used'] and 
            datetime.now() < data['expires_at']):
            
            # Mark as used
            data['used'] = True
            return True
        
        return False
    
    def verify_reset_token(self, user_id: str, token: str) -> bool:
        """
        Verify if reset token is valid.
        
        Args:
            user_id: User's unique identifier
            token: Reset token to verify
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        if user_id not in self.reset_codes:
            return False
        
        data = self.reset_codes[user_id]
        
        # Check if token matches and is not expired
        if (data['token'] == token and 
            not data['used'] and 
            datetime.now() < data['expires_at']):
            
            # Mark as used
            data['used'] = True
            return True
        
        return False
    
    def cleanup_expired_codes(self):
        """Clean up expired activation and reset codes."""
        now = datetime.now()
        
        # Clean activation codes
        expired_users = [
            user_id for user_id, data in self.activation_codes.items()
            if now >= data['expires_at']
        ]
        for user_id in expired_users:
            del self.activation_codes[user_id]
        
        # Clean reset codes
        expired_users = [
            user_id for user_id, data in self.reset_codes.items()
            if now >= data['expires_at']
        ]
        for user_id in expired_users:
            del self.reset_codes[user_id]
        
        self.logger.info(f"Cleaned up {len(expired_users)} expired codes")


if __name__ == "__main__":
    # Configuration (use environment variables in production)
    es = EmailService()
    success = es.send_activation_email("fdf@gmail.com","gdaga")


