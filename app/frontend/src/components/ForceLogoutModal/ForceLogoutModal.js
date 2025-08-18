import React from 'react';
import './ForceLogoutModal.css';

const ForceLogoutModal = ({ data, onConfirm, onClose }) => {
    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <div className="modal-header">
                    <h3>⚠️ 중복 로그인 감지</h3>
                </div>
                
                <div className="modal-body">
                    <p className="warning-message">
                        {data.message || '다른 곳에서 로그인되어 자동으로 로그아웃됩니다.'}
                    </p>
                    
                    {data.reason && (
                        <p className="reason">
                            <strong>사유:</strong> {data.reason}
                        </p>
                    )}
                    
                    {data.timestamp && (
                        <p className="timestamp">
                            <strong>발생 시간:</strong> {new Date(data.timestamp).toLocaleString()}
                        </p>
                    )}
                    
                    {data.new_device && (
                        <p className="new-device">
                            <strong>새 로그인 장치:</strong> {data.new_device}
                        </p>
                    )}
                </div>
                
                <div className="modal-footer">
                    <button 
                        className="confirm-button"
                        onClick={onConfirm}
                    >
                        확인 및 로그아웃
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ForceLogoutModal;
