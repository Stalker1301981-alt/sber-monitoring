import urllib.request
resp = urllib.request.urlopen('http://localhost:3000')
print(resp.read().decode())
