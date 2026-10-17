with open('public/app.js', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace('color: #fff;', 'color: var(--text-main);')
code = code.replace('color: #fff"', 'color: var(--text-main)"')
code = code.replace("color: ${sn.cure_rate > 0.65 ? '#34d399' : '#fff'};", "color: ${sn.cure_rate > 0.65 ? 'var(--accent-emerald)' : 'var(--text-main)'};")

with open('public/app.js', 'w', encoding='utf-8') as f:
    f.write(code)

print("Replaced #fff text colors with var(--text-main) successfully.")
