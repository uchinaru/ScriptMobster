from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from colorama import init, Fore, Back, Style
import os
import re
import time


class MobsterBot:

    def __init__(self):
        self.SITE_LINK = "https://app.playersrevenge.com/front.php"
        self.USER_LOGIN = ''
        self.USER_PASSWORD = ''
        self.USER_CODE = ''
        self.LIFE_VERIFY = 390
        self.MAX_LEVEL_TO_ATACK = 200
        self.MAX_HEAL_CLICKS = 20  # Limite de cliques no Heal para nao travar se faltar dinheiro
        self.STAMINA_WAIT = 60  # Segundos de espera quando a stamina acabar
        self.PLAYER_ALVO = ''
        self.STRONG_PLAYERS = self.load_strong_players_list()

        chrome_options = Options()
        #chrome_options.add_argument("--headless")  # Com essa opção ativa vai rodar o navegador sem opção grafica!

        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        self.driver.get(self.SITE_LINK)

    def login(self):

        self.load_login_password()

        # Localizando o campo de login pelo XPath e inserindo o login
        login_input = WebDriverWait(self.driver, 15).until((ec.element_to_be_clickable((By.XPATH, "/html/body/center[2]/center/div[1]/form/input[1]"))))
        login_input.send_keys(self.USER_LOGIN)

        # Localizando o campo de senha pelo XPath e inserindo a senha
        password_input = WebDriverWait(self.driver, 15).until((ec.element_to_be_clickable((By.XPATH, "/html/body/center[2]/center/div[1]/form/input[2]"))))
        password_input.send_keys(self.USER_PASSWORD)

        # Localizando o botão de login pelo XPath e clicando nele
        login_button = WebDriverWait(self.driver, 15).until((ec.element_to_be_clickable((By.XPATH, "/html/body/center[2]/center/div[1]/form/input[6]"))))
        login_button.click()

    def load_login_password(self):
        with open("LOGIN.txt", "r") as login:
            dados = login.read().splitlines()

            self.USER_LOGIN = dados[0].strip()
            self.USER_PASSWORD = dados[1].strip()

    def hitlist_players(self):
        self.access_iframe()
        self.close_popups()

        hitlistplayer_button = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.ID, "I7"))
        )
        hitlistplayer_button.click()

        self.exit_iframe()

    def close_popups(self):
        # Fecha popups (fancybox) do jogo que ficam por cima da pagina e bloqueiam os cliques
        overlay = self.driver.find_elements(By.ID, "fancybox-overlay")
        if not overlay or not overlay[0].is_displayed():
            return

        print(Fore.YELLOW + "Fechando popup do jogo." + Fore.RESET)
        fechar = self.driver.find_elements(By.ID, "fancybox-close")
        if fechar and fechar[0].is_displayed():
            fechar[0].click()
        else:
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        WebDriverWait(self.driver, 10).until(ec.invisibility_of_element_located((By.ID, "fancybox-overlay")))

    def heal(self):
        self.access_iframe()
        self.close_popups()
        self.heal_attack_again()
        self.exit_iframe()

    def heal_attack_again(self):
        # Esse metodo nao interege com o iframe mprgameframe
        # So abre o hospital se a vida estiver abaixo do limite
        if not self.check_life():
            return

        hospitalOpen_button = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.ID, "I9"))
        )
        hospitalOpen_button.click()

        healer_button = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.ID, "healbut"))
        )

        cliques = 0
        while self.check_life():
            if cliques >= self.MAX_HEAL_CLICKS:
                print(Fore.RED + Style.BRIGHT + "Nao consegui curar, verifique se tem dinheiro para o hospital!" + Fore.RESET + Style.RESET_ALL)
                break
            healer_button.click()
            cliques += 1
            time.sleep(0.5)

        close_button = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.ID, "closeheal"))
        )
        close_button.click()
        WebDriverWait(self.driver, 15).until(ec.invisibility_of_element_located((By.ID, "healbox2")))

    def check_stamina(self):
        # Esse metodo nao interege com o iframe mprgameframe
        stamin_div = WebDriverWait(self.driver, 15).until(
            ec.presence_of_element_located((By.ID, "fuckyoustam"))
        )
        return int(stamin_div.text.replace(",", ""))

    def has_stamina(self):
        self.access_iframe()
        stamina = self.check_stamina()
        self.exit_iframe()
        return stamina > 0

    def check_life(self):

        health_div = WebDriverWait(self.driver, 15).until(
            ec.presence_of_element_located((By.ID, "healthStater"))
        )

        health_value = int(health_div.text.replace(",", ""))
        print("Seu nivel de vida: " + Fore.RED + Style.BRIGHT + f"{health_value}" + Fore.RESET + Style.RESET_ALL)
        return health_value < self.LIFE_VERIFY

    def access_iframe(self):
        iframe = WebDriverWait(self.driver, 15).until(ec.presence_of_element_located((By.ID, "mprgameframe")))  # Localiza o iframe pelo ID)
        self.driver.switch_to.frame(iframe)

    def exit_iframe(self):
        self.driver.switch_to.default_content()

    def findUserToAtack(self):
        self.access_iframe()

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

        self.exit_iframe()

    def check_attack_status(self):

        status_atack = WebDriverWait(self.driver, 15).until(
            ec.presence_of_element_located((By.XPATH, "/html/body/div[5]/center/div[1]/div[1]/div/div/font/b")))

        if status_atack.text == 'Insuccesso!':
            self.heal_attack_again()
            print(Fore.RED + Style.BRIGHT + f"Deu ruim, player {self.PLAYER_ALVO} é muito forte, Insuccesso!" + Fore.RESET + Style.RESET_ALL)
            self.save_strong_players_list()
            return True
        else:
            self.heal_attack_again()
            print(Fore.GREEN + Style.BRIGHT + f"Ataque ao {self.PLAYER_ALVO} feito com successo!" + Fore.RESET + Style.RESET_ALL)
            return False

    @staticmethod
    def player_name(texto):
        # Remove o "(Lotto Listing)" e o "Level: N" para comparar so o nome do player
        texto = texto.replace("(Lotto Listing)", "")
        texto = re.sub(r"Level:\s*[\d,]+", "", texto)
        return " ".join(texto.split())

    def load_strong_players_list(self):

        if not os.path.exists("LIST_PLAYERS_STRONGS.txt"):
            return set()

        with open("LIST_PLAYERS_STRONGS.txt", "r") as arquivo:
            return {self.player_name(linha) for linha in arquivo if linha.strip()}

    def save_strong_players_list(self):
        nome = self.player_name(self.PLAYER_ALVO)
        self.STRONG_PLAYERS.add(nome)
        with open("LIST_PLAYERS_STRONGS.txt", "a") as arquivo:
            arquivo.write("\n" + nome)

    def attack_wanted_players(self):

        try:
            self.access_iframe()

            WebDriverWait(self.driver, 15).until(ec.presence_of_element_located((By.XPATH, "/html/body/div[5]/center/div[1]/div[7]")))  # Lista de procurados
            procurados = self.driver.find_elements(By.CLASS_NAME, "bountied_hunter_row")  # Pegando os elementos dentro da lista de procurados

            if procurados.__len__() != 0:

                for procurado in procurados:
                    try:
                        PLAYER_ALVO = procurado.find_element(By.CLASS_NAME, "bounty_name").text.strip()

                        if PLAYER_ALVO == "":
                            continue

                        stamina = self.check_stamina()
                        if stamina <= 0:
                            print(f"Sua estamina:" + Fore.LIGHTRED_EX + Style.BRIGHT + f" {stamina}" + Fore.RESET + Style.RESET_ALL)
                            break

                        NIVEL_PLAYER_ALVO = int(PLAYER_ALVO.split("\n")[-1].replace("Level: ", "").replace(",", "").strip())
                        self.PLAYER_ALVO = PLAYER_ALVO.replace("\n", " ")

                        if NIVEL_PLAYER_ALVO < self.MAX_LEVEL_TO_ATACK and "MEGA" not in self.PLAYER_ALVO.upper():

                            if self.player_name(self.PLAYER_ALVO) in self.STRONG_PLAYERS:
                                continue

                            print(Fore.YELLOW + Style.BRIGHT + f"Alvo selecionado: {self.PLAYER_ALVO}" + Fore.RESET + Style.RESET_ALL)
                            botao_attack = procurado.find_element(By.XPATH, ".//a[contains(@class, 'button_blue')]")
                            botao_attack.click()
                            time.sleep(1)

                            if self.check_attack_status():
                                continue

                            while True:
                                # Verificando se o botão atack again esta em tela para atacar novamente
                                repetir_atack = self.driver.find_elements(By.XPATH, "/html/body/div[5]/center/div[1]/div[1]/font/font/div/a")

                                stamina = self.check_stamina()
                                if stamina <= 0:
                                    print(f"Sua estamina:" + Fore.LIGHTRED_EX + Style.BRIGHT + f" {stamina}" + Fore.RESET + Style.RESET_ALL)
                                    break

                                if repetir_atack:
                                    print(Fore.LIGHTCYAN_EX + Style.BRIGHT + f"Repetindo o atack em {self.PLAYER_ALVO}" + Fore.RESET + Style.RESET_ALL)
                                    repetir_atack[0].click()
                                    time.sleep(2)
                                    self.heal_attack_again()

                                else:
                                    print(Fore.YELLOW + "Botão 'Attack Again' desapareceu. Seguindo para o próximo alvo." + Fore.RESET)
                                    break
                        else:
                            print(" O player não vai ser atacado: " + Fore.RED + Style.BRIGHT + f"{self.PLAYER_ALVO}" + Fore.RESET + Style.RESET_ALL)
                    except StaleElementReferenceException:
                        # A pagina mudou depois do ataque, a lista sera recarregada no proximo ciclo
                        print(Fore.YELLOW + "Lista de procurados mudou, recarregando no próximo ciclo." + Fore.RESET)
                        break
                    except Exception as e:
                        print(Fore.RED + f"{type(e).__name__}: {(str(e).strip().splitlines() or [''])[0]}" + Fore.RESET)

                self.exit_iframe()
            else:
                print(Fore.RED + "Lista de players procurados vazia !" + Fore.RESET)
                self.exit_iframe()

        except Exception as e:
            print(Fore.RED + f"Erro ao carregar a lista de players: {type(e).__name__}: {(str(e).strip().splitlines() or [''])[0]}" + Fore.RESET)
            self.exit_iframe()


