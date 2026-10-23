# Nous Workstation

Estação de trabalho híbrida para orquestrar agentes, ferramentas, habilidades e memória por projeto.

## Primeira versão

- CLI em português, executável no Windows com Python 3.11 ou superior.
- Fluxo LangGraph: planejamento → execução → revisão.
- Provedor selecionável por etapa.
- SQLite para tarefas e eventos; memória compartilhada local ou semântica com Mem0.
- Habilidades Markdown e ferramentas locais com limite de diretório.
- Demonstração offline, protocolo de adaptadores externos por processo e rota para GPU em nuvem.
- Testes automatizados em Windows e Linux.

**Esta versão é uma base executável, não uma integração pronta com todos os serviços.**
Manus, OpenAI, Codex, Claude Code, Gemini e Grok têm entradas de configuração.
Os adaptadores de Grok, Claude API, Gemini e Manus já estão disponíveis. Claude Code continua como
adaptador de agente local separado.
Painel visual e MCP estão no roteiro.
A demonstração não chama modelos, não programa e não altera arquivos do projeto.

## Instalar no Windows PowerShell

Se você recebeu um ZIP, extraia-o e abra o PowerShell na pasta que contém pyproject.toml.
Nesse caso, ignore as duas primeiras linhas abaixo (clone e Set-Location).
O clone só funciona depois que a implementação for publicada no repositório.

```powershell
git clone https://github.com/NousDev89/Nous_workspace.git
Set-Location Nous_workspace
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m nous_dev init
.\.venv\Scripts\python.exe -m nous_dev status
```

Não é necessário ativar o ambiente virtual. uv, pnpm, Docker e Ollama não são necessários para
o modo de demonstração. Docker passa a ser necessário apenas para o Llama isolado.

## Execução híbrida: nuvem e Llama isolado

O Nous Workstation encaminha tarefas por perfil:

- Nuvem: OpenAI, Codex, Claude, Gemini, Grok e Manus usam suas APIs; a inferência e a GPU ficam
  no provedor.
- GPU em nuvem privada: o mesmo contêiner Llama pode ser executado em uma VM com GPU, acessível
  somente por uma API HTTPS autenticada.
- Llama local opcional: o arquivo docker-compose.llama.yml inicia um servidor llama.cpp com limite
  de 5 GB de RAM, contexto de 1024 tokens, uma sessão paralela e modelo GGUF de aproximadamente 3B em Q4.

O Llama local não usa GPU neste computador. Ele serve como rota privada de baixo custo e pode ser
lento no processador disponível. Para usar GPU, execute o mesmo perfil em uma máquina alugada com
GPU e mantenha o endpoint privado; não exponha a porta diretamente à internet.

    Copy-Item .env.llama.example .env.llama
    # Copie manualmente um arquivo GGUF confiável de ~3B/Q4 para .\models\
    docker compose --env-file .env.llama -f docker-compose.llama.yml up -d

O contêiner aceita conexões somente em 127.0.0.1:8081, monta os modelos como somente leitura e
possui limite de 5 GB. Não há download automático de modelo nem envio de dados para terceiros.

## Demonstrar a memória e o fluxo

```powershell
.\.venv\Scripts\python.exe -m nous_dev memory add --project nous "Interface e documentação em português."
.\.venv\Scripts\python.exe -m nous_dev run --project nous --prompt "Planejar um catálogo de habilidades"
.\.venv\Scripts\python.exe -m nous_dev memory search --project nous --query "português"
.\.venv\Scripts\python.exe -m nous_dev skills
```

O comando run imprime um JSON com ID, estado, etapas e resultados.
Consulte novamente com `python -m nous_dev task ID`.
No modo demo, as saídas são rotuladas como simulação.

## Adaptador externo de exemplo

O exemplo usa Python para demonstrar o protocolo de entrada/saída, sem acessar uma IA:

```powershell
.\.venv\Scripts\python.exe -m nous_dev run --project nous --prompt "Testar o protocolo" --planner bridge-example --worker bridge-example --reviewer demo --allow-commands
```

Veja [o protocolo](docs/ADAPTERS.md) antes de configurar um serviço real.
Uma assinatura de aplicativo não é automaticamente uma credencial para API.
Não coloque chaves no repositório, nas habilidades ou nas memórias.
Os dados selecionados do projeto serão enviados ao processo configurado quando o adaptador for executado.

## Grok, Manus e .env local

O Nous lê opcionalmente um arquivo `.env` na raiz, antes de carregar a configuração. O arquivo é
ignorado pelo Git; variáveis que já existam no Windows têm precedência. Copie o modelo e guarde as
chaves apenas no computador que executará as chamadas:

```powershell
Copy-Item .env.example .env
# Edite .env localmente: XAI_API_KEY=..., ANTHROPIC_API_KEY=..., GEMINI_API_KEY=... e/ou MANUS_API_KEY=...
```

Em `nous.config.json`, altere o provedor desejado para `"enabled": true`. Depois, uma chamada de
rede exige confirmação explícita na própria CLI:

```powershell
.\.venv\Scripts\python.exe -m nous_dev run --project nous --prompt "Criar alternativas" --planner grok --allow-network
.\.venv\Scripts\python.exe -m nous_dev run --project nous --prompt "Implementar o módulo" --worker claude-api --allow-network
.\.venv\Scripts\python.exe -m nous_dev run --project nous --prompt "Classificar esta tarefa" --planner gemini --allow-network
.\.venv\Scripts\python.exe -m nous_dev run --project nous --prompt "Executar pesquisa" --worker manus --allow-network
```

Grok usa a Responses API; `claude-api` usa a Messages API e retorna texto; Gemini usa
`generateContent` para texto. Isso não substitui o Claude Code com terminal e edição de arquivos.
Manus cria uma tarefa privada e assíncrona,
retornando o ID e o link; o Nous não aprova conectores, envios, compras ou outras ações externas
em nome do usuário.

## Ferramentas

```powershell
.\.venv\Scripts\python.exe -m nous_dev tool list .
.\.venv\Scripts\python.exe -m nous_dev tool read README.md
```

As ferramentas locais desta versão são invocadas pelo usuário na CLI.
O fluxo de IA ainda não possui execução automática de ferramentas.

## Validar

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

[Arquitetura](docs/ARCHITECTURE.md) · [Especificação do Workspace](docs/NOUS_WORKSPACE.md) · [GPU e Llama](docs/LLAMA.md) · [Roteiro](docs/ROADMAP.md)

A base usa SQLite com busca textual literal. A instalação anterior de mem0ai no Python global não
o torna automaticamente disponível no ambiente virtual. Para ativar a memória semântica do Mem0,
instale o extra, defina a chave fora do repositório e altere o backend:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[mem0]
$env:MEM0_API_KEY = "sua-chave-do-mem0"
# Em nous.config.json, troque memory.backend de "sqlite" para "mem0".
.\.venv\Scripts\python.exe -m nous_dev memory status
```

O `user_id` enviado ao Mem0 inclui o nome do projeto, portanto todos os nós do LangGraph recebem
o mesmo contexto daquele projeto sem acessar memórias de outro. Use `--remember-result` no comando
`run` somente para persistir a revisão final da tarefa.
