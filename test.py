import requests
import json

def main():
    server_url = "http://localhost:8888/solve_captcha"
    print("----  -----")
    print("exit - leave.\n")
    while True:
        sid = input("Введите SID: ").strip()
        if sid.lower() == 'exit':
            print("Завершение тестера.")
            break
        if not sid.isdigit():
            print("Ошибка: SID должен состоять только из цифр.\n")
            continue
        payload = {"sid": sid}
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(server_url, headers=headers, data=json.dumps(payload), timeout=30)
        except requests.exceptions.RequestException as e:
            print(f"Ошибка соединения с сервером: {e}\n")
            continue
        if response.status_code == 200:
            try:
                data = response.json()
                if "answer" in data and "confidence" in data:
                    answer = data['answer']
                    confidence = data['confidence']
                    print(f"Ответ: {answer}")
                    print(f"Уверенность: {confidence*100:.2f}%\n")
                elif "error" in data:
                    print(f"Ошибка: {data['error']}\n")
                else:
                    print("Неизвестный ответ от сервера.\n")
            except json.JSONDecodeError:
                print("Ошибка: Не удалось декодировать ответ сервера как JSON.\n")
        else:
            print(f"Сервер вернул статус {response.status_code}: {response.text}\n")
if __name__ == "__main__":
    main()
