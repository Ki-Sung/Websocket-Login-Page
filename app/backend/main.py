from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware             
from fastapi.security import HTTPBearer
import asyncio
import logging
import time
import uuid
import json
from typing import Dict, Set, Optional
from datetime import datetime, timedelta
import redis
import jwt

# 웹소켓에 필요 라이브러리
# fastapi: 웹 프레임워크 -> 웹 서버 구축 및 API 개발
# fastapi.middleware.cors: CORS 설정 -> 다른 도메인에서의 요청 허용(백엔드 - 프론트엔드 통신)
# fastapi.security: 보안 설정 -> 토큰 인증 및 권한 관리
# asyncio: 비동기 프로그래밍 -> 비동기 작업 처리
# redis: Redis 클라이언트 -> Redis 데이터베이스 연결 및 작업 처리

# 로깅 설정 최적화 - 로그 레벨 및 로그 형식 설정 
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 현재 모듈의 로거 생성
logger = logging.getLogger(__name__)

# Redis 연결 설정
redis_client = redis.Redis(
    host='localhost',                   # Redis 서버 주소 
    port=6379,                          # Redis 포트 번호 
    db=0,                               # Redis 데이터베이스 번호 (0-15)
    decode_responses=True,              # 응답을 문자열로 자동 디코딩 
    socket_connect_timeout=5,           # 연결 타임아웃 (5초)
    socket_timeout=5                    # 데이터 전송(소켓) 타임아웃 (5초)
)

# Redis 연결 테스트
try:
    redis_client.ping()                 # Redis 서버에 ping 요청
    logger.info("Redis 연결 성공!")        

except redis.ConnectionError:
    logger.error("Redis 연결 실패! Redis 서버가 실행 중인지 확인하세요.")
    redis_client = None                 # Redis 연결 실패 시 None 설정

# FastAPI 애플리케이션 설정
app = FastAPI(
    title="Redis 기반 중복 로그인 방지 시스템",
    description="WebSocket과 Redis를 활용한 고성능 보안 시스템",
    version="2.0.0"
)

# CORS(Cross-Origin Resource Sharing) 설정 -> 다른 도메인에서의 요청 허용(백엔드 - 프론트엔드 통신)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://192.168.2.55:3000"],     # 허용할 프론트엔드 주소 (도메인)
    allow_credentials=True,             # 쿠키, 인증 헤더 허용 
    allow_methods=["*"],                # 모든 HTTP 메서드(GET, POST, PUT, DELETE 등) 허용
    allow_headers=["*"],                # 모든 헤더 허용
)

# 보안 설정 -> 토큰 인증 및 권한 관리
security = HTTPBearer()

# 사용자 데이터 (실제 프로젝트에서는 데이터베이스 사용)
USERS = {
    "user1": {
        "password": "password1",         # 사용자 비밀번호 
        "name": "사용자1",                # 사용자명 
        "is_admin": True                # 관리자 여부
    },
    "user2": {
        "password": "password2", 
        "name": "사용자2", 
        "is_admin": False
    },
    "user3": {
        "password": "password3", 
        "name": "사용자3", 
        "is_admin": False
    }
}

