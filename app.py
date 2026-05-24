from flask import Flask, Response
import os
import requests
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")

ACCOUNT_URL = "https://asia.api.riotgames.com"


def riot_get(url: str):
    headers = {
        "X-Riot-Token": API_KEY
    }
    return requests.get(url, headers=headers, timeout=10)


def get_rank_text(game_name: str, tag_line: str, lol_url: str):
    if not API_KEY:
        return "錯誤：找不到 RIOT_API_KEY"

    encoded_name = quote(game_name)
    encoded_tag = quote(tag_line)

    # 1. Riot ID -> PUUID
    account_url = f"{ACCOUNT_URL}/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
    r = riot_get(account_url)

    if r.status_code != 200:
        return f"{game_name}#{tag_line}：取得 PUUID 失敗，HTTP {r.status_code}"

    account_data = r.json()
    puuid = account_data.get("puuid")

    if not puuid:
        return f"{game_name}#{tag_line}：找不到 PUUID"

    # 2. PUUID -> Summoner ID
    summoner_url = f"{lol_url}/lol/summoner/v4/summoners/by-puuid/{puuid}"
    r = riot_get(summoner_url)

    if r.status_code != 200:
        return f"{game_name}#{tag_line}：取得召喚師資料失敗，HTTP {r.status_code}"

    summoner_data = r.json()
    summoner_id = summoner_data.get("id")

    if not summoner_id:
        return f"{game_name}#{tag_line}：找不到 Summoner ID"

    # 3. Summoner ID -> Ranked Data
    rank_url = f"{lol_url}/lol/league/v4/entries/by-summoner/{summoner_id}"
    r = riot_get(rank_url)

    if r.status_code != 200:
        return f"{game_name}#{tag_line}：取得牌位失敗，HTTP {r.status_code}"

    ranked_data = r.json()

    solo = next(
        (x for x in ranked_data if x.get("queueType") == "RANKED_SOLO_5x5"),
        None
    )

    if not solo:
        return f"{game_name}#{tag_line}：目前沒有單雙排資料"

    tier = solo.get("tier", "")
    rank = solo.get("rank", "")
    lp = solo.get("leaguePoints", 0)
    wins = solo.get("wins", 0)
    losses = solo.get("losses", 0)

    total = wins + losses
    winrate = (wins / total * 100) if total > 0 else 0

    return f"{game_name}#{tag_line}：{tier} {rank} {lp}LP / {wins}W-{losses}L / 勝率 {winrate:.1f}%"


@app.route("/")
def home():
    return Response("API is running", mimetype="text/plain")


@app.route("/krrank")
def krrank():
    game_name = "Collage"
    tag_line = "1224"
    lol_url = "https://kr.api.riotgames.com"

    result = get_rank_text(game_name, tag_line, lol_url)
    return Response(result, mimetype="text/plain; charset=utf-8")


@app.route("/twrank")
def twrank():
    game_name = "Ziv"
    tag_line = "5566"
    lol_url = "https://tw2.api.riotgames.com"

    result = get_rank_text(game_name, tag_line, lol_url)
    return Response(result, mimetype="text/plain; charset=utf-8")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
