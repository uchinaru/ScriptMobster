from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from colorama import init, Fore, Back, Style
import os
import time


class MobsterBot:

    def __init__(self):
        self.SITE_LINK = "https://app.playersrevenge.com/iframe.php"
        self.USER_LOGIN = ''
        self.USER_PASSWORD = ''
        self.USER_CODE = ''
        self.LIFE_VERIFY = 390
        self.MAX_LEVEL_TO_ATACK = 200
        self.PLAYER_ALVO = ''

        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Com essa opção ativa vai rodar o navegador sem opção grafica!

        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        self.driver.get(self.SITE_LINK)

    def logar(self):

        self.carrega_login_password()

        # Localizando o campo de login pelo XPath e inserindo o login
        login_input = WebDriverWait(self.driver, 15).until((ec.element_to_be_clickable((By.XPATH, "/html/body/center[2]/center/div[1]/form/input[1]"))))
        login_input.send_keys(self.USER_LOGIN)

        # Localizando o campo de senha pelo XPath e inserindo a senha
        password_input = WebDriverWait(self.driver, 15).until((ec.element_to_be_clickable((By.XPATH, "/html/body/center[2]/center/div[1]/form/input[2]"))))
        password_input.send_keys(self.USER_PASSWORD)

        # Localizando o botão de login pelo XPath e clicando nele
        login_button = WebDriverWait(self.driver, 15).until((ec.element_to_be_clickable((By.XPATH, "/html/body/center[2]/center/div[1]/form/input[6]"))))
        login_button.click()

    def carrega_login_password(self):
        with open("LOGIN.txt", "r") as login:
            dados = login.readlines()

            self.USER_LOGIN = dados[0].replace("\n", "")
            self.USER_PASSWORD = dados[1]

    def hitlist_players(self):
        self.acessa_iframe()

        hitlistplayer_button = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.XPATH, "//span[@id='I7']"))
        )
        hitlistplayer_button.click()

        self.sai_do_iframe()

    def curar(self):

        self.acessa_iframe()

        hospitalOpen_button = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.XPATH, "//span[@id='I9']"))
        )
        hospitalOpen_button.click()

        healer_button = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.XPATH, "//span[@id='healer']/button"))
        )

        while self.verificar_life():
            healer_button.click()

        close_button = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.XPATH, "/html/body/div[6]/span[1]/a/b/font"))
        )
        close_button.click()

        self.sai_do_iframe()
        time.sleep(1)

    def curar_atack_again(self):
        # Esse metodo nao interege com o iframe mprgameframe
        hospitalOpen_button = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.XPATH, "//span[@id='I9']"))
        )
        hospitalOpen_button.click()

        healer_button = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.XPATH, "//span[@id='healer']/button"))
        )

        while self.verificar_life():
            healer_button.click()

        close_button = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.XPATH, "/html/body/div[6]/span[1]/a/b/font"))
        )
        close_button.click()

    def verificar_stm(self):
        # Esse metodo nao interege com o iframe mprgameframe
        stamin_div = WebDriverWait(self.driver, 15).until(
            ec.presence_of_element_located((By.ID, "fuckyoustam"))
        )
        return int(stamin_div.text)

    def verificar_life(self):
        health_div = WebDriverWait(self.driver, 15).until(
            ec.presence_of_element_located((By.ID, "healthStater"))
        )

        health_value = int(health_div.text)
        print("Seu nivel de vida: " + Fore.RED + Style.BRIGHT + f"{health_div.text}" + Fore.RESET + Style.RESET_ALL)
        return health_value < self.LIFE_VERIFY

    def acessa_iframe(self):
        iframe = WebDriverWait(self.driver, 15).until(ec.presence_of_element_located((By.ID, "mprgameframe")))  # Localiza o iframe pelo ID)
        self.driver.switch_to.frame(iframe)

    def sai_do_iframe(self):
        self.driver.switch_to.default_content()

    def pegar_login_senha(self):
        self.USER_LOGIN = input("Digite o login")
        self.USER_PASSWORD = input("Digite a senha")

    def findUserToAtack(self):
        self.acessa_iframe()

        myMobs_button = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.XPATH, "//span[@id='I12']"))
        )
        myMobs_button.click()

        show_user = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.XPATH, "/html/body/div[5]/center/div[1]/div[5]/span[4]"))
        )
        show_user.click()

        userid_input = self.driver.find_element(By.XPATH, "/html/body/div[11]/div/div[9]/div/input")
        userid_input.send_keys(self.USER_CODE)

        findUserid_input = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.XPATH, "/html/body/div[11]/div/div[9]/div/button"))
        )
        findUserid_input.click()

        close_input = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.XPATH, "/html/body/div[11]/div/a[1]"))
        )
        close_input.click()

        self.sai_do_iframe()

    def verifica_status_do_atack(self):

        status_atack = WebDriverWait(self.driver, 15).until(
            ec.presence_of_element_located((By.XPATH, "/html/body/div[5]/center/div[1]/div[1]/div/div/font/b")))

        if status_atack.text == 'Insuccesso!':
            self.curar_atack_again()
            print(Fore.RED + Style.BRIGHT + f"Deu ruim, player {self.PLAYER_ALVO} é muito forte, Insuccesso!" + Fore.RESET + Style.RESET_ALL)
            self.salva_lista_players_fortes()
            return True
        else:
            self.curar_atack_again()
            print(Fore.GREEN + Style.BRIGHT + f"Ataque ao {self.PLAYER_ALVO} feito com successo!" + Fore.RESET + Style.RESET_ALL)
            return False

    def carrega_lista_players_fortes(self):

        if os.path.getsize("LIST_PLAYERS_STRONGS.txt") > 0:
            with open("LIST_PLAYERS_STRONGS.txt", "r") as arquivo:
                return arquivo.readlines().__contains__(self.PLAYER_ALVO)

    def salva_lista_players_fortes(self):
        with open("LIST_PLAYERS_STRONGS.txt", "a") as arquivo:
            arquivo.write("\n"+self.PLAYER_ALVO)

    def atacar_procurados(self):

        try:
            self.acessa_iframe()

            WebDriverWait(self.driver, 15).until(ec.presence_of_element_located((By.XPATH, "/html/body/div[5]/center/div[1]/div[7]")))  # Lista de procurados
            procurados = self.driver.find_elements(By.CLASS_NAME, "bountied_hunter_row")  # Pegando os elementos dentro da lista de procurados

            if procurados.__len__() != 0:

                for procurado in procurados:
                    try:
                        PLAYER_ALVO = procurado.find_element(By.CLASS_NAME, "bounty_name").text.strip()

                        if PLAYER_ALVO == "":
                            continue

                        if self.verificar_stm() <= 0:
                            print(f"Sua estamina:" + Fore.LIGHTRED_EX + Style.BRIGHT + f" {self.verificar_stm()}" + Fore.RESET + Style.RESET_ALL)
                            break

                        NIVEL_PLAYER_ALVO = int(PLAYER_ALVO.split("\n")[-1].replace("Level: ", "").replace(",", "").strip())
                        self.PLAYER_ALVO = PLAYER_ALVO.replace("\n", " ")

                        if NIVEL_PLAYER_ALVO < self.MAX_LEVEL_TO_ATACK and "MEGA" not in self.PLAYER_ALVO.upper():

                            if self.carrega_lista_players_fortes():
                                continue

                            print(Fore.YELLOW + Style.BRIGHT + f"Alvo selecionado: {self.PLAYER_ALVO}" + Fore.RESET + Style.RESET_ALL)
                            botao_attack = procurado.find_element(By.XPATH, ".//a[contains(@class, 'button_blue')]")
                            botao_attack.click()
                            time.sleep(1)

                            if self.verifica_status_do_atack():
                                continue

                            while True:
                                # Verificando se o botão atack again esta em tela para atacar novamente
                                repetir_atack = self.driver.find_elements(By.XPATH, "/html/body/div[5]/center/div[1]/div[1]/font/font/div/a")

                                if self.verificar_stm() <= 0:
                                    print(f"Sua estamina:" + Fore.LIGHTRED_EX + Style.BRIGHT + f" {self.verificar_stm()}" + Fore.RESET + Style.RESET_ALL)
                                    break

                                if repetir_atack:
                                    print(Fore.LIGHTCYAN_EX + Style.BRIGHT + f"Repetindo o atack em {self.PLAYER_ALVO}" + Fore.RESET + Style.RESET_ALL)
                                    repetir_atack[0].click()
                                    time.sleep(2)
                                    self.curar_atack_again()
                                    time.sleep(1)

                                else:
                                    print(Fore.YELLOW + "Botão 'Attack Again' desapareceu. Seguindo para o próximo alvo." + Fore.RESET)
                                    break
                        else:
                            print(" O player não vai ser atacado: " + Fore.RED + Style.BRIGHT + f"{self.PLAYER_ALVO}" + Fore.RESET + Style.RESET_ALL)
                    except Exception as e:
                        print(e)

                self.sai_do_iframe()
            else:
                print(Fore.RED + "Lista de players procurados vazia !" + Fore.RESET)
                self.sai_do_iframe()

        except Exception as e:
            print(Fore.RED + f"Erro ao carregar a lista de players: {e}" + Fore.RESET)


scriptMobster = MobsterBot()
scriptMobster.logar()
scriptMobster.curar()

contador = 0
while contador < 40000:
    time.sleep(2)
    scriptMobster.hitlist_players()
    scriptMobster.carrega_lista_players_fortes()
    scriptMobster.atacar_procurados()
    scriptMobster.curar()
    contador = contador + 1
    print(Fore.LIGHTCYAN_EX + Style.BRIGHT + f"Contador em {contador}" + Fore.RESET + Style.RESET_ALL)