# Redis 기반 세션 관리자
class RedisSessionManager:
    def __init__(self):
        self.redis = redis_client           # Redis 클라이언트 연결
        self.session_ttl = 3600             # 세션 유효 시간 (1시간 = 3600초)
        self.websocket_ttl = 7200           # WebSocket 연결 유효 시간 (2시간 = 7200초) 
    
    
    async def create_session(self, username: str, session_id: str) -> bool:
        """새 세션 생성"""
        if not self.redis:                  # Redis 연결 확인  
            return False                    # 연결이 없으면 False로 반환 
            
        try:
            # 세션 데이터 생성
            session_data = {                    
                "username": username,           # 사용자명
                "session_id": session_id,       # 세션 ID
                "created_at": time.time(),      # 세션 생성 시간
                "last_activity": time.time()    # 마지막 활동 시간(현재 시간)
            }
            
            # 세션 정보 저장 -> Redis에 세션 데이터 저장 (TTL 1시간)
            self.redis.setex(
                f"session:{session_id}",        # 세션 ID를 키로 사용
                self.session_ttl,               # 세션 유효 시간 (1시간 = 3600초)
                json.dumps(session_data)        # 세션 데이터를 JSON 형식으로 변환 후 저장
            )
            
            # 사용자별 세션 ID 매핑
            self.redis.setex(
                f"user_session:{username}",     # 사용자명을 키로 사용
                self.session_ttl,               # 세션 유효 시간 (1시간 = 3600초)
                session_id                      # 세션 ID 저장
            )
            
            # 활성 세션 목록에 사용자 추가 (set 구조)
            self.redis.sadd("active_sessions", username)
            
            logger.info(f"사용자 {username} 세션 생성: {session_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"세션 생성 실패: {e}")
            return False
    
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """세션 정보 조회"""
        if not self.redis:
            return None
            
        try:
            session_data = self.redis.get(f"session:{session_id}")    # Redis에서 세션 데이터 조회 
            
            if session_data:
                return json.loads(session_data)    # JSON 형식으로 변환 후 반환     
            
            return None                            # 세션 데이터가 없으면 None 반환
        
        except Exception as e:
            logger.error(f"세션 조회 실패: {e}")
            return None
    
    
    async def update_session_activity(self, session_id: str) -> bool:
        """세션 활동 시간 업데이트"""
        if not self.redis:
            return False
            
        try:
            session_data = self.redis.get(f"session:{session_id}")    # 기존 세션 데이터 조회
            
            if session_data:
                data = json.loads(session_data)        # JSON 형식으로 변환 후 반환
                data["last_activity"] = time.time()    # 마지막 활동 시간 업데이트
                
                # 세션 데이터 업데이트 -> Redis에 세션 데이터 저장 (TTL 1시간)
                self.redis.setex(
                    f"session:{session_id}",        # 세션 ID를 키로 사용
                    self.session_ttl,               # 세션 유효 시간 (1시간 = 3600초)   
                    json.dumps(data)                # 세션 데이터를 JSON 형식으로 변환 후 저장
                )
                return True                         # 세션 데이터 업데이트 성공 시 True 반환
            
            return False                            # 세션 데이터가 없으면 False 반환
        
        except Exception as e:
            logger.error(f"세션 활동 업데이트 실패: {e}")
            return False
    
    
    async def remove_session(self, username: str) -> bool:
        """세션 제거"""
        if not self.redis:
            return False
            
        try:
            session_id = self.redis.get(f"user_session:{username}")     # 사용자의 세션 ID 조회
            
            if session_id:
                # 세션 정보 삭제 -> Redis에서 세션 데이터 삭제
                self.redis.delete(f"session:{session_id}")
                # 사용자 세션 매핑 삭제 -> Redis에서 사용자의 세션 ID 삭제
                self.redis.delete(f"user_session:{username}")
                # 활성 세션 목록에서 제거 -> Redis에서 사용자 제거 (set 구조)
                self.redis.srem("active_sessions", username)
                
                logger.info(f"사용자 {username} 세션 제거")
                return True                         # 세션 제거 성공 시 True 반환
            
            return False                            # 세션 ID가 없으면 False 반환
        
        except Exception as e:
            logger.error(f"세션 제거 실패: {e}")
            return False
    
    
    async def is_user_active(self, username: str) -> bool:
        """사용자 활성 상태 확인"""
        if not self.redis:
            return False
            
        try:
            return self.redis.exists(f"user_session:{username}") > 0    # 사용자의 세션 ID가 존재하는지 확인 - ID가 존재하면 True 반환
            
        except Exception as e:
            logger.error(f"사용자 활성 상태 확인 실패: {e}")
            return False
    
    
    async def get_active_sessions(self) -> list:
        """활성 세션 목록 조회"""
        if not self.redis:                          # Redis 연결 확인
            return []                               # 연결이 없으면 빈 리스트 반환
            
        try:
            active_users = list(self.redis.smembers("active_sessions"))    # 활성 세션 목록 조회 (set 구조)
            return active_users                     # 활성 세션 목록 반환
        
        except Exception as e:
            logger.error(f"활성 세션 목록 조회 실패: {e}")
            return []
    
    async def cleanup_expired_sessions(self) -> int:
        """만료된 세션 정리"""
        if not self.redis:                          # Redis 연결 확인
            return 0                                # 연결이 없으면 0 반환
            
        try:
            cleaned_count = 0                        # 정리된 세션 수 초기화
            current_time = time.time()               # 현재 시간 저장
            
            # 모든 활성 세션 확인
            active_users = list(self.redis.smembers("active_sessions"))         # 활성 세션 목록 조회 (set 구조)
            
            for username in active_users:
                session_id = self.redis.get(f"user_session:{username}")         # 사용자의 세션 ID 조회
                
                if session_id:
                    session_data = self.redis.get(f"session:{session_id}")      # 세션 데이터 조회
                    
                    if session_data:
                        data = json.loads(session_data)                         # JSON 형식으로 변환 후 반환
                        
                        if current_time - data["last_activity"] > self.session_ttl:    # 마지막 활동 시간이 세션 유효 시간을 초과한 경우
                            await self.remove_session(username)                        # 세션 제거
                            cleaned_count += 1                                         # 정리된 세션 수 증가
            
            logger.info(f"만료된 세션 {cleaned_count}개 정리 완료")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"세션 정리 실패: {e}")
            return 0

