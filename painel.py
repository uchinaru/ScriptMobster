"""Painel web local para controlar o bot: liga/desliga cada acao com o bot rodando.

Uso: .venv/bin/python painel.py   ->  abre http://127.0.0.1:8765 no navegador
"""
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime
import json
import logging
import os
import threading
import urllib.parse
import urllib.request
import webbrowser

from scriptMobster import ANSI, ARQUIVO_MISSOES, CONFIG_PADRAO, carregar_config, ler_login, ler_missoes, log, resumo_erro, run_bot, salvar_login

PORTA = 8765
ARQUIVO_CONFIG = "config.json"
HOST_IMAGENS = "images.playersrevenge.com"
cache_imagens = {}


def imagem_do_jogo(url):
    # O servidor de imagens do jogo bloqueia hotlink: so entrega com o Referer do jogo
    if urllib.parse.urlparse(url).hostname != HOST_IMAGENS:
        raise ValueError("Imagem fora do jogo.")
    if url not in cache_imagens:
        pedido = urllib.request.Request(url, headers={"Referer": "https://app.playersrevenge.com/", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(pedido, timeout=10) as resposta:
            cache_imagens[url] = (resposta.headers.get_content_type(), resposta.read())
    return cache_imagens[url]


class MemoriaLog(logging.Handler):
    # Guarda as ultimas linhas do log para mostrar no painel
    def __init__(self):
        super().__init__()
        self.linhas = deque(maxlen=300)

    def emit(self, record):
        hora = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        self.linhas.append(f"{hora} {ANSI.sub('', record.getMessage())}")


class Controle:

    def __init__(self):
        self.config = carregar_config(ARQUIVO_CONFIG)
        self.parar = threading.Event()
        self.thread = None
        self.bot = None
        self.log = MemoriaLog()
        self.atualizando_missoes = False
        log.addHandler(self.log)

    @property
    def rodando(self):
        return self.thread is not None and self.thread.is_alive()

    def iniciar(self):
        if self.rodando:
            return
        if not all(ler_login()):
            log.info("Preencha usuário e senha em Conta antes de iniciar o bot.")
            return
        self.parar.clear()
        self.thread = threading.Thread(target=self._rodar, daemon=True)
        self.thread.start()

    def _rodar(self):
        try:
            run_bot(self.config, self.parar, ao_iniciar=lambda bot: setattr(self, "bot", bot))
        except Exception as e:
            log.info(f"Bot parou com erro: {type(e).__name__}: {e}")

    def parar_bot(self):
        self.parar.set()
        log.info("Parando o bot, aguarde o fim da ação atual...")

    def atualizar_config(self, novos):
        # So aceita chaves conhecidas, convertendo para o tipo do valor padrao
        for chave, valor in novos.items():
            if chave not in CONFIG_PADRAO:
                continue
            padrao = CONFIG_PADRAO[chave]
            if valor in ("", None):
                valor = None if padrao is None or chave in ("alvo_id", "missao_id") else padrao
            elif isinstance(padrao, bool):
                valor = bool(valor)
            elif chave in ("alvo_id", "missao_id", "nivel_maximo_alvo") or isinstance(padrao, int):
                valor = int(valor)
            self.config[chave] = valor

        with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as arquivo:
            json.dump(self.config, arquivo, indent=2, ensure_ascii=False)
        log.info("Configuração atualizada pelo painel.")

    def atualizar_login(self, dados):
        # Senha em branco mantem a que ja esta salva
        usuario = str(dados.get("usuario") or "").strip()
        senha = str(dados.get("senha") or "").strip() or ler_login()[1]
        if not usuario or not senha:
            raise ValueError("Informe usuário e senha.")
        salvar_login(usuario, senha)
        log.info(f"Login salvo para {usuario}." + (" Vale no próximo início do bot." if self.rodando else ""))

    def missoes(self):
        # Ultima lista lida pelo bot (fica salva para o painel funcionar com o bot parado)
        dados = ler_missoes()
        dados["atualizando"] = self.atualizando_missoes
        return dados

    def item_missao(self, missao_id):
        # Busca no jogo o nome do item exigido pela missao (precisa do bot rodando)
        if not self.rodando or not self.bot:
            raise ValueError("Inicie o bot para consultar o item exigido.")
        with self.bot.trava:
            self.bot.access_iframe()
            try:
                return {"item": self.bot.mission_required_item(int(missao_id))}
            finally:
                self.bot.exit_iframe()

    def atualizar_missoes(self):
        # Pede ao bot para reler as missoes assim que ele terminar a acao atual
        if not self.rodando or not self.bot or self.atualizando_missoes:
            return
        self.atualizando_missoes = True

        def tarefa():
            try:
                with self.bot.trava:
                    self.bot.refresh_missions()
            except Exception as e:
                log.info(f"Não consegui atualizar as missões: {resumo_erro(e)}")
            finally:
                self.atualizando_missoes = False

        threading.Thread(target=tarefa, daemon=True).start()

    def estado(self):
        bot = self.bot
        usuario, senha = ler_login()
        return {
            "rodando": self.rodando,
            # A senha nunca sai do servidor, so se existe uma salva
            "login": {"usuario": usuario, "tem_senha": bool(senha)},
            "parando": self.rodando and self.parar.is_set(),
            "config": self.config,
            "stats": bot.stats if bot else {},
            "status": bot.status if bot else {},
            "inicio": bot.inicio.strftime("%H:%M:%S") if bot and self.rodando else None,
            # Versao do missoes.json: o painel recarrega a lista quando o bot regrava o arquivo
            "missoes_versao": os.path.getmtime(ARQUIVO_MISSOES) if os.path.exists(ARQUIVO_MISSOES) else None,
            "log": list(self.log.linhas)[-150:],
        }


controle = Controle()


class Handler(BaseHTTPRequestHandler):

    def _responder(self, corpo, tipo="application/json", status=200):
        dados = corpo.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{tipo}; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path == "/":
            self._responder(PAGINA, "text/html")
        elif self.path == "/api/estado":
            self._responder(json.dumps(controle.estado(), ensure_ascii=False))
        elif self.path == "/api/missoes":
            self._responder(json.dumps(controle.missoes(), ensure_ascii=False))
        elif self.path.startswith("/api/imagem?"):
            try:
                tipo, dados = imagem_do_jogo(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)["u"][0])
            except Exception:
                return self._responder("{}", status=404)
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(dados)))
            self.send_header("Cache-Control", "max-age=86400")
            self.end_headers()
            self.wfile.write(dados)
        elif self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self._responder("{}", status=404)

    def do_POST(self):
        # So aceita pedidos vindos do proprio painel (outro site aberto no navegador nao consegue mexer no bot)
        origem = self.headers.get("Origin")
        if origem and origem not in (f"http://127.0.0.1:{PORTA}", f"http://localhost:{PORTA}"):
            return self._responder("{}", status=403)
        tamanho = int(self.headers.get("Content-Length") or 0)
        corpo = json.loads(self.rfile.read(tamanho) or b"{}")
        try:
            if self.path == "/api/iniciar":
                controle.iniciar()
            elif self.path == "/api/parar":
                controle.parar_bot()
            elif self.path == "/api/config":
                controle.atualizar_config(corpo)
            elif self.path == "/api/login":
                controle.atualizar_login(corpo)
            elif self.path == "/api/missoes/item":
                return self._responder(json.dumps(controle.item_missao(corpo.get("id")), ensure_ascii=False))
            elif self.path == "/api/missoes/atualizar":
                controle.atualizar_missoes()
                return self._responder(json.dumps(controle.missoes(), ensure_ascii=False))
            else:
                return self._responder("{}", status=404)
        except (ValueError, TypeError) as e:
            return self._responder(json.dumps({"erro": str(e)}), status=400)
        self._responder(json.dumps(controle.estado(), ensure_ascii=False))

    def log_message(self, *args):
        pass  # Nao polui o terminal com cada requisicao do painel


