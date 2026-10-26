from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from colorama import init, Fore, Style
from datetime import date, datetime
import argparse
import json
import logging
import os
import re
import threading
import time

init()

CONFIG_PADRAO = {
    "headless": False,
    "max_ciclos": 40000,
    "atacar_hitlist": True,             # Ataca os procurados da hitlist
    "alvo_id": None,                    # ID de qualquer player para atacar pelo perfil (tem prioridade sobre a hitlist)
    "alvo_parar_na_derrota": True,      # Para de atacar o alvo no ciclo em que perder
    "fazer_missoes": True,              # Gasta a energia na missao "missao_id" quando o ciclo nao atacou ninguem
    "vida_minima": 390,                 # Abaixo disso o bot cura
    "nivel_extra_alvo": 60,             # Ataca players ate o seu nivel + esse valor
    "nivel_maximo_alvo": None,          # Se preenchido, usa esse nivel fixo no lugar do calculo acima
    "max_cliques_cura": 20,             # Limite de cliques no Heal para nao travar se faltar dinheiro
    "dias_expirar_fortes": 3,           # Depois desses dias o player forte volta a ser atacado
    "missao_id": 2,                     # ID da missao (2 = Make a Drop Off, 24 de energia)
    "missao_repeticoes": 50,            # Vezes por clique: 1, 10, 25, 50, 100, 250, 500, 1,000 ou 10,000
    "missao_max_rodadas": 10,           # Limite de cliques em "Do Mission Again" por pausa de stamina
    "depositar_banco": False,           # Atencao: o banco cobra 10% de taxa em cada deposito
    "reserva_dinheiro": 1000000000000,  # Dinheiro que fica na mao para pagar o hospital
    "estatisticas_a_cada": 10,          # Mostra o resumo da sessao a cada N ciclos
    "coletar_bonus": True,              # Coleta os bonus gratis da pagina inicial (2000 ENERGY e DAILY BONUS)
    "bonus_intervalo_min": 60,          # Tenta coletar de novo a cada N minutos
}

ARQUIVO_FORTES = "LIST_PLAYERS_STRONGS.txt"
ARQUIVO_MISSOES = "missoes.json"
ARQUIVO_LOGIN = "LOGIN.txt"
REPETICOES_MISSAO = [1, 10, 25, 50, 100, 250, 500, 1000, 10000]  # Opcoes do "Do Mission Again"

# Le todas as missoes da aba Missions, inclusive as das cidades escondidas
MISSOES_JS = """
const vistos = new Set();
return [...document.querySelectorAll(".mblock")].flatMap(b => {
  const id = b.id;
  if (!/^\\d+$/.test(id) || vistos.has(id)) return [];
  vistos.add(id);
  const txt = s => (document.getElementById(s + "-" + id) || {}).textContent || "";
  const head = document.getElementById("misshead-" + id);
  const pct = head ? [...head.querySelectorAll("font")].map(f => f.textContent.trim()).find(t => /%$/.test(t)) : "";
  const bloco = b.closest("[id^='mission-list-block-']");
  return [{
    id: Number(id),
    nome: head && head.querySelector("a") ? head.querySelector("a").textContent.trim() : "",
    cidade: bloco ? bloco.id.replace("mission-list-block-", "") : "",
    energia: Number(txt("ereq").replace(/\\D/g, "")),
    dinheiro: txt("misscash").trim(),
    exp: txt("missexp").trim(),
    requisito: txt("mobreq").trim(),
    maestria: pct || "",
    // Imagem do item exigido (so aparece nas missoes que pedem item). O nome vem de mission_details
    item_img: (b.querySelector("img[onclick^='buyRequiredItemPitch']") || {}).src || "",
  }];
});
"""

# Detalhes da missao (mesma chamada do link do nome da missao), sem abrir popup
DETALHE_MISSAO_JS = """
let r = null;
$.ajax({type: "POST", url: dy + "mission_details.php?mission=" + arguments[0] + "&" + ak, async: false, dataType: "json",
        success: t => { r = t; }});
return r;
"""
ANSI = re.compile(r"\x1b\[[0-9;]*m")


class SemCores(logging.Formatter):
    # Remove as cores do colorama no arquivo de log
    def format(self, record):
        return ANSI.sub("", super().format(record))


