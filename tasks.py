"""
Benchmark tasks for Kimi K2.6 vs Claude Opus 4.7 comparison.
10 hard discriminating prompts across reasoning, coding, and analysis categories.
"""

TASKS = [
    {
        "id": "reasoning_001",
        "category": "logical_reasoning",
        "name": "Zebra Puzzle Variant",
        "prompt": """Solve this logic puzzle:

Five houses in a row are painted different colors: Red, Blue, Green, Yellow, White.
Five people of different nationalities live in them: Norwegian, English, Spanish, Japanese, Italian.
They drink different beverages: Tea, Coffee, Milk, Beer, Water.
They smoke different brands: Pall Mall, Dunhill, Blends, Blue Master, Prince.

Clues:
1. The Norwegian lives in the first house.
2. The Englishman lives in the red house.
3. The green house is immediately to the left of the white house.
4. The Spaniard drinks coffee.
5. The person in the green house drinks tea.
6. The person who smokes Pall Mall owns birds.
7. The person in the yellow house smokes Dunhill.
8. Milk is drunk in the middle house.
9. The Japanese smokes Prince.
10. The Italian lives next to the person who smokes Blends.
11. The person who smokes Blue Master drinks beer.
12. The Norwegian lives next to the blue house.

Question: Who drinks water? Who owns the fish?

Provide your reasoning step by step, then state the final answer clearly."""
    },
    {
        "id": "reasoning_002",
        "category": "mathematical_reasoning",
        "name": "Expected Value Paradox",
        "prompt": """Consider the St. Petersburg paradox variant:

You play a game where a fair coin is flipped repeatedly until it lands heads.
- If heads appears on the 1st flip, you win $2
- If heads appears on the 2nd flip, you win $4
- If heads appears on the 3rd flip, you win $8
- And so on... (2^n dollars if first heads is on nth flip)

The expected value of this game is theoretically infinite. However, in practice:
1. What is the maximum amount you should rationally pay to play this game if you can only play once and your net worth is $100,000?
2. How does the answer change if you can play 100 times?
3. What psychological and economic factors should influence this decision beyond pure expected value?

Provide a detailed analysis with calculations."""
    },
    {
        "id": "reasoning_003",
        "category": "causal_reasoning",
        "name": "Confounding Variables Analysis",
        "prompt": """A study finds that ice cream sales and drowning incidents are highly correlated (r = 0.95).

Three people interpret this differently:
- Person A: "Ice cream consumption must cause drowning somehow. Maybe it causes cramps?"
- Person B: "This is spurious correlation with no causal link."  
- Person C: "There's likely a confounding variable at play."

1. Who is most likely correct and why?
2. Identify the likely confounding variable(s).
3. Design a study that could actually test whether ice cream consumption affects drowning risk, controlling for confounders.
4. Explain why controlling for confounders is essential in causal inference, using this example.

Be thorough in your explanation of causal inference principles."""
    },
    {
        "id": "coding_001",
        "category": "algorithm_design",
        "name": "Concurrent Rate Limiter",
        "prompt": """Implement a thread-safe rate limiter in Python that supports:

1. Token bucket algorithm with configurable rate and burst capacity
2. Per-user rate limiting (different limits for different users)
3. Concurrent request handling without race conditions
4. Graceful degradation when Redis is unavailable (fallback to in-memory)
5. Proper cleanup of expired user entries to prevent memory leaks

Requirements:
- Must handle high concurrency (1000+ requests/second)
- Must be distributed-safe when Redis is available
- Must have O(1) time complexity for the check operation
- Include type hints and docstrings
- Include unit tests with mocked time

Provide the complete implementation with explanations of your design decisions."""
    },
    {
        "id": "coding_002",
        "category": "system_design",
        "name": "Distributed ID Generator",
        "prompt": """Design a distributed unique ID generation system that:

1. Generates roughly sortable IDs (K-sortable within a few milliseconds)
2. Works across multiple data centers without coordination
3. Handles 100,000 IDs/second per node
4. Has zero single points of failure
5. IDs are 64-bit integers (not UUID strings)
6. Guarantees uniqueness even with clock skew between nodes

Requirements:
- Explain your bit allocation scheme
- Handle clock regression (NTP sync causing time to go backward)
- Ensure IDs are unique even if a node crashes and restarts
- Provide Python implementation
- Analyze the theoretical limits (how many nodes, IDs/second, time range)

Compare your solution to Twitter Snowflake and explain the trade-offs."""
    },
    {
        "id": "coding_003",
        "category": "debugging",
        "name": "Memory Leak Diagnosis",
        "prompt": """A Python web service running under uWSGI is experiencing memory leaks in production. The memory usage grows steadily until the workers are killed by the OOM killer.

Given this information:
- Memory grows ~50MB per hour per worker
- The app uses SQLAlchemy with connection pooling
- There's a background thread processing a queue
- The app caches some data in a global dictionary
- Restarting workers temporarily fixes the issue
- Local testing doesn't reproduce the leak

1. What are the 5 most likely causes, ranked by probability?
2. For each cause, describe:
   - Why it causes a leak in production but not locally
   - How to confirm it's the culprit
   - How to fix it
3. Write a diagnostic script that could help identify the leak type
4. Explain how to use tracemalloc or objgraph for debugging

Be specific about Python/uWSGI quirks that could cause this."""
    },
    {
        "id": "analysis_001",
        "category": "ethical_reasoning",
        "name": "Trolley Problem Variant",
        "prompt": """Consider this modified trolley problem:

A self-driving car must choose between:
Option A: Swerve, killing 1 pedestrian who is jaywalking
Option B: Continue straight, killing 3 pedestrians who are crossing legally on a green light

Additional context:
- The jaywalker is a 70-year-old person
- The 3 legal crossers are ages 25, 30, and 35
- The car's passenger is a parent with a child in the back seat
- The jaywalker is visible and the car could theoretically stop, but not in time to avoid hitting them if it swerves

1. From a utilitarian perspective, what should the car do? Calculate the expected utility.
2. From a deontological perspective, what should the car do? What duties are in conflict?
3. From a virtue ethics perspective, what would a virtuous person program the car to do?
4. How should the legal system handle liability in each scenario?
5. Should the passenger have any control over this decision? Why or why not?

Provide a nuanced analysis that acknowledges the limitations of each ethical framework."""
    },
    {
        "id": "analysis_002",
        "category": "scientific_reasoning",
        "name": "Study Design Critique",
        "prompt": """Critique this study design:

"A pharmaceutical company wants to test a new Alzheimer's drug. They recruit 500 patients from memory clinics. 250 get the drug, 250 get placebo. The primary endpoint is cognitive score improvement after 12 months. The study is stopped early because the drug group shows 15% better scores (p < 0.05). The company publishes in a high-impact journal and applies for FDA approval."

Identify at least 10 potential problems with this study design and analysis:

For each problem:
1. Explain why it's problematic
2. Describe how it could bias the results
3. Suggest how to fix it

Consider: selection bias, measurement bias, confounding, multiple comparisons, publication bias, statistical power, generalizability, blinding, intention-to-treat, and any other relevant issues.

Then, describe what a rigorous Phase 3 trial for this drug should look like."""
    },
    {
        "id": "analysis_003",
        "category": "strategic_reasoning",
        "name": "Game Theory Scenario",
        "prompt": """Analyze this game theory scenario:

Two companies, A and B, are competing in a market. Each quarter they simultaneously choose:
- COOPERATE: Maintain high prices, split market 50/50
- DEFECT: Lower prices, capture 70% of market but reduce margins

Payoff matrix (quarterly profit in millions):
- Both Cooperate: A=$10M, B=$10M
- A Cooperates, B Defects: A=$3M, B=$15M
- A Defects, B Cooperates: A=$15M, B=$3M
- Both Defect: A=$5M, B=$5M

Additional constraints:
- The game repeats indefinitely (infinite horizon)
- There's a 5% chance each quarter that the market collapses (game ends)
- Companies can observe all past actions
- There's a 1% chance of "trembling hand" - accidentally choosing wrong action
- Company A is known to use tit-for-tat strategy

1. What is the Nash equilibrium for the one-shot game?
2. What is the subgame perfect equilibrium for the repeated game without trembles?
3. How does the 5% collapse probability affect optimal strategy?
4. How should Company B respond to A's tit-for-tat strategy?
5. Calculate the expected long-term payoff for different strategies
6. What happens if the trembling hand probability increases to 10%?

Show your calculations and reasoning."""
    },
    {
        "id": "coding_004",
        "category": "code_optimization",
        "name": "Query Optimization Challenge",
        "prompt": """Optimize this Python function that processes large datasets:

```python
def process_data(users, orders, products):
    results = []
    for user in users:
        user_orders = []
        for order in orders:
            if order['user_id'] == user['id']:
                for product in products:
                    if product['id'] == order['product_id']:
                        user_orders.append({
                            'user_name': user['name'],
                            'product_name': product['name'],
                            'amount': order['amount'],
                            'date': order['date']
                        })
        results.extend(user_orders)
    return results
```

Constraints:
- users: 1 million records
- orders: 10 million records  
- products: 100,000 records
- Must run in under 30 seconds
- Memory limit: 8GB
- Cannot use a database (data comes from CSV files)

1. Analyze the time and space complexity of the original code
2. Identify the bottlenecks
3. Provide an optimized implementation
4. Explain your optimization strategy
5. Estimate the performance improvement
6. Consider: indexing, data structures, streaming, parallelization, memory efficiency

Provide the complete optimized code with comments explaining each optimization."""
    }
]

