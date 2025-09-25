from flask import Flask
from flask_restx import Api, Resource, fields
from model_runner import run_model, switch_model
from intent_classifier import classify_text, DEFAULT_MODEL_DIR, DEFAULT_TOKENIZER_NAME
import requests

DEFAULT_MODEL_NAME = "distilbert-base-multilingual-cased"


app = Flask(__name__)
api = Api(app, version='1.1', title='반도체 검사 시스템 인터페이스',
          description='LLM 명령 실행 및 Intent 분류')


# LLM 명령 실행 namespace
ns_instruct = api.namespace('instruct', description='LLM 명령 실행')

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
        """사용자 명령어를 입력받아 함수 호출 형식으로 응답"""
        print("Received JSON payload:", api.payload)  # <-- 여기 추가
        user_input = api.payload['text']
        model_name = api.payload.get('model_name', DEFAULT_MODEL_NAME)
        result = run_model(user_input, model_name)

        api_url = f"http://localhost:3000{result['output']}"
        try:
            response = requests.get(api_url)
            # 필요하면 써
        except Exception as err:
            print(err)

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

# llm모델 전환 namespace
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
