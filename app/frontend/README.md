# WebSocket 중복 로그인 테스트 - React 프론트엔드

## 🚀 실행 방법

### 1. 의존성 설치
```bash
cd app/frontend-react
npm install
```

### 2. 개발 서버 실행
```bash
npm start
```

프론트엔드가 `http://localhost:3000`에서 실행됩니다.

### 3. 프로덕션 빌드
```bash
npm run build
```

빌드된 파일은 `build/` 폴더에 생성됩니다.

## 🔗 API 서버 연결

프론트엔드는 `http://localhost:8000`의 백엔드 API 서버와 연결됩니다.

**중요**: 백엔드 서버를 먼저 실행해야 합니다!

```bash
# 백엔드 서버 실행 (다른 터미널에서)
cd app/backend
python main.py
```

## 🧪 테스트 방법

1. **백엔드 서버 실행** (포트 8000)
2. **프론트엔드 실행** (포트 3000)
3. **브라우저에서 접속**: `http://localhost:3000`
4. **테스트 계정으로 로그인**:
   - user1 / password1 (관리자)
   - user2 / password2 (일반사용자)
   - user3 / password3 (일반사용자)

## 🔄 중복 로그인 테스트

1. **첫 번째 브라우저**: 사용자1로 로그인
2. **두 번째 브라우저**: 같은 사용자1로 로그인
3. **첫 번째 브라우저**: 강제 로그아웃 모달 표시
4. **"확인 및 로그아웃" 버튼 클릭**: 강제 로그아웃 실행

## 📁 프로젝트 구조

```
frontend-react/
├── src/
│   ├── components/
│   │   ├── LoginForm.js          # 로그인 폼
│   │   ├── UserDashboard.js      # 사용자 대시보드
│   │   ├── WebSocketStatus.js    # WebSocket 상태
│   │   └── ForceLogoutModal.js   # 강제 로그아웃 모달
│   ├── App.js                    # 메인 앱 컴포넌트
│   ├── App.css                   # 메인 스타일
│   └── index.js                  # 진입점
├── package.json                  # 의존성 및 스크립트
└── README.md                     # 이 파일
```

## 🌐 다른 PC에서 테스트

### 프론트엔드 접속
```
http://[현재PC_IP주소]:3000
```

### 백엔드 API 접속
```
http://[현재PC_IP주소]:8000
```

## 🛠️ 개발 도구

- **React 18**: 최신 React 기능 사용
- **CSS Grid/Flexbox**: 반응형 레이아웃
- **WebSocket API**: 실시간 통신
- **Fetch API**: HTTP 요청

## 📱 반응형 디자인

모바일, 태블릿, 데스크톱 모든 기기에서 최적화된 UI를 제공합니다.
