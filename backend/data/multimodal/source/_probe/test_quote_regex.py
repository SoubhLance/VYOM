import re

text = '''Here is a quote: "The mind is restless, turbulent,
strong and unyielding, O Krishna." And another: “He whose mind is not shaken by adversity, who does not hanker after pleasures.”'''

quotes = re.findall(r'["“]([^"”]+?)["”]', text)
for q in quotes:
    words = q.split()
    if len(words) >= 6:
        print("Found quote:", repr(q))

