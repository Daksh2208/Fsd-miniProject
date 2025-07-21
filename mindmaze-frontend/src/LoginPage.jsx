import React, { useState } from 'react';
import { Brain, Zap, Mail, Lock, Eye, EyeOff } from 'lucide-react';

const LoginPage = ({ isLogin, setIsLogin, onLogin, onSignup, message, isLoading }) => {
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.username.trim()) {
      alert('Please enter a username');
      return;
    }

    if (!isLogin) {
      if (!formData.password) {
        alert('Please enter a password');
        return;
      }
      if (formData.password !== formData.confirmPassword) {
        alert('Passwords do not match');
        return;
      }
    }

    if (isLogin) {
      await onLogin({ username: formData.username, password: formData.password });
    } else {
      await onSignup({ 
        username: formData.username, 
        password: formData.password, 
        confirmPassword: formData.confirmPassword,
        email: formData.email 
      });
    }
  };

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setFormData({
      username: '',
      email: '',
      password: '',
      confirmPassword: ''
    });
  };

  return (
    <div className="auth-container">
      {/* Background Elements */}
      <div className="background-elements">
        <div className="bg-element bg-element-1"></div>
        <div className="bg-element bg-element-2"></div>
        <div className="bg-element bg-element-3"></div>
      </div>

      {/* Main Card */}
      <div className="main-card">
        {/* Header */}
        <div className="header">
          <div className="logo-container">
            <Brain className="brain-icon" />
            <Zap className="zap-icon" />
          </div>
          <h1 className="title">Mind Maze</h1>
          <p className="subtitle">
            {isLogin ? 'Welcome back! Please sign in to continue.' : 'Join us and start your journey!'}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="form-container">
          {/* Username Input */}
          <div className="input-group">
            <label className="input-label" htmlFor="username">Username</label>
            <div className="input-wrapper">
              <Mail className="input-icon" />
              <input
                type="text"
                id="username"
                name="username"
                className="form-input"
                placeholder="Enter your username"
                value={formData.username}
                onChange={handleInputChange}
                required
              />
            </div>
          </div>

          {/* Email Input (for signup only) */}
          {!isLogin && (
            <div className="input-group">
              <label className="input-label" htmlFor="email">Email</label>
              <div className="input-wrapper">
                <Mail className="input-icon" />
                <input
                  type="email"
                  id="email"
                  name="email"
                  className="form-input"
                  placeholder="Enter your email"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                />
              </div>
            </div>
          )}

          {/* Password Input */}
          <div className="input-group">
            <label className="input-label" htmlFor="password">Password</label>
            <div className="input-wrapper">
              <Lock className="input-icon" />
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                name="password"
                className="form-input password-input"
                placeholder="Enter your password"
                value={formData.password}
                onChange={handleInputChange}
                required={!isLogin}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={togglePasswordVisibility}
              >
                {showPassword ? (
                  <EyeOff className="password-toggle-icon" />
                ) : (
                  <Eye className="password-toggle-icon" />
                )}
              </button>
            </div>
          </div>

          {/* Confirm Password Input (for signup) */}
          {!isLogin && (
            <div className="input-group">
              <label className="input-label" htmlFor="confirmPassword">Confirm Password</label>
              <div className="input-wrapper">
                <Lock className="input-icon" />
                <input
                  type="password"
                  id="confirmPassword"
                  name="confirmPassword"
                  className="form-input"
                  placeholder="Confirm your password"
                  value={formData.confirmPassword}
                  onChange={handleInputChange}
                  required
                />
              </div>
            </div>
          )}

          {/* Message Display */}
          {message && (
            <div className="message-container">
              <p className="message">{message}</p>
            </div>
          )}

          {/* Submit Button */}
          <button 
            type="submit" 
            className="submit-btn" 
            disabled={isLoading}
          >
            {isLoading ? 'Loading...' : (isLogin ? 'Sign In' : 'Create Account')}
          </button>

          {/* Forgot Password (only for login) */}
          {isLogin && (
            <div className="forgot-password">
              <button type="button" className="forgot-btn">
                Forgot your password?
              </button>
            </div>
          )}
        </form>

        {/* Toggle Section */}
        <div className="toggle-section">
          <p className="toggle-text">
            {isLogin ? "Don't have an account?" : "Already have an account?"}
            <button type="button" className="toggle-btn" onClick={toggleMode}>
              {isLogin ? ' Sign up' : ' Sign in'}
            </button>
          </p>
        </div>

        {/* Footer */}
        <div className="footer">
          <p className="footer-text">
            © 2024 Mind Maze. All rights reserved.
          </p>
        </div>
      </div>

      <style jsx>{`
        /* Mind Maze Auth Styles */
        .auth-container {
          min-height: 100vh;
          background: linear-gradient(135deg, #581c87 0%, #1e3a8a 50%, #312e81 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 1rem;
          position: relative;
        }

        .background-elements {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          overflow: hidden;
          pointer-events: none;
        }

        .bg-element {
          position: absolute;
          border-radius: 50%;
          opacity: 0.2;
        }

        .bg-element-1 {
          top: 25%;
          left: 25%;
          width: 8rem;
          height: 8rem;
          background-color: #a855f7;
          animation: pulse 2s infinite;
        }

        .bg-element-2 {
          top: 75%;
          right: 25%;
          width: 6rem;
          height: 6rem;
          background-color: #60a5fa;
          animation: pulse 2s infinite;
          animation-delay: 1s;
        }

        .bg-element-3 {
          bottom: 25%;
          left: 50%;
          width: 4rem;
          height: 4rem;
          background-color: #818cf8;
          animation: pulse 2s infinite;
          animation-delay: 2s;
        }

        .main-card {
          position: relative;
          width: 100%;
          max-width: 28rem;
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(16px);
          border-radius: 1rem;
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
          border: 1px solid rgba(255, 255, 255, 0.2);
          padding: 2rem;
          transition: all 0.3s ease;
        }

        .main-card:hover {
          transform: translateY(-5px);
          box-shadow: 0 35px 60px -12px rgba(0, 0, 0, 0.3);
        }

        .header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .logo-container {
          display: flex;
          justify-content: center;
          align-items: center;
          margin-bottom: 1rem;
          position: relative;
        }

        .brain-icon {
          width: 4rem;
          height: 4rem;
          color: #d8b4fe;
          animation: pulse 2s infinite;
        }

        .zap-icon {
          width: 1.5rem;
          height: 1.5rem;
          color: #fbbf24;
          position: absolute;
          top: -0.25rem;
          right: -0.25rem;
          animation: bounce 1s infinite;
        }

        .title {
          font-size: 1.875rem;
          font-weight: bold;
          color: white;
          margin-bottom: 0.5rem;
          margin-top: 0;
        }

        .subtitle {
          color: #ddd6fe;
          font-size: 0.875rem;
          margin: 0;
        }

        .form-container {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .input-group {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .input-label {
          color: white;
          font-size: 0.875rem;
          font-weight: 500;
          margin: 0;
        }

        .input-wrapper {
          position: relative;
        }

        .input-icon {
          width: 1.25rem;
          height: 1.25rem;
          color: #d8b4fe;
          position: absolute;
          left: 0.75rem;
          top: 0.75rem;
          pointer-events: none;
        }

        .form-input {
          width: 100%;
          padding: 0.75rem 0.75rem 0.75rem 2.5rem;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 0.5rem;
          color: white;
          font-size: 1rem;
          transition: all 0.3s ease;
          box-sizing: border-box;
        }

        .form-input::placeholder {
          color: #ddd6fe;
        }

        .form-input:focus {
          outline: none;
          border-color: #a855f7;
          background: rgba(255, 255, 255, 0.2);
          box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.1);
        }

        .password-input {
          padding-right: 3rem;
        }

        .password-toggle {
          position: absolute;
          right: 0.75rem;
          top: 0.75rem;
          background: none;
          border: none;
          color: #d8b4fe;
          cursor: pointer;
          padding: 0;
          transition: color 0.3s ease;
        }

        .password-toggle:hover {
          color: white;
        }

        .password-toggle-icon {
          width: 1.25rem;
          height: 1.25rem;
        }

        .message-container {
          text-align: center;
        }

        .message {
          color: #fbbf24;
          font-size: 0.875rem;
          margin: 0;
          padding: 0.5rem;
          background: rgba(251, 191, 36, 0.1);
          border-radius: 0.375rem;
          border: 1px solid rgba(251, 191, 36, 0.2);
        }

        .submit-btn {
          width: 100%;
          background: linear-gradient(90deg, #a855f7 0%, #3b82f6 100%);
          color: white;
          padding: 0.75rem 1.5rem;
          border-radius: 0.5rem;
          font-weight: 600;
          font-size: 1rem;
          border: none;
          cursor: pointer;
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
          transition: all 0.3s ease;
        }

        .submit-btn:hover:not(:disabled) {
          background: linear-gradient(90deg, #9333ea 0%, #2563eb 100%);
          transform: translateY(-2px);
          box-shadow: 0 15px 25px -5px rgba(0, 0, 0, 0.2);
        }

        .submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .submit-btn:focus {
          outline: none;
          box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.5);
        }

        .toggle-section {
          margin-top: 1.5rem;
          text-align: center;
        }

        .toggle-text {
          color: #ddd6fe;
          font-size: 0.875rem;
          margin: 0;
        }

        .toggle-btn {
          color: #d8b4fe;
          font-weight: 600;
          text-decoration: underline;
          background: none;
          border: none;
          cursor: pointer;
          font-size: 0.875rem;
          transition: color 0.3s ease;
        }

        .toggle-btn:hover {
          color: white;
        }

        .forgot-password {
          margin-top: 1rem;
          text-align: center;
        }

        .forgot-btn {
          color: #d8b4fe;
          font-size: 0.875rem;
          background: none;
          border: none;
          cursor: pointer;
          text-decoration: none;
          transition: color 0.3s ease;
        }

        .forgot-btn:hover {
          color: white;
        }

        .footer {
          text-align: center;
          margin-top: 1.5rem;
        }

        .footer-text {
          color: #ddd6fe;
          font-size: 0.75rem;
          margin: 0;
        }

        /* Animations */
        @keyframes pulse {
          0%, 100% {
            opacity: 0.2;
          }
          50% {
            opacity: 0.4;
          }
        }

        @keyframes bounce {
          0%, 100% {
            transform: translateY(0);
          }
          50% {
            transform: translateY(-25%);
          }
        }

        /* Responsive Design */
        @media (max-width: 640px) {
          .auth-container {
            padding: 0.5rem;
          }
          
          .main-card {
            padding: 1.5rem;
          }
          
          .title {
            font-size: 1.5rem;
          }
          
          .brain-icon {
            width: 3rem;
            height: 3rem;
          }
          
          .zap-icon {
            width: 1.25rem;
            height: 1.25rem;
          }
        }
      `}</style>
    </div>
  );
};

export default LoginPage;