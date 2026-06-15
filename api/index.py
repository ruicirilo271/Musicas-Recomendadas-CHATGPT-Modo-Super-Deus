# -*- coding: utf-8 -*-

import os
import json
import re
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, "templates"),
    static_folder=os.path.join(ROOT_DIR, "static"),
    static_url_path="/static"
)

CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def extract_json(text):
    if not text:
        raise ValueError("Resposta vazia da OpenAI.")

    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("Não foi possível encontrar JSON válido na resposta.")

    return json.loads(match.group(0))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "ok": True,
        "app": "Músicas Recomendadas ChatGPT Super Deus",
        "openai_key_ready": bool(OPENAI_API_KEY),
        "model": OPENAI_MODEL
    })


@app.route("/api/recommendations", methods=["POST"])
def recommendations():
    if not client:
        return jsonify({
            "ok": False,
            "error": "OPENAI_API_KEY não encontrada. No Vercel coloca a variável de ambiente OPENAI_API_KEY."
        }), 500

    data = request.get_json(silent=True) or {}

    mood = str(data.get("mood", "")).strip()
    artists = str(data.get("artists", "")).strip()
    genres = str(data.get("genres", "")).strip()
    language = str(data.get("language", "")).strip()
    amount = data.get("amount", 20)

    try:
        amount = int(amount)
    except Exception:
        amount = 20

    amount = max(5, min(amount, 40))

    default_artists = "Adele, Rihanna, The Weeknd, Nininho Vaz Maia, Roberto Carlos, Boss AC, Matias Damásio"
    default_genres = "pop, kizomba, R&B, soul, música romântica, música portuguesa, afro pop"
    default_mood = "músicas boas para ouvir seguidas, com vibe romântica, moderna e viciante"
    default_language = "português, inglês, kizomba, pop, soul e R&B"

    system_prompt = """
És um especialista mundial em recomendações musicais.

Tens de devolver APENAS JSON válido.
Não uses Markdown.
Não uses texto fora do JSON.
Não inventes músicas impossíveis.
Recomenda músicas reais.
A ordem deve funcionar como uma playlist para tocar seguida.

Formato obrigatório:

{
  "playlist_name": "nome criativo da playlist",
  "description": "descrição curta da playlist",
  "tracks": [
    {
      "artist": "Nome do artista",
      "title": "Nome da música",
      "reason": "Motivo curto da recomendação",
      "youtube_query": "Nome do artista Nome da música official music video",
      "vibe": "romântica / energia / calma / kizomba / pop / R&B / etc",
      "estimated_seconds": 240
    }
  ]
}
"""

    user_prompt = f"""
Cria uma playlist com {amount} músicas recomendadas.

Preferências do utilizador:
- Estado de espírito: {mood or default_mood}
- Artistas de referência: {artists or default_artists}
- Géneros: {genres or default_genres}
- Idiomas/estilos: {language or default_language}

Regras:
- Recomenda exatamente {amount} músicas.
- Não repitas artistas demasiadas vezes.
- Mistura músicas muito conhecidas com algumas descobertas boas.
- A playlist tem de começar forte.
- Depois deve manter boa energia para tocar seguida.
- Cada youtube_query tem de ser excelente para encontrar a música no YouTube.
- estimated_seconds deve ser a duração aproximada da música em segundos.
"""

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )

        text = response.output_text.strip()
        parsed = extract_json(text)

        raw_tracks = parsed.get("tracks", [])
        cleaned_tracks = []
        used = set()

        for track in raw_tracks:
            artist = str(track.get("artist", "")).strip()
            title = str(track.get("title", "")).strip()
            reason = str(track.get("reason", "")).strip()
            youtube_query = str(track.get("youtube_query", "")).strip()
            vibe = str(track.get("vibe", "")).strip()

            try:
                estimated_seconds = int(track.get("estimated_seconds", 240))
            except Exception:
                estimated_seconds = 240

            estimated_seconds = max(120, min(estimated_seconds, 480))

            if not artist or not title:
                continue

            key = f"{artist.lower()}---{title.lower()}"
            if key in used:
                continue

            used.add(key)

            if not youtube_query:
                youtube_query = f"{artist} {title} official music video"

            cleaned_tracks.append({
                "artist": artist,
                "title": title,
                "reason": reason or "Combina com o teu gosto musical.",
                "youtube_query": youtube_query,
                "vibe": vibe or "boa vibe",
                "estimated_seconds": estimated_seconds
            })

        return jsonify({
            "ok": True,
            "playlist_name": parsed.get("playlist_name", "Playlist Super Deus"),
            "description": parsed.get("description", "Músicas recomendadas pelo ChatGPT."),
            "tracks": cleaned_tracks
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    print("")
    print("✨ Músicas Recomendadas ChatGPT Super Deus iniciado")
    print("🌐 Abre: http://127.0.0.1:5000")
    print("")
    app.run(host="127.0.0.1", port=5000, debug=True)