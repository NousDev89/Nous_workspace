# Arquitetura inicial

A CLI carrega nous.config.json e abre .nous/nous.sqlite3.
O fluxo LangGraph executa plan → work → review sequencialmente.
Cada etapa pode usar um provedor diferente, definido por argumento.
A revisão é um resultado textual; não representa aprovação automática nem prova de correção.

Cada etapa recebe o pedido, até dez memórias recentes do projeto, habilidades selecionadas
e resultados das etapas anteriores. Tarefas e eventos persistem no banco.
Se uma etapa falhar, a tarefa fica failed e as próximas etapas não executam.
Não há retomada de checkpoints nesta versão. Reiniciar um run cria outra tarefa.

Memórias são adicionadas explicitamente pelo usuário e têm origem e horário.
As respostas dos agentes permanecem no histórico da tarefa, sem promoção automática a fatos.
A busca usa texto literal, não embeddings. O isolamento por projeto é lógico, não autenticação.
Não existe sincronização com o histórico ou a memória interna de aplicativos terceiros.

As ferramentas de leitura bloqueiam escape do diretório configurado, links para fora,
.git, .nous, .venv e arquivos .env. São chamadas manualmente.
Processos de adaptadores não são um sandbox: recebem os privilégios do usuário,
o ambiente do processo e podem acessar a rede. --allow-commands autoriza essa execução.
Configure somente adaptadores confiáveis. Não trate uma habilidade como permissão de sistema.

Esta base não possui servidor HTTP, painel, múltiplos usuários, execução paralela ou
contabilidade de cobrança. Esses módulos devem ser construídos e validados separadamente.

## Execução híbrida

O orquestrador deve encaminhar cada etapa conforme o perfil selecionado:

| Perfil | Execução | Uso previsto |
| --- | --- | --- |
| cloud-api | API do provedor | Raciocínio, código e tarefas que exigem modelos comerciais |
| cloud-gpu-private | Contêiner Llama em VM com GPU | Modelos próprios, dados controlados e cargas repetitivas |
| local-fallback | Contêiner llama.cpp no computador | Testes privados, tarefas simples e contingência |

O perfil local é limitado a 5 GB de RAM por Docker e a um modelo GGUF de aproximadamente 3B em Q4.
Ele não é uma rota de GPU neste computador. O mesmo contêiner pode ser implantado em uma máquina
alugada com GPU; nesse caso, a GPU fica inteiramente no provedor de nuvem e o endpoint precisa usar
TLS, autenticação e restrição de rede antes de receber memória ou arquivos de projetos.
