import urllib.request
resp = urllib.request.urlopen('http://localhost:8080')
print(resp.read().decode())
