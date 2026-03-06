import urllib.error
import urllib.parse
import urllib.request


def post(url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            print(f"OK {r.status}: {r.read().decode()}")
    except urllib.error.HTTPError as e:
        print(f"ERR {e.code}: {e.read().decode()}")


post(
    "http://localhost:8000/register",
    {"username": "hello@test.com", "password": "MyStr0ngPassword123!"},
)
post(
    "http://localhost:8000/token",
    {"username": "hello@test.com", "password": "MyStr0ngPassword123!"},
)
