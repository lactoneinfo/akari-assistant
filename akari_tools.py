import os
import requests
from datetime import datetime
from langchain.tools import Tool
from tools.calender_read import calendar_read_tool
from tools.calender_write import calendar_write_tool
from tools.calender_delete import calendar_delete_tool
from tools.tasks_read import tasks_read_tool
from tools.tasks_write import tasks_write_tool
from tools.tasks_delete import tasks_delete_tool
from tools.browser_agent import browser_agent_tool
from langchain.tools import Tool

# === 現在時刻取得 ===
def get_current_datetime(_: str) -> str:
    now = datetime.now()
    weekdays = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
    weekday_jp = weekdays[now.weekday()]
    return f"現在の日時は {now.strftime('%Y年%m月%d日')}（{weekday_jp}）{now.strftime('%H時%M分%S秒')} です。"

datetime_tool = Tool(
    name="GetTodayDate",
    func=get_current_datetime,
    description="現在の曜日と日付と時刻をJSTで返します。"
    "指示に「今日」「明日」「今から」「一週間後に」などの、時刻にかかわる言葉が含まれる場合はかならず確認してください。"
)

# === 緯度経度取得 ===
def get_lat_lon(city_name: str) -> str:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={api_key}"
    response = requests.get(url)
    data = response.json()
    if not data:
        return f"❌ 都市名から座標が見つかりませんでした。"
    lat, lon = data[0]["lat"], data[0]["lon"]
    return f"{lat},{lon}"

latlon_tool = Tool(
    name="GetLatLon",
    func=get_lat_lon,
    description="都市名を緯度経度に変換します。例: '東京' → '35.75,139.73'"
)

# === 天気予報取得 ===
def fetch_weather_forecast(latlon: str) -> str:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    try:
        lat, lon = latlon.split(",")

        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=ja"
        response = requests.get(url)
        data = response.json()

        if data.get("cod") != "200":
            return f"❌ 天気情報の取得に失敗しました: {data.get('message', 'エラー内容不明')}"
        city = data.get("city", {}).get("name", "指定地")
        lines = []
        for entry in data["list"]:
            dt_txt = entry["dt_txt"]
            temp = entry["main"]["temp"]
            desc = entry["weather"][0]["description"]
            pop = int(entry.get("pop", 0) * 100)
            lines.append(f"{dt_txt}: {desc}, {temp:.1f}℃, 降水確率{pop}%")
        return f"{city}の天気予報（直近）:\n" + "\n".join(lines)

    except Exception as e:
        return f"❌ API呼び出し中にエラーが発生しました: {e}"

weather_forecast_tool = Tool(
    name="WeatherForecast",
    func=fetch_weather_forecast,
    description="緯度経度（lat,lon）を受け取り5日分3時間ごとの天気予報を返します。"
    "天気予報は5日分のみなのでそれより先の天気や過去の天気は検索を使ってください"
)

# === 為替レート取得 ===
def get_exchange_rate(query: str) -> str:
    try:
        if "→" not in query:
            return "❌ 'USD→JPY' のように2通貨コードを '→' でつなげてください。"
        base, target = map(str.strip, query.split("→"))
        url = f"https://api.frankfurter.app/latest?from={base}&to={target}"
        response = requests.get(url)
        data = response.json()
        if "rates" not in data or target not in data["rates"]:
            return f"❌ {base}から{target}へのレートが取得できませんでした。"
        rate = data["rates"][target]
        return f"【{data['date']}】1 {base} = {rate:.3f} {target}"
    except Exception as e:
        return f"❌ 為替API呼び出しエラー: {e}"

exchange_rate_tool = Tool(
    name="GetExchangeRate",
    func=get_exchange_rate,
    description="為替レートを取得します。形式: 'USD→JPY'"
    "返答には変換レートと日付が含まれます。"
)

# === Web検索 ===
def web_search_tool_func(query: str) -> str:
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return "❌ Perplexity APIキーが設定されていません"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": (
                    "あなたは検索結果を活用して、ユーザーの質問に簡潔に答えるアシスタントです。\n"
                    "返答はできるだけ短く、1〜2文で、最大でも200文字以内で要点のみを伝えてください。\n"
                )
            },
            {"role": "user", "content": query}
        ],
        "temperature": 0,
        "top_p": 0.9,
        "return_related_questions": False,
        "return_images": False,
        "top_k": 3,
        "stream": False
    }
    try:
        response = requests.post("https://api.perplexity.ai/chat/completions", json=payload, headers=headers)
        response_data = response.json()
        content = response_data['choices'][0]['message']['content']
        citations = response_data.get("citations", [])
        urls = "\n".join([f"🔗 {url}" for url in citations])
        return f"{content}\n\n{urls}" if citations else content
    except Exception as e:
        return f"❌ Perplexity APIエラー: {e}"

search_tool = Tool(
    name="WebSearch",
    func=web_search_tool_func,
    description="Perplexityを使って、ニュースや政治などの**事実ベースの最新情報**を検索するためのツールです。\n"
        "**天気、日付、時刻、感情や主観的な話題、個人的な会話には使わないでください。**\n"
        "**検索は1つの話題につき1回までにしてください。特に事実確認の再検索は禁止です。**\n"
        "以前の会話履歴によって事実関係が明らかになっている内容を再度検索することは避けてください。"
        "ほかのAPI が失敗した場合に補完的に検索を用いることは許可されます"
)

# === マスター情報取得 ===
def get_master_info(_: str) -> str:
    try:
        with open("master_profile.txt", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "❌ master_profile.txt が見つかりません。"
    except Exception as e:
        return f"❌ マスター情報取得中にエラー: {e}"

master_info_tool = Tool(
    name="GetMasterInfo",
    func=get_master_info,
    description="マスターの本名、所属、居住地、趣味などが書かれた `master_profile.txt` の内容を取得します。"
    "マスターの情報を正確に答えるために使ってください。"
)


tools = [
    search_tool,
    browser_agent_tool,
    datetime_tool,
    latlon_tool,
    weather_forecast_tool,
    exchange_rate_tool,
    master_info_tool,
    calendar_read_tool,
    calendar_write_tool,
    calendar_delete_tool,
    tasks_read_tool,
    tasks_write_tool,
    tasks_delete_tool
]