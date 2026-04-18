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

GAME_NAME = "collage"
TAG_LINE = "1224"

ACCOUNT_URL = "https://asia.api.riotgames.com"
LOL_URL = "https://kr.api.riotgames.com"


def riot_get(url: str):
    return requests.get(url, headers=HEADERS, timeout=10)


@app.route("/")
def home():
    return Response("API is running", mimetype="text/plain")


@app.route("/lolrank")
def lolrank():
    try:
        if not API_KEY:
            return Response("錯誤：找不到 RIOT_API_KEY", mimetype="text/plain")

        encoded_name = quote(GAME_NAME)
        encoded_tag = quote(TAG_LINE)

        url = f"{ACCOUNT_URL}/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
        r = riot_get(url)
        if r.status_code != 200:
            return Response(f"取得 puuid 失敗：{r.status_code} / {r.text}", mimetype="text/plain")

        puuid = r.json().get("puuid")
        if not puuid:
            return Response(f"錯誤：找不到 puuid / {r.text}", mimetype="text/plain")

        url = f"{LOL_URL}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        r = riot_get(url)

        summoner_id = None
        if r.status_code == 200:
            summoner_id = r.json().get("id")

        if summoner_id:
            url = f"{LOL_URL}/lol/league/v4/entries/by-summoner/{summoner_id}"
            r = riot_get(url)
            if r.status_code != 200:
                return Response(f"取得牌位失敗：{r.status_code} / {r.text}", mimetype="text/plain")
            data = r.json()
        else:
            url = f"{LOL_URL}/lol/league/v4/entries/by-puuid/{puuid}"
            r = riot_get(url)
            if r.status_code != 200:
                return Response(
                    f"錯誤：拿不到 summoner_id，且 by-puuid 也失敗：{r.status_code} / {r.text}",
                    mimetype="text/plain"
                )
            data = r.json()

        solo = next((x for x in data if x.get("queueType") == "RANKED_SOLO_5x5"), None)
        if not solo:
            return Response("沒有單雙排資料", mimetype="text/plain")

        tier = solo.get("tier", "")
        rank = solo.get("rank", "")
        lp = solo.get("leaguePoints", 0)
        wins = solo.get("wins", 0)
        losses = solo.get("losses", 0)

        total = wins + losses
        winrate = (wins / total * 100) if total > 0 else 0

        result = f"{GAME_NAME}#{TAG_LINE}：{tier} {rank} {lp}LP / {wins}W-{losses}L / 勝率 {winrate:.1f}%"
        return Response(result, mimetype="text/plain")

    except Exception as e:
        return Response(f"錯誤：{str(e)}", mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)