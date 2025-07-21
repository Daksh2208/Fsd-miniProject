import React, { useState, useEffect } from 'react';
import { User, Brain, Zap, Trophy, Users, Search, Target, PartyPopper } from 'lucide-react';
import './App.css';
import LoginPage from './LoginPage';

function App() {
  const [user, setUser] = useState(null);
  const [ws, setWs] = useState(null);
  const [gameState, setGameState] = useState('menu');
  const [currentPuzzle, setCurrentPuzzle] = useState('');
  const [opponent, setOpponent] = useState('');
  const [answer, setAnswer] = useState('');
  const [leaderboard, setLeaderboard] = useState([]);
  const [message, setMessage] = useState('');
  const [stats, setStats] = useState({});
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  const [isLoading, setIsLoading] = useState(false);
  const [isLogin, setIsLogin] = useState(true);

  const login = async (username) => {
    if (!username.trim()) {
      setMessage('Please enter a username');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim() })
      });
      
      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
        setMessage('Login successful!');
        connectWebSocket(username.trim());
        setTimeout(() => setMessage(''), 2000);
      } else {
        const errorData = await response.json();
        setMessage(errorData.detail || 'Login failed');
      }
    } catch (error) {
      setMessage('Connection error. Make sure backend is running.');
      console.error('Login error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (username, email) => {
    if (!username.trim()) {
      setMessage('Please enter a username');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), email: email || '' })
      });

      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
        setMessage('Account created successfully!');
        connectWebSocket(username.trim());
        setTimeout(() => setMessage(''), 2000);
      } else {
        const errorData = await response.json();
        setMessage(errorData.detail || 'Signup failed');
      }
    } catch (error) {
      setMessage('Connection error. Make sure backend is running.');
      console.error('Signup error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const connectWebSocket = (username) => {
    if (ws) {
      ws.close();
    }

    const websocket = new WebSocket(`ws://localhost:8000/ws/${username}`);
    
    websocket.onopen = () => {
      console.log('WebSocket connected');
      setConnectionStatus('Connected');
    };
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'connected') {
        setMessage(data.message);
        setTimeout(() => setMessage(''), 2000);
      } else if (data.type === 'waiting_for_opponent') {
        setGameState('waiting');
        setMessage('Looking for opponent...');
      } else if (data.type === 'game_start') {
        setGameState('playing');
        setCurrentPuzzle(data.puzzle);
        setOpponent(data.opponent);
        setMessage(`Battle started against ${data.opponent}!`);
        setTimeout(() => setMessage(''), 2000);
      } else if (data.type === 'game_end') {
        setGameState('finished');
        setMessage(data.message);
        if (data.is_winner) {
          setUser(prev => ({ ...prev, score: (prev.score || 0) + 10 }));
        }
        setTimeout(() => {
          setGameState('menu');
          setCurrentPuzzle('');
          setOpponent('');
          setAnswer('');
          loadLeaderboard();
          loadStats();
        }, 3000);
      } else if (data.type === 'wrong_answer') {
        setMessage(data.message);
        setTimeout(() => setMessage(''), 2000);
      } else if (data.type === 'opponent_disconnected') {
        setGameState('menu');
        setMessage(data.message);
        setCurrentPuzzle('');
        setOpponent('');
        setAnswer('');
        setTimeout(() => setMessage(''), 3000);
      } else if (data.type === 'error') {
        setMessage(data.message);
        setTimeout(() => setMessage(''), 3000);
      }
    };
    
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('Error');
      setMessage('Connection error');
    };
    
    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      setConnectionStatus('Disconnected');
    };
    
    setWs(websocket);
  };

  const findMatch = () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'find_match' }));
      setMessage('Finding opponent...');
    } else {
      setMessage('Not connected to server');
    }
  };

  const submitAnswer = (e) => {
    e?.preventDefault();
    if (ws && ws.readyState === WebSocket.OPEN && answer.trim()) {
      ws.send(JSON.stringify({ type: 'submit_answer', answer: answer.trim() }));
      setAnswer('');
    }
  };

  const loadLeaderboard = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/leaderboard');
      if (response.ok) {
        const data = await response.json();
        setLeaderboard(data);
      }
    } catch (error) {
      console.error('Leaderboard error:', error);
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Stats error:', error);
    }
  };

  const logout = () => {
    if (ws) {
      ws.close();
    }
    setUser(null);
    setWs(null);
    setGameState('menu');
    setCurrentPuzzle('');
    setOpponent('');
    setAnswer('');
    setMessage('');
    setConnectionStatus('Disconnected');
  };

  useEffect(() => {
    loadLeaderboard();
    loadStats();
    
    const interval = setInterval(() => {
      loadStats();
    }, 30000);
    
    return () => {
      clearInterval(interval);
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const handleLogin = async ({ username, password }) => {
    await login(username);
  };

  const handleSignup = async ({ username, password, confirmPassword, email }) => {
    await signup(username, email);
  };

  if (!user) {
    return (
      <LoginPage
        isLogin={isLogin}
        setIsLogin={setIsLogin}
        onLogin={handleLogin}
        onSignup={handleSignup}
        message={message}
        isLoading={isLoading}
      />
    );
  }

  return (
    <div className="app">
      <div className="container">
        <div className="app-header">
          <h1>🧠 MindMaze</h1>
          <button className="logout-btn" onClick={logout}>
            Logout
          </button>
        </div>
        
        <div className="user-info">
          <p>Welcome, <strong>{user.username}</strong>!</p>
          <p>Score: <strong>{user.score || 0}</strong> points</p>
          <p className={`status ${connectionStatus.toLowerCase()}`}>
            {connectionStatus}
          </p>
        </div>
        
        {message && <div className="message-banner">{message}</div>}
        
        {gameState === 'menu' && (
          <div className="menu">
            <div className="menu-actions">
              <button className="play-button" onClick={findMatch}>
                🎮 Find Match
              </button>
              <button className="refresh-button" onClick={loadLeaderboard}>
                🔄 Refresh Leaderboard
              </button>
            </div>
            
            <div className="stats">
              <h3>📊 Live Stats</h3>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="stat-label">Total Players:</span>
                  <span className="stat-value">{stats.total_users || 0}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Active Games:</span>
                  <span className="stat-value">{stats.active_games || 0}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Online Now:</span>
                  <span className="stat-value">{stats.connected_players || 0}</span>
                </div>
              </div>
            </div>
            
            <div className="leaderboard">
              <h3>🏆 Leaderboard</h3>
              {leaderboard.length === 0 ? (
                <p className="no-players">No players yet. Be the first!</p>
              ) : (
                <div className="leaderboard-list">
                  {leaderboard.map((player, index) => (
                    <div key={index} className="leaderboard-item">
                      <span className="rank">#{index + 1}</span>
                      <span className="username">{player.username}</span>
                      <span className="score">{player.score || 0} pts</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
        
        {gameState === 'waiting' && (
          <div className="waiting">
            <h2>🔍 Finding opponent...</h2>
            <div className="spinner">⟳</div>
            <p>Please wait while we find you an opponent!</p>
            <button className="cancel-button" onClick={() => setGameState('menu')}>
              Cancel
            </button>
          </div>
        )}
        
        {gameState === 'playing' && (
          <div className="game">
            <h2>🎯 Battle vs {opponent}</h2>
            <div className="puzzle-container">
              <div className="puzzle-question">
                <h3>{currentPuzzle}</h3>
              </div>
              <form onSubmit={submitAnswer} className="answer-form">
                <div className="answer-section">
                  <input 
                    type="text" 
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="Type your answer..."
                    className="answer-input"
                    autoFocus
                  />
                  <button type="submit" className="submit-answer-btn">
                    Submit
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
        
        {gameState === 'finished' && (
          <div className="finished">
            <h2>🎉 Game Finished!</h2>
            <p>Returning to menu...</p>
            <div className="spinner">⟳</div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;