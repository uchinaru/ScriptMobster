## 🤖 Script Bot Mobster Player Revenge

Bot em Python + Selenium para o [Mobsters Players Revenge](https://app.playersrevenge.com/front.php), com um painel web local para ligar e desligar cada ação enquanto ele roda.

> 🇺🇸 Python + Selenium bot for Mobsters Players Revenge, with a local web panel to toggle each action while it runs. See [English summary](#-english-summary).

---

### 📑 Sumário

- [Começando](#-começando)
- [Painel web](#️-painel-web)
- [Linha de comando](#️-linha-de-comando)
- [Como o bot funciona](#-como-o-bot-funciona)
- [Funcionalidades](#️-funcionalidades)
- [Configuração](#️-configuração)
- [Arquivos do projeto](#-arquivos-do-projeto)
- [Problemas comuns](#-problemas-comuns)
- [Aviso](#️-aviso)

---

### 🚀 Começando

**Requisitos:** Python 3.10+ (testado no 3.12) e Google Chrome. O chromedriver é baixado automaticamente pelo Selenium.

#### 1. Instalar (só na primeira vez)

Abra o terminal na pasta do projeto e rode:

**🍎 macOS / Linux** (Terminal)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**🪟 Windows** (PowerShell ou Prompt de Comando)

```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

> No Windows, instale o Python pelo [python.org](https://www.python.org/downloads/) marcando **"Add python.exe to PATH"**. Se o comando `py` não existir, use `python`.
> No macOS, se o Python do sistema for antigo, instale um novo com `brew install python@3.12` e use `python3.12` no lugar de `python3`.

#### 2. Login

O jeito mais fácil é pelo painel: no cartão **Conta**, preencha usuário e senha do jogo e clique em **Salvar login**. Para trocar só o usuário, deixe a senha em branco e a atual é mantida.

O painel grava os dados no arquivo `LOGIN.txt` (usuário na primeira linha, senha na segunda). Quem usa só a linha de comando pode criar esse arquivo na mão:

```
meu_usuario
minha_senha
```

> 🔒 `LOGIN.txt` está no `.gitignore` e nunca vai para o repositório. O painel nunca mostra a senha salva, só avisa que ela existe.

#### 3. Rodar

Com tudo instalado, basta abrir o painel e clicar em **Iniciar**:

| Sistema | Comando |
|---|---|
| 🍎 macOS / Linux | `.venv/bin/python painel.py` |
| 🪟 Windows | `.venv\Scripts\python painel.py` |

---

### 🖥️ Painel web

**🍎 macOS / Linux**

```bash
.venv/bin/python painel.py
```

**🪟 Windows**

```powershell
.venv\Scripts\python painel.py
```

Abre `http://127.0.0.1:8765` no navegador (só acessível na sua máquina). Feche com `Ctrl+C` no terminal: o bot é parado antes de sair.

| Seção | O que tem |
|---|---|
| **Cabeçalho** | Nome do personagem, estado do bot (Parado / Rodando / Parando) e botões **Iniciar** e **Parar**. |
| **Personagem** | Nível, mob, vida, stamina, tempo até o próximo ponto de stamina e energia, atualizados a cada ciclo. |
| **Ações** | Liga/desliga e parâmetros de cada ação: hitlist, alvo específico, missões, bônus grátis, banco e Chrome sem janela. |
| **Missões** | Lista de todas as missões do jogo com busca por nome, ordenada pelo dinheiro médio por ponto de energia, mostrando cidade, energia, dinheiro e maestria. Missões bloqueadas pelo seu nível/mob ficam escondidas (marque "mostrar bloqueadas" para ver, com 🔒). O botão **Atualizar lista** relê as missões no jogo com o bot rodando. |
| **Sessão** | Vitórias, derrotas, taxa de acerto, ataques repetidos, curas, missões, depósitos e bônus coletados desde o início. |
| **Log** | Últimas 150 linhas do log, ao vivo. |

As mudanças feitas no painel valem **a partir do próximo ciclo**, sem reiniciar o bot, e ficam salvas em `config.json`. A opção "Chrome sem janela" só vale ao iniciar.

---

### ⌨️ Linha de comando

O bot também roda sem o painel.

**🍎 macOS / Linux**

```bash
.venv/bin/python scriptMobster.py                     # usa config.json (ou os padrões)
.venv/bin/python scriptMobster.py --headless          # Chrome sem janela
.venv/bin/python scriptMobster.py --ciclos 100        # para depois de 100 ciclos
.venv/bin/python scriptMobster.py --alvo 284938       # ataca esse player pelo perfil dele
.venv/bin/python scriptMobster.py --config outro.json # usa outro arquivo de configuração
```

**🪟 Windows**

```powershell
.venv\Scripts\python scriptMobster.py                     # usa config.json (ou os padrões)
.venv\Scripts\python scriptMobster.py --headless          # Chrome sem janela
.venv\Scripts\python scriptMobster.py --ciclos 100        # para depois de 100 ciclos
.venv\Scripts\python scriptMobster.py --alvo 284938       # ataca esse player pelo perfil dele
.venv\Scripts\python scriptMobster.py --config outro.json # usa outro arquivo de configuração
```

Pare com `Ctrl+C`: o bot mostra o resumo da sessão e fecha o Chrome.

---

### 🔄 Como o bot funciona

Ao iniciar, o bot faz login, lê os **dados do personagem** (nome, nível, mob, vida, stamina, energia), lê a **lista de missões** e tenta **coletar os bônus grátis**. Depois repete o ciclo:

```
┌─► 1. Confere a sessão (refaz o login se tiver caído)
│   2. Coleta os bônus grátis (se passou o intervalo)
│   3. Cura se a vida estiver abaixo do limite
│   4. Tem stamina?
│        ├─ alvo específico definido → ataca o alvo pelo perfil
│        └─ senão, hitlist ligada    → ataca os procurados da hitlist
│   5. Não atacou ninguém? → faz missões com a energia
│   6. Deposita no banco (se ligado)
│   7. Atacou? espera 1s : espera o próximo ponto de stamina (ou 30s)
└───┘
```

Um erro pontual não derruba o bot: ele registra, espera 5s e segue. Só para depois de **5 erros seguidos**.

---

### ⚔️ Funcionalidades

#### 🎯 Hitlist
- Ataca os procurados com **maior recompensa primeiro**.
- Só ataca players até o **seu nível + `nivel_extra_alvo`** (ou até `nivel_maximo_alvo`, se definido) e ignora os **MEGA**.
- Repete o ataque enquanto o botão **"Attack Again"** aparecer, curando entre os ataques quando precisa.

#### 💪 Players fortes
- Quem venceu você é salvo em `LIST_PLAYERS_STRONGS.txt` com a data da derrota e é ignorado na hitlist.
- Depois de `dias_expirar_fortes` dias o player volta a ser atacado (você pode ter ficado mais forte).

#### 👤 Alvo específico
- Ataca **qualquer player**, mesmo fora da hitlist, pelo botão "Attack" do perfil dele.
- Repete enquanto houver stamina e, por padrão, para no ciclo em que perder (`alvo_parar_na_derrota`).
- Se o alvo estiver **morto** ou **no hospital**, o bot registra o aviso do jogo e tenta de novo no próximo ciclo. Enquanto isso, a energia vai para as missões.
- **Como achar o ID:** passe o mouse no nome do player no jogo; o ID é o número em `seePage_<id>`.
- Quando definido, tem prioridade sobre a hitlist. Deixe vazio para voltar à hitlist.

#### 📋 Missões
- Gasta a energia na missão escolhida sempre que o ciclo não atacou ninguém (sem stamina, alvo indisponível ou ataques desligados).
- Usa o **"Do Mission Again"** em lote, escolhendo a maior quantidade de repetições que a energia paga, até `missao_repeticoes`, por até `missao_max_rodadas` cliques.
- Se a missão falhar (ex.: falta item ou nível), o bot mostra o motivo dado pelo jogo.
- A lista de missões é salva em `missoes.json` e usada pelo painel.

> 💡 A diferença entre missões é enorme: algumas rendem centenas de dólares por energia, outras milhões. Use a ordenação do painel.

#### 🎁 Bônus grátis
- Clica em **"2000 ENERGY"** e **"DAILY BONUS"** da página inicial ao iniciar e a cada `bonus_intervalo_min` minutos.
- Registra a resposta do jogo (coletado ou "volte amanhã").
- Os caça-níqueis **SILVER / GOLD / PLATINUM** gastam tokens e **não** são usados.

#### 🏥 Hospital
- Cura quando a vida fica abaixo de `vida_minima`, só abrindo o hospital quando necessário.
- Limite de `max_cliques_cura` cliques: se faltar dinheiro, o bot avisa em vez de travar.

#### 🏦 Banco
- Deposita o dinheiro em mãos acima de `reserva_dinheiro` (a reserva fica para pagar o hospital).
- ⚠️ O jogo cobra **10% de taxa** em cada depósito, por isso vem **desligado**.

#### 🛡️ Robustez
- Fecha automaticamente os popups do jogo que bloqueiam os cliques.
- Refaz o login se a sessão expirar.
- Espera pelo **timer real de stamina** do jogo em vez de ficar recarregando a página.
- Fecha o Chrome ao sair, mesmo com erro.

#### 📊 Estatísticas e log
- Resumo da sessão a cada `estatisticas_a_cada` ciclos e ao parar: vitórias, derrotas, taxa de acerto, ataques repetidos, curas, missões, depósitos e bônus.
- Log com horário no terminal (colorido) e no arquivo `bot.log`.

---

### ⚙️ Configuração

Tudo pode ser ajustado pelo painel. Para editar à mão, crie um `config.json` na raiz; qualquer chave omitida usa o padrão de `CONFIG_PADRAO` em `scriptMobster.py`.

| Chave | Padrão | Descrição |
|---|---|---|
| **Geral** | | |
| `headless` | `false` | Roda o Chrome sem janela |
| `max_ciclos` | `40000` | Para depois desse número de ciclos |
| `estatisticas_a_cada` | `10` | Mostra o resumo da sessão a cada N ciclos |
| **Ataque** | | |
| `atacar_hitlist` | `true` | Ataca os procurados da hitlist |
| `nivel_extra_alvo` | `60` | Ataca até o seu nível + esse valor |
| `nivel_maximo_alvo` | `null` | Nível máximo fixo (substitui o cálculo acima) |
| `dias_expirar_fortes` | `3` | Dias até atacar de novo quem venceu você |
| `alvo_id` | `null` | ID de qualquer player para atacar pelo perfil (prioridade sobre a hitlist) |
| `alvo_parar_na_derrota` | `true` | Para de atacar o alvo no ciclo em que perder |
| **Hospital** | | |
| `vida_minima` | `390` | Cura abaixo desse valor |
| `max_cliques_cura` | `20` | Limite de cliques no botão Heal |
| **Missões** | | |
| `fazer_missoes` | `true` | Faz missões quando o ciclo não atacou |
| `missao_id` | `2` | ID da missão (escolha pelo nome no painel) |
| `missao_repeticoes` | `50` | Máximo de repetições por clique: 1, 10, 25, 50, 100, 250, 500, 1000 ou 10000 |
| `missao_max_rodadas` | `10` | Cliques em "Do Mission Again" por ciclo |
| **Bônus** | | |
| `coletar_bonus` | `true` | Coleta os bônus grátis da página inicial |
| `bonus_intervalo_min` | `60` | Minutos entre as tentativas de coleta |
| **Banco** | | |
| `depositar_banco` | `false` | Deposita no banco (⚠️ taxa de 10%) |
| `reserva_dinheiro` | `1000000000000` | Dinheiro mantido em mãos |

Exemplo de `config.json`:

```json
{
  "headless": true,
  "missao_id": 279,
  "missao_repeticoes": 100,
  "nivel_extra_alvo": 40
}
```

---

### 📁 Arquivos do projeto

| Arquivo | Descrição | Versionado |
|---|---|---|
| `scriptMobster.py` | O bot: classe `MobsterBot`, loop `run_bot` e linha de comando | ✅ |
| `painel.py` | Painel web local (só biblioteca padrão do Python) | ✅ |
| `requirements.txt` | Dependências (`selenium`, `colorama`) | ✅ |
| `LOGIN.txt` | Usuário e senha | ❌ |
| `config.json` | Configuração salva pelo painel | ❌ |
| `LIST_PLAYERS_STRONGS.txt` | Players que venceram você, com a data | ❌ |
| `missoes.json` | Última lista de missões lida do jogo | ❌ |
| `bot.log` | Log completo com data e hora | ❌ |

---

### 🔧 Problemas comuns

| Problema | Solução |
|---|---|
| Painel diz "Inicie o bot uma vez para carregar as missões" | A lista é lida do jogo no primeiro início. Clique em **Iniciar**. |
| "Atualizar lista" pede para o bot estar rodando | A leitura usa a sessão do bot no jogo. Inicie o bot primeiro. |
| "Nao consegui curar, verifique se tem dinheiro para o hospital!" | Falta dinheiro em mãos. Diminua `reserva_dinheiro` ou desligue o banco. |
| "O alvo … está morto / no hospital" | Normal: o bot tenta de novo no próximo ciclo. |
| Porta 8765 em uso | Já existe um painel aberto. Feche-o ou mude `PORTA` em `painel.py`. |
| Aviso `NotOpenSSLWarning` | Python antigo do macOS. Use o Python 3.12 (`brew install python@3.12`). |

---

### ⚠️ Aviso

Bots costumam violar os termos de uso de jogos online e podem levar ao banimento da conta. Use por sua conta e risco.

---

### 🇺🇸 English summary

- **Setup:** macOS/Linux `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` · Windows `py -m venv .venv` then `.venv\Scripts\pip install -r requirements.txt`. Set username and password in the panel's **Conta** card (saved to `LOGIN.txt`, username on line 1, password on line 2).
- **Panel:** `.venv/bin/python painel.py` (Windows: `.venv\Scripts\python painel.py`) opens `http://127.0.0.1:8765` to start/stop the bot, toggle each action live, pick missions by name and follow stats and the log.
- **CLI:** `.venv/bin/python scriptMobster.py [--headless] [--ciclos N] [--alvo ID] [--config FILE]`.
- **Features:** hitlist attacks (highest bounty first, level-capped, skips MEGA and players who beat you), attacking any player by profile ID, missions with spare energy, free daily bonus collection, auto-heal, optional bank deposits (10% fee), popup handling, auto re-login, session stats and `bot.log`.
- **Disclaimer:** bots usually violate online games' terms of service and may get the account banned. Use at your own risk.
