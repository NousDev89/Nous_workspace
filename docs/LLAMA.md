# Llama isolado

O perfil local usa o servidor oficial do llama.cpp, em contêiner Docker, com um arquivo GGUF
fornecido manualmente. A imagem oficial oferece a variante server e aceita um GGUF via -m.

## Limites adotados

| Recurso | Limite |
| --- | --- |
| RAM do contêiner | 5 GB |
| CPU | 2 vCPUs |
| Processos | 128 |
| Contexto | 1024 tokens |
| Requisições paralelas | 1 |
| Porta exposta | somente 127.0.0.1:8081 |
| Modelo | aproximadamente 3B, quantização Q4, formato GGUF |

O limite de 5 GB é para a RAM do contêiner, não para a VRAM. Arquivos Q4 desse porte costumam
caber nesse limite com contexto pequeno, mas o consumo final depende do arquivo GGUF, do contexto
e da versão do runtime. Verifique o uso real após iniciar antes de confiar nessa rota.

## Iniciar localmente

    Copy-Item .env.llama.example .env.llama
    New-Item -ItemType Directory -Force models
    # Coloque manualmente o GGUF em .\models e ajuste LLAMA_MODEL_FILE em .env.llama
    docker compose --env-file .env.llama -f docker-compose.llama.yml up -d
    docker compose -f docker-compose.llama.yml ps

O compose não baixa modelos. O volume de modelos é somente leitura e o servidor não é publicado
fora da máquina. Pare a rota com:

    docker compose --env-file .env.llama -f docker-compose.llama.yml down

## GPU em nuvem

Para usar GPU, crie uma VM ou um serviço de contêiner que ofereça GPU, execute o mesmo compose
adaptado à plataforma e mantenha o servidor em rede privada. O endpoint deve ficar atrás de TLS,
autenticação e uma regra de entrada que permita apenas o Nous Workstation.

Antes de conectar a memória compartilhada ou arquivos do projeto, valide o adaptador com uma tarefa
sem dados sensíveis. Credenciais e URL da nuvem devem ficar fora do Git, por exemplo em variáveis de
ambiente do adaptador.

Referência: https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md
