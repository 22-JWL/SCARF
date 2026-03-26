from flask import Flask
from flask_restx import Api, Resource, fields
from flask import request
from model_runner import run_model, switch_model
from intent_classifier import classify_text, DEFAULT_MODEL_DIR, DEFAULT_TOKENIZER_NAME
import requests
import os
import time
from whitelist_filter import create_url_whitelist #whitelist
import rag_pipeline

DEFAULT_MODEL_NAME = "distilbert-base-multilingual-cased"


app = Flask(__name__)                                                    # Flask 앱 생성
api = Api(app, version='1.2', title='반도체 검사 시스템 인터페이스',       # API 버전 및 제목 설정
          description='LLM 명령 실행 및 Intent 분류 (복합 명령어 지원)')

ns_instruct = api.namespace('instruct', description='LLM 명령 실행')     # 명령 실행 네임스페이스

input_model = api.model('InputModel', {
    'text': fields.String(required=False, description='명령어 텍스트 (새 명령 시 필수)'),
    'model_name': fields.String(required=False, description='사용할 모델명'),
    'session_id': fields.String(required=False, description='슬롯 필링 세션 ID (후속 답변 시 사용)'),
    'answer': fields.String(required=False, description='슬롯 필링 후속 답변 (session_id 와 함께 사용)'),
})

gpu_model = api.model('GpuModel', {
    'allocated_mb': fields.Float(description='사용된 GPU 메모리'),
    'reserved_mb': fields.Float(description='예약된 GPU 메모리')
})

output_model = api.model('OutputModel', {
    'output': fields.String(description='LLM 응답 / 실행된 API URL / 슬롯 필링 질문'),
    'elapsed_time': fields.Float(description='응답 시간(초)'),
    'gpu_memory': fields.Nested(gpu_model),
    'status': fields.String(description='처리 상태: complete | need_info | error'),
    'session_id': fields.String(description='슬롯 필링 세션 ID (need_info 시 반환)'),
    'intent': fields.String(description='분류된 인텐트'),
})

# whitelist url 생성
file_path = r"whitelist_getURL.py"
is_valid_api_safe = create_url_whitelist(file_path)

