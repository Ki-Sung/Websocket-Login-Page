import React from 'react';
import './WebSocketStatus.css';

const WebSocketStatus = ({ websocket, currentUser }) => {
    const getStatusText = () => {
        if (!websocket) return '연결되지 않음';
        
        switch (websocket.readyState) {
            case WebSocket.CONNECTING:
                return '연결 중...';
            case WebSocket.OPEN:
                return '연결됨';
            case WebSocket.CLOSING:
                return '연결 종료 중...';
            case WebSocket.CLOSED:
                return '연결 종료됨';
            default:
                return '알 수 없음';
        }
    };

    const getStatusClass = () => {
        if (!websocket) return 'disconnected';
        
        switch (websocket.readyState) {
            case WebSocket.OPEN:
                return 'connected';
            case WebSocket.CONNECTING:
                return 'connecting';
            case WebSocket.CLOSING:
            case WebSocket.CLOSED:
                return 'disconnected';
            default:
                return 'unknown';
        }
    };

    return (
        <div className="websocket-status">
            <h3>🌐 WebSocket 연결 상태</h3>
            
            <div className={`status-indicator ${getStatusClass()}`}>
                {getStatusText()}
            </div>
            
            {websocket && websocket.readyState === WebSocket.OPEN && (
                <div className="connection-details">
                    <p><strong>사용자:</strong> {currentUser?.username}</p>
                    <p><strong>연결 시간:</strong> {new Date().toLocaleTimeString()}</p>
                    <p><strong>핑 상태:</strong> 활성 (30초마다)</p>
                </div>
            )}
            
            {websocket && websocket.readyState === WebSocket.CLOSED && (
                <div className="connection-details">
                    <p><strong>연결 종료됨</strong></p>
                    <p>다시 로그인하여 WebSocket을 재연결하세요.</p>
                </div>
            )}
        </div>
    );
};

export default WebSocketStatus;
