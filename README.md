# AWS Serverless Quiz

DynamoDB, Lambda, API Gateway HTTP API, S3 정적 웹사이트 호스팅으로 만든 간단한 공개형 퀴즈 사이트입니다.

회원가입과 로그인은 포함하지 않습니다.

## 구성

```text
브라우저
  ├─ S3 정적 웹사이트: HTML 화면
  └─ API Gateway HTTP API
       └─ Lambda
            └─ DynamoDB
```

## 저장소 구조

```text
aws-serverless-quiz/
├─ README.md
├─ GITHUB_UPLOAD.md
├─ questions.json
├─ load_questions.py
├─ lambda_function.py
├─ iam-policy.json
├─ requirements.txt
├─ LICENSE
├─ web/
│  └─ index.html
└─ scripts/
   ├─ create-table.sh
   ├─ delete-table.sh
   └─ deploy-web.sh
```

## 준비 사항

- AWS 계정
- AWS CLI 또는 AWS CloudShell
- 서울 리전 `ap-northeast-2`
- 로컬에서 적재할 경우 Python 3과 Boto3

AWS CloudShell에는 AWS CLI와 인증 정보가 기본으로 준비되어 있습니다.

## 1. 저장소 내려받기

```bash
git clone https://github.com/YOUR_GITHUB_ID/aws-serverless-quiz.git
cd aws-serverless-quiz
```

GitHub에 올리기 전에는 위 주소의 `YOUR_GITHUB_ID`를 자신의 GitHub ID로 바꿉니다.

## 2. DynamoDB 테이블 만들기

```bash
./scripts/create-table.sh
```

직접 실행하려면 다음 두 명령을 순서대로 실행합니다.

```bash
aws dynamodb create-table \
  --table-name quiz-questions-v2 \
  --attribute-definitions \
    AttributeName=exam,AttributeType=S \
    AttributeName=no,AttributeType=N \
  --key-schema \
    AttributeName=exam,KeyType=HASH \
    AttributeName=no,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region ap-northeast-2
```

```bash
aws dynamodb wait table-exists \
  --table-name quiz-questions-v2 \
  --region ap-northeast-2
```

## 3. 문제 데이터 적재하기

CloudShell에서 실행할 경우 Boto3가 이미 설치되어 있습니다. 로컬에서 실행한다면 먼저 설치합니다.

```bash
python3 -m pip install -r requirements.txt
python3 load_questions.py
```

정상적으로 적재되면 다음과 같이 출력됩니다.

```text
done. 1 items.
```

첫 번째 문항을 직접 확인할 수도 있습니다.

```bash
aws dynamodb get-item \
  --table-name quiz-questions-v2 \
  --key '{"exam":{"S":"SAA-C03"},"no":{"N":"1"}}' \
  --region ap-northeast-2
```

## 4. Lambda 함수 만들기

AWS Lambda 콘솔에서 함수를 생성합니다.

- 함수 이름: `aws-quiz-api`
- 런타임: Python 3.x
- 리전: `ap-northeast-2`
- 핸들러: `lambda_function.handler`

`lambda_function.py`의 내용을 Lambda 코드 편집기에 붙여 넣고 배포합니다.

### 실행 역할 권한

Lambda 실행 역할에는 다음 두 권한이 필요합니다.

1. CloudWatch Logs 기록용 `AWSLambdaBasicExecutionRole`
2. DynamoDB 읽기 권한

`iam-policy.json`에서 `ACCOUNT_ID`를 자신의 AWS 계정 ID로 바꾼 뒤 실행 역할에 인라인 정책으로 추가합니다.

계정 ID는 다음 명령으로 확인할 수 있습니다.

```bash
aws sts get-caller-identity --query Account --output text
```

## 5. API Gateway HTTP API 만들기

API Gateway 콘솔에서 HTTP API를 생성하고 Lambda 함수 `aws-quiz-api`를 연결합니다.

라우트는 두 개만 만듭니다.