# Redis 세션 매니저 인스턴스
session_manager = RedisSessionManager()

# 최적화된 WebSocket 관리자
class OptimizedWebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}                 # 사용자별 Websocket 연결 관리 
        self.connection_timestamps: Dict[str, float] = {}                       # 연결 시간 기록 
        self.last_cleanup = time.time()                                         # 마지막 정리 시간
        self.cleanup_interval = 300                                             # 5분 마다 정리
        self.max_connections_per_user = 3                                       # 사용자당 최대 연결 수
    
    
    async def connect(self, websocket: WebSocket, user_id: str) -> bool:
        """WebSocket 연결 관리"""
        if user_id not in self.active_connections:               # 사용자별 연결 관리 딕셔너리에 사용자 ID가 없으면 빈 set 생성
            self.active_connections[user_id] = set()             # 사용자 ID를 키로 사용하여 빈 set 생성
        
        # 연결 수 제한 확인
        if len(self.active_connections[user_id]) >= self.max_connections_per_user:  # 사용자별 연결 수가 최대 연결 수를 초과한 경우
            logger.warning(f"사용자 {user_id}의 연결 수 제한 도달")
            
            return False    # False 반환
        
        self.active_connections[user_id].add(websocket)         # 사용자별 연결 관리 딕셔너리에 연결 추가
        self.connection_timestamps[user_id] = time.time()       # 연결 시간 기록 딕셔너리에 연결 시간 추가
        
        # Redis에 WebSocket 연결 정보 저장
        if redis_client:                                        # Redis 연결 확인
            try:
                # WebSocket 연결 정보 생성
                connection_data = {
                    "user_id": user_id,                         # 사용자 ID
                    "connected_at": time.time(),                # 연결 시간
                    "websocket_count": len(self.active_connections[user_id])    # 사용자별 연결 수
                }
                
                # Redis에 WebSocket 연결 정보 저장 -> Redis에 연결 정보 저장 (TTL 2시간)
                redis_client.setex(
                    f"websocket:{user_id}:{id(websocket)}",     # 연결 정보 키 생성
                    session_manager.websocket_ttl,              # WebSocket 연결 유효 시간 (2시간 = 7200초)
                    json.dumps(connection_data)                 # 연결 정보를 JSON 형식으로 변환 후 저장
                )
                
            except Exception as e:
                logger.error(f"WebSocket 연결 정보 Redis 저장 실패: {e}")
        
        # 정기적인 정리 작업
        await self._cleanup_old_connections()
        
        logger.info(f"사용자 {user_id} WebSocket 연결 추가 (총 {len(self.active_connections[user_id])}개)")
        
        return True
    
    
    async def disconnect(self, websocket: WebSocket, user_id: str):
        """WebSocket 연결 해제"""
        if user_id in self.active_connections:                      # 사용자별 연결 관리 딕셔너리에 사용자 ID가 존재하는지 확인
            self.active_connections[user_id].discard(websocket)     # 사용자별 연결 관리 딕셔너리에서 연결 제거
            
            # Redis에서 연결 정보 제거
            if redis_client:
                try:
                    redis_client.delete(f"websocket:{user_id}:{id(websocket)}")    # Redis에서 연결 정보 삭제
                
                except Exception as e:
                    logger.error(f"WebSocket 연결 정보 Redis 제거 실패: {e}")
            
            # 사용자별 연결 관리 딕셔너리에 사용자 ID가 존재하지 않으면 딕셔너리에서 삭제
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]        # 사용자별 연결 관리 딕셔너리에서 사용자 ID 삭제
                del self.connection_timestamps[user_id]     # 연결 시간 기록 딕셔너리에서 사용자 ID 삭제
                
                logger.info(f"사용자 {user_id}의 모든 WebSocket 연결 해제")
                
            else:
                logger.info(f"사용자 {user_id} WebSocket 연결 해제 (남은 연결: {len(self.active_connections[user_id])}개)")
    
    
    async def send_personal_message(self, message: dict, user_id: str) -> int:
        """특정 사용자에게 메시지 전송"""
        if user_id not in self.active_connections:            # 사용자별 연결 관리 딕셔너리에 사용자 ID가 존재하는지 확인
            return 0                                          # 연결이 없으면 0 반환
        
        sent_count = 0                                        # 전송된 메시지 수 초기화
        disconnected = set()                                  # 끊어진 연결 정보 저장 (set 구조)
        
        for websocket in self.active_connections[user_id]:    # 사용자별 연결 관리 딕셔너리에서 연결 정보 조회
            try:
                await websocket.send_json(message)            # 메시지 전송
                sent_count += 1                               # 전송된 메시지 수 증가
                
            except Exception as e:
                logger.error(f"메시지 전송 실패: {e}")
                
                disconnected.add(websocket)                   # 끊어진 연결 정보 추가 (set 구조)    
        
        # 끊어진 연결 정리
        for websocket in disconnected:
            await self.disconnect(websocket, user_id)         # 끊어진 연결 정보 제거 (disconnect 메서드 호출)
        
        logger.info(f"사용자 {user_id}에게 메시지 전송 완료 ({sent_count}개 연결)")
        
        return sent_count    # 전송된 메시지 수 반환
    
    
    async def force_disconnect_user(self, user_id: str) -> int:
        """사용자의 모든 WebSocket 연결 강제 종료"""
        if user_id not in self.active_connections:            # 사용자별 연결 관리 딕셔너리에 사용자 ID가 존재하는지 확인
            return 0                                          # 연결이 없으면 0 반환
        
        disconnected_count = 0                                # 끊어진 연결 수 초기화
        websockets_to_disconnect = list(self.active_connections[user_id])    # 사용자별 연결 관리 딕셔너리에서 연결 정보 조회
        
        for websocket in websockets_to_disconnect:            # 사용자별 연결 관리 딕셔너리에서 연결 정보 조회
            try:
                await websocket.close(code=1000, reason="Force disconnect")   # 연결 해제
                disconnected_count += 1                                       # 끊어진 연결 수 증가
                
            except Exception as e:
                logger.error(f"강제 연결 해제 실패: {e}")
        
        # 연결 정보 정리
        if user_id in self.active_connections:
            del self.active_connections[user_id]        # 사용자별 연결 관리 딕셔너리에서 사용자 ID 삭제
            
        if user_id in self.connection_timestamps:
            del self.connection_timestamps[user_id]     # 연결 시간 기록 딕셔너리에서 사용자 ID 삭제
        
        logger.info(f"사용자 {user_id} 강제 연결 해제 완료 ({disconnected_count}개)")
        
        return disconnected_count       # 끊어진 연결 수 반환
    
    
    async def _cleanup_old_connections(self):
        """오래된 연결 정리"""
        current_time = time.time()                                      # 현재 시간 저장
        if current_time - self.last_cleanup > self.cleanup_interval:    # 마지막 정리 시간이 정리 간격을 초과한 경우
            cutoff_time = current_time - 600                            # 10분 이상 비활성인 연결 정리
            users_to_remove = []                                        # 제거할 사용자 ID 저장 (list 구조)
            
            for user_id, timestamp in self.connection_timestamps.items():    # 연결 시간 기록 딕셔너리에서 연결 시간 조회
                if timestamp < cutoff_time:                                  # 연결 시간이 10분 이상 비활성인 경우
                    users_to_remove.append(user_id)                          # 제거할 사용자 ID 추가 (list 구조)
            
            for user_id in users_to_remove:                                  # 제거할 사용자 ID 조회
                await self.force_disconnect_user(user_id)                    # 사용자의 모든 WebSocket 연결 강제 종료
            
            self.last_cleanup = current_time                                 # 마지막 정리 시간 업데이트
            
            if users_to_remove:                                              # 제거할 사용자 ID가 있는 경우
                logger.info(f"정리된 비활성 연결: {len(users_to_remove)}개")

