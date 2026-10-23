# Protocolo de adaptadores, versão 1

Um adaptador é um processo que lê um único objeto JSON de stdin e escreve
um único objeto JSON em stdout. Logs devem ir para stderr.

Entrada:
```json
{
  "protocol_version": 1,
  "task_id": "identificador",
  "project": "nous",
  "stage": "plan",
  "prompt": "Pedido do usuário",
  "instructions": "Instruções da etapa",
  "memories": [],
  "skills": [],
  "previous": []
}
```

Saída:
```json
{"text": "Resultado textual da etapa"}
```

Configure um argv explícito, por exemplo:
```json
{
  "kind": "command",
  "enabled": true,
  "argv": ["{python}", "adapters/meu_adaptador.py"],
  "timeout_seconds": 120
}
```

{python} é substituído pelo Python que executa o Nous.
O diretório de execução é a pasta do arquivo de configuração.
Não há shell nem interpolação de comandos. O timeout limita o processo direto;
adaptadores devem gerenciar e encerrar seus próprios subprocessos.

O exemplo bridge.py comprova o protocolo, não a integração com um provedor.
Uma CLI nativa não deve ser colocada diretamente no argv: normalmente ela não implementa
este protocolo. É necessário um adaptador que traduza a entrada e normalize a saída.

## Integrações previstas

| Serviço | Situação nesta versão |
| --- | --- |
| Manus | `kind: manus`; cria tarefa v2 assíncrona e retorna ID/link |
| OpenAI | Registro desativado; adaptador de API pendente |
| Codex | Registro desativado; adaptador de agente pendente |
| Claude Code | Registro desativado; adaptador de agente pendente |
| Gemini | Registro desativado; adaptador pendente |
| Grok | `kind: grok`; chama a Responses API da xAI |
| Demo | Fluxo local sem IA |
| bridge-example | Processo de exemplo sem IA |

A disponibilidade de API, autenticação e cobrança deve ser verificada ao implementar
cada conector. Não compartilhar cookies ou tokens de login entre produtos.
Segredos devem ser lidos do ambiente pelo adaptador; nunca gravados no JSON de saída.
Memórias são texto enviado ao provedor selecionado. Revise o conteúdo antes de executar.

Referências consultadas:
- LangGraph: https://docs.langchain.com/oss/python/langgraph/quickstart
- Gemini: https://ai.google.dev/gemini-api/docs/function-calling
- Anthropic: https://platform.claude.com/docs/en/cli-sdks-libraries/overview
- Manus: https://open.manus.im/docs/v1/api-overview (indica migração para v2)
