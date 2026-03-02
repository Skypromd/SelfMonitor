import urllib.error
import urllib.request

tests = [
    ("analytics health", "http://localhost:8009/health", "GET"),
    ("advice health", "http://localhost:8010/health", "GET"),
    ("analytics CORS preflight", "http://localhost:8009/forecast/cash-flow", "OPTIONS"),
    ("advice CORS preflight", "http://localhost:8010/generate", "OPTIONS"),
]
for name, url, method in tests:
    try:
        req = urllib.request.Request(
            url,
            method=method,
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        r = urllib.request.urlopen(req)
        cors = r.headers.get("Access-Control-Allow-Origin", "MISSING")
        print(f"{name}: {r.status}  CORS={cors}")
    except urllib.error.HTTPError as e:
        cors = e.headers.get("Access-Control-Allow-Origin", "MISSING")
        print(f"{name}: HTTP {e.code}  CORS={cors}")
    except Exception as e:
        print(f"{name}: ERROR {e}")
