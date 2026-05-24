from flask import Flask, Response
import os
import requests
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("RIOT_API_KEY")

ACCOUNT_URL = "https://asia.api.riotgames.com"


def plain_text(text: str):
    return Response(text, mimetype="text/plain; charset=utf-8")


def riot_get(url: str):
    headers = {
        "X-Riot-Token": API_KEY
    }
    return requests.get(url, headers=headers, timeout=10)


def get_rank_text(game_name: str, tag_line: str, lol_url: str):
    if not API_KEY:
        return "錯誤：找不到 RIOT_API_KEY，請確認 Render Environment Variables 是否有設定 RIOT_API_KEY"

    encoded_name = quote(game_name, safe="")
    encoded_tag = quote(tag_line, safe="")

    try:
        # 1. Riot ID -> PUUID
        account_api = f"{ACCOUNT_URL}/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
        r = riot_get(account_api)

        if r.status_code != 200:
            return f"{game_name}#{tag_line}：取得 PUUID 失敗，HTTP {r.status_code}"

        account_data = r.json()
        puuid = account_data.get("puuid")

        if not puuid:
            return f"{game_name}#{tag_line}：找不到 PUUID"

        # 2. 直接用 PUUID 查 Ranked Data
        rank_api = f"{lol_url}/lol/league/v4/entries/by-puuid/{puuid}"
        r = riot_get(rank_api)

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

    except requests.exceptions.Timeout:
        return f"{game_name}#{tag_line}：查詢逾時，請稍後再試"

    except requests.exceptions.RequestException:
        return f"{game_name}#{tag_line}：連線 Riot API 失敗，請稍後再試"

    except Exception as e:
        return f"{game_name}#{tag_line}：程式錯誤：{str(e)}"


@app.route("/")
def home():
    return plain_text("API is running")


@app.route("/kr")
@app.route("/krrank")
def kr_rank():
    game_name = "Collage"
    tag_line = "1224"
    lol_url = "https://kr.api.riotgames.com"

    result = get_rank_text(game_name, tag_line, lol_url)
    return plain_text(result)


@app.route("/tw")
@app.route("/twrank")
def tw_rank():
    game_name = "Ziv"
    tag_line = "5566"
    lol_url = "https://tw2.api.riotgames.com"

    result = get_rank_text(game_name, tag_line, lol_url)
    return plain_text(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
