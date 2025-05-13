# 絆星あかりAI アシスタント

紲星あかりの音声で会話してくれる Discord ボイスアシスタントです。  
音声読み上げ・チャット応答・天気や予定の確認などができます。

> 🔧 **Windows 環境前提**（音声合成が SeikaSay2, ai voice に依存）

---

## 機能

- Discord でボイスチャット対応
- SeikaSay2 + A.I.VOICE によるあかり音声読み上げ
- Google Calendar / Google Tasks 読み書き
- 天気予報・為替情報・Web検索対応
- Whisper によるリアルタイム音声認識
- 会話履歴の記憶と文脈対応チャット

---

## 🔧 セットアップ

### 1. 音声合成ソフト（Seika + A.I.VOICE）

- A.I.VOICE 絆星あかりのインストール
- [AssistantSeika](https://voicepeak.technospeech.co.jp/seika/) をインストール
- `SeikaSay2.exe` を `assistantseika/SeikaSay2/` に配置

### 2. Python 環境構築

- CUDA 12.1 に対応したPyTorch 環境のインストール

```bash
torch==2.2.0+cu121
torchaudio==2.2.0+cu121
torchvision==0.17.0+cu121
--extra-index-url https://download.pytorch.org/whl/cu121
```

で動作確認済み

```bash
git clone https://github.com/lactoneinfo/akari-assistant.git
cd akari-assistant
python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. 環境変数の準備

- .env に以下のようにAPIキーを配置してください

```bash
DISCORD_TOKEN = 'xxxxx'
GEMINI_API_KEY = 'xxxxx'
PERPLEXITY_API_KEY= 'xxxxx' # 検索ツール
OPENWEATHER_API_KEY= 'xxxxx' # 天気予報
GOOGLE_MAPS_API_KEY = 'xxxxx' # Google カレンダー, TODO
```

### 4. プロンプトの準備

- prompt.txt にアシスタントの性格を記述してください
- master_profile.txt にマスターの情報を記述することができます
- config.py にカレンダーのラベルを付与できます.
```python
CALENDAR_LABELS = [
    {
        "keywords": ["あかり"],
        "description": "（あかりちゃんのカレンダー・編集可能）"
    }
]
```

## 実行方法

```python
python discordbot.py
```

以下のコマンドを使うことができます

| コマンド      | 内容                                         |
|---------------|----------------------------------------------|
| `!join`       | VCに接続                                     |
| `!leave`      | VCから退出                                   |
| `!say こんにちは` | あかりが喋ります                              |
| `!chat 今日何する？` | Gemini + LangChain による会話             |
| `!listen`     | Whisper でリアルタイム音声認識を開始         |
| `!stop`       | 音声認識を停止                                |
| `!forget`     | あかりの記憶をリセット                        |


## 備考
- 現状、discord ボイスチャットによる音声入力には対応していません. サーバーに音声入力を行う必要があります.
- Whisper による音声認識には GPU が推奨されます。
- `memory` により会話履歴が保持されますが、現状ではセッションのたびに失われます. `!forget` でセッション中でも初期化可能。
