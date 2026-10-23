"""Exemplo do protocolo Nous; NÃO chama IA nem executa ferramentas."""
import json
import sys


def main():
    request = json.load(sys.stdin)
    result = {
        "text": (
            "[EXEMPLO DE ADAPTADOR — sem IA] "
            f"Recebida etapa {request['stage']} do projeto {request['project']}; "
            f"{len(request['memories'])} memórias e {len(request['previous'])} saídas anteriores."
        )
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
