from dotenv import load_dotenv
from groq import Groq
from langsmith import traceable
import requests
import json

load_dotenv()

client = Groq()

@traceable(run_type="llm", name="groq_chat")
def chamar_llm(messages, tools=None):
    kwargs = {"model": "openai/gpt-oss-20b", "messages": messages}
    if tools:
        kwargs["tools"] = tools
    return client.chat.completions.create(**kwargs)

@traceable(run_type="tool", name="get_weather")
def get_weather(cidade: str) -> str:
    # Primeiro busca as coordenadas da cidade
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": cidade, "count": 1, "language": "pt"}
    ).json()

    if not geo.get("results"):
        return f"Cidade '{cidade}' não encontrada."

    resultado = geo["results"][0]
    lat = resultado["latitude"]
    lon = resultado["longitude"]

    # Depois busca o clima
    clima = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weathercode",
            "timezone": "America/Fortaleza"
        }
    ).json()

    temp = clima["current"]["temperature_2m"]
    return f"Temperatura atual em {cidade}: {temp}°C"

@traceable(run_type="tool", name="get_populacao")
def get_populacao(cidade: str) -> str:
    populacoes = {
        "Teresina": "870.000 habitantes - capital do Piauí",
        "Timon": "170.000 habitantes - cidade do Maranhão",
        "São Paulo": "12.3 milhões de habitantes - capital de São Paulo"
    }
    return populacoes.get(cidade, "Cidade não encontrada na base.")

@traceable(run_type="tool", name="get_servicos")
def get_servicos(tipo: str) -> str:
    servicos = {
        "agua": "Ligue 0800-123-456 ou acesse saaec.gov.br para solicitar reparo de vazamento.",
        "iluminacao": "Acesse timon.ma.gov.br/iluminacao ou vá à Secretaria de Infraestrutura.",
        "coleta": "A coleta ocorre às terças e sextas. Denúncias: 0800-789-000."
    }
    return servicos.get(tipo, "Serviço não encontrado. Ligue 156 para mais informações.")

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Retorna o clima atual de uma cidade",
            "parameters": {
                "type": "object",
                "properties": {
                    "cidade": {"type": "string", "description": "Nome da cidade"}
                },
                "required": ["cidade"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_populacao",
            "description": "Retorna a população de uma cidade",
            "parameters": {
                "type": "object",
                "properties": {
                    "cidade": {"type": "string", "description": "Nome da cidade"}
                },
                "required": ["cidade"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_servicos",
            "description": "Retorna informações sobre serviços municipais de Timon",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo": {
                        "type": "string",
                        "description": "Tipo de serviço",
                        "enum": ["agua", "iluminacao", "coleta"]
                    }
                },
                "required": ["tipo"]
            }
        }
    }
]

# Mapa nome -> função, evita a cadeia de if/elif
TOOLS_MAP = {
    "get_weather": get_weather,
    "get_populacao": get_populacao,
    "get_servicos": get_servicos,
}

@traceable(run_type="chain", name="agente_municipio")
def responder(entrada, historico):
    historico.append({"role": "user", "content": entrada})

    # Loop de agente: continua enquanto o modelo pedir tools (sempre com tools=tools)
    while True:
        response = chamar_llm(historico, tools=tools)
        msg = response.choices[0].message

        if not msg.tool_calls:
            resposta = msg.content
            break

        historico.append(msg)

        for tool_call in msg.tool_calls:
            args = json.loads(tool_call.function.arguments)
            func = TOOLS_MAP.get(tool_call.function.name)
            resultado = func(**args) if func else "Tool não encontrada."

            print(f"[tool chamada: {tool_call.function.name}({args})]")
            print(f"[resultado: {resultado}]\n")

            historico.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": resultado
            })

    historico.append({"role": "assistant", "content": resposta})
    return resposta