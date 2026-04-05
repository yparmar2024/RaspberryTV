import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

os.environ["DISPLAY"] = ":0"
os.environ["XAUTHORITY"] = "/home/rpitv/.Xauthority"

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "raspberrytv-secret")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

TMDB_ACCESS_TOKEN = os.getenv("TMDB_ACCESS_TOKEN", "")
TMDB_URL    = "https://api.themoviedb.org/3"
TMDB_IMG    = "https://image.tmdb.org/t/p/w500"
TMDB_IMG_LG = "https://image.tmdb.org/t/p/w1280"
TMDB_IMG_SM = "https://image.tmdb.org/t/p/w300"


def tmdb(path, params=None):
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {TMDB_ACCESS_TOKEN}"
    }
    try:
        r = requests.get(f"{TMDB_URL}{path}", headers=headers, params=params, timeout=8)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


# ── Search ────────────────────────────────────────────────────────────────────

@app.route("/api/search")
def api_search():
    q    = request.args.get("q", "").strip()
    kind = request.args.get("type", "multi")
    if not q:
        return jsonify({"error": "missing q"}), 400

    paths = {
        "multi": ("/search/multi", {"query": q, "include_adult": "false"}),
        "movie": ("/search/movie", {"query": q}),
        "tv":    ("/search/tv",    {"query": q}),
    }
    if kind not in paths:
        return jsonify({"error": "invalid type"}), 400

    data = tmdb(*paths[kind])
    if not data:
        return jsonify({"results": []})

    results = []
    for item in data.get("results", []):
        media = item.get("media_type", kind)
        if media not in ("movie", "tv"):
            continue
        poster = item.get("poster_path")
        results.append({
            "tmdbId":   item["id"],
            "type":     media,
            "title":    item.get("title") or item.get("name", "Unknown"),
            "poster":   f"{TMDB_IMG}{poster}" if poster else None,
            "year":     (item.get("release_date") or item.get("first_air_date") or "")[:4],
            "rating":   round(item.get("vote_average", 0), 1),
            "overview": item.get("overview", ""),
        })

    return jsonify({"results": results, "total": data.get("total_results", len(results))})


# ── Details ───────────────────────────────────────────────────────────────────

@app.route("/api/details/<media_type>/<int:tmdb_id>")
def api_details(media_type, tmdb_id):
    if media_type not in ("movie", "tv"):
        return jsonify({"error": "invalid type"}), 400

    data = tmdb(f"/{media_type}/{tmdb_id}", {"append_to_response": "credits,videos"})
    if not data:
        return jsonify({"error": "not found"}), 404

    poster   = data.get("poster_path")
    backdrop = data.get("backdrop_path")
    genres   = [g["name"] for g in data.get("genres", [])]
    cast     = [
        {
            "name":      p["name"],
            "character": p.get("character", ""),
            "photo":     f"{TMDB_IMG}{p['profile_path']}" if p.get("profile_path") else None,
        }
        for p in data.get("credits", {}).get("cast", [])[:8]
    ]

    trailer_key = next(
        (v["key"] for v in data.get("videos", {}).get("results", [])
         if v.get("site") == "YouTube" and v.get("type") == "Trailer"),
        None
    )

    result = {
        "tmdbId":      data["id"],
        "type":        media_type,
        "title":       data.get("title") or data.get("name"),
        "tagline":     data.get("tagline", ""),
        "overview":    data.get("overview", ""),
        "rating":      round(data.get("vote_average", 0), 1),
        "vote_count":  data.get("vote_count", 0),
        "genres":      genres,
        "poster":      f"{TMDB_IMG}{poster}" if poster else None,
        "backdrop":    f"{TMDB_IMG_LG}{backdrop}" if backdrop else None,
        "trailer_key": trailer_key,
        "cast":        cast,
    }

    if media_type == "movie":
        result["release_date"] = data.get("release_date", "")
        result["runtime"]      = data.get("runtime")
    else:
        result["first_air_date"]     = data.get("first_air_date", "")
        result["number_of_seasons"]  = data.get("number_of_seasons", 1)
        result["number_of_episodes"] = data.get("number_of_episodes")
        result["status"]             = data.get("status", "")

    return jsonify(result)


# ── TV Season ─────────────────────────────────────────────────────────────────

@app.route("/api/tv/<int:tmdb_id>/season/<int:season_number>")
def api_season(tmdb_id, season_number):
    data = tmdb(f"/tv/{tmdb_id}/season/{season_number}")
    if not data:
        return jsonify({"error": "not found"}), 404

    episodes = []
    for ep in data.get("episodes", []):
        still = ep.get("still_path")
        episodes.append({
            "episode_number": ep["episode_number"],
            "name":           ep.get("name", f"Episode {ep['episode_number']}"),
            "overview":       ep.get("overview", ""),
            "air_date":       ep.get("air_date", ""),
            "runtime":        ep.get("runtime"),
            "still":          f"{TMDB_IMG_SM}{still}" if still else None,
        })

    return jsonify({
        "season_number": season_number,
        "name":          data.get("name", f"Season {season_number}"),
        "episodes":      episodes,
    })


# ── Trending ──────────────────────────────────────────────────────────────────

@app.route("/api/trending")
def api_trending():
    kind   = request.args.get("type", "all")
    window = request.args.get("window", "week")
    data   = tmdb(f"/trending/{kind}/{window}")
    if not data:
        return jsonify({"results": []})

    results = []
    for item in data.get("results", [])[:20]:
        media = item.get("media_type", kind)
        if media not in ("movie", "tv"):
            continue
        poster = item.get("poster_path")
        results.append({
            "tmdbId":   item["id"],
            "type":     media,
            "title":    item.get("title") or item.get("name", "Unknown"),
            "poster":   f"{TMDB_IMG}{poster}" if poster else None,
            "year":     (item.get("release_date") or item.get("first_air_date") or "")[:4],
            "rating":   round(item.get("vote_average", 0), 1),
            "overview": item.get("overview", ""),
        })

    return jsonify({"results": results})


# ── WebSocket ─────────────────────────────────────────────────────────────────

VALID_COMMANDS = {"up", "down", "left", "right", "enter", "back", "home", "search"}

@socketio.on("command")
def handle_command(data):
    cmd = data.get("cmd", "")
    if cmd not in VALID_COMMANDS:
        return
    payload = {"cmd": cmd}
    if cmd == "search":
        payload["query"] = data.get("query", "").strip()
    emit("command", payload, broadcast=True, include_self=False)


# ── Static ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/remote")
def remote():
    return send_from_directory(".", "remote.html")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)