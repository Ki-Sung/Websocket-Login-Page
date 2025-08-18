import React, { useState } from 'react';
import './LoginForm.css';

const LoginForm = ({ onLogin, setWebsocket, showForceLogoutModal }) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    // 유효성 검사 상태
    const [usernameError, setUsernameError] = useState('');
    const [passwordError, setPasswordError] = useState('');
    const [isFormValid, setIsFormValid] = useState(false);

    // 사용자명 유효성 검사
    const validateUsername = (value) => {
        if (!value.trim()) {
            return '사용자명을 입력해주세요.';
        }
        if (value.trim().length < 3) {
            return '사용자명은 3자 이상이어야 합니다.';
        }
        if (!/^[a-zA-Z0-9_]+$/.test(value.trim())) {
            return '사용자명은 영문, 숫자, 언더스코어만 사용 가능합니다.';
        }
        return '';
    };

    // 비밀번호 유효성 검사
    const validatePassword = (value) => {
        if (!value) {
            return '비밀번호를 입력해주세요.';
        }
        if (value.length < 6) {
            return '비밀번호는 6자 이상이어야 합니다.';
        }
        return '';
    };

    // 폼 유효성 검사
    const validateForm = () => {
        const usernameErr = validateUsername(username);
        const passwordErr = validatePassword(password);
        
        setUsernameError(usernameErr);
        setPasswordError(passwordErr);
        
        const isValid = !usernameErr && !passwordErr;
        setIsFormValid(isValid);
        return isValid;
    };

    // 실시간 유효성 검사 (입력 중에는 에러 표시하지 않음)
    const handleUsernameChange = (e) => {
        const value = e.target.value;
        setUsername(value);
        setError(''); // 서버 에러 메시지 초기화
        // 입력 중에는 필드 에러 표시하지 않음
    };

    const handlePasswordChange = (e) => {
        const value = e.target.value;
        setPassword(value);
        setError(''); // 서버 에러 메시지 초기화
        // 입력 중에는 필드 에러 표시하지 않음
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        // 폼 유효성 검사 (제출 시에만)
        if (!validateForm()) {
            return; // 에러가 있으면 여기서 중단
        }
        
        setIsLoading(true);
        setError('');

        try {
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);

            const response = await fetch('http://192.168.2.55:8000/api/auth/login', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (response.ok) {
                // 로그인 성공
                onLogin(data.user);
                
                // WebSocket 연결
                connectWebSocket(data.user.username, data.access_token);
                
                // 폼 초기화
                setUsername('');
                setPassword('');
                setUsernameError('');
                setPasswordError('');
                setIsFormValid(false);
            } else {
                // 서버 에러 메시지 처리
                let errorMessage = '로그인에 실패했습니다.';
                
                if (data.detail) {
                    if (typeof data.detail === 'string') {
                        errorMessage = data.detail;
                    } else if (data.detail.msg) {
                        errorMessage = data.detail.msg;
                    } else if (Array.isArray(data.detail)) {
                        errorMessage = data.detail.map(err => err.msg || err.message || '알 수 없는 오류').join(', ');
                    }
                }
                
                setError(errorMessage);
            }
        } catch (error) {
            setError('네트워크 오류가 발생했습니다.');
            console.error('Login error:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const connectWebSocket = (userId, token) => {
        console.log('WebSocket 연결 시도:', userId, '토큰:', token ? '있음' : '없음');
        const wsUrl = `ws://192.168.2.55:8000/ws/${userId}?token=${token}`;
        console.log('WebSocket URL:', wsUrl);
        
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('✅ WebSocket 연결 성공!');
            setWebsocket(ws);
            
            // 핑 전송 시작 (30초마다)
            const pingInterval = setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    console.log('핑 전송:', new Date().toLocaleTimeString());
                    ws.send('ping');
                }
            }, 30000);
            
            // WebSocket 객체에 interval 저장
            ws.pingInterval = pingInterval;
        };

        ws.onmessage = (event) => {
            console.log('WebSocket 메시지 원본:', event.data);
            
            try {
                const data = JSON.parse(event.data);
                console.log('WebSocket JSON 메시지 수신:', data);
                
                if (data.type === 'force_logout') {
                    console.log('강제 로그아웃 메시지 감지! 모달 표시 시도...');
                    // 강제 로그아웃 알림 표시
                    showForceLogoutModal(data);
                }
            } catch (e) {
                if (event.data === 'pong') {
                    console.log('Pong 수신');
                } else {
                    console.log('텍스트 메시지:', event.data);
                }
            }
        };

        ws.onclose = (event) => {
            console.log('❌ WebSocket 연결 종료:', event.code, event.reason);
            setWebsocket(null);
            
            // ping interval 정리
            if (ws.pingInterval) {
                clearInterval(ws.pingInterval);
            }
        };

        ws.onerror = (error) => {
            console.error('❌ WebSocket 오류:', error);
            setError('WebSocket 연결에 실패했습니다.');
        };
    };

    return (
        <div className="login-form-container">
            <h2>🔐 로그인</h2>
            
            <form onSubmit={handleSubmit} className="login-form">
                <div className="form-group">
                    <label htmlFor="username">사용자명:</label>
                    <input
                        type="text"
                        id="username"
                        value={username}
                        onChange={handleUsernameChange}
                        required
                        placeholder="user1, user2, user3"
                    />
                    {usernameError && <div className="field-error">{usernameError}</div>}
                </div>

                <div className="form-group">
                    <label htmlFor="password">비밀번호:</label>
                    <input
                        type="password"
                        id="password"
                        value={password}
                        onChange={handlePasswordChange}
                        required
                        placeholder="password1, password2, password3"
                    />
                    {passwordError && <div className="field-error">{passwordError}</div>}
                </div>

                {error && <div className="error-message">{error}</div>}

                <button 
                    type="submit" 
                    className="login-button"
                    disabled={isLoading}
                >
                    {isLoading ? '로그인 중...' : '로그인'}
                </button>
            </form>

            <div className="test-accounts">
                <h3>🧪 테스트 계정</h3>
                <div className="account-list">
                    <div className="account-item">
                        <strong>user1</strong> / password1 (관리자)
                    </div>
                    <div className="account-item">
                        <strong>user2</strong> / password2 (일반사용자)
                    </div>
                    <div className="account-item">
                        <strong>user3</strong> / password3 (일반사용자)
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LoginForm;