@ns_instruct.route('/')
class Instruct(Resource):
    @ns_instruct.expect(input_model)
    @ns_instruct.marshal_with(output_model)
    def post(self):
        """사용자 명령어를 입력받아 함수 호출 형식으로 응답.

        신규 명령: text 필드를 포함해서 전송.
        슬롯 필링 후속 답변: session_id + answer 필드를 포함해서 전송.
        """
        total_start = time.time()
        print("Received JSON payload:", api.payload)

        model_name          = api.payload.get('model_name', DEFAULT_MODEL_NAME)
        current_window_info = api.payload.get('current_opened_window_and_tab', {})
        session_id          = api.payload.get('session_id')
        answer              = api.payload.get('answer')

        def _gpu_mem():
            from model_runner import get_gpu_memory
            alloc, resv = get_gpu_memory()
            return {"allocated_mb": alloc, "reserved_mb": resv}

        # ── 슬롯 필링 후속 답변 처리 ─────────────────────────────────────────
        if session_id and answer is not None:
            print(f"[RAG] 슬롯 필링 계속: session_id={session_id}, answer={answer}")
            rag_result = rag_pipeline.continue_session(session_id, answer)

            total_elapsed = round(time.time() - total_start, 5)

            if rag_result["status"] == "need_info":
                # 다음 질문을 클라이언트에게 반환
                print(f"[RAG] 다음 질문: {rag_result['output']}")
                return {
                    "output":       rag_result["output"],
                    "status":       "need_info",
                    "session_id":   rag_result["session_id"],
                    "intent":       rag_result.get("intent", ""),
                    "elapsed_time": total_elapsed,
                    "gpu_memory":   _gpu_mem(),
                }

            if rag_result["status"] == "complete":
                api_url_path = rag_result["output"]
                print(f"[RAG] 슬롯 필링 완료, API 실행: {api_url_path}")
                _execute_api_calls([api_url_path], current_window_info, model_name)
                return {
                    "output":       api_url_path,
                    "status":       "complete",
                    "intent":       rag_result.get("intent", ""),
                    "elapsed_time": total_elapsed,
                    "gpu_memory":   _gpu_mem(),
                }

            # error
            return {
                "output":       rag_result["output"],
                "status":       "error",
                "elapsed_time": total_elapsed,
                "gpu_memory":   _gpu_mem(),
            }

        # ── 신규 명령 처리 ────────────────────────────────────────────────────
        user_input = api.payload.get('text', '')
        if not user_input:
            return {
                "output":       "text 또는 (session_id + answer) 중 하나를 제공해야 합니다.",
                "status":       "error",
                "elapsed_time": 0.0,
                "gpu_memory":   _gpu_mem(),
            }

        print(f"[RAG] 신규 명령 처리: {user_input}")
        rag_result = rag_pipeline.process_new_query(user_input)
        print(f"[RAG] 파이프라인 결과: status={rag_result['status']}")

        # 3a. 모호 → 슬롯 필링 질문 반환
        if rag_result["status"] == "need_info":
            total_elapsed = round(time.time() - total_start, 5)
            print(f"[RAG] 슬롯 필링 시작, 첫 질문: {rag_result['output']}")
            return {
                "output":       rag_result["output"],
                "status":       "need_info",
                "session_id":   rag_result["session_id"],
                "intent":       rag_result.get("intent", ""),
                "elapsed_time": total_elapsed,
                "gpu_memory":   _gpu_mem(),
            }

        # 3b. 슬롯이 첫 발화에서 이미 완성된 경우
        if rag_result["status"] == "complete":
            api_url_path = rag_result["output"]
            print(f"[RAG] 즉시 완성, API 실행: {api_url_path}")
            _execute_api_calls([api_url_path], current_window_info, model_name)
            total_elapsed = round(time.time() - total_start, 5)
            return {
                "output":       api_url_path,
                "status":       "complete",
                "intent":       rag_result.get("intent", ""),
                "elapsed_time": total_elapsed,
                "gpu_memory":   _gpu_mem(),
            }

        # 3c. 거부됨 (no_function)
        if rag_result["status"] == "rejected":
            total_elapsed = round(time.time() - total_start, 5)
            return {
                "output":       "/NO_FUNCTION",
                "status":       "complete",
                "intent":       "no_function",
                "elapsed_time": total_elapsed,
                "gpu_memory":   _gpu_mem(),
            }

        # 3d. 명확한 명령 → LLM 호출
        # (rag_result["status"] == "use_llm")
        result = run_model(
            user_input,
            current_window_info,
            model_name,
            action_candidates=rag_result.get("action_candidates"),
            intent=rag_result.get("intent", ""),
        )

        # output 정리
        result['output'] = result['output'].replace("json\n", "").replace("json", "").strip()

        # 복합 명령어 처리
        api_calls = result['output'].strip().split('\n')
        api_calls = [c.strip() for c in api_calls if c.strip() and not c.startswith('#')]

        print(f"\n[API Calls Detected] {len(api_calls)} API(s)")
        for idx, call in enumerate(api_calls, 1):
            print(f"  {idx}. {call}")

        _execute_api_calls(api_calls, current_window_info, model_name)

        total_elapsed = round(time.time() - total_start, 5)
        print(f"  Total Elapsed Time: {total_elapsed:.3f} seconds")
        print("-" * 50)

        result['status'] = "complete"
        result['intent'] = rag_result.get("intent", "")
        return result


def _execute_api_calls(api_calls: list, current_window_info: dict, model_name: str) -> None:
    """API 목록을 순차 실행한다 (화이트리스트 검증 포함)."""
    success_count = 0
    failed_apis   = []

    for api_call in api_calls:
        if api_call == "/NO_FUNCTION":
            print(f"[Skip] {api_call}")
            continue

        # 화이트리스트 검증
        if is_valid_api_safe(api_call):
            api_url = f"http://localhost:3000{api_call}"
        else:
            print(f"[Blocked] Unsafe API call: {api_call}")
            fallback_prompt = (
                f"'{api_call}'는 허용되지 않는 URL입니다. "
                "프롬프트 내에 존재하는 URL로 변환해 주세요. "
                "백틱(`)이나 코드블록 없이 URL만 출력하세요."
            )
            fallback_result = run_model(fallback_prompt, current_window_info, model_name)
            api_call = fallback_result['output'].replace("```", "").replace("json", "").strip()

            if is_valid_api_safe(api_call):
                api_url = f"http://localhost:3000{api_call}"
            else:
                print(f"[Fallback Unsafe] {api_call}")
                api_call = "/NO_FUNCTION"
                api_url  = f"http://localhost:3000{api_call}"

        try:
            response = requests.get(api_url, timeout=30)
            if response.status_code == 200:
                success_count += 1
                print(f"[Success] {api_call} → {response.status_code}")
            else:
                failed_apis.append(api_call)
                print(f"[Failed] {api_call} → {response.status_code}")
        except Exception as err:
            failed_apis.append(api_call)
            print(f"[Error] {api_call} → {err}")

    print(f"\n[Execution Summary] Total={len(api_calls)}, "
          f"Success={success_count}, Failed={len(failed_apis)}")
    if failed_apis:
        print(f"  Failed APIs: {failed_apis}")


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