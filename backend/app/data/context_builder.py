import logging
from datetime import datetime

from flask import current_app

from app.data.apifootball_client import APIFootballClient, LEAGUES_MAP
from app.data.football_data import FootballDataClient, LEAGUES_FREE

logger = logging.getLogger(__name__)

FOOTBALL_DATA_CODE_BY_LEAGUE = {name: code for code, name in LEAGUES_FREE.items()}
APIFOOTBALL_ID_BY_LEAGUE = {name: league_id for league_id, name in LEAGUES_MAP.items()}

FORM_MAP = {
    'W': 'W',
    'D': 'D',
    'L': 'L',
}


def _safe_client_call(client, endpoint: str, params: dict | None = None) -> dict | None:
    try:
        return client._get(endpoint, params)
    except Exception as exc:
        logger.debug(f"[Context] Falha em {endpoint}: {exc}")
        return None


def _format_form(results: list[str]) -> str:
    return "-".join(results[:5]) if results else "Sem dados"


def _summarize_h2h(matches: list[dict], home_team: str, away_team: str) -> tuple[str, str, str]:
    home_form = []
    away_form = []
    home_wins = 0
    away_wins = 0
    draws = 0

    for match in matches[:5]:
        teams = match.get('teams', {})
        fixture_home = teams.get('home', {}).get('name', '')
        fixture_away = teams.get('away', {}).get('name', '')
        goals = match.get('goals', {})
        hs = goals.get('home')
        as_ = goals.get('away')
        if hs is None or as_ is None:
            continue

        if fixture_home == home_team:
            if hs > as_:
                home_form.append('W')
                away_form.append('L')
                home_wins += 1
            elif hs < as_:
                home_form.append('L')
                away_form.append('W')
                away_wins += 1
            else:
                home_form.append('D')
                away_form.append('D')
                draws += 1
        elif fixture_away == home_team:
            if as_ > hs:
                home_form.append('W')
                away_form.append('L')
                home_wins += 1
            elif as_ < hs:
                home_form.append('L')
                away_form.append('W')
                away_wins += 1
            else:
                home_form.append('D')
                away_form.append('D')
                draws += 1

    h2h_line = f"H2H últimos 5: {home_team} {home_wins}V {draws}E {away_wins}D"
    return _format_form(home_form), _format_form(away_form), h2h_line


def _fetch_api_football_context(home_team: str, away_team: str, league: str) -> dict:
    api_key = current_app.config.get('APIFOOTBALL_KEY') or current_app.config.get('RAPIDAPI_KEY')
    if not api_key:
        return {}

    client = APIFootballClient(api_key)
    league_id = APIFOOTBALL_ID_BY_LEAGUE.get(league)
    season = datetime.utcnow().year
    context = {}

    h2h = _safe_client_call(client, '/fixtures/headtohead', {'h2h': f'{home_team}-{away_team}', 'last': 5})
    if h2h and h2h.get('response'):
        home_form, away_form, h2h_line = _summarize_h2h(h2h['response'], home_team, away_team)
        context['home_form'] = f"Forma recente {home_team}: {home_form}"
        context['away_form'] = f"Forma recente {away_team}: {away_form}"
        context['h2h'] = h2h_line

    if league_id:
        injuries = _safe_client_call(
            client,
            '/injuries',
            {'league': league_id, 'season': season}
        )
        if injuries and injuries.get('response'):
            home_notes = []
            away_notes = []
            for item in injuries['response']:
                team_name = item.get('team', {}).get('name', '')
                player_name = item.get('player', {}).get('name', 'Jogador')
                reason = item.get('player', {}).get('reason') or item.get('type') or 'indisponível'
                note = f"{player_name} ({reason})"
                if team_name == home_team and len(home_notes) < 2:
                    home_notes.append(note)
                elif team_name == away_team and len(away_notes) < 2:
                    away_notes.append(note)

            context['injuries_home'] = f"Lesões {home_team}: {', '.join(home_notes) if home_notes else 'Nenhuma conhecida'}"
            context['injuries_away'] = f"Lesões {away_team}: {', '.join(away_notes) if away_notes else 'Nenhuma conhecida'}"

    return context


def _fetch_standings_context(home_team: str, away_team: str, league: str) -> str:
    code = FOOTBALL_DATA_CODE_BY_LEAGUE.get(league)
    api_key = current_app.config.get('FOOTBALL_DATA_API_KEY', '')
    if not code or not api_key:
        return ""

    client = FootballDataClient(api_key)
    data = client.get_standings(code)
    if not data:
        return ""

    positions = {}
    for standing in data.get('standings', []):
        table = standing.get('table', [])
        for row in table:
            positions[row.get('team', {}).get('name', '')] = row.get('position')

    home_pos = positions.get(home_team)
    away_pos = positions.get(away_team)
    if home_pos is None and away_pos is None:
        return ""

    home_label = f"{home_pos}º" if home_pos is not None else "N/D"
    away_label = f"{away_pos}º" if away_pos is not None else "N/D"
    return f"Posição tabela: {home_team} {home_label} | {away_team} {away_label}"


def get_match_context(home_team: str, away_team: str, league: str) -> str:
    """Monta contexto adicional sem bloquear o fluxo principal."""
    try:
        api_context = _fetch_api_football_context(home_team, away_team, league)
        standings_line = _fetch_standings_context(home_team, away_team, league)

        lines = []
        for key in ('home_form', 'away_form', 'h2h'):
            value = api_context.get(key)
            if value:
                lines.append(value)

        if standings_line:
            lines.append(standings_line)

        for key in ('injuries_home', 'injuries_away'):
            value = api_context.get(key)
            if value:
                lines.append(value)

        return "\n".join(lines)
    except Exception as exc:
        logger.debug(f"[Context] Erro montando contexto: {exc}")
        return ""
