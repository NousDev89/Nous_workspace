# Arquitetura de Orquestração de IA — Nous Workstation

## Visão geral

O PC local, com cerca de 12 GB de RAM, é o plano de controle: mantém o grafo, estado, roteamento,
prompts curtos, memória e interface. Modelos de API e cargas pesadas executam remotamente.

O estado de cada tarefa percorre todos os nós autorizados. A memória do projeto deve ter
proveniência, separação por projeto e exclusão explícita. A primeira implementação possui busca
textual; o alvo é SQLite-vec para uso local e pgvector para uma implantação multiusuário.

## Papéis dos nós

| Papel | Serviço preferencial | Responsabilidade |
| --- | --- | --- |
| router | Llama pequeno ou modelo econômico | Classificar o pedido e selecionar a rota |
| creative | Grok | Brainstorm, alternativas e arquitetura |
| implement | Claude Code | Implementar, editar e executar tarefas de desenvolvimento autorizadas |
| review | Codex | Revisar código, falhas, testes e otimizações |
| action | Manus | Tarefas autônomas com navegação e execução externa |
| cloud_gpu | Llama em GPU privada | Cargas próprias, repetitivas ou com dados controlados |

O roteador é uma decisão de baixo custo; ele não substitui os modelos especialistas.

## Contas e credenciais

Cada conta é uma entrada de configuração, com um nome de variável de ambiente e papéis permitidos.
O grafo escolhe a conta no estado da tarefa, permitindo rate limit, faturamento separado e failover.

O arquivo nous.config.json contém somente os nomes dessas variáveis. As chaves ficam no ambiente do
processo e nunca entram em memória, logs, tarefas, habilidades, commits ou capturas de tela.
Uma assinatura de produto não deve ser tratada como credencial de API.

## GPU em nuvem

O Llama local é opcional e isolado; seu limite de 5 GB é adequado apenas a um modelo próximo de 3B
em Q4 e contexto curto. Para inferência pesada, o mesmo papel cloud_gpu deve apontar para uma VM
com GPU. A VM precisa:

- desligar após dez minutos sem tarefas pendentes;
- manter a API em rede privada ou atrás de TLS, autenticação e lista de origem;
- expor métricas de GPU, tempo, custo e estado da instância;
- receber somente o contexto mínimo necessário da tarefa.

Vast.ai, Salad e RunPod são opções de infraestrutura que precisam de cotação e disponibilidade
verificadas no momento da contratação. Valores de GPU variam com região, capacidade, modalidade e
taxas; não estão fixados como premissa do projeto.

## Estado de grafo

O estado mínimo de uma tarefa deve conter mensagens, projeto, nó atual, conta selecionada, contexto
de memória, orçamento, endpoint opcional de GPU e eventos de auditoria. As transições são
condicionais: router seleciona creative, implement, review, action ou cloud_gpu; cada nó grava seu
resultado e retorna ao controlador para a próxima decisão.

## Fases

1. Grafo com nós simulados, seleção de contas e eventos.
2. Memória semântica com SQLite-vec e habilidades por nó.
3. Interface mínima com árvore de arquivos, terminal e Monaco Editor.
4. Adaptador de GPU em nuvem, auto-shutdown e painel de custo.

O painel vem depois do grafo funcional. A primeira versão não declara integração ou GPU como
conectada sem um teste real, credencial configurada e evidência de execução.
