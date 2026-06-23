import re
import random
from fuzzywuzzy import fuzz, process
from database import db

PROBLEMS = {'gal.пастила h.s.p.мед.обл.': ['салатила', 'салат пастила', 'пастила н.', 's.p.мед', 's.p.нед', 'н.5.р.нец', 'h.s.p.мед'],
    'nina farina тараллини с чесноком': ['tanai', 'farina', 'sf j)nina', 'taran', 'taranfvh'],
    'святой источник вода питьевая лимон': ['свят ион', 'свято', 'святой'],
    'хлебцы молод.лайт с вино.кос': ['executor', 'honoo', 'aaat', 'кгс7оф'],
    'салат фрилис': ['фрилис', 'phankc', 'opnankc', 'фрилик', 'фрилиc', 'салат фрилис'],
    'хлебец зож': ['xnebeu', 'зож', 'body-эф', 'body', 'хлебец зож'],
    'mentos жев.рез.p.fr.з.м.15,5г': ['mentos', 'heb.pe3.p.fr.3.m.15'],
    'gl.vil.нект.м/фр.из см.фруко': ['фруко', 'см.фруко'],
    'джин gletcher 40% 0.25л': ['gletcher', "'gletcher"],
    'ml.s.сыр серб.брынза мяг.': ['брынза', 'серб.брынза', 'ml.s.сыр', 'сыр серб', 'брынза мяг', 'аззне'],
    'lor.чипсы nat.мор.сол/перец.': ['lor.чипсы', 'nat.мор.'],
    'пиво варим сусло св.нефил.': ['варим сусло', 'baphn cycno', 'cb.heohn'],
    'ром выдержанный steersman': ['steersman', 'ром выдержанный'],
    'argeta паштет куриный 95г ж/б (дрога колинска' : ['argeta паштет куриный', 'argeta', 'argeta паштет']}

ECO_TIPS_HIGH = ["🛍️ Старайтесь выбирать товары в бумажной упаковке вместо пластиковой — это снижает углеродный след.",
    "🥕 Добавьте в рацион больше растительных продуктов — их производство экологичнее.",
    "🚫 Откажитесь от товаров с избыточной упаковкой — каждая пластиковая обёртка увеличивает выбросы CO₂.",
    "🚲 Замените частые поездки на машине на общественный транспорт или велосипед, когда идёте за покупками.",
    "♻️ Покупайте продукты местного производства — меньше логистика = меньше CO₂.",
    "💡 Не берите лишние пакеты на кассе — используйте многоразовые сумки.",
    "🥩 Сократите потребление красного мяса — животноводство даёт огромный углеродный след.",
    "📦 Выбирайте товары в упаковке из переработанных материалов.",
    "🌡️ Храните продукты правильно, чтобы они дольше не портились и не создавали пищевые отходы.",
    "🍎 Покупайте ровно столько, сколько съедите — пищевые отходы производят метан, который вреднее CO₂."]

ECO_TIPS_LOW = ["🎉 Отличный выбор! Вы уже следуете экологичным привычкам — так держать!",
    "🌱 Ваш чек — пример ответственного потребления. Спасибо!",
    "💚 Вы делаете вклад в чистое будущее планеты. Продолжайте в том же духе!",
    "🌟 Отличная работа! Чем больше таких чеков, тем здоровее наша планета.",
    "🌍 Вы — эко-герой! Низкий углеродный след ваших покупок вдохновляет.",
    "🌸 Спасибо, что выбираете продукты с умом. Природа ценит вашу заботу!",
    "💪 Вы доказываете, что заботиться о климате — легко и приятно!",
    "🌿 Ваш чек — пример для подражания. Так держать!",
    "🍀 Экологичный подход к покупкам — это ваша суперсила!",
    "🏆 Браво! Ваши привычки помогают планете дышать легче."]

def is_false_match(product_name, receipt_line, match_score=100):
    prod_l = product_name.lower()
    receipt_l = receipt_line.lower()

    if 'томат' in prod_l or 'помидор' in prod_l:
        if 'томат' not in receipt_l and 'помидор' not in receipt_l and 'черри' not in receipt_l:
            return True

    if match_score < 55:
        return True

    if 'святой' in prod_l and match_score < 75:
        return True

    return False

def find_products(text):
    store_prods = db.get_store_products()
    prod_info = db.get_product_info()
    found = []
    found_prods = set()

    for prod_name, aliases in PROBLEMS.items():
        for alias in aliases:
            if alias in text:
                product_id = store_prods.get(prod_name)
                if product_id and product_id in prod_info:
                    if is_false_match(prod_name, alias, 100):
                        continue
                    product = prod_info[product_id]
                    if prod_name not in found_prods:
                        found.append({'receipt_name': prod_name, 'category': product['category'], 'co2': product['co2']})
                        found_prods.add(prod_name)
                    break

    lines = text.split('\n')
    candidates = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 4:
            continue
        clean = re.sub(r'\d+', '', line)
        clean = re.sub(r'[^\w\s]', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip().lower()
        if len(clean) > 3:
            candidates.append(clean)

    all_names = list(store_prods.keys())

    for c in candidates:
        already_f = any(f['receipt_name'] in c for f in found)
        if already_f:
            continue

        if len(c) < 5:
            continue

        if not re.search(r'[а-яё]', c):
            continue

        cand_len = len(c)
        if cand_len < 10:
            dynamic_thr = 80
        elif cand_len > 30:
            dynamic_thr = 55
        else:
            dynamic_thr = 65

        mtchs = process.extract(c, all_names, limit=1, scorer=fuzz.ratio)

        for mtch, score in mtchs:
            if score >= dynamic_thr:
                if is_false_match(mtch, c, score):
                    continue

                if 'банан' in mtch.lower():
                    pastila = any('пастила' in f['receipt_name'].lower() for f in found)
                    if pastila or 'салатила' in c or 'листила' in c:
                        continue

                if 'томат' in mtch.lower():
                    txt_low = text.lower()
                    if 'томат' not in txt_low and 'черри' not in txt_low and 'помидор' not in txt_low:
                        continue

                if 'магнит' in mtch.lower():
                    keywrds = ['сок', 'ролл', 'напиток', 'энергет', 'пиво', 'шоколад', 'сыр', 'пастила', 'хлеб']
                    prod_keyw = any(keyword in c for keyword in keywrds)
                    if not prod_keyw:
                        continue

                product_id = store_prods.get(mtch)
                if product_id and product_id in prod_info:
                    if mtch in found_prods:
                        continue
                    product = prod_info[product_id]
                    found.append({'receipt_name': mtch, 'category': product['category'], 'co2': product['co2']})
                    found_prods.add(mtch)
                    break

    return found

def get_eco_tip(is_high_emission):
    if is_high_emission:
        return random.choice(ECO_TIPS_HIGH)
    return random.choice(ECO_TIPS_LOW)