scriptMobster = MobsterBot()

try:
    scriptMobster.login()

    contador = 0
    erros_seguidos = 0
    while contador < 40000:
        try:
            scriptMobster.heal()

            if not scriptMobster.has_stamina():
                print(Fore.LIGHTRED_EX + f"Sem estamina, aguardando {scriptMobster.STAMINA_WAIT}s..." + Fore.RESET)
                time.sleep(scriptMobster.STAMINA_WAIT)
                continue

            scriptMobster.hitlist_players()
            scriptMobster.attack_wanted_players()
            erros_seguidos = 0
        except Exception as e:
            # Um erro pontual nao derruba o bot, so para depois de varios erros seguidos
            erros_seguidos += 1
            print(Fore.RED + f"Erro no ciclo ({erros_seguidos}/5): {type(e).__name__}: {(str(e).strip().splitlines() or [''])[0]}" + Fore.RESET)
            scriptMobster.exit_iframe()
            if erros_seguidos >= 5:
                raise
            time.sleep(5)
            continue

        contador = contador + 1
        print(Fore.LIGHTCYAN_EX + Style.BRIGHT + f"Contador em {contador}" + Fore.RESET + Style.RESET_ALL)
        time.sleep(1)
except KeyboardInterrupt:
    print(Fore.YELLOW + "Bot interrompido pelo usuário." + Fore.RESET)
finally:
    scriptMobster.driver.quit()
