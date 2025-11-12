# features/steps/steps_enviar_mensagem.py
from behave import given, when, then
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Tempo padrão de espera
DEFAULT_TIMEOUT = 20

def _start_chrome_with_profile(user_data_dir=None, profile_dir=None, headless=False):
    options = Options()
    # mantém sessão (útil para evitar ter que escanear QR toda vez)
    if user_data_dir:
        options.add_argument(f"--user-data-dir={user_data_dir}")
    if profile_dir:
        options.add_argument(f"--profile-directory={profile_dir}")
    # abre maximizado
    options.add_argument("--start-maximized")
    # evita mensagem "Chrome is being controlled by automated test software"
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    return driver

def _wait_for_presence(driver, by, locator, timeout=DEFAULT_TIMEOUT):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, locator)))

def _find_search_box(driver):
    # Tenta alguns seletores possíveis para a caixa de pesquisa do WhatsApp Web
    selectors = [
        (By.XPATH, "//div[@contenteditable='true' and @data-tab='3']"),
        (By.XPATH, "//div[@title='Search or start new chat']"),
        (By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='3']"),
    ]
    for by, sel in selectors:
        try:
            elem = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, sel)))
            return elem
        except:
            continue
    # fallback: pega o primeiro contenteditable visível (menos robusto)
    elems = driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
    for e in elems:
        if e.is_displayed():
            return e
    raise RuntimeError("Não foi possível localizar a caixa de pesquisa do WhatsApp Web.")

def _find_message_box(driver):
    # Tenta seletores para a caixa de mensagem (conteúdo editável no chat)
    selectors = [
        (By.XPATH, "//div[@contenteditable='true' and @data-tab='10']"),
        (By.XPATH, "//div[@contenteditable='true' and @data-tab='6']"),
        (By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='10']"),
    ]
    for by, sel in selectors:
        try:
            elem = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, sel)))
            return elem
        except:
            continue
    # fallback: usar ultimo contenteditable visível (tipicamente é a caixa de mensagem)
    elems = driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
    if elems:
        for e in reversed(elems):
            if e.is_displayed():
                return e
    raise RuntimeError("Não foi possível localizar a caixa de envio de mensagem.")

@given('que o WhatsApp Web está aberto')
def step_open_whatsapp(context):
    """
    Inicia o Chrome e abre o WhatsApp Web.
    Para manter a sessão entre execuções, você pode passar:
      context.user_data_dir = "/caminho/para/pasta/do/perfil"
    ou editar as linhas abaixo para um caminho local.
    """
    # Opcional: personalize estes caminhos para manter sessão entre execuções
    # Exemplo Windows: r"C:\Users\Fernando\AppData\Local\Google\Chrome\User Data"
    # Exemplo Linux: "/home/usuario/.config/google-chrome"
    user_data_dir = getattr(context, "user_data_dir", None)
    profile_dir = getattr(context, "profile_dir", None)
    headless = getattr(context, "headless", False)

    context.driver = _start_chrome_with_profile(user_data_dir=user_data_dir, profile_dir=profile_dir, headless=headless)
    context.driver.get("https://web.whatsapp.com/")
    # espera até a interface carregar (procura por caixa de pesquisa ou lista de chats)
    try:
        _wait_for_presence(context.driver, By.XPATH, "//div[@id='pane-side']", timeout=60)
    except:
        # fallback curto: espera a caixa de pesquisa aparecer
        _find_search_box(context.driver)
    time.sleep(1)  # pequeno delay para estabilizar

@when('eu procurar pelo grupo "voce"')
def step_search_group(context, nome):
    """
    Pesquisa pelo contato/grupo com o nome exato passado no feature.
    Use o nome exatamente como aparece no WhatsApp (pode ser seu próprio contato).
    """
    driver = context.driver
    search_box = _find_search_box(driver)
    # limpar e digitar
    search_box.clear()
    time.sleep(0.3)
    search_box.click()
    search_box.send_keys(nome)
    # aguarda aparecer resultado com o título igual ao nome
    try:
        contato_xpath = f"//span[@title=\"{nome}\"]"
        elem = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, contato_xpath)))
        elem.click()
    except Exception as e:
        # tenta alternativa: clicar primeiro resultado da lista
        try:
            lista_item = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div._2aBzC")) )
            lista_item.click()
        except:
            raise RuntimeError(f"Não foi possível localizar o contato/grupo '{nome}' no WhatsApp Web. Erro: {e}")
    time.sleep(0.7)

@when('eu enviar a mensagem "{texto}"')
def step_send_message(context, texto):
    driver = context.driver
    msg_box = _find_message_box(driver)
    # escreve mensagem (usa SHIFT+ENTER para novas linhas, ENTER para enviar)
    msg_box.click()
    # inserir texto com quebra de linha segura
    for line in texto.split("\n"):
        msg_box.send_keys(line)
        msg_box.send_keys(Keys.SHIFT, Keys.ENTER)
    # remove o último SHIFT+ENTER inserido e envia com ENTER
    msg_box.send_keys(Keys.BACKSPACE)
    msg_box.send_keys(Keys.ENTER)
    # guarda último texto enviado para verificação
    context.last_sent_text = texto
    # dá um tempinho para a mensagem ser enviada
    time.sleep(1)

@then('a mensagem deve ser enviada com sucesso')
def step_verify_sent(context):
    driver = context.driver
    texto = getattr(context, "last_sent_text", None)
    if not texto:
        raise AssertionError("Nenhuma mensagem registrada como enviada (context.last_sent_text ausente).")
    # tenta verificar se há bolha de saída com o texto exato
    # xpath procura por elementos 'message-out' contendo o texto
    # (o HTML do WhatsApp muda com frequência — usamos contains() como fallback)
    safe_xpath_variants = [
        f"//div[contains(@class,'message-out') or contains(@data-testid,'msg-out')]//span[contains(text(), \"{texto}\")]",
        f"//span[contains(@class,'selectable-text') and contains(text(), \"{texto}\")]",
        f"//div[contains(@class,'message-out') and .//span[contains(text(), \"{texto}\")]]"
    ]
    found = False
    for xp in safe_xpath_variants:
        try:
            WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, xp)))
            found = True
            break
        except:
            continue
    # encerra sessão (opcional)
    try:
        context.driver.quit()
    except:
        pass

    if not found:
        raise AssertionError("Não foi possível confirmar que a mensagem foi enviada. Verifique manualmente no WhatsApp Web.")




