import random
import numpy as np
from collections import defaultdict
from core.periods import PERIOD_INDICES

class GeneticAlgorithmEngine:
    def __init__(self, teams_data, availabilities, group_blocks, robotics_class_slots=None, first_period=1):
        """
        teams_data: List of dicts: [{'id': 1, 'group_name': 'B', 'members': [{'id': 101, 'role': 'TEAM_LEADER'}, ...]}, ...]
        availabilities: Dict mapping user_id -> set of (day, period).
        group_blocks: Set of (group_name, day, period) tuples.
        robotics_class_slots: List of {'group_name': 'B', 'day': 0, 'period': 3} - mandatory lab reservations.
        first_period: int, 1 or 3 (whether the lab opens at P1 or P3).
        """
        self.teams_data = teams_data
        self.team_ids = [t['id'] for t in teams_data]
        self.team_map = {t['id']: t for t in teams_data}
        self.availabilities = availabilities
        self.group_blocks = group_blocks

        # Pre-assign robotics class slots (these are locked, not part of GA chromosome)
        self.locked_slots = {}  # (day, period) -> group_name
        if robotics_class_slots:
            for rcs in robotics_class_slots:
                self.locked_slots[(rcs['day'], rcs['period'])] = rcs['group_name']

        # Build free slots: all periods NOT already locked by robotics classes
        self.slots = []
        for day in range(0, 5):
            for period in PERIOD_INDICES:
                if period >= first_period:
                    slot = (day, period)
                    if slot not in self.locked_slots:
                        self.slots.append(slot)

        self.num_slots = len(self.slots)

        # Precompute valid teams for each free slot
        self.valid_teams_for_slot = []
        for i, (day, period) in enumerate(self.slots):
            valid = []
            for team in self.teams_data:
                if (team['group_name'], day, period) in self.group_blocks:
                    continue
                valid.append(team['id'])
            self.valid_teams_for_slot.append(valid)

    def generate_initial_population(self, pop_size=50):
        population = []
        for _ in range(pop_size):
            chromosome = []
            for i in range(self.num_slots):
                valid_teams = self.valid_teams_for_slot[i]
                if valid_teams and random.random() > 0.3:
                    chromosome.append(random.choice(valid_teams))
                else:
                    chromosome.append(None)
            population.append(chromosome)
        return population

    def calculate_fitness(self, chromosome):
        score = 0
        team_hours = defaultdict(int)

        BONUS_LEADER = 50
        PENALTY_NO_LEADER = 50
        BONUS_ATTENDANCE = 10
        PENALTY_UNEVEN = 20

        for i, team_id in enumerate(chromosome):
            if team_id is None:
                continue

            day, period = self.slots[i]
            team = self.team_map[team_id]
            team_hours[team_id] += 1

            # Hard Constraint: Group Blocks
            if (team['group_name'], day, period) in self.group_blocks:
                return -float('inf')

            # Soft Constraints
            available_members = 0
            leader_available = False
            total_members = len(team['members'])

            for member in team['members']:
                if (day, period) in self.availabilities.get(member['id'], set()):
                    available_members += 1
                    if member['role'] == "TEAM_LEADER":
                        leader_available = True

            if total_members > 0:
                score += (available_members / total_members) * BONUS_ATTENDANCE

            if leader_available:
                score += BONUS_LEADER
            else:
                score -= PENALTY_NO_LEADER

        # Fairness
        hours = list(team_hours.values())
        for tid in self.team_ids:
            if tid not in team_hours:
                hours.append(0)

        if hours:
            std_dev = np.std(hours)
            score -= (std_dev * PENALTY_UNEVEN)

        return score

    def crossover(self, parent1, parent2):
        if self.num_slots < 2:
            return parent1, parent2
        point = random.randint(1, self.num_slots - 1)
        child1 = parent1[:point] + parent2[point:]
        child2 = parent2[:point] + parent1[point:]
        return child1, child2

    def mutate(self, chromosome, mutation_rate=0.05):
        new_chrom = list(chromosome)
        for i in range(self.num_slots):
            if random.random() < mutation_rate:
                valid_teams = self.valid_teams_for_slot[i]
                if valid_teams and random.random() > 0.3:
                    new_chrom[i] = random.choice(valid_teams)
                else:
                    new_chrom[i] = None
        return new_chrom

    def run(self, generations=50, pop_size=20):
        population = self.generate_initial_population(pop_size)

        for gen in range(generations):
            fitnesses = [self.calculate_fitness(chrom) for chrom in population]
            pop_fit = list(zip(population, fitnesses))
            pop_fit.sort(key=lambda x: x[1], reverse=True)
            population = [x[0] for x in pop_fit]

            # Elitism: Keep top 2
            new_population = population[:2]

            while len(new_population) < pop_size:
                limit = len(population) // 2
                p1 = population[random.randint(0, limit)]
                p2 = population[random.randint(0, limit)]

                child1, child2 = self.crossover(p1, p2)
                new_population.append(self.mutate(child1))
                if len(new_population) < pop_size:
                    new_population.append(self.mutate(child2))

            population = new_population

        best_chromosome = population[0]
        return self.decode_chromosome(best_chromosome)

    def decode_chromosome(self, chromosome):
        schedule = []
        # Free-slot assignments from GA
        for i, team_id in enumerate(chromosome):
            if team_id is not None:
                day, period = self.slots[i]
                schedule.append({
                    "team_id": team_id,
                    "day_of_week": day,
                    "period": period,
                    "is_robotics_class": False,
                    "group_name": None
                })
        # Locked robotics class slots
        for (day, period), group_name in self.locked_slots.items():
            schedule.append({
                "team_id": None,
                "day_of_week": day,
                "period": period,
                "is_robotics_class": True,
                "group_name": group_name
            })
        return schedule
