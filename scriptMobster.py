from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
import time


class click:

    def __init__(self):
        self.SITE_LINK = "https://app.playersrevenge.com/iframe.php"
        self.USER_LOGIN = "payafk"
        self.USER_SENHA = "payafk"
        self.USER_CODE = "283231"
        self.LIFE_VERIFY = 290

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
        login_input.send_keys("payafk")

        # Localizando o campo de senha pelo XPath e inserindo a senha
        password_input = self.driver.find_element(By.XPATH, "/html/body/center[2]/center/div[1]/form/input[2]")
        password_input.send_keys("payafk")

        # Localizando o botão de login pelo XPath e clicando nele
        login_button = self.driver.find_element(By.XPATH, "/html/body/center[2]/center/div[1]/form/input[6]")
        login_button.click()

    def hitlist_players(self):
        iframe = WebDriverWait(self.driver, 10).until(
            ec.presence_of_element_located((By.ID, "mprgameframe"))  # Localiza o iframe pelo ID
        )

        self.driver.switch_to.frame(iframe)

        hitlistplayer_button = WebDriverWait(self.driver, 5).until(
            ec.element_to_be_clickable((By.XPATH, "//span[@id='I7']"))
        )
        hitlistplayer_button.click()

        self.driver.switch_to.default_content()

    def curar(self):

        iframe = WebDriverWait(self.driver, 5).until(
            ec.presence_of_element_located((By.ID, "mprgameframe"))
        )
        self.driver.switch_to.frame(iframe)

        hospitalOpen_button = WebDriverWait(self.driver, 5).until(
            ec.element_to_be_clickable((By.XPATH, "//span[@id='I9']"))
        )
        hospitalOpen_button.click()

        healer_button = WebDriverWait(self.driver, 5).until(
            ec.element_to_be_clickable((By.XPATH, "//span[@id='healer']/button"))
        )

        while self.verificar_life():
            healer_button.click()

        close_button = WebDriverWait(self.driver, 5).until(
            ec.element_to_be_clickable((By.XPATH, "/html/body/div[6]/span[1]/a/b/font"))
        )
        close_button.click()

        self.driver.switch_to.default_content()
        time.sleep(5)

    def verificar_life(self):
        health_div = WebDriverWait(self.driver, 5).until(
            ec.presence_of_element_located((By.ID, "healthStater"))
        )

        health_value = int(health_div.text)

        if health_value < self.LIFE_VERIFY:
            return True
        else:
            return False

    def findUserToAtack(self):
        iframe = WebDriverWait(self.driver, 5).until(
            ec.presence_of_element_located((By.ID, "mprgameframe"))  # Localiza o iframe pelo ID
        )

        self.driver.switch_to.frame(iframe)

        myMobs_button = WebDriverWait(self.driver, 5).until(
            ec.element_to_be_clickable((By.XPATH, "//span[@id='I12']"))
        )
        myMobs_button.click()

        show_user = WebDriverWait(self.driver, 5).until(
            ec.element_to_be_clickable((By.XPATH, "/html/body/div[5]/center/div[1]/div[5]/span[4]"))
        )
        show_user.click()

        userid_input = self.driver.find_element(By.XPATH, "/html/body/div[11]/div/div[9]/div/input")
        userid_input.send_keys(self.USER_CODE)

        findUserid_input = WebDriverWait(self.driver, 5).until(
            ec.element_to_be_clickable((By.XPATH, "/html/body/div[11]/div/div[9]/div/button"))
        )
        findUserid_input.click()

        close_input = WebDriverWait(self.driver, 5).until(
            ec.element_to_be_clickable((By.XPATH, "/html/body/div[11]/div/a[1]"))
        )
        close_input.click()

        self.driver.switch_to.default_content()
        time.sleep(5)

    def attack(self):
        attack_button = WebDriverWait(self.driver, 5).until(
            ec.element_to_be_clickable((By.XPATH, "/html/body/div[5]/center/div[1]/div[4]/span[3]"))
        )
        attack_button.click()

        attack_again_button = WebDriverWait(self.driver, 5).until(
            ec.element_to_be_clickable((By.XPATH, "/html/body/div[11]/div/div[9]/div/div/div/a"))
        )
        attack_again_button.click()


scriptMobster = click()
scriptMobster.abrir_site()
scriptMobster.logar()
scriptMobster.hitlist_players()
