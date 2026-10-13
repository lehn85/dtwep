from __future__ import annotations
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, Any
from pathlib import Path
import numpy as np
import pandas as pd

from calibration_framework.schemas import OptimizerConfig, ParameterConfig
from calibration_framework.optimizers.base import BaseOptimizer


class GeneticAlgorithm(BaseOptimizer):
    """
    Domain-agnostic Genetic Algorithm for multi-parameter digital twin model calibration.
    Supports parallel population evaluation, elitism, tournament selection, crossover, and mutation.
    """

    def __init__(
        self,
        parameters: list[ParameterConfig],
        config: OptimizerConfig | None = None,
        results_dir: str | Path | None = None,
        **kwargs: Any,
    ):
        super().__init__(parameters=parameters, config=config, results_dir=results_dir, **kwargs)

    def generate_initial_population(self, pop_size: int) -> list[list[float]]:
        """Generates uniformly distributed initial parameter vectors within defined bounds."""
        population = []
        for _ in range(pop_size):
            chrom = [random.uniform(b[0], b[1]) for b in self.bounds]
            population.append(chrom)
        return population

    def crossover(self, parent1: list[float], parent2: list[float]) -> list[float]:
        """Performs arithmetic crossover between two candidate parameter vectors."""
        alpha = random.random()
        return [alpha * p1 + (1.0 - alpha) * p2 for p1, p2 in zip(parent1, parent2)]

    def mutate(self, chromosome: list[float], mutation_rate: float) -> list[float]:
        """Applies Gaussian mutation with bounded clipping to a candidate parameter vector."""
        mutated = list(chromosome)
        for idx, (b_min, b_max) in enumerate(self.bounds):
            if random.random() < mutation_rate:
                span = b_max - b_min
                deviation = random.normalvariate(0, 0.1 * span)
                mutated[idx] = float(np.clip(mutated[idx] + deviation, b_min, b_max))
        return mutated

    def run(
        self,
        evaluate_fn: Callable[[list[float], int, int], tuple[float, float, pd.DataFrame]],
        initial_parameters: list[list[float]] | None = None,
        on_progress_callback: Callable[[int, list[float], float, list[float]], None] | None = None,
        initial_population: list[list[float]] | None = None,
        on_generation_callback: Callable[[int, list[float], float, list[float]], None] | None = None,
        **kwargs: Any,
    ) -> tuple[list[float], float]:
        """
        Runs the Genetic Algorithm optimization loop.
        """
        # Support aliases
        init_pop = initial_parameters if initial_parameters is not None else initial_population
        callback = on_progress_callback if on_progress_callback is not None else on_generation_callback

        pop_size = self.config.pop_size
        generations = self.config.generations
        mutation_rate = self.config.mutation_rate
        elite_count = self.config.elite_count
        workers = self.config.max_workers or min(pop_size, os.cpu_count() or 4)

        population: list[list[float]] = []
        if init_pop:
            population.extend(init_pop)

        if len(population) < pop_size:
            population.extend(self.generate_initial_population(pop_size - len(population)))
        elif len(population) > pop_size:
            population = population[:pop_size]

        best_overall_chromosome: list[float] | None = None
        best_overall_fitness = -1e10
        fitness_history: list[float] = []
        history_records: list[dict[str, Any]] = []

        print(f"Starting Genetic Algorithm: Population={pop_size}, Generations={generations}, Workers={workers}")

        with ProcessPoolExecutor(max_workers=workers) as executor:
            for gen in range(generations):
                # Parallel candidate evaluation
                futures = [
                    executor.submit(evaluate_fn, chrom, idx, gen)
                    for idx, chrom in enumerate(population)
                ]
                results = [f.result() for f in futures]

                fitnesses = [r[0] for r in results]
                exec_times = [r[1] for r in results]
                dfs = [r[2] for r in results]

                pop_fitness = list(zip(population, fitnesses, exec_times, dfs))
                pop_fitness.sort(key=lambda x: x[1], reverse=True)

                current_best_chrom, current_best_fit, current_best_exec_time, current_best_df = pop_fitness[0]
                fitness_history.append(current_best_fit)

                mean_fitness = float(np.mean(fitnesses))
                diversity = float(np.mean(np.std(population, axis=0)))
                mean_exec_time = float(np.mean(exec_times))

                if current_best_fit > best_overall_fitness:
                    best_overall_fitness = current_best_fit
                    best_overall_chromosome = list(current_best_chrom)

                formatted_chrom = [round(x, 4) for x in current_best_chrom]
                print(
                    f"Iteration {gen+1}/{generations} | Best Fitness: {current_best_fit:.6f} | Mean: {mean_fitness:.6f} | Div: {diversity:.4f} | Exec: {mean_exec_time:.2f}s | Params: {formatted_chrom}"
                )

                record: dict[str, Any] = {
                    "generation": gen + 1,
                    "iteration": gen + 1,
                    "best_fitness": current_best_fit,
                    "mean_fitness": mean_fitness,
                    "diversity": diversity,
                    "mean_exec_time_s": mean_exec_time,
                }
                for p_name, val in zip(self.param_names, current_best_chrom):
                    record[f"best_{p_name}"] = val
                history_records.append(record)

                # Save best candidate results dataframe
                if not current_best_df.empty:
                    gen_dir = os.path.join(self.results_dir, f"gen_{gen}")
                    os.makedirs(gen_dir, exist_ok=True)
                    current_best_df.to_csv(os.path.join(gen_dir, "best_individual_results.csv"), index=False)

                if callback and best_overall_chromosome is not None:
                    callback(
                        gen + 1,
                        best_overall_chromosome,
                        best_overall_fitness,
                        fitness_history,
                    )

                # Generate next generation
                next_generation = []
                for i in range(min(elite_count, pop_size)):
                    next_generation.append(list(pop_fitness[i][0]))

                def tournament_select():
                    candidates = random.sample(pop_fitness, min(self.config.tournament_size, len(pop_fitness)))
                    candidates.sort(key=lambda x: x[1], reverse=True)
                    return candidates[0][0]

                while len(next_generation) < pop_size:
                    p1 = tournament_select()
                    p2 = tournament_select()
                    child = self.crossover(p1, p2)
                    child = self.mutate(child, mutation_rate)
                    next_generation.append(child)

                population = next_generation

        # Save optimization history CSV
        self.history = history_records
        df_history = pd.DataFrame(history_records)
        df_history.to_csv(os.path.join(self.results_dir, "calibration_history.csv"), index=False)
        df_history.to_csv(os.path.join(self.results_dir, "ga_results.csv"), index=False)

        return best_overall_chromosome or population[0], best_overall_fitness
