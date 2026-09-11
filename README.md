# langsmith_estudo — Agente da Prefeitura de Timon

Laboratório de estudo sobre **como agentes de IA realmente funcionam** — não a
mágica, mas a mecânica. Um assistente municipal (clima, população e serviços de
Timon) usado para materializar os conceitos em código, com observabilidade
(LangSmith) desde o início.

## Stack

- **LLM:** `gpt-oss-20b` via [Groq](https://groq.com)
- **Observabilidade:** [LangSmith](https://smith.langchain.com) (`@traceable`)
- **API externa:** [Open-Meteo](https://open-meteo.com) (geocoding + forecast)

## Estrutura

| Arquivo    | Responsabilidade                                                        |
|------------|-------------------------------------------------------------------------|
| `main.py`  | Definições: client Groq, tools, `TOOLS_MAP` e o orquestrador `responder`. Módulo puro, sem execução no import. |
| `cli.py`   | Loop interativo de terminal: monta o `historico` (system prompt) e chama `responder`. |
| `.env`     | `LANGSMITH_*` e `GROQ_API_KEY` (não versionado).                         |

## Como rodar

```bash
source venv/bin/activate
python cli.py
```

## Fluxo atual

```
                      ┌─────────────────────────────────────────┐
                      │              cli.py (loop)               │
                      │  input("Você: ")  ──►  responder(...)    │
                      └───────────────────┬─────────────────────┘
                                          │
             ┌────────────────────────────▼────────────────────────────┐
             │           responder()  ── @traceable(chain)              │
             │                                                          │
             │   while True:                                            │
             │     ┌──────────────────────────────────────────────┐    │
             │     │  chamar_llm(historico, tools) ─ @traceable(llm)│    │
             │     └───────────────────┬──────────────────────────┘    │
             │                         │                                │
             │            msg.tool_calls?                               │
             │             │                    │                       │
             │          não│                 sim│                       │
             │             ▼                    ▼                       │
             │        resposta final    para cada tool_call:           │
             │        (break)           TOOLS_MAP[nome](**args)         │
             │                          ─ @traceable(tool)              │
             │                                  │                       │
             │                          resultado ► historico          │
             │                          (role: "tool")                 │
             │                                  │                       │
             │                          volta ao topo do while ────────┤
             └──────────────────────────────────────────────────────────┘

   Tools (workers):
     • get_weather   → Open-Meteo (geocoding → forecast)  [dado real]
     • get_populacao → base local
     • get_servicos  → base local (agua | iluminacao | coleta)
```

Cada pergunta vira **um trace** no LangSmith: um `chain` (`agente_municipio`)
com runs `llm` (`groq_chat`) e `tool` aninhadas.

---

## O que estou estudando (e onde o código se encaixa)

### 1) O modelo — o laço é meu, não do modelo
> LLM é função sem estado: entra texto, sai texto. "Agente" é o laço que você escreve em volta dele.

O laço é a função `responder()`. O `while True` é literalmente "o laço em volta
do modelo". A cada volta passo o `historico` inteiro — o modelo não tem memória
nem controle. **Quem controla o laço sou eu** (estrutura fixa), o lado mais
previsível do espectro, oposto de um agente autônomo.

### 2) Tool use — o único jeito de tocar o mundo
> O modelo pede, seu código executa, o resultado volta pro contexto.

1. **Modelo pede** → `msg.tool_calls`
2. **Código executa** → `TOOLS_MAP[nome](**args)`
3. **Resultado volta** → `historico.append({"role": "tool", ...})`

`get_weather` chama a **Open-Meteo** de verdade — a prova concreta de "tocar o
mundo": o laço depende de dado externo real, não inventado.

### 3) Os cinco padrões de composição — onde o nosso está
Na base, isto é o **"augmented LLM"** (LLM + tools num laço), o tijolo embaixo
dos cinco padrões. Quando o modelo dispara **múltiplas tools numa solicitação**
(ex: "vazamento de água + clima"), se aproxima de **orchestrator-workers**: o LLM
orquestra quais workers (tools) acionar. Não é *prompt chaining* clássico
(etapas fixas) — é dispatch dinâmico.

### 4) Graph engineering — o que ainda NÃO fiz (de propósito)
Hoje `responder()` é o "if/else espalhado" (`while` + `if msg.tool_calls`).
Falta nó, aresta, estado compartilhado e ponto de retomada — território do
**LangGraph**. O objetivo não é "usar LangGraph", é entender **quando compensa**:
ramificação real, trabalho longo, retomar de onde parou. Meu caso ainda é
simples demais para justificar — saber isso *é* o aprendizado.

### 5) Context engineering + avaliação — a fundação já plantada
- **Context engineering:** o system prompt (escopo + "nunca invente dados") e o
  gerenciamento do `historico` são "decidir o que entra na janela". Vi ao vivo
  quando o modelo omitiu "cidade do Maranhão" e resolvi via system prompt.
- **Avaliação:** ainda não fiz, mas o pré-requisito está pronto — o **LangSmith
  tracing** (`@traceable`). Sem enxergar o que o modelo faz, não dá para avaliar.

---

## Próximos passos

**Item 4 — Graph engineering (quando/se compensar)**
- [ ] Reescrever `responder()` como grafo explícito no LangGraph (nós: `llm`, `tools`; aresta condicional em `tool_calls`).
- [ ] Introduzir estado compartilhado tipado em vez de mutar `historico` na mão.
- [ ] Experimentar checkpointing (ponto de retomada) e avaliar se o caso realmente pede isso.

**Item 5 — Context engineering + avaliação**
- [ ] Transformar traces do LangSmith em um **dataset** de exemplos.
- [ ] Escrever evals: escolha correta de tool, fidelidade ao resultado da tool, respeito ao escopo (recusar fora de serviços/clima/população).
- [ ] Medir efeito de mudanças de system prompt / `temperature` **antes vs. depois** com os evals.

**Melhorias pontuais**
- [ ] Usar o `weathercode` do Open-Meteo para descrever a condição (ensolarado, chuva, etc.).
- [ ] Gerar a lista `tools` (schemas JSON) automaticamente a partir do `TOOLS_MAP`, evitando manter dois lugares em sincronia.
- [ ] `api.py`: expor `responder` via FastAPI.

---

## Referências

- [Building Effective AI Agents — Anthropic (dez/2024)](https://www.anthropic.com/engineering/building-effective-agents)
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [Effective Context Engineering — Anthropic](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [12-Factor Agents](https://github.com/humanlayer/12-factor-agents)
- [Your AI Product Needs Evals — Hamel Husain](https://hamel.dev/blog/posts/evals/)
- [AI Engineering — Chip Huyen (O'Reilly)](https://www.oreilly.com/library/view/ai-engineering/9781098166298/)
