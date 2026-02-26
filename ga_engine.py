import random
import numpy as np
from collections import defaultdict

class GeneticAlgorithmEngine:
    def __init__(self, teams_data, availabilities, group_blocks, opening_hour, closing_hour):
        """
        teams_data: List of dicts: [{'id': 1, 'group_name': 'B', 'members': [{'id': 101, 'role': 'TEAM_LEADER'}, ...]}, ...]
        availabilities: Dict mapping user_id -> set of (day, hour).
        group_blocks: Set of (group_name, day, hour) tuples.
        opening_hour: int
        closing_hour: int
        """
        self.teams_data = teams_data
        self.team_ids = [t['id'] for t in teams_data]
        self.team_map = {t['id']: t for t in teams_data}
        self.availabilities = availabilities
        self.group_blocks = group_blocks # Set of (group_name, day, hour)
        self.opening_hour = int(opening_hour)
        self.closing_hour = int(closing_hour)

        # Define the slots (Day, Hour)
        self.slots = []
        # Assumption: Mon-Fri (0-4)
        for day in range(0, 5):
            for hour in range(self.opening_hour, self.closing_hour):
                self.slots.append((day, hour))

        self.num_slots = len(self.slots)

        # Precompute valid teams for each slot
        self.valid_teams_for_slot = []
        for i, (day, hour) in enumerate(self.slots):
            valid = []
            for team in self.teams_data:
                # Check Group Block Hard Constraint
                if (team['group_name'], day, hour) in self.group_blocks:
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

        # Penalties/Bonuses
        BONUS_LEADER = 50
        PENALTY_NO_LEADER = 50
        BONUS_ATTENDANCE = 10
        PENALTY_UNEVEN = 20

        for i, team_id in enumerate(chromosome):
            if team_id is None:
                continue

            day, hour = self.slots[i]
            team = self.team_map[team_id]
            team_hours[team_id] += 1

            # Hard Constraint: Group Blocks (Double check)
            if (team['group_name'], day, hour) in self.group_blocks:
                return -float('inf')

            # Soft Constraints

            # Attendance & Leader
            available_members = 0
            leader_available = False
            total_members = len(team['members'])

            for member in team['members']:
                if (day, hour) in self.availabilities.get(member['id'], set()):
                    available_members += 1
                    if member['role'] == "TEAM_LEADER":
                        leader_available = True

            # Maximize Attendance
            if total_members > 0:
                score += (available_members / total_members) * BONUS_ATTENDANCE

            # Leader Priority
            if leader_available:
                score += BONUS_LEADER
            else:
                score -= PENALTY_NO_LEADER

        # Fairness: Standard deviation of hours
        hours = list(team_hours.values())
        # Include 0 for teams with no slots
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
            # Evaluate fitness
            fitnesses = [self.calculate_fitness(chrom) for chrom in population]

            # Sort by fitness
            # Combine population and fitness
            pop_fit = list(zip(population, fitnesses))
            pop_fit.sort(key=lambda x: x[1], reverse=True)

            population = [x[0] for x in pop_fit]

            # Elitism: Keep top 2
            new_population = population[:2]

            # Selection & Breeding (Tournament Selection)
            while len(new_population) < pop_size:
                # Tournament
                candidates = random.sample(population[:10], k=2) # Pick from top 10
                parent1 = candidates[0] # Already sorted? No, sample returns random.
                # Actually, pop is sorted.
                # Let's pick from top half
                limit = len(population) // 2
                p1 = population[random.randint(0, limit)]
                p2 = population[random.randint(0, limit)]

                child1, child2 = self.crossover(p1, p2)
                new_population.append(self.mutate(child1))
                if len(new_population) < pop_size:
                    new_population.append(self.mutate(child2))

            population = new_population

        best_chromosome = population[0] # Best one is at index 0 because we sort every gen
        return self.decode_chromosome(best_chromosome)

    def decode_chromosome(self, chromosome):
        schedule = []
        for i, team_id in enumerate(chromosome):
            if team_id is not None:
                day, hour = self.slots[i]
                schedule.append({
                    "team_id": team_id,
                    "day_of_week": day,
                    "hour": hour
                })
        return schedule
