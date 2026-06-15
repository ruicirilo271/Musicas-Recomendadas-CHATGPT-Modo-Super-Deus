# -*- coding: utf-8 -*-

import os
import json
import re
import secrets
import requests

from flask import Flask, render_template, jsonify, request, session, redirect
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

app.secret_key = os.getenv("SECRET_KEY", "troca-esta-chave-super-deus")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
YOUTUBE_REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI", "").strip()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"

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


def get_base_url():
    if YOUTUBE_REDIRECT_URI:
        return YOUTUBE_REDIRECT_URI.replace("/oauth2callback", "").rstrip("/")

    host = request.headers.get("X-Forwarded-Host", request.host)
    proto = request.headers.get("X-Forwarded-Proto", request.scheme)
    return f"{proto}://{host}".rstrip("/")


def get_redirect_uri():
    if YOUTUBE_REDIRECT_URI:
        return YOUTUBE_REDIRECT_URI

    return f"{get_base_url()}/oauth2callback"


def youtube_headers():
    token = session.get("youtube_access_token", "")

    if not token:
        return None

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "ok": True,
        "app": "ChatGPT Music Super Deus",
        "openai_key_ready": bool(OPENAI_API_KEY),
        "youtube_api_key_ready": bool(YOUTUBE_API_KEY),
        "youtube_oauth_ready": bool(YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET),
        "youtube_logged_in": bool(session.get("youtube_access_token")),
        "model": OPENAI_MODEL
    })


@app.route("/login-youtube")
def login_youtube():
    if not YOUTUBE_CLIENT_ID or not YOUTUBE_CLIENT_SECRET:
        return jsonify({
            "ok": False,
            "error": "Faltam YOUTUBE_CLIENT_ID ou YOUTUBE_CLIENT_SECRET nas variáveis de ambiente."
        }), 500

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    params = {
        "client_id": YOUTUBE_CLIENT_ID,
        "redirect_uri": get_redirect_uri(),
        "response_type": "code",
        "scope": YOUTUBE_SCOPE,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state
    }

    url = GOOGLE_AUTH_URL + "?" + requests.compat.urlencode(params)
    return redirect(url)


@app.route("/oauth2callback")
def oauth2callback():
    error = request.args.get("error", "")

    if error:
        return f"Erro no login Google: {error}", 400

    state = request.args.get("state", "")
    code = request.args.get("code", "")

    if not state or state != session.get("oauth_state"):
        return "Estado OAuth inválido.", 400

    if not code:
        return "Código OAuth não recebido.", 400

    data = {
        "code": code,
        "client_id": YOUTUBE_CLIENT_ID,
        "client_secret": YOUTUBE_CLIENT_SECRET,
        "redirect_uri": get_redirect_uri(),
        "grant_type": "authorization_code"
    }

    try:
        r = requests.post(GOOGLE_TOKEN_URL, data=data, timeout=15)
        token_data = r.json()

        if r.status_code != 200:
            return f"Erro ao obter token: {token_data}", 500

        session["youtube_access_token"] = token_data.get("access_token", "")
        session["youtube_refresh_token"] = token_data.get("refresh_token", "")
        session["youtube_token_type"] = token_data.get("token_type", "Bearer")

        return redirect("/")

    except Exception as e:
        return f"Erro OAuth: {str(e)}", 500


@app.route("/logout-youtube")
def logout_youtube():
    session.pop("youtube_access_token", None)
    session.pop("youtube_refresh_token", None)
    session.pop("youtube_token_type", None)
    session.pop("oauth_state", None)
    return redirect("/")


