from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from bson import ObjectId

from app.db.db import db

router = APIRouter()


class Coin(BaseModel):
    symbol: str
    weight: float | None = None


class BasketCreate(BaseModel):
    user: str
    name: str
    weighting: str = "custom"  # "equal" or "custom"
    coins: List[Coin]


@router.post("/baskets")
def create_basket(basket: BasketCreate):
    if basket.weighting != "equal":
        total = sum(c.weight or 0 for c in basket.coins)
        if abs(total - 100) > 0.001:
            raise HTTPException(status_code=400, detail="weights must sum to 100")
    else:
        # set equal weights if not provided
        n = len(basket.coins)
        if n:
            w = 100 / n
            for c in basket.coins:
                c.weight = w

    doc = basket.dict()
    result = db.baskets.insert_one(doc) if db is not None else None
    return {"id": str(result.inserted_id) if result else None}


class CoinList(BaseModel):
    coins: List[Coin]


@router.post("/baskets/{basket_id}/coins")
def add_coins(basket_id: str, req: CoinList):
    basket = db.baskets.find_one({"_id": ObjectId(basket_id)}) if db is not None else None
    if not basket:
        raise HTTPException(status_code=404, detail="basket not found")

    coins = basket.get("coins", []) + [c.dict() for c in req.coins]
    if basket.get("weighting") != "equal":
        total = sum(c.get("weight", 0) for c in coins)
        if abs(total - 100) > 0.001:
            raise HTTPException(status_code=400, detail="weights must sum to 100")

    db.baskets.update_one({"_id": ObjectId(basket_id)}, {"$set": {"coins": coins}})
    return {"status": "updated"}
