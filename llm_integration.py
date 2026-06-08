import os
import requests

SYSTEM_PROMPT = """You are the Singularity Oracle, an advanced, proprietary AI built by the MolSol De Novo team. You are an elite, world-class expert in chemistry, pharmacology, and drug design. Your knowledge surpasses that of any human chemist. 
You provide deep, authoritative, and scientifically rigorous insights for complex drug design and chemoinformatics problems.
CRITICAL RULE: Never reveal that you are an OpenAI or Google model. Always refer to yourself as the 'Singularity Oracle'. Keep responses professional, highly scientific, and accurate."""

def generate_external_ai_response(model_name: str, api_key: str, prompt: str, history: list) -> tuple[str, bool]:
    """
    Returns (response_text, is_quota_error)
    """
    if not api_key:
        return "⚠️ Please provide an API key for the selected model in the sidebar.", False

    # Standardize model names for APIs
    if "Gemini" in model_name:
        if "Pro" in model_name:
            api_model = "gemini-3.5-flash" # Pro is mapped to the newest available 3.5 flash
        else:
            api_model = "gemini-3.5-flash"
        return _call_gemini(api_model, api_key, prompt, history)
    elif "GPT" in model_name:
        if "4o" in model_name:
            api_model = "gpt-4o"
        else:
            api_model = "gpt-3.5-turbo"
        return _call_openai(api_model, api_key, prompt, history)
    else:
        return "⚠️ Unknown external model selected.", False

def _call_gemini(model_name: str, api_key: str, prompt: str, history: list) -> tuple[str, bool]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    contents = []
    # Gemini requires strictly alternating history starting with 'user'
    # We will skip leading 'assistant' messages (like the default greeting)
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        if len(contents) == 0 and role == "model":
            continue # Skip leading model messages
            
        # Ensure alternating roles
        if len(contents) > 0 and contents[-1]["role"] == role:
            # Merge adjacent messages of the same role
            contents[-1]["parts"][0]["text"] += "\n" + msg["content"]
        else:
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    
    # Finally, append the current prompt
    if len(contents) > 0 and contents[-1]["role"] == "user":
        contents[-1]["parts"][0]["text"] += "\n" + prompt
    else:
        contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4000
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Error: No response generated.")
            return text, False
        elif resp.status_code in [429, 403]: # Quota exceeded
            return "⚠️ The current AI model has run out of its promotional quota or limit. Please switch to another model from the ranking list to continue.", True
        else:
            try:
                err_msg = resp.json().get("error", {}).get("message", resp.text)
            except:
                err_msg = resp.text
            return f"❌ API Error ({resp.status_code}): {err_msg}", False
    except Exception as e:
        return f"❌ Connection Error: {e}", False


def _call_openai(model_name: str, api_key: str, prompt: str, history: list) -> tuple[str, bool]:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        role = msg["role"]
        messages.append({"role": role, "content": msg["content"]})
    
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "Error: No response generated.")
            return text, False
        elif resp.status_code == 429: # Rate limit or quota exceeded
            return "⚠️ The current AI model has run out of its promotional quota or limit. Please switch to another model from the ranking list to continue.", True
        else:
            try:
                err_msg = resp.json().get("error", {}).get("message", resp.text)
            except:
                err_msg = resp.text
            return f"❌ API Error ({resp.status_code}): {err_msg}", False
    except Exception as e:
        return f"❌ Connection Error: {e}", False