@app.route("/api/youtube/liked", methods=["GET"])
def youtube_liked():
    headers = youtube_headers()

    if not headers:
        return jsonify({
            "ok": False,
            "login_required": True,
            "error": "Tens de iniciar sessão com o YouTube primeiro."
        }), 401

    try:
        max_results = int(request.args.get("max", 50))
    except Exception:
        max_results = 50

    max_results = max(5, min(max_results, 50))

    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "part": "snippet,contentDetails",
        "myRating": "like",
        "maxResults": max_results
    }

    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        data = r.json()

        if r.status_code != 200:
            return jsonify({
                "ok": False,
                "error": data.get("error", {}).get("message", "Erro ao buscar vídeos gostados.")
            }), r.status_code

        videos = []

        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            video_id = item.get("id", "")

            title = snippet.get("title", "")
            channel = snippet.get("channelTitle", "")

            thumbs = snippet.get("thumbnails", {})
            thumbnail = ""

            if "high" in thumbs:
                thumbnail = thumbs["high"].get("url", "")
            elif "medium" in thumbs:
                thumbnail = thumbs["medium"].get("url", "")
            elif "default" in thumbs:
                thumbnail = thumbs["default"].get("url", "")

            videos.append({
                "videoId": video_id,
                "title": title,
                "channelTitle": channel,
                "thumbnail": thumbnail,
                "watchUrl": f"https://www.youtube.com/watch?v={video_id}",
                "text": f"{title} - {channel}"
            })

        return jsonify({
            "ok": True,
            "count": len(videos),
            "videos": videos
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


@app.route("/api/recommendations", methods=["POST"])
def recommendations():
    if not client:
        return jsonify({
            "ok": False,
            "error": "OPENAI_API_KEY não encontrada. Coloca a chave da OpenAI no Vercel."
        }), 500

    data = request.get_json(silent=True) or {}

    liked_videos = data.get("liked_videos", [])
    mood = str(data.get("mood", "")).strip()
    genres = str(data.get("genres", "")).strip()
    amount = data.get("amount", 20)

    try:
        amount = int(amount)
    except Exception:
        amount = 20

    amount = max(5, min(amount, 40))

    liked_lines = []

    for video in liked_videos[:50]:
        title = str(video.get("title", "")).strip()
        channel = str(video.get("channelTitle", "")).strip()

        if title:
            liked_lines.append(f"- {title} | Canal: {channel}")

    if not liked_lines:
        liked_lines = [
            "- Adele - Easy On Me",
            "- Rihanna - Diamonds",
            "- The Weeknd - Blinding Lights",
            "- Nininho Vaz Maia - Calon",
            "- Roberto Carlos - Detalhes",
            "- Boss AC - Sexta-feira"
        ]

    system_prompt = """
És um especialista mundial em recomendações musicais.

Tens de analisar vídeos gostados no YouTube e perceber o gosto musical do utilizador.
Deves recomendar músicas reais e boas para tocar numa playlist.

Tens de devolver APENAS JSON válido.
Não uses Markdown.
Não uses texto fora do JSON.
Não inventes músicas impossíveis.
A ordem deve funcionar como uma playlist para tocar seguida.

Formato obrigatório:

{
  "playlist_name": "nome criativo da playlist",
  "description": "descrição curta baseada nos likes do YouTube",
  "taste_summary": "resumo curto do gosto musical detetado",
  "tracks": [
    {
      "artist": "Nome do artista",
      "title": "Nome da música",
      "reason": "Motivo curto ligado aos vídeos gostados",
      "youtube_query": "Nome do artista Nome da música official music video",
      "vibe": "romântica / energia / calma / kizomba / pop / R&B / etc",
      "estimated_seconds": 240
    }
  ]
}
"""

    user_prompt = f"""
Cria uma playlist com exatamente {amount} músicas recomendadas.

Estas recomendações têm de ser baseadas nos vídeos que o utilizador deu like no YouTube:

{chr(10).join(liked_lines)}

Preferências adicionais:
- Estado de espírito: {mood or "boa vibe, músicas para ouvir seguidas"}
- Géneros preferidos adicionais: {genres or "pop, kizomba, R&B, soul, música portuguesa, afro pop"}

Regras:
- Baseia as recomendações nos vídeos gostados.
- Recomenda exatamente {amount} músicas.
- Não repitas a mesma música.
- Não recomendes apenas os mesmos vídeos gostados; recomenda músicas parecidas também.
- Mistura músicas conhecidas com descobertas boas.
- A playlist deve começar forte e depois manter boa energia.
- Cada youtube_query deve encontrar muito bem a música no YouTube.
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
                "reason": reason or "Combina com os vídeos que deste like no YouTube.",
                "youtube_query": youtube_query,
                "vibe": vibe or "boa vibe",
                "estimated_seconds": estimated_seconds
            })

        return jsonify({
            "ok": True,
            "playlist_name": parsed.get("playlist_name", "Playlist Super Deus"),
            "description": parsed.get("description", "Músicas recomendadas pelo ChatGPT com base nos teus likes do YouTube."),
            "taste_summary": parsed.get("taste_summary", "Gosto musical analisado com base nos vídeos gostados."),
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