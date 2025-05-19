import pandas as pd
from geopy.geocoders import Nominatim
import geojson
import time
import json
from geopy.extra.rate_limiter import RateLimiter

# Настройки
USER_AGENT = "english_football_map_2024/25"
CACHE_FILE = "stadiums_cache_all_leagues.json"
OUTPUT_FILE = "english_football_2024_25.geojson"

# Данные по лигам (URL Wikipedia и данные стадионов)
LEAGUE_DATA = {
    "Premier League": {
        "url": "https://en.wikipedia.org/wiki/2024%E2%80%9325_Premier_League",
        "stadiums": {
            "Emirates Stadium": {"capacity": 60704},
            "Villa Park": {"capacity": 42657},
            # ... остальные стадионы Премьер-лиги
        }
    },
    "EFL Championship": {
        "url": "https://en.wikipedia.org/wiki/2024%E2%80%9325_EFL_Championship",
        "stadiums": {
            "Elland Road": {"capacity": 37608},
            "Stadium of Light": {"capacity": 49000},
            # ... стадионы Чемпионшипа
        }
    },
    "EFL League One": {
        "url": "https://en.wikipedia.org/wiki/2024%E2%80%9325_EFL_League_One",
        "stadiums": {
            "Stadium MK": {"capacity": 30500},
            "Hillsborough": {"capacity": 39859},
            # ... стадионы Лиги 1
        }
    },
    "EFL League Two": {
        "url": "https://en.wikipedia.org/wiki/2024%E2%80%9325_EFL_League_Two",
        "stadiums": {
            "Vale Park": {"capacity": 19052},
            "Rodney Parade": {"capacity": 7850},
            # ... стадионы Лиги 2
        }
    }
}

# Инициализация геокодера
geolocator = Nominatim(user_agent=USER_AGENT)
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

# Загрузка кеша
try:
    with open(CACHE_FILE) as f:
        coordinates_cache = json.load(f)
except FileNotFoundError:
    coordinates_cache = {}

def get_coordinates(stadium_name, team_name, league):
    """Геокодирование стадионов с кешированием"""
    cache_key = f"{league}|{team_name}|{stadium_name}"
    
    if cache_key in coordinates_cache:
        return coordinates_cache[cache_key]
    
    try:
        location = geocode(f"{stadium_name}, UK", timeout=15)
        if location:
            coords = (location.longitude, location.latitude)
            coordinates_cache[cache_key] = coords
            print(f"Найдены координаты для {stadium_name}: {coords}")
            return coords
    except Exception as e:
        print(f"Ошибка геокодирования ({stadium_name}): {e}")
    
    print(f"Не удалось найти координаты для {stadium_name}")
    return None

def parse_teams(league):
    """Парсинг данных команд для конкретной лиги"""
    print(f"\nПарсинг данных для {league}...")
    try:
        tables = pd.read_html(LEAGUE_DATA[league]["url"])
        
        # Ищем таблицу с командами
        for table in tables:
            cols = [str(col).lower() for col in table.columns]
            if 'team' in cols and 'stadium' in cols:
                return table[['Team', 'Stadium']].rename(columns={
                    'Team': 'team',
                    'Stadium': 'stadium'
                }).drop_duplicates().dropna()
        
        raise ValueError(f"Таблица с командами не найдена для {league}")
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        # Возвращаем пустой DataFrame
        return pd.DataFrame(columns=['team', 'stadium'])

def generate_geojson():
    """Генерация GeoJSON для всех лиг"""
    features = []
    
    for league, data in LEAGUE_DATA.items():
        teams_data = parse_teams(league)
        print(f"Обработка {len(teams_data)} команд из {league}")
        
        for _, row in teams_data.iterrows():
            coords = get_coordinates(row['stadium'], row['team'], league)
            if not coords:
                continue
            
            stadium_info = data["stadiums"].get(row['stadium'], {"capacity": 0})
            
            # Properties с изменённым порядком (league перед capacity)
            feature = geojson.Feature(
                geometry=geojson.Point(coords),
                properties={
                    "team": row['team'],
                    "league": league,
                    "stadium": row['stadium'],
                    "capacity": stadium_info["capacity"],
                    "icon": f"icons/{row['team'].lower().replace(' ', '_')}.png"
                }
            )
            features.append(feature)
    
    return geojson.FeatureCollection(features)

def main():
    geojson_data = generate_geojson()
    
    with open(OUTPUT_FILE, 'w') as f:
        geojson.dump(geojson_data, f, indent=2)
    
    with open(CACHE_FILE, 'w') as f:
        json.dump(coordinates_cache, f, indent=2)
    
    print(f"\nГотово! Результат сохранён в {OUTPUT_FILE}")
    print(f"Всего обработано {len(geojson_data['features'])} стадионов")

if __name__ == "__main__":
    main()