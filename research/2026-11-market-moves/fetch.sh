#!/usr/bin/env bash
# Downloads the public daily series the studies read into ./data (git-ignored). No keys needed.
set -euo pipefail
mkdir -p data
get() { curl -sS -m 30 -A "Mozilla/5.0" -o "data/$2.json" "https://query1.finance.yahoo.com/v8/finance/chart/$1?period1=${3:-946684800}&period2=1794000000&interval=1d"; }
get %5ENSEI NIFTY; get %5EINDIAVIX INDIAVIX; get %5EGSPC SPX; get %5EVIX USVIX
get %5EVIX3M VIX3M; get %5EVVIX VVIX; get INR%3DX USDINR; get BZ%3DF BRENT; get %5ETNX US10Y; get DX-Y.NYB DXY
get %5ENSEBANK BANKNIFTY; get GC%3DF GOLD; get %5EIXIC NASDAQ; get %5EHSI HSI; get %5EN225 NIKKEI; get %5EMOVE MOVE; get HYG HYG; get EEM EEM
get %5EGSPC SPXL 600000000; get %5EVIX USVIXL 600000000; get %5ENDX NDX 600000000; get %5EVXN VXN 600000000
cp data/NIFTY.json nsei.json; cp data/INDIAVIX.json vix.json; cp data/SPX.json GSPC.json; cp data/USVIX.json VIX.json
