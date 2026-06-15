# -*- coding: utf-8 -*-

import os
import json
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)
CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


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
            "error": "OPENAI_API_KEY não encontrada. Verifica o ficheiro .env."
        }), 500

    data = request.get_json(silent=True) or {}

    mood = data.get("mood", "").strip()
    artists = data.get("artists", "").strip()
    genres = data.get("genres", "").strip()
    language = data.get("language", "português, inglês, kizomba, pop, soul, R&B").strip()
    amount = int(data.get("amount", 20))

    if amount < 5:
        amount = 5

    if amount > 40:
        amount = 40

    user_profile = f"""
Quero recomendações musicais para tocar numa aplicação web.

Preferências:
- Estado de espírito: {mood or "mistura boa para ouvir sem parar"}
- Artistas de referência: {artists or "Adele, Rihanna, The Weeknd, Nininho Vaz Maia, Roberto Carlos, Boss AC, Matias Damásio"}
- Géneros: {genres or "pop, kizomba, R&B, soul, música romântica, música portuguesa"}
- Idiomas/estilo: {language}

Regras:
- Recomenda {amount} músicas reais.
- Evita músicas repetidas.
- Mistura músicas conhecidas com algumas descobertas.
- A ordem deve funcionar como uma playlist: começa forte, depois mantém bom ritmo.
- Cada item deve ter artista, título, motivo curto e uma query boa para procurar no YouTube.
"""

    system_prompt = """
És um especialista em recomendações musicais.
Tens de devolver APENAS JSON válido.
Não uses Markdown.
Não expliques nada fora do JSON.

Formato obrigatório:

{
  "playlist_name": "nome criativo da playlist",
  "description": "descrição curta",
  "tracks": [
    {
      "artist": "Artista",
      "title": "Título da música",
      "reason": "Motivo curto",
      "youtube_query": "Artista Título official music video",
      "vibe": "romântica / energia / calma / kizomba / pop / etc"
    }
  ]
}
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
                    "content": user_profile
                }
            ]
        )

        text = response.output_text.strip()

        try:
            parsed = json.loads(text)
        except Exception:
            start = text.find("{")
            end = text.rfind("}") + 1
            parsed = json.loads(text[start:end])

        tracks = parsed.get("tracks", [])

        cleaned_tracks = []

        for track in tracks:
            artist = str(track.get("artist", "")).strip()
            title = str(track.get("title", "")).strip()
            reason = str(track.get("reason", "")).strip()
            vibe = str(track.get("vibe", "")).strip()
            youtube_query = str(track.get("youtube_query", "")).strip()

            if not youtube_query:
                youtube_query = f"{artist} {title} official music video"

            if artist and title:
                cleaned_tracks.append({
                    "artist": artist,
                    "title": title,
                    "reason": reason or "Combina com o teu gosto musical.",
                    "vibe": vibe or "boa vibe",
                    "youtube_query": youtube_query
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