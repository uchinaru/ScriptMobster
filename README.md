## 🤖 Script Bot Mobster Player Revenge

### 🚀 Começando / Getting started
* Essas instruções permitirão que você obtenha uma cópia do projeto em operação na sua máquina local para fins de desenvolvimento e teste.
* These instructions will allow you to obtain a copy of the project running on your local machine for development and testing purposes.

### 🔧 Instalação / Installation
* pip install selenium
* pip install webdriver-manager
* pip install colorama

### 🛠️ Import's
* from selenium import webdriver
* from selenium.webdriver.chrome.service import Service
* from selenium.webdriver.common.by import By
* from selenium.webdriver.support.ui import WebDriverWait
* from selenium.webdriver.support import expected_conditions as ec
* from webdriver_manager.chrome import ChromeDriverManager
* from selenium.webdriver.chrome.options import Options
* from colorama import init, Fore, Back, Style
* import os
* import time

### ⚙️ Funções da classe MobsterBot / Functions of the MobsterBot class
As funções abaixo estão funcionais, nem todas estão em uso na parte inferior do bot como é possivel, caso precise você poderá ativar e utilizar da forma que achar melhor.

The functions below are functional, not all of them are in use at the bottom of the bot as is possible, if you need them you can activate them and use them as you see fit.

*  def login(self): 👥 
    - Realiza o login no sistema.  
    - Logs into the system.  


* def load_login_password(self):  📝
    - Carrega o login e a senha do usuário.  
    - Loads the user's login and password.  


* def hitlist_players(self):  📝
    - Obtém a lista de jogadores na hitlist.  
    - Retrieves the list of players on the hitlist.  


* def heal(self):  ❤️
    - Cura o personagem.  
    - Heals the character.  


* def heal_attack_again(self):  ❤️
    - Cura e ataca novamente sem a interação do iframe da pagina.  
    - Heals and attacks again without the interaction of the page iframe.  


* def check_stamina(self):  💚
    - Verifica a quantidade de stamina disponível.  
    - Checks the available stamina.  


* def check_life(self):  ❤️
    - Verifica a quantidade de vida disponível.  
    - Checks the available life/health.  


* def access_iframe(self):  👨‍💻
    - Acessa um iframe na página.  
    - Accesses an iframe on the page.  


* def exit_iframe(self):  🚪
    - Sai do iframe e retorna à página principal.  
    - Exits the iframe and returns to the main page.  


* def get_login_password(self):  🗃️
    - Obtém o login e a senha do usuário.  
    - Retrieves the user's login and password.  


* def find_user_to_attack(self):  📜
    - Encontra um jogador adequado para atacar.  
    - Finds a suitable player to attack.  


* def check_attack_status(self):  👀
    - Verifica o status do ataque atual.  
    - Checks the status of the current attack.  


* def save_strong_players_list(self):  🧾
    - Salva a lista de jogadores fortes que voce já atacou e perdeu.  
    - Saves the list of strong players you've attacked and lost to.  


* def load_strong_players_list(self):  🧾
    - Carrega a lista de jogadores fortes.  
    - Loads the list of strong players.  


* def attack_wanted_players(self):  ⚔️
    - Ataca jogadores procurados na hitlist.  
    - Attacks wanted players on the hitlist.  
