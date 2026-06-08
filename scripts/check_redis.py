import redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    print(r.llen('raw_odds_queue'))
except Exception as e:
    print(e)
