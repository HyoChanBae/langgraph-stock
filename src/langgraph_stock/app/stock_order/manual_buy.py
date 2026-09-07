import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent
_STOCK_ORDER_DIR = Path(__file__).resolve().parent
for _path in (_APP_DIR, _STOCK_ORDER_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from buy import ORDER_QUANTITY, place_buy_order


def ask_symbol() -> str:
    symbol = input("종목코드 6자리를 입력하세요: ").strip()
    if len(symbol) != 6 or not symbol.isdigit():
        raise SystemExit("종목코드는 숫자 6자리여야 합니다.")
    return symbol


def ask_confirm(symbol: str) -> bool:
    answer = input(
        f"{symbol} 을(를) 시장가 {ORDER_QUANTITY}주 매수할까요? (y/n): "
    ).strip().lower()
    return answer in ("y", "yes", "ㅛ")


def main() -> None:
    symbol = ask_symbol()
    if not ask_confirm(symbol):
        print("매수를 취소했습니다.")
        return

    print(f"[buy] {symbol} 시장가 매수 진행")
    result = place_buy_order(symbol)
    print(result)


if __name__ == "__main__":
    main()
