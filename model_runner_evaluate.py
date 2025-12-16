import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from prompt_combine_none import system_prompt

device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.bfloat16 if device == "cuda" else torch.float32

MODEL_NAME = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"

print(f"[INFO] Loading model on {device} ...")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=dtype,
    trust_remote_code=True
).to(device)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def run_model_evaluate(user_text: str):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

    input_ids = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to(device)

    with torch.no_grad():
        output = model.generate(
            input_ids,
            max_new_tokens=64,
            eos_token_id=tokenizer.eos_token_id,
            do_sample=False
        )

    decoded = tokenizer.decode(output[0], skip_special_tokens=True)

    if "[|assistant|]" in decoded:
        decoded = decoded.split("[|assistant|]")[1].strip()

    decoded = decoded.replace("```json", "").replace("```", "").strip()

    return decoded