```text
GET  /questions
POST /answer
```

Lambda 통합의 payload format은 `2.0`을 사용합니다.

### CORS 설정

HTTP API의 CORS 설정에 다음 값을 입력합니다.

```text
허용 출처: *
허용 메서드: GET, POST, OPTIONS
허용 헤더: content-type
최대 기간: 3600
```

API 생성 후 다음과 같은 호출 주소를 확인합니다.

```text
https://API_ID.execute-api.ap-northeast-2.amazonaws.com
```

## 6. 웹 화면에 API 주소 넣기

`web/index.html`에서 다음 줄을 찾습니다.

```javascript
const API =
  "https://API_ID.execute-api.ap-northeast-2.amazonaws.com";
```

`API_ID`를 실제 API Gateway ID로 바꿉니다.

예를 들어 API 주소가 다음과 같다면,

```text
https://abc123xyz.execute-api.ap-northeast-2.amazonaws.com
```

HTML도 같은 주소로 수정합니다.

```javascript
const API =
  "https://abc123xyz.execute-api.ap-northeast-2.amazonaws.com";
```

## 7. S3 정적 웹사이트로 배포하기

```bash
./scripts/deploy-web.sh
```

스크립트는 다음 작업을 수행합니다.

- 계정 ID를 포함한 고유한 버킷 생성
- S3 정적 웹사이트 호스팅 활성화
- 공개 읽기용 버킷 정책 적용
- `web/index.html` 업로드

마지막에 웹사이트 주소가 출력됩니다.

```text
http://aws-quiz-web-ACCOUNT_ID.s3-website.ap-northeast-2.amazonaws.com
```

S3 정적 웹사이트 엔드포인트는 HTTPS를 지원하지 않습니다. 학습용 또는 간단한 데모 용도로 사용하고, 실제 서비스에서는 CloudFront 또는 Amplify Hosting을 검토하세요.

## 8. API 테스트

### 문제 조회

```bash
curl "https://API_ID.execute-api.ap-northeast-2.amazonaws.com/questions?exam=SAA-C03&count=10"
```

### 정답 제출

```bash
curl -X POST \
  "https://API_ID.execute-api.ap-northeast-2.amazonaws.com/answer" \
  -H "Content-Type: application/json" \
  -d '{"exam":"SAA-C03","no":1,"choice":["A","D"]}'
```

## 9. 문제 추가하기

`questions.json` 배열에 문제를 추가한 뒤 다시 실행합니다.

```bash
python3 load_questions.py
```

같은 `exam`과 `no`를 사용하면 기존 문항이 새 내용으로 교체됩니다.

## 10. 테이블 삭제하기

테이블과 모든 문제 데이터가 함께 삭제됩니다.

```bash
./scripts/delete-table.sh
```

## 비용 및 주의사항

- DynamoDB는 온디맨드 모드입니다.
- Lambda와 API Gateway는 호출량에 따라 과금됩니다.
- S3 정적 웹사이트는 공개 버킷을 사용합니다.
- 로그인 없는 공개 API이므로 반복 호출에 노출될 수 있습니다.
- 학습을 마친 뒤 필요 없는 리소스는 삭제하세요.

## GitHub에 처음 올리기

자세한 화면별 절차는 `GITHUB_UPLOAD.md`를 참고합니다.


GitHub에서 빈 저장소를 만든 뒤 이 디렉터리에서 실행합니다.

```bash
git init
git add .
git commit -m "Initial commit: AWS serverless quiz"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_ID/aws-serverless-quiz.git
git push -u origin main
```

이미 Git 저장소로 내려받은 경우에는 다음만 실행하면 됩니다.

```bash
git add .
git commit -m "Update quiz application"
git push
```

## 라이선스

책이나 교육 자료의 예제 코드라면 저장소 공개 전에 사용할 라이선스를 결정하세요. 별도 라이선스 파일이 없으면 일반적으로 저작권자가 모든 권리를 보유한 상태로 취급됩니다.
