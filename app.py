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

# Riot ID / account-v1 用區域路由
ACCOUNT_URL = "https://asia.api.riotgames.com"

# LoL 遊戲資料用平台路由；韓服是 kr
LOL_URL = "https://kr.api.riotgames.com"


def riot_get(url: str):
    """包一層 GET，方便統一 timeout 與 debug"""
    r = requests.get(url, headers=HEADERS, timeout=10)
    return r


@app.route("/lolrank")
def lolrank():
    try:
        if not API_KEY:
            return Response("錯誤：找不到 RIOT_API_KEY，請檢查 .env", mimetype="text/plain")

        # 1) Riot ID -> PUUID
        encoded_name = quote(GAME_NAME)
        encoded_tag = quote(TAG_LINE)

        url = f"{ACCOUNT_URL}/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
        r = riot_get(url)

        print("【Step 1 / Account API】")
        print("URL:", url)
        print("Status Code:", r.status_code)
        print("Response:", r.text)

        if r.status_code != 200:
            return Response(f"取得 puuid 失敗：{r.status_code} / {r.text}", mimetype="text/plain")

        account_data = r.json()
        puuid = account_data.get("puuid")

        if not puuid:
            return Response(f"錯誤：找不到 puuid / {r.text}", mimetype="text/plain")

        # 2) 先試 summoner-v4 by-puuid
        summoner_id = None
        url = f"{LOL_URL}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        r = riot_get(url)

        print("【Step 2 / Summoner API】")
        print("URL:", url)
        print("Status Code:", r.status_code)
        print("Response:", r.text)

        if r.status_code == 200:
            summoner_data = r.json()
            summoner_id = summoner_data.get("id")

        # 3A) 若拿得到 summoner_id，走傳統 by-summoner
        if summoner_id:
            url = f"{LOL_URL}/lol/league/v4/entries/by-summoner/{summoner_id}"
            r = riot_get(url)

            print("【Step 3A / League API by-summoner】")
            print("URL:", url)
            print("Status Code:", r.status_code)
            print("Response:", r.text)

            if r.status_code != 200:
                return Response(f"取得牌位失敗：{r.status_code} / {r.text}", mimetype="text/plain")

            data = r.json()

        # 3B) 若拿不到 summoner_id，就改試 by-puuid
        else:
            url = f"{LOL_URL}/lol/league/v4/entries/by-puuid/{puuid}"
            r = riot_get(url)

            print("【Step 3B / League API by-puuid】")
            print("URL:", url)
            print("Status Code:", r.status_code)
            print("Response:", r.text)

            if r.status_code != 200:
                return Response(
                    "錯誤：目前拿不到 summoner_id，且 by-puuid 也失敗。\n"
                    f"Status: {r.status_code}\n"
                    f"Response: {r.text}",
                    mimetype="text/plain"
                )

            data = r.json()

        if not isinstance(data, list):
            return Response(f"錯誤：牌位資料格式異常 / {data}", mimetype="text/plain")

        # 只抓單雙排
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

        result = (
            f"{GAME_NAME}#{TAG_LINE}："
            f"{tier} {rank} {lp}LP / {wins}W-{losses}L / 勝率 {winrate:.1f}%"
        )
        return Response(result, mimetype="text/plain")

    except Exception as e:
        return Response(f"錯誤：{str(e)}", mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)