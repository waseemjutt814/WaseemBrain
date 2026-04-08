"""Data Structures & Algorithms Expert Module.

Provides comprehensive knowledge on algorithms, data structures,
complexity analysis, and optimization techniques.
"""

from dataclasses import dataclass
from types import SimpleNamespace


@dataclass
class Algorithm:
    """Algorithm specification."""
    name: str
    category: str
    time_complexity: str
    space_complexity: str
    use_cases: list[str]
    pros: list[str]
    cons: list[str]
    example: str


@dataclass
class DataStructure:
    """Data structure specification."""
    name: str
    category: str
    time_complexity: dict  # {operation: complexity}
    space_complexity: str
    use_cases: list[str]
    advantages: list[str]
    disadvantages: list[str]


class AlgorithmsKnowledgeBase:
    """Comprehensive algorithms knowledge base."""
    
    SORTING_ALGORITHMS = [
        Algorithm(
            name="QuickSort",
            category="Divide & Conquer",
            time_complexity="O(n log n) average, O(n²) worst",
            space_complexity="O(log n)",
            use_cases=["General purpose sorting", "Most built-in sort implementations"],
            pros=["Fast in practice", "In-place", "Cache-friendly"],
            cons=["Unstable", "Bad worst case without pivoting"],
            example="Python's default Timsort is hybrid with Quicksort",
        ),
        Algorithm(
            name="MergeSort",
            category="Divide & Conquer",
            time_complexity="O(n log n) guaranteed",
            space_complexity="O(n)",
            use_cases=["Guaranteed performance needed", "External sorting"],
            pros=["Guaranteed O(n log n)", "Stable"],
            cons=["Requires O(n) space", "Not in-place"],
            example="Best for linked lists",
        ),
        Algorithm(
            name="HeapSort",
            category="Selection",
            time_complexity="O(n log n) guaranteed",
            space_complexity="O(1)",
            use_cases=["Memory constrained environments"],
            pros=["Guaranteed O(n log n)", "In-place", "O(1) space"],
            cons=["Slower in practice than QuickSort", "Not stable"],
            example="Good for hard real-time systems",
        ),
    ]
    
    SEARCHING_ALGORITHMS = [
        Algorithm(
            name="Binary Search",
            category="Searching",
            time_complexity="O(log n)",
            space_complexity="O(1) iterative, O(log n) recursive",
            use_cases=["Sorted arrays", "Database indexes"],
            pros=["Very fast", "Simple", "O(1) space iterative"],
            cons=["Requires sorted input"],
            example="Finding element in [1,3,5,7,9,11] - 3 comparisons max",
        ),
        Algorithm(
            name="Linear Search",
            category="Searching",
            time_complexity="O(n)",
            space_complexity="O(1)",
            use_cases=["Unsorted arrays", "Small datasets"],
            pros=["Simple", "Works on unsorted"],
            cons=["Slow for large data"],
            example="First occurrence search",
        ),
    ]
    
    GRAPH_ALGORITHMS = [
        Algorithm(
            name="Dijkstra's Algorithm",
            category="Shortest Path",
            time_complexity="O((V+E) log V) with min-heap",
            space_complexity="O(V)",
            use_cases=["GPS navigation", "Network routing"],
            pros=["Optimal for non-negative weights", "Efficient"],
            cons=["Slow for negative weights", "Single-source only"],
            example="Finding shortest route in a road network",
        ),
        Algorithm(
            name="Depth-First Search (DFS)",
            category="Graph Traversal",
            time_complexity="O(V + E)",
            space_complexity="O(V)",
            use_cases=["Cycle detection", "Topological sorting"],
            pros=["Memory efficient with backtracking", "Simple"],
            cons=["Can get stuck in cycles"],
            example="Finding connected components",
        ),
        Algorithm(
            name="Breadth-First Search (BFS)",
            category="Graph Traversal",
            time_complexity="O(V + E)",
            space_complexity="O(V)",
            use_cases=["Shortest path in unweighted graphs", "Level-order traversal"],
            pros=["Finds shortest path in unweighted graphs"],
            cons=["Requires queue, more memory than DFS"],
            example="Social network distance calculation",
        ),
    ]
    
    DYNAMIC_PROGRAMMING_PROBLEMS = [
        {
            "problem": "Fibonacci Sequence",
            "approach": "Memoization or tabulation",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "overlapping_subproblems": True,
            "optimal_substructure": True,
        },
        {
            "problem": "Longest Common Subsequence (LCS)",
            "approach": "DP table",
            "time_complexity": "O(m * n)",
            "space_complexity": "O(m * n)",
            "overlapping_subproblems": True,
            "optimal_substructure": True,
        },
        {
            "problem": "0/1 Knapsack Problem",
            "approach": "DP table",
            "time_complexity": "O(n * W) where W is weight capacity",
            "space_complexity": "O(n * W)",
            "overlapping_subproblems": True,
            "optimal_substructure": True,
        },
    ]
    
    DESIGN_PATTERNS = [
        {
            "pattern": "Greedy",
            "description": "Make locally optimal choice at each step",
            "examples": ["Activity selection", "Huffman coding", "Dijkstra"],
            "when_to_use": "When local optimization = global optimization",
        },
        {
            "pattern": "Divide & Conquer",
            "description": "Break into subproblems, solve, combine",
            "examples": ["Merge sort", "Quick sort", "Binary search"],
            "when_to_use": "Independent subproblems",
        },
        {
            "pattern": "Dynamic Programming",
            "description": "Solve subproblems once, reuse results",
            "examples": ["Fibonacci", "LCS", "Knapsack"],
            "when_to_use": "Overlapping subproblems + optimal substructure",
        },
    ]
    
    COMPLEXITY_ANALYSIS = {
        "common_complexities": [
            "O(1) - Constant",
            "O(log n) - Logarithmic",
            "O(n) - Linear",
            "O(n log n) - Linearithmic",
            "O(n²) - Quadratic",
            "O(n³) - Cubic",
            "O(2^n) - Exponential",
            "O(n!) - Factorial",
        ],
        "performance_rules": [
            "O(1) beats O(log n) beats O(n) beats O(n log n) beats O(n²)",
            "Constants don't matter: O(2n) = O(n)",
            "Lower terms don't matter: O(n² + n) = O(n²)",
        ],
        "acceptable_complexity": {
            "100_items": "Up to O(n²) acceptable",
            "1000_items": "O(n log n) recommended",
            "1000000_items": "O(n) or O(n log n) required",
            "1000000000_items": "O(1) or O(log n) only",
        },
    }
    
    DATA_STRUCTURES = [
        DataStructure(
            name="Array",
            category="Contiguous",
            time_complexity={
                "access": "O(1)",
                "search": "O(n)",
                "insertion": "O(n)",
                "deletion": "O(n)",
            },
            space_complexity="O(n)",
            use_cases=["Cache-friendly access", "Index-based operations"],
            advantages=["O(1) access", "Cache efficient"],
            disadvantages=["Fixed size", "O(n) insertion/deletion"],
        ),
        DataStructure(
            name="Hash Table",
            category="Hash-based",
            time_complexity={
                "access": "O(1) average",
                "search": "O(1) average",
                "insertion": "O(1) average",
                "deletion": "O(1) average",
            },
            space_complexity="O(n)",
            use_cases=["Dictionary/map", "Caching", "Deduplication"],
            advantages=["O(1) average operations", "Flexible keys"],
            disadvantages=["O(n) worst case", "Hash collisions"],
        ),
        DataStructure(
            name="Binary Search Tree",
            category="Tree",
            time_complexity={
                "access": "O(log n) balanced",
                "search": "O(log n) balanced",
                "insertion": "O(log n) balanced",
                "deletion": "O(log n) balanced",
            },
            space_complexity="O(n)",
            use_cases=["Sorted data", "Range queries"],
            advantages=["Ordered", "Efficient search"],
            disadvantages=["Can degenerate to O(n)", "Requires balancing"],
        ),
        DataStructure(
            name="Heap",
            category="Tree",
            time_complexity={
                "access_min": "O(1)",
                "insertion": "O(log n)",
                "deletion": "O(log n)",
            },
            space_complexity="O(n)",
            use_cases=["Priority queue", "Heap sort"],
            advantages=["Efficient min/max access", "O(log n) operations"],
            disadvantages=["No efficient search", "Not fully sorted"],
        ),
    ]


