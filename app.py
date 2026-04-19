from flask import Flask, Response
import os
import requests
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")

HEADERS = {
    "X-Riot-Token": API_KEY
}

ACCOUNT_URL = "https://asia.api.riotgames.com"


def riot_get(url: str):
    return requests.get(url, headers=HEADERS, timeout=10)


def get_rank_text(game_name: str, tag_line: str, lol_url: str):
    if not API_KEY:
        return "錯誤：找不到 RIOT_API_KEY"

    encoded_name = quote(game_name)
    encoded_tag = quote(tag_line)

    # 1. Riot ID -> puuid
    url = f"{ACCOUNT_URL}/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
    r = riot_get(url)
    if r.status_code != 200:
        return f"取得 puuid 失敗：{r.status_code} / {r.text}"

    puuid = r.json().get("puuid")
    if not puuid:
        return f"錯誤：找不到 puuid / {r.text}"

    # 2. 先試 summoner-v4
    summoner_id = None
    url = f"{lol_url}/lol/summoner/v4/summoners/by-puuid/{puuid}"
    r = riot_get(url)
    if r.status_code == 200:
        summoner_id = r.json().get("id")

    # 3. 查牌位
    if summoner_id:
        url = f"{lol_url}/lol/league/v4/entries/by-summoner/{summoner_id}"
        r = riot_get(url)
        if r.status_code != 200:
            return f"取得牌位失敗：{r.status_code} / {r.text}"
        data = r.json()
    else:
        url = f"{lol_url}/lol/league/v4/entries/by-puuid/{puuid}"
        r = riot_get(url)
        if r.status_code != 200:
            return f"錯誤：拿不到 summoner_id，且 by-puuid 也失敗：{r.status_code} / {r.text}"
        data = r.json()

    solo = next((x for x in data if x.get("queueType") == "RANKED_SOLO_5x5"), None)
    if not solo:
        return f"{game_name}#{tag_line}：沒有單雙排資料"

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
    # 改成你的韓服帳號
    game_name = "collage"
    tag_line = "1224"
    lol_url = "https://kr.api.riotgames.com"

    result = get_rank_text(game_name, tag_line, lol_url)
    return Response(result, mimetype="text/plain")


@app.route("/twrank")
def twrank():
    # 改成你的台服帳號
    game_name = "Ziv"
    tag_line = "5566"
    lol_url = "https://tw2.api.riotgames.com"

    result = get_rank_text(game_name, tag_line, lol_url)
    return Response(result, mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
