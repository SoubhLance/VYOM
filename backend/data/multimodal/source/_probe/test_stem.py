def token_match(a, b):
    if a == b:
        return True
    if len(a) >= 4 and len(b) >= 4 and a[:3] == b[:3]:
        # check edit distance or common characters
        return True
    return False

print(token_match("celibacy", "celebacy"))
print(token_match("virtuous", "virtue"))

