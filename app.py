from flask import Flask
from flask_restx import Api, Resource, fields
from flask import request
from model_runner import run_model, switch_model
from intent_classifier import classify_text, DEFAULT_MODEL_DIR, DEFAULT_TOKENIZER_NAME
import requests
import json # Added json import

DEFAULT_MODEL_NAME = "distilbert-base-multilingual-cased"


app = Flask(__name__)
api = Api(app, version='1.1', title='반도체 검사 시스템 인터페이스',
          description='LLM 명령 실행 및 Intent 분류')


# LLM 명령 실행 namespace
ns_instruct = api.namespace('instruct', description='LLM 명령 실행')

input_model = api.model('InputModel', {
    'text': fields.String(required=True, description='명령어 텍스트'),
    'model_name': fields.String(required=False, description='사용할 모델명'),
    'current_opened_window_and_tab': fields.String(required=False, description='현재 열려있는 창 및 탭 정보') # Added this field to input_model
})

gpu_model = api.model('GpuModel', {
    'allocated_mb': fields.Float(description='사용된 GPU 메모리'),
    'reserved_mb': fields.Float(description='예약된 GPU 메모리')
})

output_model = api.model('OutputModel', {
    'output': fields.String(description='LLM 응답 함수 호출 결과 또는 사용자에게 되물을 질문'), # Updated description
    'elapsed_time': fields.Float(description='응답 시간(초)'),
    'gpu_memory': fields.Nested(gpu_model)
})



@ns_instruct.route('/')
class Instruct(Resource):
    @ns_instruct.expect(input_model)
    @ns_instruct.marshal_with(output_model)
    def post(self):
        """사용자 명령어를 입력받아 함수 호출 형식으로 응답 또는 추가 질문""" # Updated description
        print("Received JSON payload:", api.payload)
        user_input = api.payload['text']
        model_name = api.payload.get('model_name', DEFAULT_MODEL_NAME)
        current_window_info = api.payload.get('current_opened_window_and_tab', '') # Safely get current_window_info

        result = run_model(user_input, current_window_info, model_name)
        
        # LLM 응답을 JSON으로 파싱
        try:
            llm_response = json.loads(result['output'].replace("json\n", "").strip())
        except json.JSONDecodeError:
            # JSON 파싱 실패 시, 기존의 문자열 응답을 그대로 사용 (fallback)
            llm_response = {"status": "error", "message": "LLM response was not valid JSON", "output": result['output']}

        if llm_response.get("status") == "api_found":
            api_path = llm_response.get("api")
            if api_path:
                # 클라이언트 IP 주소 가져오기 (주석 처리된 부분은 그대로 유지)
                # client_ip = request.remote_addr
                
                # 클라이언트 IP로 API 주소를 만듦 (주석 처리된 부분은 그대로 유지)
                # api_url = f"http://{client_ip}:3000{api_path}"
                
                #local에서..
                api_url = f"http://localhost:3000{api_path}"
                
                try:
                    response = requests.get(api_url)
                    # 필요하면 써
                    # result['output'] = response.text # Optionally update output with actual API response
                except Exception as err:
                    print(f"Error calling external API: {err}")
                    result['output'] = f"Error calling external API: {err}"
                else:
                    result['output'] = api_path # Return the API path if successful
            else:
                result['output'] = "Error: API path not found in LLM response."
        elif llm_response.get("status") == "clarification_needed":
            result['output'] = llm_response.get("question", "Clarification needed, but no question provided.")
        else:
            # Fallback for unexpected status or error
            result['output'] = llm_response.get("output", "Unexpected LLM response format.")
            if "message" in llm_response:
                result['output'] = f"Error: {llm_response['message']} - Original output: {result['output']}"

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
