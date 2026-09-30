import io
with open('App.css', 'r', encoding='utf-8', errors='ignore') as f:
    data = f.read().replace('\x00', '')
data = data.split('}/ *')[0] + '}\n'
with open('App.css', 'w', encoding='utf-8') as f:
    f.write(data)
