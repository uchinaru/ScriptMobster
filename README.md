## 🤖 Script Bot Mobster Player Revenge

Bot em Python + Selenium para o [Mobsters Players Revenge](https://app.playersrevenge.com/front.php), com um painel web para ligar e desligar cada ação enquanto ele roda.

Python + Selenium bot for Mobsters Players Revenge, with a web panel to toggle each action while it runs.

### 🚀 Começando / Getting started

Requisitos / Requirements: Python 3.10+ e Google Chrome.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Crie o arquivo `LOGIN.txt` com o usuário na primeira linha e a senha na segunda (ele não é versionado).

Create `LOGIN.txt` with the username on the first line and the password on the second (it is not tracked by git).

### 🖥️ Painel / Panel

```bash
.venv/bin/python painel.py
```

Abre `http://127.0.0.1:8765` no navegador. Pelo painel você inicia/para o bot, liga/desliga cada ação, ajusta os parâmetros e acompanha vida, stamina, energia, estatísticas e o log ao vivo. As mudanças valem a partir do próximo ciclo e ficam salvas em `config.json`.

Opens `http://127.0.0.1:8765`. Start/stop the bot, toggle each action, tune parameters and follow health, stamina, energy, stats and the live log. Changes apply on the next cycle and are saved to `config.json`.

### ⌨️ Linha de comando / Command line

```bash
.venv/bin/python scriptMobster.py                # usa config.json (ou os padrões)
.venv/bin/python scriptMobster.py --headless     # Chrome sem janela
.venv/bin/python scriptMobster.py --ciclos 100   # para depois de 100 ciclos
.venv/bin/python scriptMobster.py --alvo 151174  # ataca só esse player quando ele estiver na hitlist
```

O log também é gravado em `bot.log`. / The log is also written to `bot.log`.

### ⚔️ O que o bot faz / What the bot does

Cada ciclo: cura se a vida estiver baixa → ataca (hitlist ou alvo) se tiver stamina → senão faz missões com a energia → deposita no banco (se ligado) → espera o próximo ponto de stamina.

| Ação | Descrição |
|---|---|
| **Hitlist** | Ataca os procurados com maior recompensa primeiro, até o seu nível + `nivel_extra_alvo`, ignorando MEGA. Repete o ataque enquanto o "Attack Again" aparecer. |
| **Players fortes** | Quem venceu você vai para `LIST_PLAYERS_STRONGS.txt` e é ignorado por `dias_expirar_fortes` dias. |
| **Alvo específico** | Com `alvo_id`, ataca só esse player quando ele estiver na hitlist (o ID aparece no perfil, `seePage_<id>`). |
| **Missões** | Sem stamina, gasta a energia na missão `missao_id` (padrão 2, "Make a Drop Off", 24 de energia). |
| **Banco** | Deposita o dinheiro acima de `reserva_dinheiro`. ⚠️ O jogo cobra 10% de taxa por depósito, por isso vem desligado. |
| **Hospital** | Cura abaixo de `vida_minima`, com limite de cliques para não travar sem dinheiro. |
| **Robustez** | Fecha popups do jogo, refaz o login se a sessão cair e só para depois de 5 erros seguidos. |

### ⚙️ Configuração / Settings (`config.json`)

Qualquer chave omitida usa o padrão de `CONFIG_PADRAO` em `scriptMobster.py`.

| Chave | Padrão | |
|---|---|---|
| `headless` | `false` | Chrome sem janela |
| `max_ciclos` | `40000` | Limite de ciclos |
| `atacar_hitlist` | `true` | Ataca a hitlist |
| `alvo_id` | `null` | ID de um player da hitlist |
| `fazer_missoes` | `true` | Missões quando falta stamina |
| `missao_id` | `2` | ID da missão |
| `missao_repeticoes` | `50` | 1, 10, 25, 50, 100, 250, 500, 1000 ou 10000 por clique |
| `missao_max_rodadas` | `10` | Cliques em "Do Mission Again" por pausa |
| `depositar_banco` | `false` | Deposita no banco (taxa de 10%) |
| `reserva_dinheiro` | `1000000000000` | Dinheiro mantido na mão |
| `vida_minima` | `390` | Cura abaixo disso |
| `max_cliques_cura` | `20` | Limite de cliques no Heal |
| `nivel_extra_alvo` | `60` | Ataca até o seu nível + isso |
| `nivel_maximo_alvo` | `null` | Nível máximo fixo (substitui o cálculo acima) |
| `dias_expirar_fortes` | `3` | Dias até tentar de novo quem venceu você |
| `estatisticas_a_cada` | `10` | Resumo da sessão a cada N ciclos |

### ⚠️ Aviso / Disclaimer

Bots costumam violar os termos de uso de jogos online e podem levar ao banimento da conta. Use por sua conta e risco.

Bots usually violate online games' terms of service and may get the account banned. Use at your own risk.
