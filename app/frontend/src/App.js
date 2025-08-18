import React, { useState, useEffect } from 'react';
import LoginForm from './components/LoginForm/LoginForm';
import UserDashboard from './components/UserDashboard/UserDashboard';
import WebSocketStatus from './components/WebSocketStatus/WebSocketStatus';
import ForceLogoutModal from './components/ForceLogoutModal/ForceLogoutModal';
import './styles/App.css';

function App() {
    const [currentUser, setCurrentUser] = useState(null);
    const [websocket, setWebsocket] = useState(null);
    const [forceLogoutData, setForceLogoutData] = useState(null);
    const [activeSessions, setActiveSessions] = useState([]);

    // 강제 로그아웃 모달 표시
    const showForceLogoutModal = (data) => {
        console.log('App.js에서 강제 로그아웃 모달 표시:', data);
        setForceLogoutData(data);
    };

    // 강제 로그아웃 모달 숨기기
    const hideForceLogoutModal = () => {
        setForceLogoutData(null);
    };

    // 강제 로그아웃 실행
    const executeForceLogout = () => {
        if (websocket) {
            websocket.close();
            setWebsocket(null);
        }
        setCurrentUser(null);
        hideForceLogoutModal();
    };

    // 활성 세션 조회
    const fetchActiveSessions = async () => {
        try {
            const response = await fetch('http://192.168.2.55:8000/api/auth/active-sessions');
            const data = await response.json();
            setActiveSessions(data.sessions || []);
        } catch (error) {
            console.error('활성 세션 조회 실패:', error);
        }
    };

    // 로그인 시에만 활성 세션 조회 (성능 최적화)
    const handleLogin = (userData) => {
        setCurrentUser(userData);
        fetchActiveSessions(); // 로그인 시에만 호출
    };

    // WebSocket 메시지로 세션 변경사항만 업데이트
    const handleWebSocketMessage = (data) => {
        if (data.type === 'session_update') {
            fetchActiveSessions(); // 세션 변경 시에만 호출
        }
    };

    return (
        <div className="App">
            <header className="App-header">
                <h1>🔐 WebSocket 중복 로그인 테스트</h1>
            </header>

            <main className="App-main">
                {!currentUser ? (
                    <LoginForm 
                        onLogin={handleLogin} 
                        setWebsocket={setWebsocket}
                        showForceLogoutModal={showForceLogoutModal}
                    />
                ) : (
                    <div className="dashboard-container">
                        <UserDashboard 
                            user={currentUser} 
                            onLogout={() => setCurrentUser(null)}
                            setWebsocket={setWebsocket}
                        />
                        <WebSocketStatus 
                            websocket={websocket} 
                            currentUser={currentUser}
                        />
                    </div>
                )}

                <div className="sessions-info">
                    <h3>🔌 활성 세션</h3>
                    <p>현재 로그인된 사용자: {activeSessions.length}명</p>
                    <ul>
                        {activeSessions.map((session, index) => (
                            <li key={index}>
                                {session.username} - {session.session_id?.substring(0, 8)}...
                            </li>
                        ))}
                    </ul>
                </div>
            </main>

            {/* 강제 로그아웃 모달 */}
            {forceLogoutData && (
                <ForceLogoutModal
                    data={forceLogoutData}
                    onConfirm={executeForceLogout}
                    onClose={hideForceLogoutModal}
                />
            )}
        </div>
    );
}

export default App;
