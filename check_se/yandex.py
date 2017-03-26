import re


def yandex_isnot_filter_tic(page):
    """
    Check domain on filter and return Index's citation of yandex
    Returns:
        None -- If page wasn't loaded
        Int -- If Index's citation was defined
        False -- Otherwise Index's citation wasn't defined
    """
    if ' ресурса — ' not in page:
        return None
    elif ' не определён' in page:
        return False
    else:
        page_regex = re.compile(r'ресурса\s—\s([0-9]+)</div>',
                                re.IGNORECASE | re.UNICODE
                                )
        r = page_regex.search(page)
        if r is not None:
            return int(r.groups()[0])
        else:
            return None


def yandex_isnot_glue(page, domain):
    """
    Check domain on glue
    Returns:
        None -- If page wasn't loaded or was other reasons
        True -- If domain isn't glued with other domains
        False -- Otherwise domain is glued
    """
    if '<url domain' not in page:
        return None

    occur = [
        '<url domain="%s">' % domain,
        '<url domain="www.%s">' % domain
    ]
    if occur[0] in page or occur[1] in page:
        return True
    else:
        return False


def yandex_num_pages(page):
    """
    Finded numbers pages indexed in yandex
    Returns:
        None -- If page wasn't loaded, or yandex requsted captcha,
        or wasn't other reasons
        Num pages (Int) -- If was found number pages indexed in yandex
        False -- Num pages is zero
    """
    errors = [
        'По вашему запросу ничего не нашлось',
        'ничего не найдено'
    ]
    if 'Яндекс' not in page or 'введите символы с' in page:
        return None
    for error in errors:
        if error in page:
            return False
    """
    Replaced word's numbers to numerical
    """
    page = page.replace('&nbsp;тыс.', '000')
    page = page.replace('&nbsp;млн', '000000')
    page = page.replace(' тыс.', '000')
    page = page.replace(' млн', '000000')
    page_regex = re.compile(r'Яндекс:\sнаш(лось|ёлся)\s([0-9]+)',
                            re.VERBOSE | re.IGNORECASE | re.UNICODE
                            )
    r = page_regex.search(page)
    if r is not None:
        return int(r.groups()[1])
    else:
        return None
