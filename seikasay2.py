import subprocess
import argparse

def say(text: str, speed: float = 1.0):
    clean_text = text.replace("\n", "、")  # 改行を読める句読点に変換
    print(f"[合成] Speaking: {clean_text} (speed={speed})")
    print(clean_text)
    subprocess.run(["seikasay2.bat", str(speed), clean_text], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--speed", type=float, default=1.15, help="話速")
    parser.add_argument("text", nargs=argparse.REMAINDER, help="しゃべるテキスト")
    args = parser.parse_args()

    if args.text and args.text[0] == '--':
        args.text = args.text[1:]

    say(" ".join(args.text), speed=args.speed)