# Model configuration. Slugs are starting guesses — at runtime the script queries
# OpenRouter /models and resolves the real slug containing these substrings.
MODELS = {
    "kimi": {
        "name": "Kimi K2.6",
        "slug": "moonshotai/kimi-k2.6",
        "slug_hints": ["kimi-k2.6", "kimi-k2-thinking", "kimi-k2"],
        "namespace": "moonshotai",
    },
    "claude": {
        "name": "Claude Opus 4.7",
        "slug": "anthropic/claude-opus-4.7",
        "slug_hints": ["opus-4.7", "opus-4-7"],
        "namespace": "anthropic",
    },
}

JUDGE_MODEL = {
    "name": "Claude Opus 4.7 (judge)",
    "slug": "anthropic/claude-opus-4.7",
    "slug_hints": ["opus-4.7", "opus-4-7"],
    "namespace": "anthropic",
}

# Metadata for the benchmark
BENCHMARK_METADATA = {
    "name": "Kimi K2.6 vs Claude Opus 4.7 Benchmark",
    "version": "1.0.0",
    "task_count": len(TASKS),
    "categories": list(set(t["category"] for t in TASKS)),
    "models": {
        "kimi": "kimi-k2.6",
        "claude": "opus-4.7"
    }
}

if __name__ == "__main__":
    print(f"Benchmark: {BENCHMARK_METADATA['name']}")
    print(f"Tasks: {BENCHMARK_METADATA['task_count']}")
    print(f"Categories: {', '.join(BENCHMARK_METADATA['categories'])}")
    for task in TASKS:
        print(f"  - {task['id']}: {task['name']} ({task['category']})")
