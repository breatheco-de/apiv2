BS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-"


def to_base(n, b=None):
    # if no base is provided, use the maximum possible numbers of chars (shortest output)
    if b is None:
        b = len(BS)

    res = ""
    while n:
        res += BS[n % b]
        n //= b
    return res[::-1] or "0"
