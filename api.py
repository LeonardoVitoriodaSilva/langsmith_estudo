from fastapi import FastAPI
from pydantic import BaseModel
from main import responder

app = FastAPI()

class Pergunta(BaseModel):
    mensagem: str
    session_id: str = "default"

# Armazena histórico por sessão
sessoes = {}

@app.post("/chat")
def chat(pergunta: Pergunta):
    if pergunta.session_id not in sessoes:
        sessoes[pergunta.session_id] = [
            {
                "role": "system",
                "content": (
                    "Você é um assistente da prefeitura de Timon. "
                    "Responda apenas sobre serviços municipais, clima e população. "
                    "Use sempre as tools disponíveis para buscar informações. "
                    "Nunca invente dados."
                )
            }
        ]

    historico = sessoes[pergunta.session_id]
    resposta = responder(pergunta.mensagem, historico)

    return {"resposta": resposta, "session_id": pergunta.session_id}

@app.get("/")
def health():
    return {"status": "ok"}