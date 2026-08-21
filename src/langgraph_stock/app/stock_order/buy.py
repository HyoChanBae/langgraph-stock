import sys
from pathlib import Path

#현재 파일 기준 파이썬 라이브러리 및 파일 (kis_auth.py) 찾기
_APP_DIR = Path(__file__).resolve().parent.parent
_STOCK_ORDER_DIR = Path(__file__).resolve().parent
for _path in (_APP_DIR, _STOCK_ORDER_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import kis_auth as ka
from domestic_stock_functions import order_cash


STOCK_CODE = "044380"
ORDER_QUANTITY = 1


def place_buy_order(symbol: str) -> dict:
    #ka.auth(svr="vps", product="01") #데모
    ka.auth(svr="prod", product="01") #실전
    trenv = ka.getTREnv()

    result = order_cash(
        #env_dv="demo", #데모
        env_dv="real", #실전
        ord_dv="buy",
        cano=trenv.my_acct,
        acnt_prdt_cd=trenv.my_prod,
        pdno=symbol,
        ord_dvsn="01",
        ord_qty=str(ORDER_QUANTITY),
        ord_unpr="0",
        excg_id_dvsn_cd="KRX",
    )

    if result.empty:
        return {
            "symbol": symbol,
            "quantity": ORDER_QUANTITY,
            "success": False,
            "message": "주문 결과가 없습니다. API 오류 메시지를 확인하세요.",
        }

    return {
        "symbol": symbol,
        "quantity": ORDER_QUANTITY,
        "success": True,
        "result": result.to_dict(orient="records"),
    }
