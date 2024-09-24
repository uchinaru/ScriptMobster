from selenium import webdriver
from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time


class click:

    def __init__(self):
        self.SITE_LINK = "https://app.playersrevenge.com/iframe.php"

        chrome_service = Service("C:\\Users\\Algo Gamer\\OneDrive\\Documentos\\chromedriver.exe")
        self.driver = webdriver.Chrome(service=chrome_service)
        # self.driver.maximize_window()

    def abrir_site(self):
        time.sleep(2)
        self.driver.get(self.SITE_LINK)
        time.sleep(2)

    def logar(self):
        # Localizando o campo de login pelo XPath e inserindo o login
        login_input = self.driver.find_element(By.XPATH, "/html/body/center[2]/center/div[1]/form/input[1]")
        login_input.send_keys(" ")

        # Localizando o campo de senha pelo XPath e inserindo a senha
        password_input = self.driver.find_element(By.XPATH, "/html/body/center[2]/center/div[1]/form/input[2]")
        password_input.send_keys(" ")

        # Localizando o botão de login pelo XPath e clicando nele
        login_button = self.driver.find_element(By.XPATH, "/html/body/center[2]/center/div[1]/form/input[6]")
        login_button.click()

    def hitlist_players(self):
        iframe = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "mprgameframe"))  # Localiza o iframe pelo ID
        )

        # Muda o foco para o iframe
        self.driver.switch_to.frame(iframe)

        # Agora, interage com os elementos dentro do iframe
        hitlistplayer_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@id='I7']"))
        )
        hitlistplayer_button.click()

        # Volta ao contexto principal (fora do iframe), se necessário
        self.driver.switch_to.default_content()

    def curar(self):

        iframe = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "mprgameframe"))
        )
        self.driver.switch_to.frame(iframe)

        # Depois disso, aguarde o botão do hospital
        hospitalOpen_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@id='I9']"))
        )
        hospitalOpen_button.click()

        healer_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@id='healer']/button"))
        )

        while self.verificar_life():
            healer_button.click()

        close_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[6]/span[1]/a/b/font"))
        )
        close_button.click()

        self.driver.switch_to.default_content()
        time.sleep(5)

    def verificar_life(self):
        health_div = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "healthStater"))
        )

        health_value = int(health_div.text)

        if health_value < 290:
            return True
        else:
            return False

    def lista_de_bounties(self):
       # Criar esse metodo


scriptMobster = click()
scriptMobster.abrir_site()
scriptMobster.logar()
scriptMobster.hitlist_players()
scriptMobster.lista_de_bounties()
