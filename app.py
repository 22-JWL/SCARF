from flask import Flask
from flask_restx import Api, Resource, fields
from flask import request
from model_runner import run_model, switch_model
from intent_classifier import classify_text, DEFAULT_MODEL_DIR, DEFAULT_TOKENIZER_NAME
import requests
import os
import time

DEFAULT_MODEL_NAME = "distilbert-base-multilingual-cased"


app = Flask(__name__)                                                    # Flask 앱 생성
api = Api(app, version='1.2', title='반도체 검사 시스템 인터페이스',       # API 버전 및 제목 설정
          description='LLM 명령 실행 및 Intent 분류 (복합 명령어 지원)')

ns_instruct = api.namespace('instruct', description='LLM 명령 실행')     # 명령 실행 네임스페이스

input_model = api.model('InputModel', {
    'text': fields.String(required=True, description='명령어 텍스트'),
    'model_name': fields.String(required=False, description='사용할 모델명')
})

gpu_model = api.model('GpuModel', {
    'allocated_mb': fields.Float(description='사용된 GPU 메모리'),
    'reserved_mb': fields.Float(description='예약된 GPU 메모리')
})

output_model = api.model('OutputModel', {
    'output': fields.String(description='LLM 응답 함수 호출 결과'),
    'elapsed_time': fields.Float(description='응답 시간(초)'),
    'gpu_memory': fields.Nested(gpu_model)
})


@ns_instruct.route('/')
class Instruct(Resource):
    @ns_instruct.expect(input_model)
    @ns_instruct.marshal_with(output_model)
    def post(self):
        """사용자 명령어를 입력받아 함수 호출 형식으로 응답 (복합 명령어 지원)"""
        
        total_start = time.time()
        
        print("Received JSON payload:", api.payload)
        user_input = api.payload['text']
        model_name = api.payload.get('model_name', DEFAULT_MODEL_NAME)
        current_window_info = api.payload['current_opened_window_and_tab']

        result = run_model(user_input, current_window_info, model_name)
        
        # output에서 "json\n" 제거
        result['output'] = result['output'].replace("json\n", "").replace("json", "").strip()

        # 복합 명령어 처리: 여러 API를 줄바꿈으로 구분
        api_calls = result['output'].strip().split('\n')
        api_calls = [call.strip() for call in api_calls if call.strip() and not call.startswith('#')]
        
        print(f"\n[API Calls Detected] {len(api_calls)} API(s)")
        for idx, api_call in enumerate(api_calls, 1):
            print(f"  {idx}. {api_call}")
        
        # 각 API 순차 실행
        success_count = 0
        failed_apis = []
        
        for api_call in api_calls:
            if api_call == "/NO_FUNCTION":
                print(f"[Skip] {api_call}")
                continue
            
            # API 호출
            api_url = f"http://localhost:3000{api_call}"
            
            try:
                response = requests.get(api_url, timeout=30)  # cpu 사용으로 인한 임시로 30초 타임아웃 설정 (원래 5초)
                if response.status_code == 200:
                    success_count += 1
                    print(f"[Success] {api_call} → {response.status_code}")
                else:
                    failed_apis.append(api_call)
                    print(f"[Failed] {api_call} → {response.status_code}")
            except Exception as err:
                failed_apis.append(api_call)
                print(f"[Error] {api_call} → {err}")
                
            total_end = time.time()
            total_elapsed = total_end - total_start
        
        # 실행 결과 요약
        print(f"\n[Execution Summary]")
        print(f"  Total APIs: {len(api_calls)}")
        print(f"  Success: {success_count}")
        print(f"  Failed: {len(failed_apis)}")
        if failed_apis:
            print(f"  Failed APIs: {failed_apis}")
        print(f"  Total Elapsed Time: {total_elapsed:.3f} seconds")
        print("-" * 50)

        return result


# Intent 분류 namespace
ns_classify = api.namespace('classify', description='문장 intent 분류')

classify_input_model = api.model('ClassifyInput', {
    'text': fields.String(required=True, description='분류할 문장'),
    'model_dir': fields.String(required=False, description='모델 경로')
})

classify_output_model = api.model('ClassifyOutput', {
    'label': fields.String(description='예측된 라벨'),
    'score': fields.Float(description='예측 확률')
})


@ns_classify.route('/')
class Classify(Resource):
    @ns_classify.expect(classify_input_model)
    @ns_classify.marshal_with(classify_output_model)
    def post(self):
        """문장을 분류하고 intent 라벨을 반환합니다."""
        text = api.payload['text']
        model_dir = api.payload.get('model_dir', DEFAULT_MODEL_DIR)
        return classify_text(text, model_dir)


# LLM 모델 전환 namespace
ns_models = api.namespace('models', description='모델 전환/관리')

switch_request = api.model('ModelSwitchRequest', {
    'model_name': fields.String(required=True, description='로드할 모델 이름 (HF Hub 식별자 또는 로컬 경로)'),
})

switch_response = api.model('ModelSwitchResponse', {
    'status': fields.String(description='loaded 또는 reused'),
    'model_name': fields.String(description='현재 로드된 모델명'),
    'hf_device_map': fields.Raw(description='Accelerate가 결정한 장치 매핑(hf_device_map)'),
    'gpu_memory': fields.Nested(api.model('GpuMem', {
        'allocated_mb': fields.Float,
        'reserved_mb': fields.Float,
    })),
})


@ns_models.route('/switch')
class ModelSwitch(Resource):
    @ns_models.expect(switch_request)
    @ns_models.marshal_with(switch_response)
    def post(self):
        """기존 모델을 언로드하고 요청된 model_name으로 새 모델을 로드합니다."""
        payload = api.payload or {}
        new_name = payload.get('model_name')
        result = switch_model(new_name)
        return result


# 서버 실행
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)