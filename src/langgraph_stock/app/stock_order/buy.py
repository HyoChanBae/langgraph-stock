import argparse
import sys
from pathlib import Path

#현재 파일 기준 파이썬 라이브러리 및 파일 (kis_auth.py) 찾기
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import kis_auth as ka
from domestic_stock_functions import order_cash


STOCK_CODE = "044380"
STOCK_NAME = "주연테크"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"{STOCK_NAME} 시장가 매수")
    parser.add_argument("--quantity", type=int, default=1, help="주문 수량(기본값: 1)")
    parser.add_argument(
        "--real",
        action="store_true",
        help="실전 계좌로 주문합니다. 생략하면 모의투자 계좌를 사용합니다.",
    )
    args = parser.parse_args()

    if args.quantity <= 0:
        parser.error("--quantity는 1주 이상이어야 합니다.")

    return args


def main() -> None:
    args = parse_args()
    server = "prod" if args.real else "vps"
    environment = "real" if args.real else "demo"

    if args.real:
        expected = f"{STOCK_NAME} {args.quantity}주 매수"
        confirmation = input(
            f"{STOCK_NAME}({STOCK_CODE}) {args.quantity}주를 "
            "시장가로 실제 매수합니다.\n"
            f"계속하려면 '{expected}'를 입력하세요: "
        )
        if confirmation != expected:
            print("실전 주문을 취소했습니다.")
            return

    ka.auth(svr=server, product="01")
    trenv = ka.getTREnv()

    result = order_cash(
        env_dv=environment,
        ord_dv="buy",
        cano=trenv.my_acct,
        acnt_prdt_cd=trenv.my_prod,
        pdno=STOCK_CODE,
        ord_dvsn="01",
        ord_qty=str(args.quantity),
        ord_unpr="0",
        excg_id_dvsn_cd="KRX",
    )

    if result.empty:
        print("주문 결과가 없습니다. API 오류 메시지를 확인하세요.")
    else:
        print(result.T.to_string(header=False))


if __name__ == "__main__":
    main()
