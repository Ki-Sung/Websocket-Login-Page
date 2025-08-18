import React from 'react';
import './UserDashboard.css';

const UserDashboard = ({ user, onLogout, setWebsocket }) => {
    const handleLogout = async () => {
        try {
            const formData = new FormData();
            formData.append('username', user.username);

            await fetch('http://192.168.2.55:8000/api/auth/logout', {
                method: 'POST',
                body: formData,
            });

            // WebSocket 연결 해제
            if (setWebsocket) {
                setWebsocket(null);
            }

            // 로그아웃 처리
            onLogout();
        } catch (error) {
            console.error('로그아웃 실패:', error);
        }
    };

    return (
        <div className="user-dashboard">
            <h2>👤 사용자 대시보드</h2>
            
            <div className="user-info">
                <div className="info-item">
                    <strong>사용자명:</strong> {user.username}
                </div>
                <div className="info-item">
                    <strong>이름:</strong> {user.name}
                </div>
                <div className="info-item">
                    <strong>권한:</strong> {user.is_admin ? '관리자' : '일반사용자'}
                </div>
            </div>

            <button 
                className="logout-button"
                onClick={handleLogout}
            >
                로그아웃
            </button>
        </div>
    );
};

export default UserDashboard;
