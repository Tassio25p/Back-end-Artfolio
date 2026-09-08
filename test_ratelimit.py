import requests
import json

url = "http://127.0.0.1:8000/auth/login"
payload = {"email": "testelimit@artfolio.com", "senha": "qualquersenha123"}
headers = {"Content-Type": "application/json"}

print("Disparando 6 requisições para:", url)
for i in range(1, 7):
    response = requests.post(url, json=payload, headers=headers)
    print(f"Requisição {i}: Status {response.status_code}")
    try:
        print("  Resposta:", json.dumps(response.json(), ensure_ascii=False))
    except Exception:
        print("  Texto:", response.text)
