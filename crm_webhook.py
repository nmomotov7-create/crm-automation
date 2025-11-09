from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

app = Flask(__name__)

# 🔐 Данные для входа в CRM
CRM_URL = "https://crm.zemzag.ru/index.php?module=users/login"
CRM_EMAIL = "t9169610619@gmail.com"
CRM_PASSWORD = "12345"

def create_client(phone, name, village):
    """Создание клиента в CRM через Selenium с поддержкой headless Chromium"""
    options = Options()
    options.add_argument("--headless=new")  # Новый headless для современного Chrome/Chromium
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.binary_location = "/usr/bin/chromium"  # путь к Chromium на Render

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        # 1️⃣ Логин в CRM
        driver.get(CRM_URL)
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(CRM_EMAIL)
        driver.find_element(By.NAME, "password").send_keys(CRM_PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit' and contains(., 'Вход')]").click()

        # 2️⃣ Создание нового клиента/лида
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Новый')]"))).click()

        # 3️⃣ Заполняем ФИО и телефон
        wait.until(EC.presence_of_element_located((By.NAME, "fields[278]"))).send_keys(name)
        driver.find_element(By.NAME, "fields[279]").send_keys(phone)

        # 4️⃣ Работа с Chosen для выбора поселка
        chosen_container = wait.until(EC.element_to_be_clickable((By.ID, "fields_283_chosen")))
        driver.execute_script("arguments[0].scrollIntoView(true);", chosen_container)
        chosen_container.click()

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

        results = wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, "#fields_283_chosen .chosen-results li.active-result"))

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
            driver.execute_script("""
                const li = arguments[0];
                li.scrollIntoView(true);
                li.dispatchEvent(new MouseEvent('mousedown', {bubbles:true}));
                li.click();
                li.dispatchEvent(new MouseEvent('mouseup', {bubbles:true}));
            """, selected)
            print(f"✅ Поселок выбран: {selected.text.strip()}")
        else:
            print(f"⚠️ Не удалось выбрать поселок '{village}'")
            driver.save_screenshot("chosen_no_results.png")

        save_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Сохранить')]")))
        save_button.click()
        wait.until(EC.invisibility_of_element(save_button))
        print("✅ Клиент успешно создан!")
        return True

    except Exception as e:
        print("❌ Ошибка при создании клиента:", e)
        driver.save_screenshot("error_debug.png")
        return False

    finally:
        driver.quit()

@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "CRM Webhook is running 🚀"})

@app.route("/new_client", methods=["POST"])
def new_client():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"ok": False, "error": "Некорректный JSON"}), 400

    phone = data.get("phone")
    name = data.get("name", "")
    village = data.get("village", "")

    if not phone:
        return jsonify({"ok": False, "error": "Телефон обязателен"}), 400

    ok = create_client(phone, name, village)
    return jsonify({"ok": ok})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
