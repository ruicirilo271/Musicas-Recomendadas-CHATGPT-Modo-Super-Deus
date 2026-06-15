# -*- coding: utf-8 -*-

import os
import json
import re
import requests
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
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()

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
        raise ValueError("Não foi possível encontrar JSON válido na resposta da OpenAI.")

    return json.loads(match.group(0))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "ok": True,
        "app": "ChatGPT Music Super Deus",
        "openai_key_ready": bool(OPENAI_API_KEY),
        "youtube_key_ready": bool(YOUTUBE_API_KEY),
        "model": OPENAI_MODEL
    })


@app.route("/api/recommendations", methods=["POST"])
def recommendations():
    if not client:
        return jsonify({
            "ok": False,
            "error": "OPENAI_API_KEY não encontrada. Coloca a chave da OpenAI no Vercel."
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
    default_mood = "músicas boas para ouvir seguidas, românticas, modernas, conhecidas e com boa vibe"
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
Cria uma playlist com exatamente {amount} músicas recomendadas.

Preferências:
- Estado de espírito: {mood or default_mood}
- Artistas de referência: {artists or default_artists}
- Géneros: {genres or default_genres}
- Idiomas/estilos: {language or default_language}

Regras:
- Recomenda exatamente {amount} músicas.
- Não repitas a mesma música.
- Não repitas artistas demasiadas vezes.
- Mistura músicas conhecidas com algumas descobertas boas.
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


@app.route("/api/youtube/search", methods=["POST"])
def youtube_search():
    if not YOUTUBE_API_KEY:
        return jsonify({
            "ok": False,
            "error": "YOUTUBE_API_KEY não encontrada. Coloca a chave do YouTube no Vercel."
        }), 500

    data = request.get_json(silent=True) or {}
    query = str(data.get("query", "")).strip()

    if not query:
        return jsonify({
            "ok": False,
            "error": "Pesquisa vazia."
        }), 400

    try:
        url = "https://www.googleapis.com/youtube/v3/search"

        params = {
            "key": YOUTUBE_API_KEY,
            "part": "snippet",
            "q": query,
            "type": "video",
            "videoEmbeddable": "true",
            "maxResults": 5,
            "safeSearch": "none"
        }

        r = requests.get(url, params=params, timeout=12)
        result = r.json()

        if r.status_code != 200:
            return jsonify({
                "ok": False,
                "error": result.get("error", {}).get("message", "Erro na API do YouTube.")
            }), 500

        items = result.get("items", [])

        if not items:
            return jsonify({
                "ok": False,
                "error": "Nenhum vídeo encontrado no YouTube."
            }), 404

        best_item = None

        for item in items:
            video_id = item.get("id", {}).get("videoId")
            if video_id:
                best_item = item
                break

        if not best_item:
            return jsonify({
                "ok": False,
                "error": "Nenhum videoId válido encontrado."
            }), 404

        video_id = best_item.get("id", {}).get("videoId")
        snippet = best_item.get("snippet", {})
        thumbs = snippet.get("thumbnails", {})

        thumbnail = ""

        if "high" in thumbs:
            thumbnail = thumbs["high"].get("url", "")
        elif "medium" in thumbs:
            thumbnail = thumbs["medium"].get("url", "")
        elif "default" in thumbs:
            thumbnail = thumbs["default"].get("url", "")

        return jsonify({
            "ok": True,
            "videoId": video_id,
            "title": snippet.get("title", ""),
            "channelTitle": snippet.get("channelTitle", ""),
            "thumbnail": thumbnail,
            "watchUrl": f"https://www.youtube.com/watch?v={video_id}"
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    print("")
    print("✨ ChatGPT Music Super Deus iniciado")
    print("🌐 Abre: http://127.0.0.1:5000")
    print("")
    app.run(host="127.0.0.1", port=5000, debug=True)