PAGINA = r"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel Mobster</title>
<style>
  :root { --bg:#f4f4f5; --card:#fff; --txt:#18181b; --sub:#71717a; --borda:#e4e4e7; --on:#16a34a; --off:#a1a1aa; --perigo:#dc2626; --log:#18181b; --logtxt:#d4d4d8; }
  @media (prefers-color-scheme: dark) { :root { --bg:#0f0f11; --card:#1c1c1f; --txt:#f4f4f5; --sub:#a1a1aa; --borda:#2e2e33; --log:#09090b; } }
  * { box-sizing:border-box; }
  body { margin:0; font:14px/1.4 -apple-system, system-ui, sans-serif; background:var(--bg); color:var(--txt); }
  main { max-width:1100px; margin:0 auto; padding:16px; display:grid; gap:16px; }
  header { display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
  h1 { font-size:20px; margin:0; flex:1; }
  h2 { font-size:13px; text-transform:uppercase; letter-spacing:.05em; color:var(--sub); margin:0 0 12px; }
  .card { background:var(--card); border:1px solid var(--borda); border-radius:10px; padding:16px; }
  .grade { display:grid; gap:16px; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
  .stats { display:grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap:10px; }
  .stat b { display:block; font-size:22px; font-variant-numeric:tabular-nums; }
  .stat span { color:var(--sub); font-size:12px; }
  .acao { display:flex; align-items:flex-start; gap:12px; padding:10px 0; border-top:1px solid var(--borda); }
  .acao:first-of-type { border-top:0; padding-top:0; }
  .acao .info { flex:1; }
  .acao small { color:var(--sub); display:block; }
  .campos { display:flex; gap:8px; flex-wrap:wrap; margin-top:6px; }
  .campos label { font-size:12px; color:var(--sub); display:flex; flex-direction:column; gap:2px; }
  input[type=number], select { width:120px; padding:5px 6px; border:1px solid var(--borda); border-radius:6px; background:var(--bg); color:var(--txt); }
  .chave { position:relative; width:44px; height:24px; flex:none; }
  .chave input { opacity:0; width:0; height:0; }
  .chave span { position:absolute; inset:0; background:var(--off); border-radius:12px; cursor:pointer; transition:.2s; }
  .chave span:before { content:""; position:absolute; width:18px; height:18px; left:3px; top:3px; background:#fff; border-radius:50%; transition:.2s; }
  .chave input:checked + span { background:var(--on); }
  .chave input:checked + span:before { transform:translateX(20px); }
  button { padding:8px 18px; border:0; border-radius:8px; font-weight:600; cursor:pointer; color:#fff; background:var(--on); }
  button.parar { background:var(--perigo); }
  button:disabled { opacity:.5; cursor:default; }
  .badge { padding:4px 10px; border-radius:20px; font-size:12px; font-weight:600; background:var(--off); color:#fff; }
  .badge.on { background:var(--on); }
  pre { background:var(--log); color:var(--logtxt); margin:0; padding:12px; border-radius:8px; height:360px; overflow:auto; font:12px/1.5 ui-monospace, Menlo, monospace; white-space:pre-wrap; word-break:break-word; }
  .aviso { color:var(--perigo); }
  .nome { font-size:14px; font-weight:400; color:var(--sub); }
  .missao-escolha { display:flex; flex-direction:column; gap:6px; margin-top:6px; }
  .missao-escolha select { width:100%; }
  .missao-escolha input[type=search] { width:100%; padding:5px 6px; border:1px solid var(--borda); border-radius:6px; background:var(--bg); color:var(--txt); }
  .linha { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  button.leve { background:transparent; color:var(--txt); border:1px solid var(--borda); padding:4px 10px; font-weight:500; }
  #missao-info { font-size:12px; color:var(--sub); }
  #missao-item { display:flex; gap:10px; align-items:center; font-size:12px; }
  #missao-item img { width:60px; height:40px; object-fit:contain; background:#000; border-radius:4px; }
  .conta { display:flex; gap:8px; flex-wrap:wrap; align-items:flex-end; }
  .conta label { font-size:12px; color:var(--sub); display:flex; flex-direction:column; gap:2px; flex:1; min-width:160px; }
  .conta input { padding:6px 8px; border:1px solid var(--borda); border-radius:6px; background:var(--bg); color:var(--txt); }
  #login-msg { font-size:12px; color:var(--sub); width:100%; }
</style>
</head>
<body>
<main>
  <header>
    <h1>🤖 Painel Mobster <small id="s-nome" class="nome"></small></h1>
    <span id="badge" class="badge">Parado</span>
    <button id="iniciar">Iniciar</button>
    <button id="parar" class="parar">Parar</button>
  </header>

  <section class="card">
    <h2>Conta</h2>
    <form class="conta" id="login-form" autocomplete="on">
      <label>Usuário<input id="login-usuario" name="username" autocomplete="username" required></label>
      <label>Senha<input id="login-senha" name="password" type="password" autocomplete="current-password"></label>
      <button type="submit">Salvar login</button>
      <div id="login-msg"></div>
    </form>
  </section>

  <section class="card">
    <h2>Personagem</h2>
    <div class="stats">
      <div class="stat"><b id="s-nivel">-</b><span>Nível</span></div>
      <div class="stat"><b id="s-mob">-</b><span>Mob</span></div>
      <div class="stat"><b id="s-vida">-</b><span>Vida</span></div>
      <div class="stat"><b id="s-stamina">-</b><span>Stamina</span></div>
      <div class="stat"><b id="s-energia">-</b><span>Energia</span></div>
    </div>
  </section>

  <div class="grade">
    <section class="card">
      <h2>Ações <small>(valem a partir do próximo ciclo)</small></h2>

      <div class="acao">
        <label class="chave"><input type="checkbox" data-cfg="atacar_hitlist"><span></span></label>
        <div class="info"><b>Atacar hitlist</b><small>Ataca os procurados, maior recompensa primeiro.</small>
          <div class="campos">
            <label>Nível extra acima do seu<input type="number" data-cfg="nivel_extra_alvo"></label>
            <label>Nível máximo fixo<input type="number" data-cfg="nivel_maximo_alvo" placeholder="automático"></label>
            <label>Esquecer derrotas após (dias)<input type="number" data-cfg="dias_expirar_fortes"></label>
          </div>
        </div>
      </div>

      <div class="acao">
        <div class="chave"></div>
        <div class="info"><b>Alvo específico</b><small>Ataca qualquer player pelo perfil dele, repetindo enquanto tiver stamina. O ID aparece no perfil (seePage_ID). Preenchido, tem prioridade sobre a hitlist.</small>
          <div class="campos">
            <label>ID do alvo<input type="number" data-cfg="alvo_id" placeholder="nenhum"></label>
            <label style="flex-direction:row;align-items:center;gap:6px;margin-top:14px"><input type="checkbox" data-cfg="alvo_parar_na_derrota"> parar se perder</label>
          </div>
        </div>
      </div>

      <div class="acao">
        <label class="chave"><input type="checkbox" data-cfg="fazer_missoes"><span></span></label>
        <div class="info"><b>Missões com a energia</b><small>Roda quando não há stamina para atacar. Ordenadas pelo dinheiro médio por ponto de energia.</small>
          <div class="missao-escolha">
            <div class="linha">
              <input type="search" id="missao-busca" placeholder="Buscar missão...">
            </div>
            <div class="linha">
              <label style="font-size:12px;color:var(--sub)"><input type="checkbox" id="missao-todas"> mostrar bloqueadas</label>
              <label style="font-size:12px;color:var(--sub)" title="463 das 524 missões pedem um item (arma, carro...) que você precisa ter"><input type="checkbox" id="missao-sem-item"> só sem item</label>
              <button class="leve" id="missao-atualizar" style="margin-left:auto" title="Relê a lista no jogo (bot precisa estar rodando)">Atualizar lista</button>
            </div>
            <select id="missao-select" size="10"></select>
            <small>🧰 exige item · ❌ última tentativa falhou · 🔒 bloqueada pelo nível/mob</small>
            <div id="missao-info"></div>
            <div id="missao-item"></div>
          </div>
          <div class="campos">
            <label>Máx. repetições por clique<select data-cfg="missao_repeticoes">
              <option>1</option><option>10</option><option>25</option><option>50</option><option>100</option><option>250</option><option>500</option><option value="1000">1,000</option><option value="10000">10,000</option>
            </select></label>
            <label>Máx. rodadas por pausa<input type="number" data-cfg="missao_max_rodadas"></label>
          </div>
        </div>
      </div>

      <div class="acao">
        <label class="chave"><input type="checkbox" data-cfg="coletar_bonus"><span></span></label>
        <div class="info"><b>Coletar bônus grátis</b><small>Botões "2000 ENERGY" e "DAILY BONUS" da página inicial. Coleta ao iniciar e tenta de novo no intervalo.</small>
          <div class="campos"><label>Intervalo (min)<input type="number" data-cfg="bonus_intervalo_min"></label></div>
        </div>
      </div>

      <div class="acao">
        <label class="chave"><input type="checkbox" data-cfg="depositar_banco"><span></span></label>
        <div class="info"><b>Depositar no banco</b><small class="aviso">O jogo cobra 10% de taxa em cada depósito.</small>
          <div class="campos"><label>Manter na mão ($)<input type="number" data-cfg="reserva_dinheiro"></label></div>
        </div>
      </div>

      <div class="acao">
        <label class="chave"><input type="checkbox" data-cfg="headless"><span></span></label>
        <div class="info"><b>Chrome sem janela</b><small>Vale ao iniciar o bot.</small>
          <div class="campos">
            <label>Curar abaixo de<input type="number" data-cfg="vida_minima"></label>
            <label>Máx. ciclos<input type="number" data-cfg="max_ciclos"></label>
          </div>
        </div>
      </div>
    </section>

    <section class="card">
      <h2>Sessão <small id="inicio"></small></h2>
      <div class="stats">
        <div class="stat"><b id="t-vitorias">0</b><span>Vitórias</span></div>
        <div class="stat"><b id="t-derrotas">0</b><span>Derrotas</span></div>
        <div class="stat"><b id="t-taxa">-</b><span>Acerto</span></div>
        <div class="stat"><b id="t-repeticoes">0</b><span>Ataques repetidos</span></div>
        <div class="stat"><b id="t-cliques_cura">0</b><span>Curas</span></div>
        <div class="stat"><b id="t-missoes">0</b><span>Missões</span></div>
        <div class="stat"><b id="t-depositos">0</b><span>Depósitos</span></div>
        <div class="stat"><b id="t-bonus">0</b><span>Bônus</span></div>
      </div>
      <h2 style="margin-top:16px">Log</h2>
      <pre id="log"></pre>
    </section>
  </div>
</main>
<script>
const $ = s => document.querySelector(s);
const fmt = v => typeof v === "number" ? v.toLocaleString("pt-BR") : (v ?? "-");
let editando = null;

async function api(caminho, corpo) {
  const r = await fetch(caminho, { method: corpo === undefined ? "GET" : "POST", body: corpo === undefined ? undefined : JSON.stringify(corpo) });
  return r.json();
}

function render(e) {
  $("#badge").textContent = e.parando ? "Parando..." : e.rodando ? "Rodando" : "Parado";
  $("#badge").classList.toggle("on", e.rodando && !e.parando);
  $("#iniciar").disabled = e.rodando;
  rodando = e.rodando;
  $("#parar").disabled = !e.rodando || e.parando;
  $("#inicio").textContent = e.inicio ? "desde " + e.inicio : "";

  const usuario = $("#login-usuario");
  if (document.activeElement !== usuario && !usuario.value) usuario.value = e.login.usuario;
  $("#login-senha").placeholder = e.login.tem_senha ? "•••••• (salva, deixe em branco para manter)" : "digite a senha";
  if (!$("#login-msg").dataset.fixo)
    $("#login-msg").textContent = e.login.usuario && e.login.tem_senha ? "Login configurado. Fica salvo só neste computador (LOGIN.txt)." : "Preencha usuário e senha do jogo para iniciar o bot.";

  for (const [k, v] of Object.entries(e.status)) { const el = $("#s-" + k); if (el) el.textContent = fmt(v); }
  for (const [k, v] of Object.entries(e.stats)) { const el = $("#t-" + k); if (el) el.textContent = fmt(v); }
  const total = (e.stats.vitorias || 0) + (e.stats.derrotas || 0);
  $("#t-taxa").textContent = total ? Math.round(100 * e.stats.vitorias / total) + "%" : "-";

  document.querySelectorAll("[data-cfg]").forEach(el => {
    if (el === editando) return;
    const v = e.config[el.dataset.cfg];
    if (el.type === "checkbox") el.checked = !!v; else el.value = v ?? "";
  });

  const mudouPersonagem = (e.status.nivel || 0) !== nivelAtual || (e.status.mob || 0) !== mobAtual;
  if (e.status.nivel) { nivelAtual = e.status.nivel; mobAtual = e.status.mob || 0; }
  if (e.config.missao_id !== missaoAtual || mudouPersonagem) { missaoAtual = e.config.missao_id; renderMissoes(); }
  if ((e.rodando && !missoes.length) || e.missoes_versao !== versaoMissoes) { versaoMissoes = e.missoes_versao; carregarMissoes(); }

  const log = $("#log"), noFim = log.scrollTop + log.clientHeight >= log.scrollHeight - 20;
  log.textContent = e.log.join("\n");
  if (noFim) log.scrollTop = log.scrollHeight;
}

document.querySelectorAll("[data-cfg]").forEach(el => {
  el.addEventListener("focus", () => editando = el);
  el.addEventListener("blur", () => editando = null);
  el.addEventListener("change", async () => {
    const v = el.type === "checkbox" ? el.checked : el.value;
    render(await api("/api/config", { [el.dataset.cfg]: v }));
  });
});
// ---------- missoes
let extras = {}, buscandoItem = null, rodando = false, versaoMissoes;
let missoes = [], nivelAtual = 0, mobAtual = 0, missaoAtual = null, ultimaAtualizacao = null;
const rotuloCidade = { newyork: "New York", chicago: "Chicago", neworleans: "New Orleans", lasvegas: "Las Vegas", seasonal: "Seasonal", upgrade: "Upgrade" };

function mediaDinheiro(m) {
  const n = (m.dinheiro.match(/[\d,]+/g) || []).map(x => Number(x.replace(/,/g, ""))).filter(x => x > 0);
  return n.length ? n.reduce((a, b) => a + b, 0) / n.length : 0;
}
function curto(v) {
  for (const [lim, s] of [[1e15, "Q"], [1e12, "T"], [1e9, "B"], [1e6, "M"], [1e3, "K"]]) if (v >= lim) return (v / lim).toFixed(v / lim < 10 ? 1 : 0) + s;
  return Math.round(v).toString();
}
function requisitos(m) {
  const n = (m.requisito.match(/\d[\d,]*/g) || []).map(x => Number(x.replace(/,/g, "")));
  return { nivel: n[0] || 0, mob: n[1] || 0 };
}
function bloqueada(m) { const r = requisitos(m); return nivelAtual && (r.nivel > nivelAtual || r.mob > mobAtual); }

function renderMissoes() {
  const busca = $("#missao-busca").value.trim().toLowerCase();
  const todas = $("#missao-todas").checked;
  const semItem = $("#missao-sem-item").checked;
  const sel = $("#missao-select"), rolagem = sel.scrollTop;
  sel.innerHTML = "";
  if (!missoes.length) {
    sel.innerHTML = '<option disabled>Inicie o bot uma vez para carregar as missões</option>';
    return;
  }
  const lista = missoes
    .filter(m => (todas || !bloqueada(m) || m.id === missaoAtual) && (!semItem || !m.item_img || m.id === missaoAtual) && (!busca || m.nome.toLowerCase().includes(busca) || String(m.id) === busca))
    .map(m => ({ ...m, porEnergia: m.energia ? mediaDinheiro(m) / m.energia : 0 }))
    .sort((a, b) => b.porEnergia - a.porEnergia);
  for (const m of lista) {
    const o = document.createElement("option");
    o.value = m.id;
    // Icones no inicio: o select corta o fim das linhas compridas
    const icones = (extras[m.id]?.falha ? "❌" : "") + (m.item_img ? "🧰" : "") + (bloqueada(m) ? "🔒" : "");
    o.textContent = (icones ? icones + " " : "") + `${m.nome} · ${rotuloCidade[m.cidade] || m.cidade} · ${m.energia} en · $${curto(mediaDinheiro(m))} · $${curto(m.porEnergia)}/en · ${m.maestria}`;
    o.title = o.textContent;
    o.selected = m.id === missaoAtual;
    sel.appendChild(o);
  }
  sel.scrollTop = rolagem;
  const m = missoes.find(x => x.id === missaoAtual);
  $("#missao-info").textContent = m
    ? `Selecionada: ${m.nome} (id ${m.id}) — ${m.energia} energia, $${m.dinheiro}, exp ${m.exp}, ${m.requisito} mob, maestria ${m.maestria}`
    : (missaoAtual ? `Selecionada: id ${missaoAtual}` : "Nenhuma missão selecionada");
  $("#missao-info").textContent += ultimaAtualizacao ? ` · lista de ${ultimaAtualizacao.replace("T", " ")}` : "";
  renderItem(m);
}
function renderItem(m) {
  const box = $("#missao-item"), ex = (m && extras[m.id]) || {};
  box.innerHTML = "";
  if (!m) return;
  const linhas = [];
  if (m.item_img) {
    const img = document.createElement("img"); img.src = "/api/imagem?u=" + encodeURIComponent(m.item_img); img.alt = "item exigido"; box.appendChild(img);
    linhas.push("Exige o item: " + (ex.item || (rodando ? "consultando..." : "inicie o bot para ver o nome")));
    if (!ex.item && rodando && buscandoItem !== m.id) buscarItem(m.id);
  } else {
    linhas.push("Não exige item.");
  }
  if (ex.falha) linhas.push("❌ Última tentativa falhou: " + ex.falha);
  const txt = document.createElement("div"); txt.textContent = linhas.join(" — "); box.appendChild(txt);
}
async function buscarItem(id) {
  buscandoItem = id;
  const d = await api("/api/missoes/item", { id });
  if (d.erro) { buscandoItem = null; return; }
  (extras[id] = extras[id] || {}).item = d.item || "(não informado pelo jogo)";
  renderMissoes();
}
async function carregarMissoes() {
  const d = await api("/api/missoes");
  missoes = d.missoes; ultimaAtualizacao = d.atualizado; extras = d.extras || {};
  $("#missao-atualizar").textContent = d.atualizando ? "Atualizando..." : "Atualizar lista";
  renderMissoes();
  return d;
}
$("#missao-busca").addEventListener("input", renderMissoes);
$("#missao-todas").addEventListener("change", renderMissoes);
$("#missao-sem-item").addEventListener("change", renderMissoes);
$("#missao-select").addEventListener("change", async e => render(await api("/api/config", { missao_id: e.target.value })));
$("#missao-atualizar").onclick = async () => {
  const d = await api("/api/missoes/atualizar", {});
  if (!d.atualizando) { alert("O bot precisa estar rodando para ler as missões do jogo."); return; }
  $("#missao-atualizar").textContent = "Atualizando...";
  const espera = setInterval(async () => { if (!(await carregarMissoes()).atualizando) clearInterval(espera); }, 2000);
};

$("#login-form").onsubmit = async ev => {
  ev.preventDefault();
  const msg = $("#login-msg");
  const d = await api("/api/login", { usuario: $("#login-usuario").value, senha: $("#login-senha").value });
  msg.dataset.fixo = "1";
  if (d.erro) { msg.textContent = d.erro; msg.className = "aviso"; }
  else { msg.textContent = "Login salvo."; msg.className = ""; $("#login-senha").value = ""; render(d); }
  setTimeout(() => { delete msg.dataset.fixo; msg.className = ""; }, 4000);
};

$("#iniciar").onclick = async () => render(await api("/api/iniciar", {}));
$("#parar").onclick = async () => render(await api("/api/parar", {}));

async function atualizar() { try { render(await api("/api/estado")); } catch (e) { $("#badge").textContent = "Painel desconectado"; } }
carregarMissoes().then(atualizar);
setInterval(atualizar, 2000);
</script>
</body>
</html>
"""


def main():
    servidor = ThreadingHTTPServer(("127.0.0.1", PORTA), Handler)
    url = f"http://127.0.0.1:{PORTA}"
    print(f"Painel em {url}  (Ctrl+C para sair)")
    webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if controle.rodando:
            controle.parar.set()
            controle.thread.join(timeout=30)
        servidor.server_close()


if __name__ == "__main__":
    main()
