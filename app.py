import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import engine

app = FastAPI(title='Phish Predictor', version='1.0')
STATIC_DIR = Path(__file__).parent / 'static'


def _records(df):
    return json.loads(df.to_json(orient='records', date_format='iso'))


class WeightsIn(BaseModel):
    weights: dict


class EvaluateIn(BaseModel):
    weights: Optional[dict] = None
    n_shows: int = 20
    top_n: Optional[int] = None


@app.get('/api/status')
def api_status(refresh: bool = False):
    try:
        return engine.status(force_refresh=refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/predict')
def api_predict(top_n: int = config.DEFAULT_TOP_N, date: str = None):
    try:
        result, meta = engine.predict_next(top_n=top_n, target_date=date)
        return {'songs': _records(result), 'meta': meta}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/backtest')
def api_backtest(date: str = None, top_n: int = config.DEFAULT_TOP_N):
    try:
        result = engine.backtest(date, top_n=top_n)
        result['predicted'] = _records(result['predicted'])
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/refresh')
def api_refresh():
    try:
        return engine.status(force_refresh=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/weights')
def api_weights_get():
    return {
        'weights': engine.load_weights(),
        'defaults': config.WEIGHTS,
        'has_overrides': os.path.exists(engine.WEIGHTS_FILE),
    }


@app.put('/api/weights')
def api_weights_put(body: WeightsIn):
    try:
        return {'weights': engine.save_weights(body.weights)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete('/api/weights')
def api_weights_delete():
    return {'weights': engine.reset_weights()}


@app.post('/api/weights/evaluate')
def api_weights_evaluate(body: EvaluateIn):
    try:
        return engine.evaluate_weights(n_shows=body.n_shows, top_n=body.top_n, weights=body.weights)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/')
def index():
    return FileResponse(STATIC_DIR / 'index.html')


app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:app', host='127.0.0.1', port=8000, reload=True)
