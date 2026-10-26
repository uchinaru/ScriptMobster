# Planejamento: venda de acesso mensal ao bot

> Status: **ideia para o futuro**. Nada disso foi implementado ainda.

## 1. Riscos (resolver antes de investir)

Quase todo jogo online proíbe bots nos termos de uso, e vender um bot transforma isso em atividade comercial.

- **Banimento dos clientes**, e da conta do dono do bot. Gera cancelamento e pedido de reembolso.
- **O jogo pode quebrar o bot a qualquer momento**, mudando o HTML. Quem paga mensalidade cobra conserto rápido.
- **Conflito com a receita do jogo.** Ele vende energia, stamina e refills por Favor points, e o bot reduz essa venda. Isso pode gerar reação, inclusive jurídica, ainda mais se o nome ou as marcas do jogo forem usados na divulgação.
- **Plataformas de pagamento** (Stripe, Mercado Pago, Hotmart) costumam proibir "cheats ou ferramentas que violam termos de terceiros" e podem bloquear a conta.
- O código do jogo tem proteções: script ofuscado, checagem de domínio protegido e funções do DOM sobrescritas. Ou seja, eles se importam com automação.

**Primeiro passo:** ler os termos completos do jogo e falar com o desenvolvedor pelo Customer Service. Uma parceria ou autorização (por exemplo, dividir receita) elimina quase todos esses riscos.

## 2. Arquitetura recomendada

O bot roda no computador do cliente e é liberado por uma chave de licença.

```
Cliente paga ──► plataforma de pagamento ──webhook──► servidor de licenças (API + banco)
                                                           ▲
Bot no PC do cliente ── valida a chave ao iniciar e a cada X horas ──┘
```

Por que não hospedar os bots em servidores próprios:

- **A senha do jogo fica com o cliente.** Não guardamos senha de terceiros, o que evita uma grande responsabilidade perante a LGPD.
- **Custo.** Cada Chrome usa de 300 a 500 MB de RAM, e hospedar muitos clientes exige servidor grande.
- **Detecção.** Com todos os bots saindo dos mesmos IPs, o jogo detecta e bane todos de uma vez.

## 3. Peças a construir

| Peça | Descrição | Esforço |
|---|---|---|
| Servidor de licenças | API pequena (FastAPI + SQLite/Postgres) com rotas de ativar e validar. Liga a chave ao computador e tem tolerância offline de algumas horas. | Baixo |
| Integração de pagamento | Webhook de assinatura (pagou, renovou, cancelou ou atrasou) que ativa ou desativa a chave | Baixo |
| Licença no bot e no painel | Campo de chave no painel; o bot valida ao iniciar e periodicamente | Baixo |
| Instalador | PyInstaller gera `.exe`/`.app`, então o cliente não precisa instalar Python | Médio |
| Atualização automática | Indispensável, porque o jogo muda. Seletores carregados do servidor ajudam a corrigir sem lançar versão nova. | Médio |
| Relatório de erros | O bot envia os erros ao servidor para corrigir antes do cliente reclamar | Baixo |

**Sobre pirataria:** Python é fácil de copiar e de crackear. Ofuscação (PyArmor, Nuitka) só atrasa. A proteção real é o servidor: atualizações e seletores só chegam para licença válida.

## 4. Pagamento recorrente

- **Hotmart, Kiwify ou Eduzz:** o mais simples. Já têm assinatura, área do cliente, afiliados e webhook.
- **Mercado Pago ou Stripe:** taxa menor, mas dá mais trabalho.
- Conferir em cada uma a política sobre ferramentas para jogos antes de criar a conta.

## 5. Burocracia

- MEI ou CNPJ e emissão de nota fiscal (algumas plataformas emitem por você).
- Termos de uso e política de privacidade próprios, incluindo que o cliente assume o risco perante o jogo.
- Reembolso: 7 dias de arrependimento previstos no Código de Defesa do Consumidor.
- Não usar o nome nem o logo do jogo como marca do produto.

## 6. Roteiro

- [ ] **Validar:** ler os termos do jogo e falar com o desenvolvedor
- [ ] **Beta:** 5 a 10 jogadores grátis ou baratinho; medir quanto tempo o bot fica sem quebrar e quanto suporte exige
- [ ] **Servidor de licenças** e checagem da chave no painel
- [ ] **Instalador** para Windows e macOS
- [ ] **Atualização automática** e seletores remotos
- [ ] **Relatório de erros**
- [ ] **Pagamento** com webhook e página de venda simples
- [ ] **Burocracia:** CNPJ, nota fiscal, termos de uso