def configurar_log():
    logger = logging.getLogger("mobster")
    logger.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))
    logger.addHandler(console)

    arquivo = logging.FileHandler("bot.log", encoding="utf-8")
    arquivo.setFormatter(SemCores("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(arquivo)
    return logger


log = configurar_log()


def numero(texto):
    # "Level:1,002" -> 1002 | "29,684" -> 29684
    return int(re.sub(r"[^\d]", "", texto) or 0)


def valor_recompensa(texto):
    # "$482B" -> 482000000000
    texto = texto.replace("$", "").replace(",", "").strip().upper()
    multiplicadores = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12, "Q": 1e15}
    try:
        if texto and texto[-1] in multiplicadores:
            return float(texto[:-1]) * multiplicadores[texto[-1]]
        return float(texto)
    except ValueError:
        return 0


def segundos(texto):
    # Timer do jogo "m:ss" -> segundos. Sem timer, espera 30s
    if ":" not in texto:
        return 30
    minutos, segs = texto.split(":")[-2:]
    return numero(minutos) * 60 + numero(segs)


def resumo_erro(e):
    return f"{type(e).__name__}: {(str(e).strip().splitlines() or [''])[0]}"


def ler_login():
    # Usuario na 1a linha, senha na 2a. Sem arquivo (ou incompleto) devolve strings vazias
    # utf-8-sig ignora o BOM que o Bloco de Notas do Windows pode gravar no inicio do arquivo
    if not os.path.exists(ARQUIVO_LOGIN):
        return "", ""
    with open(ARQUIVO_LOGIN, "r", encoding="utf-8-sig") as arquivo:
        dados = [linha.strip() for linha in arquivo.read().splitlines()] + ["", ""]
    return dados[0], dados[1]


def ler_missoes():
    if not os.path.exists(ARQUIVO_MISSOES):
        return {"atualizado": None, "missoes": [], "extras": {}}
    with open(ARQUIVO_MISSOES, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    dados.setdefault("extras", {})
    return dados


def salvar_extra_missao(missao_id, **campos):
    # Atualiza o que se sabe de uma missao no missoes.json. Valor None apaga o campo
    dados = ler_missoes()
    extra = dados["extras"].setdefault(str(missao_id), {})
    for chave, valor in campos.items():
        if valor is None:
            extra.pop(chave, None)
        else:
            extra[chave] = valor
    if not extra:
        dados["extras"].pop(str(missao_id))
    with open(ARQUIVO_MISSOES, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False)


def salvar_login(usuario, senha):
    with open(ARQUIVO_LOGIN, "w", encoding="utf-8") as arquivo:
        arquivo.write(f"{usuario}\n{senha}\n")


class MobsterBot:

    def __init__(self, config):
        self.SITE_LINK = "https://app.playersrevenge.com/front.php"
        self.config = config
        self.USER_LOGIN = ''
        self.USER_PASSWORD = ''
        self.PLAYER_ALVO = ''
        self.STRONG_PLAYERS = self.load_strong_players_list()
        self.stats = {"vitorias": 0, "derrotas": 0, "repeticoes": 0, "cliques_cura": 0, "missoes": 0, "depositos": 0, "bonus": 0}
        self.inicio = datetime.now()
        self.status = {}
        self.ultimo_bonus = None
        self.trava = threading.Lock()  # Evita que o painel e o loop usem o navegador ao mesmo tempo

        chrome_options = Options()
        if config["headless"]:
            chrome_options.add_argument("--headless=new")  # Roda o navegador sem opção grafica
            chrome_options.add_argument("--window-size=1400,1000")

        # O Selenium 4 ja baixa o chromedriver certo sozinho (Selenium Manager)
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get(self.SITE_LINK)

    # ------------------------------------------------------------------ login

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

        WebDriverWait(self.driver, 30).until(ec.presence_of_element_located((By.ID, "mprgameframe")))
        log.info(Fore.GREEN + "Login feito." + Fore.RESET)

    def load_login_password(self):
        self.USER_LOGIN, self.USER_PASSWORD = ler_login()
        if not self.USER_LOGIN or not self.USER_PASSWORD:
            raise RuntimeError("Login não configurado: preencha usuário e senha no painel (ou no LOGIN.txt).")

    def ensure_session(self):
        # Se a sessao expirou e o jogo voltou para a tela de login, loga de novo
        self.exit_iframe()
        if self.driver.find_elements(By.ID, "mprgameframe"):
            return

        log.info(Fore.YELLOW + "Sessão expirada, fazendo login de novo." + Fore.RESET)
        self.driver.get(self.SITE_LINK)
        self.login()

    # ------------------------------------------------------------- navegacao

    def access_iframe(self):
        iframe = WebDriverWait(self.driver, 15).until(ec.presence_of_element_located((By.ID, "mprgameframe")))  # Localiza o iframe pelo ID)
        self.driver.switch_to.frame(iframe)

    def exit_iframe(self):
        self.driver.switch_to.default_content()

    def open_tab(self, tab_id):
        # Abas do jogo: I2 Missions, I3 Bank, I7 Hitlist, I9 Hospital...
        self.close_popups()
        aba = WebDriverWait(self.driver, 15).until(ec.presence_of_element_located((By.ID, tab_id)))
        # Clique via JS: avisos do jogo por cima da aba (ex.: "healed") nao bloqueiam
        self.driver.execute_script("iFold = 0; arguments[0].click()", aba)

    def close_popups(self, silencioso=False):
        # A janela do hospital (healbox2) as vezes fica aberta por cima das abas
        self.close_heal_box()

        # Fecha popups (fancybox) do jogo que ficam por cima da pagina e bloqueiam os cliques
        overlay = self.driver.find_elements(By.ID, "fancybox-overlay")
        if not overlay or not overlay[0].is_displayed():
            return

        if not silencioso:
            log.info(Fore.YELLOW + "Fechando popup do jogo." + Fore.RESET)
        def fechar(driver):
            # Fecha pelo proprio fancybox do jogo, repetindo: durante a animacao de abertura ele ignora o close
            try:
                driver.execute_script("$.fancybox.close()")
            except Exception:
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            overlay = driver.find_elements(By.ID, "fancybox-overlay")
            return not overlay or not overlay[0].is_displayed()

        WebDriverWait(self.driver, 10, poll_frequency=0.5).until(fechar)

    def close_heal_box(self):
        caixa = self.driver.find_elements(By.ID, "healbox2")
        if not caixa or not caixa[0].is_displayed():
            return
        try:
            self.driver.find_element(By.ID, "closeheal").click()
            WebDriverWait(self.driver, 5).until(ec.invisibility_of_element_located((By.ID, "healbox2")))
        except Exception:
            # Se nem o X da janela for clicavel, esconde na marra para liberar as abas
            self.driver.execute_script("arguments[0].style.display = 'none'", caixa[0])

    def hitlist_players(self):
        self.access_iframe()
        self.open_tab("I7")
        self.exit_iframe()

    # ---------------------------------------------------------------- status

    def read_stat(self, element_id):
        # Esse metodo nao interege com o iframe mprgameframe
        elemento = WebDriverWait(self.driver, 15).until(ec.presence_of_element_located((By.ID, element_id)))
        return elemento.text

    def check_stamina(self):
        return numero(self.read_stat("fuckyoustam"))

    def check_energy(self):
        return numero(self.read_stat("iMobenergy"))

    def my_level(self):
        return numero(self.read_stat("levelstat"))

    def check_life(self):
        health_value = numero(self.read_stat("healthStater"))
        log.info("Seu nivel de vida: " + Fore.RED + Style.BRIGHT + f"{health_value}" + Fore.RESET + Style.RESET_ALL)
        return health_value < self.config["vida_minima"]

    def max_level_to_attack(self):
        if self.config["nivel_maximo_alvo"]:
            return self.config["nivel_maximo_alvo"]
        return self.my_level() + self.config["nivel_extra_alvo"]

    # -------------------------------------------------------------- hospital

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

        self.open_tab("I9")
        healer_button = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.ID, "healbut"))
        )

        cliques = 0
        while self.check_life():
            if cliques >= self.config["max_cliques_cura"]:
                log.info(Fore.RED + Style.BRIGHT + "Nao consegui curar, verifique se tem dinheiro para o hospital!" + Fore.RESET + Style.RESET_ALL)
                break
            # Clique nativo: o jogo ignora cliques via JS nos botoes dos popups (cura, repetir missao/ataque)
            healer_button.click()
            cliques += 1
            time.sleep(0.5)
        self.stats["cliques_cura"] += cliques

        close_button = WebDriverWait(self.driver, 15).until(
            ec.element_to_be_clickable((By.ID, "closeheal"))
        )
        close_button.click()
        WebDriverWait(self.driver, 15).until(ec.invisibility_of_element_located((By.ID, "healbox2")))

    # ------------------------------------------------------ players fortes

    @staticmethod
    def player_name(texto):
        # Remove o "(Lotto Listing)" e o "Level: N" para comparar so o nome do player
        texto = texto.replace("(Lotto Listing)", "")
        texto = re.sub(r"Level:\s*[\d,]+", "", texto)
        return " ".join(texto.split())

    def load_strong_players_list(self):
        # Formato: "nome<TAB>data da derrota". Linhas antigas sem data contam a partir de hoje
        fortes = {}
        if os.path.exists(ARQUIVO_FORTES):
            with open(ARQUIVO_FORTES, "r", encoding="utf-8") as arquivo:
                for linha in arquivo:
                    if not linha.strip():
                        continue
                    nome, _, data = linha.rstrip("\n").partition("\t")
                    try:
                        fortes[self.player_name(nome)] = date.fromisoformat(data.strip())
                    except ValueError:
                        fortes[self.player_name(nome)] = date.today()

        dias = self.config["dias_expirar_fortes"]
        fortes = {nome: data for nome, data in fortes.items() if (date.today() - data).days < dias}
        self.write_strong_players_list(fortes)
        return fortes

    @staticmethod
    def write_strong_players_list(fortes):
        with open(ARQUIVO_FORTES, "w", encoding="utf-8") as arquivo:
            for nome, data in fortes.items():
                arquivo.write(f"{nome}\t{data.isoformat()}\n")

    def save_strong_players_list(self):
        self.STRONG_PLAYERS[self.player_name(self.PLAYER_ALVO)] = date.today()
        self.write_strong_players_list(self.STRONG_PLAYERS)

    def is_strong_player(self):
        data = self.STRONG_PLAYERS.get(self.player_name(self.PLAYER_ALVO))
        return data is not None and (date.today() - data).days < self.config["dias_expirar_fortes"]

    # ---------------------------------------------------------------- ataque

    def check_attack_status(self):

        status_atack = WebDriverWait(self.driver, 15).until(
            ec.presence_of_element_located((By.XPATH, "//div[@id='content']/div[1]/div/div/font/b")))

        if status_atack.text == 'Insuccesso!':
            self.heal_attack_again()
            log.info(Fore.RED + Style.BRIGHT + f"Deu ruim, player {self.PLAYER_ALVO} é muito forte, Insuccesso!" + Fore.RESET + Style.RESET_ALL)
            self.save_strong_players_list()
            self.stats["derrotas"] += 1
            return True
        else:
            self.heal_attack_again()
            log.info(Fore.GREEN + Style.BRIGHT + f"Ataque ao {self.PLAYER_ALVO} feito com successo!" + Fore.RESET + Style.RESET_ALL)
            self.stats["vitorias"] += 1
            return False

    def attack_wanted_players(self):
        # Retorna True se atacou alguem
        atacou = False
        try:
            self.access_iframe()

            WebDriverWait(self.driver, 15).until(ec.presence_of_element_located((By.XPATH, "//div[@id='content']/div[7]")))  # Lista de procurados
            procurados = self.driver.find_elements(By.CLASS_NAME, "bountied_hunter_row")  # Pegando os elementos dentro da lista de procurados

            if not procurados:
                log.info(Fore.RED + "Lista de players procurados vazia !" + Fore.RESET)
                self.exit_iframe()
                return False

            # Ataca primeiro quem tem a maior recompensa
            def recompensa(procurado):
                valor = procurado.find_elements(By.CLASS_NAME, "bounty_amount")
                return valor_recompensa(valor[0].get_attribute("textContent")) if valor else 0
            procurados.sort(key=recompensa, reverse=True)

            nivel_maximo = self.max_level_to_attack()

            for procurado in procurados:
                try:
                    PLAYER_ALVO = procurado.find_element(By.CLASS_NAME, "bounty_name").text.strip()

                    if PLAYER_ALVO == "":
                        continue

                    stamina = self.check_stamina()
                    if stamina <= 0:
                        log.info(f"Sua estamina:" + Fore.LIGHTRED_EX + Style.BRIGHT + f" {stamina}" + Fore.RESET + Style.RESET_ALL)
                        break

                    nivel = re.search(r"Level:\s*([\d,]+)", PLAYER_ALVO)
                    NIVEL_PLAYER_ALVO = numero(nivel.group(1)) if nivel else 0
                    self.PLAYER_ALVO = " ".join(PLAYER_ALVO.replace("Level:", " Level:").split())

                    if NIVEL_PLAYER_ALVO >= nivel_maximo or "MEGA" in self.PLAYER_ALVO.upper():
                        log.info(" O player não vai ser atacado: " + Fore.RED + Style.BRIGHT + f"{self.PLAYER_ALVO}" + Fore.RESET + Style.RESET_ALL)
                        continue

                    if self.is_strong_player():
                        continue

                    log.info(Fore.YELLOW + Style.BRIGHT + f"Alvo selecionado: {self.PLAYER_ALVO} ({procurado.find_element(By.CLASS_NAME, 'bounty_amount').get_attribute('textContent')})" + Fore.RESET + Style.RESET_ALL)
                    botao_attack = procurado.find_element(By.XPATH, ".//a[contains(@class, 'button_blue')]")
                    self.driver.execute_script("iFold = 0; arguments[0].click()", botao_attack)
                    atacou = True
                    time.sleep(1)

                    if self.check_attack_status():
                        continue

                    while True:
                        # Verificando se o botão atack again esta em tela para atacar novamente
                        repetir_atack = self.driver.find_elements(By.XPATH, "//div[@id='content']/div[1]/font/font/div/a")

                        stamina = self.check_stamina()
                        if stamina <= 0:
                            log.info(f"Sua estamina:" + Fore.LIGHTRED_EX + Style.BRIGHT + f" {stamina}" + Fore.RESET + Style.RESET_ALL)
                            break

                        if repetir_atack:
                            log.info(Fore.LIGHTCYAN_EX + Style.BRIGHT + f"Repetindo o atack em {self.PLAYER_ALVO}" + Fore.RESET + Style.RESET_ALL)
                            repetir_atack[0].click()
                            self.stats["repeticoes"] += 1
                            time.sleep(2)
                            self.heal_attack_again()

                        else:
                            log.info(Fore.YELLOW + "Botão 'Attack Again' desapareceu. Seguindo para o próximo alvo." + Fore.RESET)
                            break
                except StaleElementReferenceException:
                    # A pagina mudou depois do ataque, a lista sera recarregada no proximo ciclo
                    log.info(Fore.YELLOW + "Lista de procurados mudou, recarregando no próximo ciclo." + Fore.RESET)
                    break
                except Exception as e:
                    log.info(Fore.RED + resumo_erro(e) + Fore.RESET)

            self.exit_iframe()

        except Exception as e:
            log.info(Fore.RED + f"Erro ao carregar a lista de players: {resumo_erro(e)}" + Fore.RESET)
            self.exit_iframe()
        return atacou

    def attack_target(self, player_id):
        # Ataca qualquer player pelo botao "Attack" do perfil dele, repetindo enquanto tiver stamina.
        # Retorna True se chegou a atacar
        player_id = int(player_id)
        self.access_iframe()
        try:
            self.close_popups()
            self.driver.execute_script(f"iFold = 0; GetPage('seePage_{player_id}')")
            nome = WebDriverWait(self.driver, 15).until(ec.visibility_of_element_located((By.ID, "myname"))).text
            self.PLAYER_ALVO = nome.replace("'s Stats", "").strip()

            if self.driver.find_elements(By.XPATH, "//span[contains(@onclick, 'healdead') and contains(., 'Raise from Dead')]"):
                log.info(Fore.YELLOW + f"O alvo {self.PLAYER_ALVO} está morto, aguardando ele voltar." + Fore.RESET)
                return False

            botao_xpath = f"//span[normalize-space()='Attack' and contains(@onclick, '({player_id},')]"
            if not self.driver.find_elements(By.XPATH, botao_xpath):
                log.info(Fore.RED + f"Não achei o botão de ataque no perfil {player_id}." + Fore.RESET)
                return False

            log.info(Fore.YELLOW + Style.BRIGHT + f"Atacando o alvo {self.PLAYER_ALVO} (id {player_id})" + Fore.RESET + Style.RESET_ALL)
            atacou = False
            while self.check_stamina() > 0:
                # Sempre ataca pelo botao do perfil; o resultado pode vir no perfil ou num popup
                self.close_popups(silencioso=True)
                botoes = self.driver.find_elements(By.XPATH, botao_xpath)
                if not botoes:
                    break
                # O clique dispara o ataque (ajax); limpa o resultado anterior antes da resposta chegar
                self.driver.execute_script(
                    "iFold = 0; arguments[0].click(); var a = document.getElementById('profile_attack'); if (a) a.innerHTML = '';", botoes[0])
                resultado = self.wait_attack_result()
                if resultado is None:
                    break
                if atacou:
                    self.stats["repeticoes"] += 1
                atacou = True
                venceu, mensagem = resultado
                if venceu:
                    self.stats["vitorias"] += 1
                    log.info(Fore.GREEN + Style.BRIGHT + f"Ataque ao {self.PLAYER_ALVO}: {mensagem}" + Fore.RESET + Style.RESET_ALL)
                else:
                    self.stats["derrotas"] += 1
                    log.info(Fore.RED + Style.BRIGHT + f"Ataque ao {self.PLAYER_ALVO}: {mensagem}" + Fore.RESET + Style.RESET_ALL)

                self.close_popups(silencioso=True)
                self.heal_attack_again()
                if not venceu and self.config["alvo_parar_na_derrota"]:
                    break
            return atacou
        finally:
            self.exit_iframe()

    def wait_attack_result(self):
        # O jogo mostra o resultado em #profile_attack ou, em caso de erro, num popup. Retorna (venceu, mensagem) ou None
        def pronto(driver):
            area = driver.find_elements(By.ID, "profile_attack")
            if area and area[0].is_displayed() and area[0].text.strip():
                return "perfil"
            overlay = driver.find_elements(By.ID, "fancybox-overlay")
            if overlay and overlay[0].is_displayed():
                return "popup"
            return False

        try:
            onde = WebDriverWait(self.driver, 15).until(pronto)
        except TimeoutException:
            log.info(Fore.RED + "O jogo não respondeu ao ataque." + Fore.RESET)
            return None

        if onde == "popup":
            try:
                texto = WebDriverWait(self.driver, 5).until(
                    lambda driver: " ".join(driver.find_element(By.ID, "fancybox-content").text.split()))
            except TimeoutException:
                texto = ""
        else:
            texto = " ".join(self.driver.find_element(By.ID, "profile_attack").text.split())
        texto = texto.replace("Attack Again", "").replace("Show Details", "").strip()

        if "Successo" not in texto and "Insuccesso" not in texto:
            # Ex.: "This mobster is in the hospital. Punch or Come back later.."
            log.info(Fore.YELLOW + f"O jogo recusou o ataque: {texto or 'sem mensagem'}" + Fore.RESET)
            self.close_popups(silencioso=True)
            return None

        # Resumo: "Successo! ... You won the fight dealing 53 to X while taking 1. You gained $4,559,617 and 33 experience."
        resumo = re.search(r"You (won|lost).*", texto)
        return "Insuccesso" not in texto, (("Successo! " if "Insuccesso" not in texto else "Insuccesso! ") + (resumo.group(0) if resumo else texto))[:220]

    # --------------------------------------------------- energia e dinheiro

    def collect_bonuses(self):
        # Botoes gratis da aba Main. O jogo responde num popup "Successo!" ou "Insuccesso!" com o motivo
        if not self.config["coletar_bonus"]:
            return
        intervalo = self.config["bonus_intervalo_min"] * 60
        if self.ultimo_bonus and (datetime.now() - self.ultimo_bonus).total_seconds() < intervalo:
            return
        self.ultimo_bonus = datetime.now()

        self.access_iframe()
        try:
            self.open_tab("I1")
            for texto in ["2000 ENERGY", "DAILY BONUS"]:
                botao = WebDriverWait(self.driver, 15).until(ec.presence_of_element_located(
                    (By.XPATH, f"//a[contains(@onclick, 'bonusMe') and normalize-space()='{texto}']")))
                self.driver.execute_script("iFold = 0; arguments[0].click()", botao)

                resposta = WebDriverWait(self.driver, 15).until(ec.visibility_of_element_located((By.ID, "bonus")))
                titulo = resposta.find_element(By.TAG_NAME, "h3").text.strip()
                mensagem = " ".join(resposta.find_element(By.TAG_NAME, "p").text.split())
                if titulo.startswith("Successo"):
                    self.stats["bonus"] += 1
                    log.info(Fore.GREEN + Style.BRIGHT + f"Bônus {texto} coletado: {mensagem}" + Fore.RESET + Style.RESET_ALL)
                else:
                    log.info(Fore.YELLOW + f"Bônus {texto} indisponível: {mensagem}" + Fore.RESET)
                self.close_popups()
        finally:
            self.exit_iframe()

    def read_missions(self):
        # Precisa estar dentro do iframe com a aba Missions aberta
        missoes = self.driver.execute_script(MISSOES_JS)
        # "extras" guarda o que o bot aprendeu de cada missao (nome do item exigido, motivo da ultima falha)
        extras = ler_missoes().get("extras", {})
        with open(ARQUIVO_MISSOES, "w", encoding="utf-8") as arquivo:
            json.dump({"atualizado": datetime.now().isoformat(timespec="seconds"), "missoes": missoes, "extras": extras},
                      arquivo, ensure_ascii=False)
        return missoes

    def mission_required_item(self, missao_id):
        # Nome do item exigido pela missao ("" se nao exige). Precisa estar dentro do iframe
        resposta = self.driver.execute_script(DETALHE_MISSAO_JS, int(missao_id)) or {}
        requer = re.search(r"Requires:(.*?)</a>", resposta.get("message", ""), re.S)
        nome = " ".join(re.sub(r"<[^>]+>", " ", requer.group(1)).split()) if requer else ""
        salvar_extra_missao(missao_id, item=nome)
        return nome

    def refresh_missions(self):
        self.access_iframe()
        try:
            self.open_tab("I2")
            WebDriverWait(self.driver, 15).until(ec.presence_of_element_located((By.CLASS_NAME, "mblock")))
            missoes = self.read_missions()
            log.info(Fore.LIGHTMAGENTA_EX + f"Lista de missões atualizada: {len(missoes)} missões." + Fore.RESET)
        finally:
            self.exit_iframe()

    def do_missions(self):
        # Gasta a energia numa missao enquanto espera a stamina voltar
        missao = self.config["missao_id"]
        if not self.config["fazer_missoes"] or not missao:
            return

        self.access_iframe()
        try:
            self.open_tab("I2")
            botao = WebDriverWait(self.driver, 15).until(ec.presence_of_element_located(
                (By.XPATH, f"//div[@id='{missao}' and @class='mblock']//a[contains(@class,'btn')]")))
            energia_minima = numero(self.driver.find_element(By.ID, f"ereq-{missao}").get_attribute("textContent"))
            self.read_missions()

            if self.check_energy() < energia_minima:
                return

            # O botao fica escondido na aba da cidade. O jogo trava cliques com "iFold" depois de um ataque, por isso zera antes
            energia_antes = self.check_energy()
            self.driver.execute_script("iFold = 0; arguments[0].click()", botao)
            feitas = 1
            falhou = False

            for _ in range(self.config["missao_max_rodadas"]):
                try:
                    de_novo = WebDriverWait(self.driver, 15).until(ec.presence_of_element_located(
                        (By.XPATH, "//div[@id='popup']//a[contains(., 'Do Mission Again')]")))
                except TimeoutException:
                    # Sem "Do Mission Again": a missao falhou (ex.: falta item ou nivel). Mostra o motivo do jogo
                    motivo = " ".join(self.driver.find_element(By.ID, "popup").text.split())[:200]
                    log.info(Fore.RED + f"Não consegui repetir a missão {missao}: {motivo or 'sem resposta do jogo'}" + Fore.RESET)
                    break

                # O jogo mostra "Do Mission Again" mesmo quando a missao falha (ex.: falta item exigido)
                resposta = " ".join(self.driver.find_element(By.ID, "popup").text.split())
                if "Could not do the mission" in resposta:
                    falta = re.search(r"need to have more (.+?)'s first", resposta)
                    motivo = f"falta o item {falta.group(1)}" if falta else resposta[:200]
                    log.info(Fore.RED + Style.BRIGHT + f"A missão {missao} falhou: {motivo}. Escolha outra missão no painel." + Fore.RESET + Style.RESET_ALL)
                    salvar_extra_missao(missao, falha=motivo)
                    falhou = True
                    break

                # Usa a maior quantidade de repeticoes que a energia paga, ate o limite configurado
                energia = self.check_energy()
                cabem = [r for r in REPETICOES_MISSAO if r <= self.config["missao_repeticoes"] and r * energia_minima <= energia]
                if not cabem:
                    break
                repeticoes = cabem[-1]
                Select(self.driver.find_element(By.ID, "xm")).select_by_visible_text(f"{repeticoes:,}")
                de_novo.click()
                feitas += repeticoes
                WebDriverWait(self.driver, 15).until(ec.staleness_of(de_novo))

            # So conta como feita se a energia baixou de verdade
            energia_depois = self.check_energy()
            if energia_depois < energia_antes:
                self.stats["missoes"] += feitas
                salvar_extra_missao(missao, falha=None)
                log.info(Fore.LIGHTMAGENTA_EX + f"Missões feitas, energia restante: {energia_depois:,}" + Fore.RESET)
            elif not falhou:
                log.info(Fore.RED + f"A missão {missao} não gastou energia (restante: {energia_depois:,})." + Fore.RESET)
        finally:
            self.exit_iframe()

    def deposit_cash(self):
        if not self.config["depositar_banco"]:
            return

        self.access_iframe()
        try:
            self.open_tab("I3")
            campo = WebDriverWait(self.driver, 15).until(ec.presence_of_element_located((By.ID, "amountdepo")))
            valor = numero(campo.get_attribute("value")) - self.config["reserva_dinheiro"]
            if valor <= 0:
                return

            campo.clear()
            campo.send_keys(str(valor))
            self.driver.find_element(By.XPATH, "//input[@id='amountdepo']/following-sibling::button").click()
            self.stats["depositos"] += 1
            log.info(Fore.LIGHTMAGENTA_EX + f"Depositado ${valor:,} no banco (o jogo cobra 10% de taxa)." + Fore.RESET)
            time.sleep(1)
        finally:
            self.exit_iframe()

    # ----------------------------------------------------------- estatisticas

    def update_status(self):
        # Foto dos atributos do personagem, usada pelo painel
        self.access_iframe()
        try:
            self.status = {
                "nome": self.read_stat("mystats_name").strip(),
                "vida": numero(self.read_stat("healthStater")),
                "stamina": self.check_stamina(),
                "energia": self.check_energy(),
                "nivel": self.my_level(),
                "mob": numero(self.read_stat("hgsstat")),
                "proxima_stamina": self.read_stat("stamina_timer"),
            }
        finally:
            self.exit_iframe()
        return self.status

    def print_stats(self):
        s = self.stats
        total = s["vitorias"] + s["derrotas"]
        taxa = f"{s['vitorias'] / total:.0%}" if total else "-"
        duracao = str(datetime.now() - self.inicio).split(".")[0]
        log.info(Fore.LIGHTWHITE_EX + Style.BRIGHT
                 + f"Resumo ({duracao}): {s['vitorias']} vitórias, {s['derrotas']} derrotas ({taxa}), "
                 + f"{s['repeticoes']} ataques repetidos, {s['cliques_cura']} curas, {s['missoes']} missões, {s['depositos']} depósitos, {s['bonus']} bônus"
                 + Fore.RESET + Style.RESET_ALL)


