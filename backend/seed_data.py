import os
import re
import json
from .database import init_db, get_connection

def seed():
    init_db()
    conn = get_connection()
    c = conn.cursor()
    
    # Check if already seeded
    c.execute("SELECT COUNT(*) as count FROM anime")
    if c.fetchone()['count'] > 0:
        print("Database already has anime entries.")
        conn.close()
        return

    # Seed list with accurate posters, banners, and aliases for TG auto-matching
    animes = [
        {
            "slug": "bleach-tybw",
            "title_ru": "Блич: Тысячелетняя кровавая война",
            "title_en": "Bleach: Thousand-Year Blood War",
            "format": "ТВ-сериал (Куры 1–3)",
            "episodes_done": 32,
            "episodes_total": 39,
            "status": "В процессе",
            "cast": "Глеб (Uzapax)",
            "notes": "Серии 1–32 (367–398). 1 и 2 куры закрыты полностью (по 13 эп.). Идёт 3-й кур. Сабы: Ушастая озвучка (1-26), далее Арсений Золотарёв и свой перевод. Сведение: Late_XD.",
            "description": "Финальная грандиозная битва между Обществом душ и невидимой империей квинси Ванденрейх во главе с Яхве. Вся мощь синигами против квинси в бескомпромиссной войне.",
            "poster_url": "https://desu.shikimori.one/uploads/poster/animes/41467/main-52f9b87fcfbc50097f48a9e0a0d660f7.webp",
            "banner_url": "https://images.alphacoders.com/128/1281898.jpg",
            "aliases": "Блич, Блич ТКВ, Bleach, ТКВ, Thousand-Year Blood War, блич 3 кур"
        },
        {
            "slug": "uzaki-chan",
            "title_ru": "Удзаки хочет тусоваться! (1 сезон)",
            "title_en": "Uzaki-chan wa Asobitai!",
            "format": "ТВ-сериал (Сезон 1)",
            "episodes_done": 10,
            "episodes_total": 12,
            "status": "В процессе",
            "cast": "Глеб (Uzapax)",
            "notes": "Озвучены серии 1–10. Осталось всего 2 серии до закрытия сезона!",
            "description": "Шиничи Сакурай мечтает лишь о тишине и спокойствии, но его гиперактивная кохай Хана Удзаки решает вытащить его из раковины интроверта любой ценой.",
            "poster_url": "https://desu.shikimori.one/uploads/poster/animes/41226/main-360e2d14cb3c0b05b38e078e9f560e46.webp",
            "banner_url": "https://images.alphacoders.com/109/1093121.jpg",
            "aliases": "Удзаки, Удзаки хочет тусоваться, Uzaki, Uzaki-chan"
        },
        {
            "slug": "kiba",
            "title_ru": "Киба",
            "title_en": "Kiba",
            "format": "ТВ-сериал",
            "episodes_done": 10,
            "episodes_total": 52,
            "status": "В процессе",
            "cast": "Команда Copper Dub (многоголоска)",
            "notes": "Серии 1–10. Практическая командная работа ребят проекта.",
            "description": "Зед, бунтующий парень из депрессивного города Кэлм, попадает в иной мир Темпура, где сражения ведутся с помощью волшебных кристаллов-осколков и призыва духов.",
            "poster_url": "https://desu.shikimori.one/uploads/poster/animes/845/main-aa93e7f9ee1b8273616be32b509ef868.webp",
            "banner_url": "https://images.alphacoders.com/694/694119.jpg",
            "aliases": "Киба, Kiba"
        },
        {
            "slug": "jujutsu-kaisen",
            "title_ru": "Магическая битва (1 сезон)",
            "title_en": "Jujutsu Kaisen",
            "format": "ТВ-сериал (Сезон 1)",
            "episodes_done": 2,
            "episodes_total": 24,
            "status": "В процессе",
            "cast": "Никита (Фани точно в цель)",
            "notes": "Серии 1 и 2. Сольная практика Никиты (vk.com/angrymimo).",
            "description": "Юдзи Итадори проглатывает палец короля проклятий Рёмена Сукуны и становится сосудом древнего зла, вступая в школу магов для борьбы с проклятиями.",
            "poster_url": "https://desu.shikimori.one/uploads/poster/animes/40748/main-4299b802613d94895697a591e90956b6.webp",
            "banner_url": "https://images.alphacoders.com/112/1126129.jpg",
            "aliases": "Магическая битва, Магичка, Jujutsu Kaisen, JJK"
        },
        {
            "slug": "luger-code-1951",
            "title_ru": "Код Люгера 1951",
            "title_en": "Luger Code 1951",
            "format": "Спешл / ONA",
            "episodes_done": 1,
            "episodes_total": 1,
            "status": "Завершено",
            "cast": "Девочка лисичка, Отстойная шляпа, Тесто",
            "notes": "Короткометражный спешл полностью озвучен командным составом.",
            "description": "Гениальный лингвист Алекс Росса пытается расшифровать язык волков-оборотней («Код Люгера»), захватив в плен живую девушку-оборотня Йонагу.",
            "poster_url": "https://desu.shikimori.one/uploads/poster/animes/31737/main-e4125b0451a31d99ff6db8754b5df5b1.webp",
            "banner_url": "https://images.alphacoders.com/743/743224.jpg",
            "aliases": "Код Люгера 1951, Код Люгера, Luger Code 1951, Luger Code"
        },
        {
            "slug": "mitsuami-no-kamisama",
            "title_ru": "Богиня с косичками (Богиня Мицуами)",
            "title_en": "Mitsuami no Kamisama (Pigtails)",
            "format": "Короткометражный фильм",
            "episodes_done": 1,
            "episodes_total": 1,
            "status": "Завершено",
            "cast": "Avoksil (Регина)",
            "notes": "Авторская короткометражка (28 мин) полностью озвучена.",
            "description": "Трогательная история девочки с косичками, живущей в одиночестве в домике у моря после катастрофы, переосмысливающей память, трагедию и надежду.",
            "poster_url": "https://desu.shikimori.one/uploads/poster/animes/31705/main-fba893325c3452db16ae76a6cf544fe4.webp",
            "banner_url": "https://desu.shikimori.one/uploads/poster/animes/31705/main-fba893325c3452db16ae76a6cf544fe4.webp",
            "aliases": "Богиня с косичками, Богиня Мицуами, Mitsuami no Kamisama, Pigtails"
        },
        {
            "slug": "harmony",
            "title_ru": "Гармония",
            "title_en": "Project Itoh: Harmony (<harmony/>)",
            "format": "Полнометражный фильм",
            "episodes_done": 1,
            "episodes_total": 1,
            "status": "Завершено",
            "cast": "Команда Copper Dub (многоголоска)",
            "notes": "Полнометражный фильм (119 мин) полностью озвучен.",
            "description": "Утопическое будущее, где нанотехнологии искоренили болезни. Трое девушек объявляют протест обществу абсолютного здоровья, что приводит к мировой катастрофе.",
            "poster_url": "https://desu.shikimori.one/uploads/poster/animes/28211/main-7848f0e53a2bbcf5d787799b66bb22b1.webp",
            "banner_url": "https://images.alphacoders.com/670/670183.jpg",
            "aliases": "Гармония, Project Itoh Harmony, Harmony"
        },
        {
            "slug": "vinland-saga",
            "title_ru": "Сага о Винланде (1 сезон)",
            "title_en": "Vinland Saga",
            "format": "ТВ-сериал (Сезон 1)",
            "episodes_done": 1,
            "episodes_total": 24,
            "status": "На паузе",
            "cast": "Батырхан",
            "notes": "Озвучена 1 серия («Дебил что купил труп за 8 овец»).",
            "description": "Эпос о викингах, взрослении и мести. Юный Торфинн следует за отрядом наемника Аскеладда, убившего его отца, чтобы однажды сразиться с ним в честном поединке.",
            "poster_url": "https://desu.shikimori.one/uploads/poster/animes/37521/main-31648a7b1b36d0b5ebef50ee637d94cf.webp",
            "banner_url": "https://images.alphacoders.com/102/1029015.jpg",
            "aliases": "Сага о Винланде, Винланд, Vinland Saga, Vinland"
        },
        {
            "slug": "monsters-103",
            "title_ru": "Монстры: Сто три милости — Проклятие дракона",
            "title_en": "Monsters: 103 Mercies Dragon Damnation",
            "format": "ONA / Спешл (Netflix)",
            "episodes_done": 1,
            "episodes_total": 1,
            "status": "Завершено",
            "cast": "Глеб (Uzapax)",
            "notes": "Ваншот Эйитиро Оды (создателя One Piece). Сабы: Angara. Спонсор: Мансур Кайрат (Boosty).",
            "description": "История странствующего мечника Рюмы, легендарного самурая из страны Вано, который однажды спас город от огнедышащего дракона.",
            "poster_url": "https://desu.shikimori.one/uploads/poster/animes/56230/main-81d33190e292ce5ef1c633a763cfae97.webp",
            "banner_url": "https://images.alphacoders.com/134/1349581.png",
            "aliases": "Монстры, Монстры: Сто три милости, Monsters, 103 Mercies"
        },
        {
            "slug": "vox-machina",
            "title_ru": "Легенда о Вокс Макине (1 сезон)",
            "title_en": "The Legend of Vox Machina",
            "format": "Мультсериал (Сезон 1)",
            "episodes_done": 1,
            "episodes_total": 12,
            "status": "В процессе",
            "cast": "Глеб (Колдун фиолетовых рук)",
            "notes": "Озвучена 1 серия. Спонсор: Мансур Кайрат (Boosty).",
            "description": "Разношерстная банда пьяниц, наемников и неудачников берется за спасение королевства Экзандрия от темных сил ради легких денег и выпивки.",
            "poster_url": "https://m.media-amazon.com/images/M/MV5BNTIwMjYyNTItM2M1NC00MDM3LTk4ODEtZWYyNzQ1NzgzM2Q2XkEyXkFqcGc@._V1_FMjpg_UX1000_.jpg",
            "banner_url": "https://images.alphacoders.com/121/1218876.jpg",
            "aliases": "Легенда о Вокс Макине, Вокс Макина, Vox Machina"
        },
        {
            "slug": "zankyou-no-terror",
            "title_ru": "Эхо террора",
            "title_en": "Zankyou no Terror (Terror in Resonance)",
            "format": "ТВ-сериал",
            "episodes_done": 2,
            "episodes_total": 11,
            "status": "В процессе",
            "cast": "Глеб (Uzapax)",
            "notes": "Озвучены серии 1 и 2. Заказчик: Найн / Мансур Кайрат (Boosty).",
            "description": "В Токио происходит череда загадочных терактов без человеческих жертв. За ними стоят двое гениальных подростков «Сфинкс» — Девятый и Двенадцатый.",
            "poster_url": "https://desu.shikimori.one/uploads/poster/animes/23283/main-ae8e515d4fc53dfdc9d3ceb7b5ea5b60.webp",
            "banner_url": "https://images.alphacoders.com/542/542566.png",
            "aliases": "Эхо террора, Zankyou no Terror, Terror in Resonance"
        }
    ]

    slug_to_id = {}
    for a in animes:
        c.execute("""
        INSERT INTO anime (slug, title_ru, title_en, format, episodes_done, episodes_total, status, cast, notes, description, poster_url, banner_url, aliases)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            a["slug"], a["title_ru"], a["title_en"], a["format"], a["episodes_done"],
            a["episodes_total"], a["status"], a["cast"], a["notes"], a["description"],
            a["poster_url"], a["banner_url"], a["aliases"]
        ))
        slug_to_id[a["slug"]] = c.lastrowid

    # Seed the 62 episodes from Excel
    episodes_raw = [
        # Удзаки (10 серий)
        ("uzaki-chan", "1 серия", 1.0, "Тут могла быть шутка", "Интернетом и прямыми руками", "—"),
        ("uzaki-chan", "2 серия", 2.0, "Я", "Интернетом и прямыми руками", "—"),
        ("uzaki-chan", "3 серия", 3.0, "Uzapax", "Интернетом и прямыми руками", "—"),
        ("uzaki-chan", "4 серия", 4.0, "Я устал перезаливать", "Интернетом и прямыми руками", "—"),
        ("uzaki-chan", "5 серия", 5.0, "Да", "Интернетом и прямыми руками", "—"),
        ("uzaki-chan", "6 серия", 6.0, "Говно озвучка компани", "Интернетом и прямыми руками", "—"),
        ("uzaki-chan", "7 серия", 7.0, "не пьющий человек", "Интернетом и прямыми руками", "—"),
        ("uzaki-chan", "8 серия", 8.0, "Спиддабер", "Интернетом и прямыми руками", "—"),
        ("uzaki-chan", "9 серия", 9.0, "Уставший спиддабер", "Интернетом и прямыми руками", "—"),
        ("uzaki-chan", "10 серия", 10.0, "250 тысяч тон слюней", "Интернетом и прямыми руками", "—"),
        
        # Блич ТКВ (32 серии)
        ("bleach-tybw", "1 серия (367)", 1.0, "как не странно я", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "2 серия (368)", 2.0, "как не странно я", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "3 серия (369)", 3.0, "аоаоаоа", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "4 серия (370)", 4.0, "аоаоаоа", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "5 серия (371)", 5.0, "я", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "6 серия (372)", 6.0, "Ленивая жопа", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "7 серия (373)", 7.0, "СОДРАННАЯ ГЛОТКА", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "8 серия (374)", 8.0, "челик на расслабоне", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "9 серия (375)", 9.0, "опоздавший в универ", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "10 серия (376)", 10.0, "ВЕЛИКИЙ СОЗДАТЕЛЬ ДЗАМПАКТО ОООООЭЭЭЭЦУ НИМАЯЯЯЯ", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "11 серия (377)", 11.0, "Воздававший челик", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "12 серия (378)", 12.0, "Пытающийся зарендерить как можно быстрее", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "13 серия (379)", 13.0, "Глеб", "Ушастая озвучка (vk.com/eareddub)", "Закрытие 1-го кура"),
        ("bleach-tybw", "14 серия (380)", 14.0, "Покрикушка", "Ушастая озвучка (vk.com/eareddub)", "Старт 2-го кура"),
        ("bleach-tybw", "15 серия (381)", 15.0, "АГООООООООООООНЬ", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "16 серия (382)", 16.0, "Стримлер", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "17 серия (383)", 17.0, "Чел который делает бессмысленные надписи", "Ушастая озвучка (vk.com/eareddub)", "Благодарность Арсению Золотарёву"),
        ("bleach-tybw", "18 серия (384)", 18.0, "МИИИИИИСТААААР", "Ушастая озвучка (vk.com/eareddub)", "Арсений Золотарёв люблю тебя ❤️"),
        ("bleach-tybw", "19 серия (385)", 19.0, "Я БЕШАНЫЙ БЕГИТЕ", "Ушастая озвучка (vk.com/eareddub)", "Арсений Золотарёв без тебя никуда ❤️"),
        ("bleach-tybw", "20 серия (386)", 20.0, "Самая лучшая девочка в мире", "Ушастая озвучка (vk.com/eareddub)", "Арсений Золотарёв без тебя никуда ❤️"),
        ("bleach-tybw", "21 серия (387)", 21.0, "ИСИДА ВЕРНИСЬ В КАНОХУ", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "22 серия (388)", 22.0, "Ленивое чмо", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "23 серия (389)", 23.0, "Человек который мог залить серию еще три дня назад", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "24 серия (390)", 24.0, "Ленивое чмо", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "25 серия (391)", 25.0, "ТВАААРЬЬЬЬ", "Ушастая озвучка (vk.com/eareddub)", "—"),
        ("bleach-tybw", "26 серия (392)", 26.0, "Прибабах", "Ушастая озвучка (vk.com/eareddub)", "Закрытие 2-го кура"),
        ("bleach-tybw", "27 серия (393)", 27.0, "Артас", "Сам придумал (много импровизации)", "Старт 3-го кура"),
        ("bleach-tybw", "28 серия (394)", 28.0, "Чел что пропил бюджет на надписи", "В инете свиснул", "—"),
        ("bleach-tybw", "29 серия (395)", 29.0, "А че так долго ?", "Абоба", "—"),
        ("bleach-tybw", "30 серия (396)", 30.0, "ИСИДА СИСИДА ИИСИДА АААААААА", "Ты куда дел надписи посреди серий", "—"),
        ("bleach-tybw", "31 серия (397)", 31.0, "Наивный Сейрейтейский мальчик", "Классным стульчиком", "—"),
        ("bleach-tybw", "32 серия (398)", 32.0, "А где битрейт скатина", "А я чёт эту строчку поменять забыл", "Свел: t.me/Late_XD (Грузовик атмосферы)"),

        # Киба (10 серий)
        ("kiba", "Серия 1/52", 1.0, "Любитель позвать маму, Друг детства, Какая то Мама, Самый крутой статист в мире", "Интернетом и прямыми руками", "Практическая работа ребят"),
        ("kiba", "Серия 2/52", 2.0, "i am the ветер that is approaching, Любитель шаров, Жидкий, Почему у стражников шарики синие?", "Интернетом и прямыми руками", "Практическая работа ребят"),
        ("kiba", "Серия 3/52", 3.0, "Любимая Роооооя, Смазливый мальчик спальчик, Похотливый дед, ГАСПАДИН РОООООБЕСССС", "Интернетом и прямыми руками", "Практическая работа ребят"),
        ("kiba", "Серия 4/52", 4.0, "Хорни роя, Мне не описать ту боль и унижение что я испытал сегодня", "Интернетом и прямыми руками", "Практическая работа ребят"),
        ("kiba", "Серия 5/52", 5.0, "Какой то мужик, ДА НЕ ПЛАЧУ Я, Всадник без головы, ЗА ЧЕСТЬ И ОТВАГУ", "Интернетом и прямыми руками", "Практическая работа ребят"),
        ("kiba", "Серия 6/52", 6.0, "Задинамила мальца, Откуда у меня шарики с огнём?, Чисто милая мамочка", "Интернетом и прямыми руками", "Практическая работа ребят"),
        ("kiba", "Серия 7/52", 7.0, "Я ХОЧУ СТАТЬ СИЛЬНЕЕ, ООО ЭЛЬМЕДА ЗЫРЬ КАКОЙ ЛОХ", "Интернетом и прямыми руками", "Практическая работа ребят"),
        ("kiba", "Серия 8/52", 8.0, "ДАСТАВАЙ СВОЙ МЕЧ В ЭТОТ РАЗ Я ТЕБЕ НЕ ПРОИГРАЮ", "Интернетом и прямыми руками", "Практическая работа ребят"),
        ("kiba", "Серия 9/52", 9.0, "Кто куда а я в Джимото, Задыхающийся стражник, Робе вернулся", "Интернетом и прямыми руками", "—"),
        ("kiba", "Серия 10/52", 10.0, "Человек в апатий, Грустный Ноа, Лучший в мире статист, Кар бу ху", "Интернетом и прямыми руками", "Практическая работа ребят"),

        # Магическая битва (2 серии)
        ("jujutsu-kaisen", "1 серия", 1.0, "Фани точно в цель (Никитка)", "Интернетом и прямыми руками", "Соло практика Никиты (vk.com/angrymimo)"),
        ("jujutsu-kaisen", "2 серия", 2.0, "Ммм пальчики вкусный (Никитка)", "Интернетом и прямыми руками", "Соло практика Никиты (vk.com/angrymimo)"),

        # Код Люгера 1951
        ("luger-code-1951", "Спешл", 1.0, "Девочка лисичка, Отстойная шляпа, Тесто", "—", "Полный спешл полностью озвучен"),

        # Богиня с косичками
        ("mitsuami-no-kamisama", "Фильм", 1.0, "Avoksil (Регина)", "—", "Полный авторский фильм (28 мин)"),

        # Гармония
        ("harmony", "Фильм", 1.0, "Единственный женский голос, Доктор который меняет голос, Дурак", "—", "Полнометражный фильм (119 мин)"),

        # Сага о Винланде
        ("vinland-saga", "1 серия", 1.0, "Дебил что купил труп за 8 овец (Батырхан)", "Интернет", "—"),

        # Монстры: Сто три милости
        ("monsters-103", "ONA / Спешл", 1.0, "Чел что купается в своих 150 рублях (Глеб)", "Angara", "Спонсор: Мансур Кайрат (Boosty)"),

        # Легенда о Вокс Макине
        ("vox-machina", "1 серия", 1.0, "Колдун фиолетовых рук (Глеб)", "—", "Спонсор: Мансур Кайрат (Boosty)"),

        # Эхо террора
        ("zankyou-no-terror", "1 серия", 1.0, "Тот кто забыл это скинуть сюда", "—", "Заказчик: Найн (Boosty)"),
        ("zankyou-no-terror", "2 серия", 2.0, "Лиза подлиза", "—", "Заказчик: Найн (Boosty)")
    ]

    for slug, ep_num, order, cast, sub, notes in episodes_raw:
        a_id = slug_to_id.get(slug)
        if a_id:
            c.execute("""
            INSERT INTO episodes (anime_id, episode_num, episode_order, title, cast_credits, sub_credits, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (a_id, ep_num, order, f"{ep_num}", cast, sub, notes))

    conn.commit()
    conn.close()
    print(f"Seeded {len(animes)} anime and {len(episodes_raw)} episodes successfully!")

if __name__ == "__main__":
    seed()
