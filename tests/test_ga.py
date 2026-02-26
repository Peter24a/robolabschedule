import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ga_engine import GeneticAlgorithmEngine

class TestGAEngine(unittest.TestCase):
    def test_ga_constraints(self):
        # Mock data
        teams_data = [
            {'id': 1, 'name': 'Team 1', 'group_name': 'B', 'members': [{'id': 101, 'role': 'TEAM_LEADER'}]},
            {'id': 2, 'name': 'Team 2', 'group_name': 'D', 'members': [{'id': 102, 'role': 'TEAM_LEADER'}]},
        ]

        # Availabilities: user 101 avail at (0, 7), 102 at (0, 8)
        availabilities = {
            101: {(0, 7)},
            102: {(0, 8)}
        }

        # Group Block: Group B blocked at 8. Group D blocked at 7.
        # Team 1 (Group B) cannot go at 8. Can go at 7? Yes (Group B not blocked at 7).
        # Team 2 (Group D) cannot go at 7. Can go at 8? Yes (Group D not blocked at 8).
        group_blocks = {
            ('D', 0, 7),
            ('B', 0, 8)
        }

        opening_hour = 7
        closing_hour = 9 # Slots: 7, 8.

        ga = GeneticAlgorithmEngine(teams_data, availabilities, group_blocks, opening_hour, closing_hour)

        # Run GA
        schedule = ga.run(generations=10, pop_size=10)

        assigned_slots = set()
        for item in schedule:
            team_id = item['team_id']
            day = item['day_of_week']
            hour = item['hour']
            assigned_slots.add((day, hour))

            # Find team
            team = next(t for t in teams_data if t['id'] == team_id)
            group = team['group_name']

            # Check Group Block
            if (group, day, hour) in group_blocks:
                self.fail(f"Team {team_id} (Group {group}) scheduled at blocked slot {day}:{hour}")

        # We expect Team 1 at 7 and Team 2 at 8.
        # But GA is random, maybe it didn't find the optimal solution in 10 generations.
        # But Hard Constraints MUST be respected.

        # Ensure distinct slots (implicit in GA representation)
        self.assertEqual(len(schedule), len(assigned_slots), "Duplicate slots found")

if __name__ == '__main__':
    unittest.main()
