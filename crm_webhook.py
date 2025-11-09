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
import traceback

app = Flask(__name__)
CORS(app)

# 🔐 Данные для входа в CRM
CRM_URL = "https://crm.zemzag.ru/index.php?module=users/login"
CRM_EMAIL = "t9169610619@gmail.com"
CRM_PASSWORD = "12345"

def setup_driver():
    """Настройка драйвера для Render"""
    options = Options()
    
    # Обязательные настройки для облака
    options.add_argument("--headless=new")  # новый синтаксис
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    
    # УБРАЛ binary_location - webdriver-manager сам найдет Chrome
    # options.binary_location = "/usr/bin/google-chrome"  # ← ЭТУ СТРОКУ УДАЛИЛ
    
    # Дополнительные настройки для стабильности
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=options
        )
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        print(f"❌ Ошибка создания драйвера: {e}")
        print(f"🚨 TRACEBACK: {traceback.format_exc()}")
        return None

def create_client(phone, name, village):
    """Создание клиента в CRM через Selenium с устойчивым выбором поселка"""
    driver = setup_driver()
    if not driver:
        print("❌ Не удалось создать драйвер")
        return False
        
    wait = WebDriverWait(driver, 25)  # увеличил таймаут

    try:
        print("🚀 Начало создания клиента...")
        print(f"📞 Телефон: {phone}, 👤 Имя: {name}, 🏠 Поселок: {village}")
        
        # 1️⃣ Логин в CRM
        print("1. Логинимся в CRM...")
        driver.get(CRM_URL)
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(CRM_EMAIL)
        driver.find_element(By.NAME, "password").send_keys(CRM_PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit' and contains(., 'Вход')]").click()
        time.sleep(3)

        # 2️⃣ Создание нового клиента/лида
        print("2. Создаем нового клиента...")
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Новый')]"))).click()
        time.sleep(3)

        # 3️⃣ Заполняем ФИО и телефон
        print("3. Заполняем основные поля...")
        wait.until(EC.presence_of_element_located((By.NAME, "fields[278]"))).send_keys(name)
        driver.find_element(By.NAME, "fields[279]").send_keys(phone)
        time.sleep(2)

        # 4️⃣ Работа с Chosen для выбора поселка
        print("4. Выбираем поселок...")
        chosen_container = wait.until(EC.element_to_be_clickable((By.ID, "fields_283_chosen")))
        driver.execute_script("arguments[0].scrollIntoView(true);", chosen_container)
        chosen_container.click()
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
        """, search_input, village)

        # Ждем появления вариантов
        print("   Ждем появления вариантов...")
        time.sleep(3)
        results = driver.find_elements(By.CSS_SELECTOR, "#fields_283_chosen .chosen-results li.active-result")
        print(f"   Найдено вариантов: {len(results)}")

        # Выбор нужного поселка
        selected = None
        village_lower = village.lower()
        for i, li in enumerate(results):
            text = li.text.strip().lower()
            print(f"   Вариант {i}: {text}")
            if village_lower in text:
                selected = li
                break
                
        if not selected and results:
            selected = results[0]
            print(f"   Выбран первый вариант: {selected.text}")

        if selected:
            driver.execute_script("arguments[0].click();", selected)
            print(f"✅ Поселок выбран: {selected.text.strip()}")
            time.sleep(2)
        else:
            print(f"⚠️ Не удалось выбрать поселок '{village}'")
            return False

        # 5️⃣ Сохраняем клиента
        print("5. Сохраняем клиента...")
        save_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Сохранить')]")))
        save_button.click()
        time.sleep(5)

        # Проверяем успешность
        current_url = driver.current_url
        print(f"   Текущий URL: {current_url}")
        
        success_indicators = [
            "module=clients" in current_url,
            "module=leads" in current_url, 
            "save" in current_url,
            "success" in driver.page_source.lower()
        ]
        
        if any(success_indicators):
            print("✅ Клиент успешно создан!")
            return True
        else:
            print("❌ Возможно ошибка при создании")
            # Проверяем ошибки на странице
            error_elements = driver.find_elements(By.CSS_SELECTOR, ".error, .alert-danger")
            for error in error_elements:
                print(f"   Ошибка: {error.text}")
            return False

    except Exception as e:
        print(f"❌ Ошибка при создании клиента: {e}")
        print(f"🚨 Детальный traceback: {traceback.format_exc()}")
        return False

    finally:
        driver.quit()
        print("🔚 Драйвер закрыт")

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
    print(f"🚀 Запуск сервера на порту {port}")
    app.run(host="0.0.0.0", port=port, debug=False)