# WebSocket 매니저 인스턴스
websocket_manager = OptimizedWebSocketManager()

# JWT 토큰 관리 (간소화)
SECRET_KEY = "your-secret-key-here"                                   # JWT 서명용 비밀키 (실제로는 환경 변수 사용)
ALGORITHM = "HS256"                                                   # JWT 서명 알고리즘 


def create_access_token(username: str, session_id: str) -> str:
    """JWT 토큰 생성 (실제 프로젝트에서는 더 안전한 방식 사용)"""
    payload = {
        "sub": username,                                # 사용자 ID
        "session_id": session_id,                       # 세션 ID
        "exp": datetime.utcnow() + timedelta(hours=1)   # 토큰 만료 시간 (1시간)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)    # JWT 토큰 생성


def verify_token(token: str) -> dict:
    """JWT 토큰 검증"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])    # JWT 토큰 검증 - 토큰 디코딩
        
        return payload
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")      # 토큰 만료 시 예외 발생
    
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")      # 토큰 검증 실패 시 예외 발생


# API 엔드포인트
# 루트 엔드포인트 - 서버 상태 확인
@app.get("/")
async def root():
    """서버 상태 확인"""
    return {
        "message": "Redis 기반 중복 로그인 방지 시스템",
        "version": "2.0.0",
        "status": "running",
        "redis_status": "connected" if redis_client else "disconnected"    # Redis 연결 상태 확인
    }


# 상태 확인 엔드포인트 - 서버 상태 확인
@app.get("/api/health")
async def health_check():
    """서버 상태 확인"""
    redis_status = "connected" if redis_client and redis_client.ping() else "disconnected"    # Redis 연결 상태 확인
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),                             # 현재 시간 포맷팅   
        "redis": redis_status,                                               # Redis 연결 상태 확인
        "active_connections": sum(len(conns) for conns in websocket_manager.active_connections.values()),    # 활성 연결 수 조회
        "active_sessions": len(await session_manager.get_active_sessions())    # 활성 세션 수 조회
    }


# 로그인 엔드포인트 - 사용자 로그인
@app.post("/api/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """사용자 로그인"""
    # 1. 사용자 검증
    if username not in USERS:                                                   # 사용자 id 존재 여부 
        raise HTTPException(status_code=401, detail="사용자명이 존재하지 않습니다.")
    
    if USERS[username]["password"] != password:                                 # 사용자 비밀번호 일치 여부 확인
        raise HTTPException(status_code=401, detail="비밀번호가 올바르지 않습니다.")
    
    # 2. 중복 로그인 감지 및 처리
    if await session_manager.is_user_active(username):                          # 사용자 활성 상태 확인
        logger.info(f"사용자 {username} 중복 로그인 감지 - 기존 세션 종료")
        
        # 기존 세션에 강제 로그아웃 메시지 전송
        await websocket_manager.send_personal_message(
            {
                "type": "force_logout",                                      # 강제 로그아웃 메시지 타입
                "message": "다른 곳에서 로그인되어 자동으로 로그아웃됩니다.",            # 강제 로그아웃 메시지
                "timestamp": time.time()                                     # 현재 시간 포맷팅
            },
            username
        )
        
        # 기존 WebSocket 연결 강제 종료
        await websocket_manager.force_disconnect_user(username)
        
        # 기존 세션 제거
        await session_manager.remove_session(username)
    
    # 3. 새 세션 생성
    session_id = str(uuid.uuid4())                                                  # 세션 ID 생성
    session_created = await session_manager.create_session(username, session_id)    # 세션 생성
    
    if not session_created:                                                         # 세션 생성 실패 시 예외 발생
        raise HTTPException(status_code=500, detail="Session creation failed")      # 세션 생성 실패 시 예외 발생
    
    # 4. JWT 토큰 생성 및 반환
    access_token = create_access_token(username, session_id)                         # JWT 토큰 생성
    
    logger.info(f"사용자 {username} 로그인 성공 - 세션 {session_id}")
    
    # 4. 로그인 성공 시 응답 반환
    return {
        "access_token": access_token,                   # 액세스 토큰 - JWT 토큰 
        "user": {                                       # 사용자 정보 
            "username": username,                             # 사용자 ID
            "name": USERS[username]["name"],                  # 사용자 이름 
            "is_admin": USERS[username]["is_admin"]           # 관리자 여부
        },
        "session_id": session_id                        # 세션 ID
    }


# 로그아웃 엔드포인트 - 사용자 로그아웃
@app.post("/api/auth/logout")
async def logout(username: str = Form(...)):
    """사용자 로그아웃"""
    try:
        # WebSocket 연결 해제
        await websocket_manager.force_disconnect_user(username)
        
        # 세션 제거
        await session_manager.remove_session(username)
        
        logger.info(f"사용자 {username} 로그아웃 완료")
        return {"message": "Logout successful"}
        
    except Exception as e:
        logger.error(f"로그아웃 실패: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")


# 활성 세션 목록 조회 엔드포인트 - 활성 세션 목록 조회 (Redis 캐싱 최적화)
@app.get("/api/auth/active-sessions")
async def get_active_sessions():
    """활성 세션 목록 조회 (Redis 캐싱 최적화)"""
    try:
        # Redis에서 캐시된 결과 확인
        cache_key = "cached_active_sessions"
        cached_result = redis_client.get(cache_key) if redis_client else None
        
        if cached_result:
            # 캐시된 결과 반환 (5초간 유효)
            return json.loads(cached_result)
        
        # 캐시가 없으면 새로 조회
        active_sessions = await session_manager.get_active_sessions()
        
        # 세션 상세 정보 조회
        session_details = []
        for username in active_sessions:
            session_id = redis_client.get(f"user_session:{username}") if redis_client else None
            if session_id:
                session_data = await session_manager.get_session(session_id)
                if session_data:
                    session_details.append({
                        "username": username,
                        "session_id": session_id,
                        "connected_at": session_data.get("created_at"),
                        "last_activity": session_data.get("last_activity"),
                        "websocket_count": len(websocket_manager.active_connections.get(username, set()))
                    })
        
        # 결과 반환
        result = {
            "sessions": session_details,
            "count": len(session_details),
            "timestamp": time.time()
        }
        
        # 결과를 Redis에 캐싱 (5초간)
        if redis_client:
            redis_client.setex(cache_key, 5, json.dumps(result))
        
        return result
        
    except Exception as e:
        logger.error(f"활성 세션 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch active sessions")


# 사용자 목록 조회 엔드포인트 - 사용자 목록 조회
@app.get("/api/users")
async def get_users():
    """사용자 목록 조회"""
    return {
        "users": [
            {
                "username": username,
                "name": user_data["name"],
                "is_admin": user_data["is_admin"],
                "is_active": await session_manager.is_user_active(username)
            }
            for username, user_data in USERS.items()
        ]
    }

# WebSocket 엔드포인트
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket 연결 처리"""
    # 1. 토큰 추출 및 검증
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Token missing")
        return
    
    try:
        # 토큰 검증
        payload = verify_token(token)
    
    except HTTPException:
        await websocket.close(code=4003, reason="Token validation failed")
        return
    
    # 2. 사용자 ID 일치 확인
    if payload.get("sub") != user_id:
        await websocket.close(code=4002, reason="User ID mismatch")
        return
    
    # 3. 연결 수락 및 관리
    await websocket.accept()
    connection_success = await websocket_manager.connect(websocket, user_id)
    
    # 연결 수락 실패 시 예외 발생
    if not connection_success:
        await websocket.close(code=4004, reason="Connection limit exceeded")
        return
    
    # 4. 연결 성공 메시지 전송
    await websocket.send_json({
        "type": "connection_established",
        "message": "WebSocket 연결이 성공적으로 설정되었습니다.",
        "timestamp": time.time()
    })
    
    try:
        # 5. 메시지 수신 대기 (타임아웃 설정)
        while True:
            data = await asyncio.wait_for(
                websocket.receive_text(), 
                timeout=300.0  # 5분 타임아웃
            )
            
            # ping/pong 처리 (로그 최소화) -> 클라이언트와의 연결 상태 확인
            if data == "ping":                                # ping 메시지 수신시
                await websocket.send_text("pong")             # pong 응답 전송
            elif data == "heartbeat":                         # heartbeat 메시지 수신시
                await websocket.send_text("heartbeat_ack")    # heartbeat_ack 응답 전송
                
                session_id = payload.get("session_id")        # 세션 ID 조회
                
                if session_id:
                    await session_manager.update_session_activity(session_id)    # 세션 활동 시간 업데이트
            else:
                # 기타 메시지 처리
                logger.info(f"사용자 {user_id}로부터 메시지 수신: {data}")
                
    except asyncio.TimeoutError:    # 타임아웃 예외 발생 시
        logger.info(f"사용자 {user_id} WebSocket 타임아웃")
        await websocket.close(code=1000, reason="Timeout")    # 연결 해제
    
    except WebSocketDisconnect:    # WebSocket 연결 해제 예외 발생 시
        logger.info(f"사용자 {user_id} WebSocket 연결 해제")
    
    except Exception as e:          # 예외 발생 시
        logger.error(f"WebSocket 오류: {e}")
        await websocket.close(code=1011, reason="Internal error")    # 연결 해제
    
    finally:
        await websocket_manager.disconnect(websocket, user_id)    # WebSocket 연결 해제


# 정기적인 세션 정리 작업 - 만료된 세션 정리
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    logger.info("Redis 기반 중복 로그인 방지 시스템 시작")
    
    # Redis 연결 상태 확인
    if redis_client and redis_client.ping():
        logger.info("Redis 연결 성공")
    else:
        logger.warning("Redis 연결 실패 - 메모리 기반으로 동작")

# 백그라운드 작업: 만료된 세션 정리
async def cleanup_expired_sessions_task():
    """만료된 세션 정리 작업"""
    while True:
        try:
            await asyncio.sleep(300)  # 5분마다 실행
            cleaned_count = await session_manager.cleanup_expired_sessions()    # 만료된 세션 정리
            
            if cleaned_count > 0:    # 만료된 세션이 있는 경우
                logger.info(f"백그라운드에서 {cleaned_count}개 만료 세션 정리 완료")    # 만료된 세션 정리 완료 로그 출력
        
        except Exception as e:
            logger.error(f"백그라운드 세션 정리 실패: {e}")

# 백그라운드 작업 시작
@app.on_event("startup")
async def start_background_tasks():
    """백그라운드 작업 시작"""
    asyncio.create_task(cleanup_expired_sessions_task())


# 메인 함수 - 서버 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
