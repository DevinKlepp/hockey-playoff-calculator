import pprint
from collections import defaultdict
from functools import cmp_to_key

from requests import get


class HockeyStandings:
    def __init__(self, skip_load=False):
        self.skip_load = skip_load
        self.teams = {}
        self.seen_games = set()
        self.remainging_games = {}

    def get_current_standings_data(self):
        """
        Gets the current standings data from the NHL API
        """
        standings = get("https://api-web.nhle.com/v1/standings/now").json()["standings"]
        return standings

    def set_standings_data(self, standings_data):
        """
        Sets the standings data to the standings attribute by team abbreviation
        """
        for team in standings_data:
            team_data = {
                "name": team["teamAbbrev"]["default"],
                "points": team["points"],
                "games_played": team["gamesPlayed"],
                "regulation_wins": team["regulationWins"],
                "regulation_plus_ot_wins": team["regulationPlusOtWins"],
                "total_wins": team["wins"],
                "goal_differential": team["goalDifferential"],
                "goals_for": team["goalFor"],
                "division": team["divisionAbbrev"],
                "conference": team["conferenceAbbrev"],
                "head_to_head_record": defaultdict(
                    lambda: {"wins": 0, "losses": 0}
                ),  # Key is opposing team's abbreviation, value is {wins: x, losses: y}
            }
            self.teams[team["teamAbbrev"]["default"]] = team_data

    def get_team_schedule(self):
        """
        Gets the schedule for the team
        """
        schedule = {}

        for team in self.teams:
            print(f"Getting schedule for {team}...")
            team_schedule = get(
                f"https://api-web.nhle.com/v1/club-schedule-season/{team}/20242025"
            ).json()

            schedule[team] = team_schedule
        return schedule

    def set_game_outcome(self, game):  # We're double writing games here
        """
        Sets the outcome of the game
        """
        home_score = game["homeTeam"]["score"]
        away_score = game["awayTeam"]["score"]
        home_team = game["homeTeam"]["abbrev"]
        away_team = game["awayTeam"]["abbrev"]

        # Always make home team the winning team for simplicity
        if away_score > home_score:
            home_team, away_team = away_team, home_team

        # Set head to head record for teams
        self.teams[home_team]["head_to_head_record"][away_team]["wins"] += 1
        self.teams[away_team]["head_to_head_record"][home_team]["losses"] += 1

    def set_completed_and_future_games(self, team_schedule):
        """
        Sets the completed and future games for each team
        """
        for team in team_schedule:
            print(f"Setting games for {team}...")
            for game in team_schedule[team]["games"]:
                # Skip preseason games
                if game["gameType"] == 1 or game["id"] in self.seen_games:
                    continue
                if game["gameState"] == "OFF":
                    self.set_game_outcome(game)
                    self.seen_games.add(game["id"])
                else:
                    self.remainging_games[game["id"]] = game

    def set_games(self):
        team_schedule = self.get_team_schedule()
        self.set_completed_and_future_games(team_schedule)

    def set_current_standings(self):
        standings_data = self.get_current_standings_data()
        self.set_standings_data(standings_data)

    def get_future_games():
        pass

    def simulate_remaining_games():
        pass

    def primary_tiebreaker(self, team):
        """
        Given a teams data, returns a tuple of primary tiebreaker data before head-to-head
        """
        return (
            -team["points"],  # 1. Points (higher is better)
            team["games_played"],  # 2. Fewer games played
            -team["regulation_wins"],  # 3. Regulation wins
            -team["regulation_plus_ot_wins"],  # 4. Regulation + OT wins
            -team["total_wins"],  # 5. Total wins
            # 6. Head to head results (handled separately)
        )

    def secondary_tiebreaker(self, team):
        """
        Given a teams data, returns a tuple of secondary tiebreaker data after head-to-head
        """
        return (
            -team["goal_differential"],  # 7. Goal differential
            -team["goals_for"],  # 8. Most goals for
        )

    def compare_head_to_head(self, team1_data, team2_data):
        """
        Compares the head-to-head record between two teams within a group of tied teams.
        """
        matchup = team1_data["head_to_head_record"][team2_data["name"]]
        if matchup["wins"] > matchup["losses"]:
            return -1
        elif matchup["losses"] > matchup["wins"]:
            return 1
        else:  # Compare secondary tiebreakers
            0

    def team_comparator(self, team1_data, team2_data):
        """
        Compares two teams based on head to head and secondary tiebreakers
        """
        head_to_head = self.compare_head_to_head(team1_data, team2_data)
        if head_to_head != 0:
            return head_to_head
        else:
            secondary_result = self.secondary_tiebreaker(
                team1_data
            ) < self.secondary_tiebreaker(team2_data)
            return -1 if secondary_result else 1

    def sort_tied_teams(self, tied_teams):
        """
        Sorts tied teams based on head-to-head and secondary tiebreakers
        """
        sorted_teams = sorted(tied_teams, key=cmp_to_key(self.team_comparator))
        return sorted_teams

    def get_playoff_picture(self):
        """
        Given the current standings, constructs and returns a wildcard playoff picture
        """
        # Initial sorting based on all criteria except head-to-head
        sorted_teams = sorted(
            self.teams.items(), key=lambda item: self.primary_tiebreaker(item[1])
        )

        # Look for equals and store them in a dict
        equal_primary_tiebreakers = defaultdict(list)
        for team, data in sorted_teams:
            key = self.primary_tiebreaker(data)
            equal_primary_tiebreakers[key].append((team, data))

        # Add final standings to list
        final_standings = []
        for key, tied_teams in equal_primary_tiebreakers.items():
            if len(tied_teams) > 1:
                # Sort the tied teams using head-to-head and secondary tiebreakers
                sorted_tied_teams = self.sort_tied_teams(tied_teams)
                final_standings.extend(sorted_tied_teams)
            else:
                final_standings.extend(tied_teams)

        return final_standings


standings = HockeyStandings()
standings.set_current_standings()
standings.set_games()
standings.get_playoff_picture()