class AlgorithmsExpert:
    """Expert module for algorithms and data structures."""

    def __init__(self):
        self.kb = AlgorithmsKnowledgeBase()
        self.knowledge_base = SimpleNamespace(
            sorting_algorithms=list(self.kb.SORTING_ALGORITHMS),
            searching_algorithms=list(self.kb.SEARCHING_ALGORITHMS),
            graph_algorithms=list(self.kb.GRAPH_ALGORITHMS),
            data_structures=list(self.kb.DATA_STRUCTURES),
        )
        self.name = "Algorithms & Data Structures Expert"
        self.specialties = [
            "Algorithm Design",
            "Complexity Analysis",
            "Data Structure Selection",
            "Optimization",
            "Problem-Solving Patterns",
            "Performance Tuning",
        ]

    def recommend_algorithm_details(self, problem: str) -> dict[str, object]:
        recommendations = {
            'sorting': {
                'recommended': 'QuickSort or TimSort',
                'consideration': 'QuickSort for speed, MergeSort for predictable O(n log n), TimSort for real-world partially ordered data.',
            },
            'shortest_path': {
                'recommended': "Dijkstra's Algorithm",
                'consideration': 'Use Bellman-Ford only when negative edges are possible.',
            },
            'search': {
                'recommended': 'Binary Search for sorted data or Hash Table for constant-time average lookup',
                'consideration': 'Choose based on whether the data must remain ordered.',
            },
        }
        normalized = problem.lower().replace('-', '_').replace(' ', '_')
        return recommendations.get(normalized, {'error': f'Unknown problem type: {problem}'})

    def recommend_algorithm(self, problem: str, scale_hint: int | None = None) -> str:
        details = self.recommend_algorithm_details(problem)
        if 'error' in details:
            return f"Unknown problem type: {problem}."
        scale_text = f" at roughly {scale_hint} items" if scale_hint is not None else ''
        return f"Recommended algorithm for {problem}{scale_text}: {details['recommended']}. {details['consideration']}"

    def analyze_complexity(self, algorithm_name: str) -> str:
        normalized = algorithm_name.lower().strip()
        if normalized.startswith('o('):
            return f"{algorithm_name} is a complexity class. Use it to estimate how time or space grows as input size increases."
        all_algos = self.kb.SORTING_ALGORITHMS + self.kb.SEARCHING_ALGORITHMS + self.kb.GRAPH_ALGORITHMS
        for algo in all_algos:
            if algo.name.lower() == normalized:
                return f"{algo.name} complexity: time {algo.time_complexity}, space {algo.space_complexity}."
        return f"Complexity reference unavailable for {algorithm_name}. Common scalable targets are O(n log n) or better."

    def select_data_structure_details(self, requirement: str) -> dict[str, object]:
        normalized = requirement.lower().replace('-', '_').replace(' ', '_')
        recommendations = {
            'fast_lookup': {
                'recommended': 'Hash Table',
                'reason': 'It gives O(1) average lookup and update performance.',
            },
            'sorted_order': {
                'recommended': 'Binary Search Tree or Sorted Array',
                'reason': 'Choose BST for mutable workloads and sorted arrays for read-heavy access.',
            },
            'priority_queue': {
                'recommended': 'Heap',
                'reason': 'It gives efficient min/max extraction with O(log n) insertion and deletion.',
            },
            'cache_friendly': {
                'recommended': 'Array',
                'reason': 'Sequential access patterns map well to CPU caches.',
            },
        }
        return recommendations.get(normalized, {'error': f'Unknown requirement: {requirement}'})

    def select_data_structure(self, requirement: str, shape: str | None = None) -> str:
        details = self.select_data_structure_details(requirement)
        if 'error' in details:
            return f"Unknown requirement: {requirement}."
        shape_text = f" for a {shape} workload" if shape else ''
        return f"Recommended data structure{shape_text}: {details['recommended']}. {details['reason']}"

    def get_summary(self) -> str:
        return f"Algorithms Expert covering {len(self.knowledge_base.sorting_algorithms)} sorting algorithms and {len(self.knowledge_base.data_structures)} data structures."

    def answer_query(self, query: str) -> str:
        lowered = query.lower()
        if 'complexity' in lowered or lowered.startswith('o('):
            return self.analyze_complexity(query.strip())
        if 'sort' in lowered:
            return self.recommend_algorithm('sorting')
        if 'lookup' in lowered or 'dictionary' in lowered or 'hash' in lowered:
            return self.select_data_structure('fast_lookup')
        if 'graph' in lowered or 'shortest path' in lowered:
            return self.recommend_algorithm('shortest_path')
        return self.get_summary()
