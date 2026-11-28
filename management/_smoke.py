import re
import requests

BASE = "http://127.0.0.1:8765"
s = requests.Session()

r = s.get(f"{BASE}/")
print("anon ->", r.status_code, r.url)
r = s.get(f"{BASE}/accounts/login/")
token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text).group(1)
r = s.post(f"{BASE}/accounts/login/", data={"username": "demo_admin", "password": "Demo-parola-123", "csrfmiddlewaretoken": token, "next": "/"})
print("login ->", r.status_code, r.url)

for path in ["/", "/graph/run/", "/graph/runs/", "/accounts/users/", "/accounts/users/new/", "/accounts/profile/", "/accounts/password/"]:
    r = s.get(BASE + path)
    bad = [m for m in re.findall(r'style="[^"]*\d,\d[^"]*"', r.text)]
    print(path, r.status_code, len(r.text), "bad-style:", bad[:2], "None:", r.text.count(">None<"))

for static in ["/static/css/app.css", "/static/js/app.js", "/static/graph/runner.js"]:
    print(static, s.get(BASE + static).status_code)

csrf = s.cookies["csrftoken"]
r = s.post(f"{BASE}/graph/run/execute/", data={"service": ["cafe", "housekeeping", "technical"]}, headers={"X-CSRFToken": csrf})
print("execute ->", r.status_code)
data = r.json()
html = data["html"]
print("count", data["count"], "len", len(html))
print("bad-style:", re.findall(r'style="[^"]*\d,\d[^"]*"', html)[:3])
print("badges:", re.findall(r'badge (?:red|green) dot">([^<]+)<', html))
open("run_fragment.html", "w", encoding="utf-8").write(html)

r = s.get(f"{BASE}/graph/runs/")
print("history rows:", r.text.count("Ayrıntı"))
r = s.get(f"{BASE}/graph/runs/1/")
print("detail ->", r.status_code, "timeline items:", r.text.count('class="tl-item'))
