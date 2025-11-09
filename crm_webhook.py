from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
import time

app = Flask(__name__)
CORS(app)

# 🔐 Данные для входа в CRM
CRM_URL = "https://crm.zemzag.ru/index.php?module=users/login"
CRM_EMAIL = "t9169610619@gmail.com"
CRM_PASSWORD = "12345"

def setup_driver():
    """Настройка драйвера для облака и локальной разработки"""
    options = Options()
    
    # Базовые настройки
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Если в облачной среде - включаем headless
    if os.environ.get('RENDER'):
        options.add_argument("--headless")
        options.binary_location = "/usr/bin/google-chrome"  # Путь в Render
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=options
    )
    return driver

def create_client(phone, name, village):
    """Создание клиента в CRM через Selenium с устойчивым выбором поселка"""
    driver = setup_driver()
    wait = WebDriverWait(driver, 20)

    try:
        print("🚀 Начало создания клиента...")
        
        # 1️⃣ Логин в CRM
        driver.get(CRM_URL)
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(CRM_EMAIL)
        driver.find_element(By.NAME, "password").send_keys(CRM_PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit' and contains(., 'Вход')]").click()
        time.sleep(3)

        # 2️⃣ Создание нового клиента/лида
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Новый')]"))).click()
        time.sleep(3)

        # 3️⃣ Заполняем ФИО и телефон
        wait.until(EC.presence_of_element_located((By.NAME, "fields[278]"))).send_keys(name)
        driver.find_element(By.NAME, "fields[279]").send_keys(phone)
        time.sleep(2)

        # 4️⃣ Работа с Chosen для выбора поселка
        chosen_container = wait.until(EC.element_to_be_clickable((By.ID, "fields_283_chosen")))
        driver.execute_script("arguments[0].scrollIntoView(true);", chosen_container)
        chosen_container.click()  # открываем список
        time.sleep(1)

        # Ввод текста в Chosen input через JS
        search_input = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#fields_283_chosen input.chosen-search-input")
        ))
        driver.execute_script("""
            const input = arguments[0];
            const value = arguments[1];
            input.focus();
            input.value = value;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('keyup', { bubbles: true }));
        """, search_input, village)

        # Ждем появления вариантов
        time.sleep(3)
        results = driver.find_elements(By.CSS_SELECTOR, "#fields_283_chosen .chosen-results li.active-result")

        # Выбор нужного поселка
        selected = None
        village_lower = village.lower()
        for li in results:
            text = li.text.strip().lower()
            if village_lower in text or text.startswith(village_lower):
                selected = li
                break
        if not selected and results:
            selected = results[0]

        if selected:
            driver.execute_script("arguments[0].click();", selected)
            print(f"✅ Поселок выбран: {selected.text.strip()}")
        else:
            print(f"⚠️ Не удалось выбрать поселок '{village}'")
            return False

        # 5️⃣ Сохраняем клиента
        save_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Сохранить')]")))
        save_button.click()
        time.sleep(5)

        # Проверяем успешность
        current_url = driver.current_url
        success = any(x in current_url for x in ["module=clients", "module=leads", "save"])
        
        if success:
            print("✅ Клиент успешно создан!")
            return True
        else:
            print("❌ Возможно ошибка при создании")
            return False

    except Exception as e:
        print(f"❌ Ошибка при создании клиента: {e}")
        return False

    finally:
        driver.quit()

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "CRM Automation API is running!", 
        "endpoints": {
            "new_client": "POST /new_client"
        }
    })

@app.route("/new_client", methods=["POST"])
def new_client():
    """WebHook: принимает данные от Nextbot"""
    data = request.get_json()
    phone = data.get("phone")
    name = data.get("name", "")
    village = data.get("village", "")

    if not phone:
        return jsonify({"ok": False, "error": "Телефон обязателен"}), 400

    ok = create_client(phone, name, village)
    return jsonify({"ok": ok})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)