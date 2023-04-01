def parse_child_field(name, l: list[str]) -> tuple | None:
    if l is None:
        return None

    return tuple([i.replace(f'{name}__', '').replace(name, '') for i in l if name in i])
