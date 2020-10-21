def call_sequence(*functions):
    return lambda *args,**xargs: [f(*args,**xargs) for f in functions]

