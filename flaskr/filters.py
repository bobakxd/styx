import flask

filters = flask.Blueprint('filters', __name__)

@filters.app_template_filter()
def date_format(value):
    """Фильтр, который преобразовывает DateTime в строку формата 
    %-d %B, %Y г.
    """
    return value.strftime('%-d %B, %Y г.') 


@filters.app_template_filter()
def time_format(value):
    """Фильтр, который преобразовывает DateTime в строку формата 
    %-d %B в %H:%M
    """
    return value.strftime('%-d %B в %H:%M') 


@filters.app_template_filter()
def dir_path(d):
    """Фильтр, который возвращает путь относительно корня проекта 
    для директории *d*
    """
    path=''

    if not d:
        return path

    while True:
        if not d.dir_name:
            #path = '/' + path
            return path
        else:
            path = d.dir_name + '/' + path

        d = d.dir_parent


@filters.app_template_filter()
def pretty_date(time=False):
    """Фильтр, который преобразовывает дату в красивую строку 
    вида 'час назад', 'вчера', '3 месяца назад' и т.д.

    Получает объекта :class:`datetime.datetime` и возвращает 
    строку в красивом формате.
    """
    from datetime import datetime
    now = datetime.utcnow()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time,datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "только что"
        if second_diff < 60:
            return str(second_diff) + " секунд назад"
        if second_diff < 120:
            return "минуту назад"
        if second_diff < 3600:
            return str(round(second_diff / 60)) + " минут назад"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(round(second_diff / 3600)) + " часов назад"
    if day_diff == 1:
        return "вчера"
    if day_diff < 7:
        return str(day_diff) + " дней назад"
    if day_diff < 31:
        return str(round(day_diff / 7)) + " недель назад"
    if day_diff < 365:
        return str(round(day_diff / 30)) + " месяцев назад"
    return str(round(day_diff / 365)) + " лет назад"