def carregar_config(caminho):
    config = dict(CONFIG_PADRAO)
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as arquivo:
            config.update(json.load(arquivo))
    return config


def run_bot(config, parar=None, ao_iniciar=None):
    # Loop principal. A config e relida a cada ciclo, entao o painel pode ligar/desligar acoes com o bot rodando.
    # "parar" e um threading.Event usado pelo painel para encerrar o bot.
    parar = parar or threading.Event()
    scriptMobster = MobsterBot(config)
    if ao_iniciar:
        ao_iniciar(scriptMobster)

    try:
        scriptMobster.login()
        try:
            # Ao iniciar, le os dados do personagem e a lista de missoes
            st = scriptMobster.update_status()
            log.info(Fore.GREEN + Style.BRIGHT + f"Personagem: {st['nome']} | Nível {st['nivel']} | Mob {st['mob']} | "
                     + f"Vida {st['vida']} | Stamina {st['stamina']} | Energia {st['energia']:,}" + Fore.RESET + Style.RESET_ALL)
            scriptMobster.refresh_missions()
            scriptMobster.collect_bonuses()
        except Exception as e:
            log.info(Fore.RED + f"Não consegui ler os dados iniciais: {resumo_erro(e)}" + Fore.RESET)

        contador = 0
        erros_seguidos = 0
        while contador < config["max_ciclos"] and not parar.is_set():
            atacou = False
            scriptMobster.trava.acquire()
            try:
                scriptMobster.ensure_session()
                scriptMobster.collect_bonuses()
                scriptMobster.heal()
                stamina = scriptMobster.update_status()["stamina"]

                if stamina > 0 and config["alvo_id"]:
                    atacou = scriptMobster.attack_target(config["alvo_id"])
                elif stamina > 0 and config["atacar_hitlist"]:
                    scriptMobster.hitlist_players()
                    atacou = scriptMobster.attack_wanted_players()

                if not atacou:
                    scriptMobster.do_missions()
                scriptMobster.deposit_cash()
                scriptMobster.update_status()
                erros_seguidos = 0
            except Exception as e:
                # Um erro pontual nao derruba o bot, so para depois de varios erros seguidos
                erros_seguidos += 1
                log.info(Fore.RED + f"Erro no ciclo ({erros_seguidos}/5): {resumo_erro(e)}" + Fore.RESET)
                scriptMobster.exit_iframe()
                if erros_seguidos >= 5:
                    raise
                parar.wait(5)
                continue
            finally:
                scriptMobster.trava.release()

            contador = contador + 1
            log.info(Fore.LIGHTCYAN_EX + Style.BRIGHT + f"Contador em {contador}" + Fore.RESET + Style.RESET_ALL)
            if contador % config["estatisticas_a_cada"] == 0:
                scriptMobster.print_stats()

            if atacou:
                parar.wait(1)
            else:
                # Sem stamina (ou sem ataque ligado): espera o proximo ponto de stamina
                espera = 30
                if scriptMobster.status.get("stamina", 0) <= 0:
                    espera = segundos(scriptMobster.status.get("proxima_stamina", "")) + 3
                espera = min(max(espera, 5), 600)
                log.info(Fore.LIGHTRED_EX + f"Nada para atacar agora, aguardando {espera}s..." + Fore.RESET)
                parar.wait(espera)
    except KeyboardInterrupt:
        log.info(Fore.YELLOW + "Bot interrompido pelo usuário." + Fore.RESET)
    finally:
        scriptMobster.print_stats()
        scriptMobster.driver.quit()
        log.info(Fore.YELLOW + "Bot parado." + Fore.RESET)


def main():
    parser = argparse.ArgumentParser(description="Bot do Mobsters Players Revenge")
    parser.add_argument("--config", default="config.json", help="arquivo de configuração (padrão: config.json)")
    parser.add_argument("--headless", action="store_true", help="roda o Chrome sem janela")
    parser.add_argument("--ciclos", type=int, help="quantidade máxima de ciclos")
    parser.add_argument("--alvo", type=int, help="ID de qualquer player para atacar pelo perfil")
    args = parser.parse_args()

    config = carregar_config(args.config)
    if args.headless:
        config["headless"] = True
    if args.ciclos:
        config["max_ciclos"] = args.ciclos
    if args.alvo:
        config["alvo_id"] = args.alvo

    run_bot(config)


if __name__ == "__main__":
    main()
