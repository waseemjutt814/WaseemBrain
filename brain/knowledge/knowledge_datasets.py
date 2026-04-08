"""Multi-domain knowledge datasets for Waseem Brain.

High-quality structured datasets covering reasoning, mathematics, logic,
programming, science, and general knowledge to enhance system expertise.
"""

# =============================================================================
# LOGIC & REASONING DATASET
# =============================================================================
LOGIC_REASONING_DATASET = [
    {
        "id": "logic_001",
        "category": "Deductive Logic",
        "difficulty": "beginner",
        "premise": "All cats are animals. Fluffy is a cat.",
        "question": "Is Fluffy an animal?",
        "answer": "Yes",
        "reasoning": "By logical deduction: All cats → animals; Fluffy is a cat → Fluffy is an animal",
        "proof_steps": [
            "1. All cats ⊆ animals (premise)",
            "2. Fluffy ∈ cats (premise)",
            "3. Therefore, Fluffy ∈ animals (from 1,2)",
        ],
        "confidence": 1.0,
    },
    {
        "id": "logic_002",
        "category": "Conditional Logic",
        "difficulty": "intermediate",
        "premise": "If it rains, the ground is wet. It is raining.",
        "question": "Is the ground wet?",
        "answer": "Yes",
        "reasoning": "Modus Ponens: P→Q, P ⊢ Q",
        "proof_steps": [
            "1. rain → wet (premise)",
            "2. rain (premise)",
            "3. Therefore, wet (modus ponens)",
        ],
        "confidence": 1.0,
    },
    {
        "id": "logic_003",
        "category": "Set Theory",
        "difficulty": "intermediate",
        "premise": "{1,2,3} ⊆ {1,2,3,4,5}",
        "question": "Is 2 in the second set?",
        "answer": "Yes",
        "reasoning": "All elements of {1,2,3} are in {1,2,3,4,5}, including 2",
        "proof_steps": [
            "1. ∀x: x∈A → x∈B (given A⊆B)",
            "2. 2∈A (premise)",
            "3. Therefore, 2∈B",
        ],
        "confidence": 1.0,
    },
]

# =============================================================================
# MATHEMATICAL REASONING DATASET
# =============================================================================
MATH_REASONING_DATASET = [
    {
        "id": "math_001",
        "category": "Algebra",
        "difficulty": "beginner",
        "problem": "Solve: 2x + 5 = 13",
        "answer": "x = 4",
        "solution_steps": [
            "2x + 5 = 13",
            "2x = 13 - 5",
            "2x = 8",
            "x = 8/2",
            "x = 4",
        ],
        "verification": "2(4) + 5 = 8 + 5 = 13 ✓",
        "concept": "Linear equations",
    },
    {
        "id": "math_002",
        "category": "Geometry",
        "difficulty": "intermediate",
        "problem": "Find the area of a triangle with base=10, height=6",
        "answer": "Area = 30",
        "solution_steps": [
            "Area = (1/2) × base × height",
            "Area = (1/2) × 10 × 6",
            "Area = (1/2) × 60",
            "Area = 30 square units",
        ],
        "concept": "Triangle area formula",
    },
    {
        "id": "math_003",
        "category": "Statistics",
        "difficulty": "intermediate",
        "problem": "Calculate mean of: 10, 20, 30, 40, 50",
        "answer": "Mean = 30",
        "solution_steps": [
            "Mean = (10 + 20 + 30 + 40 + 50) / 5",
            "Mean = 150 / 5",
            "Mean = 30",
        ],
        "concept": "Arithmetic mean",
    },
]

# =============================================================================
# PROGRAMMING & ALGORITHM DATASET
# =============================================================================
PROGRAMMING_DATASET = [
    {
        "id": "prog_001",
        "category": "Python Basics",
        "difficulty": "beginner",
        "task": "Write a function to reverse a string",
        "solution": "def reverse_string(s: str) -> str:\n    return s[::-1]",
        "explanation": "Python slicing [::-1] reverses the string efficiently",
        "test_cases": [
            {"input": "hello", "expected": "olleh"},
            {"input": "python", "expected": "nohtyp"},
            {"input": "", "expected": ""},
        ],
        "complexity": "O(n) time, O(n) space",
    },
    {
        "id": "prog_002",
        "category": "Algorithms",
        "difficulty": "intermediate",
        "task": "Implement binary search",
        "solution": """def binary_search(arr: list[int], target: int) -> int:
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1""",
        "explanation": "Binary search halves the search space each iteration",
        "prerequisite": "Array must be sorted",
        "complexity": "O(log n) time, O(1) space",
    },
    {
        "id": "prog_003",
        "category": "Data Structures",
        "difficulty": "intermediate",
        "task": "Implement a stack using a list",
        "solution": """class Stack:
    def __init__(self):
        self.items = []
    
    def push(self, item):
        self.items.append(item)
    
    def pop(self):
        return self.items.pop() if not self.is_empty() else None
    
    def is_empty(self):
        return len(self.items) == 0""",
        "explanation": "LIFO (Last In First Out) data structure",
        "use_cases": ["Expression evaluation", "Function call stack"],
    },
]

# =============================================================================
# SCIENCE & REASONING DATASET
# =============================================================================
SCIENCE_DATASET = [
    {
        "id": "sci_001",
        "category": "Physics",
        "difficulty": "beginner",
        "concept": "Speed = Distance / Time",
        "problem": "A car travels 150 km in 3 hours. What is its speed?",
        "answer": "50 km/h",
        "calculation": "150 km ÷ 3 hours = 50 km/h",
        "units": "kilometers per hour",
    },
    {
        "id": "sci_002",
        "category": "Chemistry",
        "difficulty": "intermediate",
        "concept": "Molar mass calculation",
        "problem": "Calculate molar mass of H2O",
        "answer": "18 g/mol",
        "calculation": "H: 2 × 1 = 2, O: 1 × 16 = 16, Total: 18",
        "elements": {"H": 2, "O": 1},
    },
    {
        "id": "sci_003",
        "category": "Biology",
        "difficulty": "beginner",
        "concept": "Photosynthesis",
        "problem": "What is the main product of photosynthesis?",
        "answer": "Glucose and Oxygen",
        "equation": "6CO2 + 6H2O + light energy → C6H12O6 + 6O2",
        "process": "Light energy converts carbon dioxide and water to glucose",
    },
]

# =============================================================================
# PROBLEM-SOLVING PATTERNS
# =============================================================================
PROBLEM_SOLVING_PATTERNS = [
    {
        "id": "pattern_001",
        "pattern_name": "Divide and Conquer",
        "description": "Break problem into smaller subproblems, solve each, combine results",
        "examples": ["Merge sort", "Quick sort", "Binary search"],
        "when_to_use": "When problem can be divided into independent subproblems",
    },
    {
        "id": "pattern_002",
        "pattern_name": "Dynamic Programming",
        "description": "Store results of subproblems to avoid recomputation",
        "examples": ["Fibonacci", "Longest common subsequence", "0/1 Knapsack"],
        "when_to_use": "When problem has overlapping subproblems and optimal substructure",
    },
    {
        "id": "pattern_003",
        "pattern_name": "Greedy Approach",
        "description": "Make locally optimal choice at each step",
        "examples": ["Activity selection", "Huffman coding", "Dijkstra's algorithm"],
        "when_to_use": "When local optimization leads to global optimum",
    },
]

# =============================================================================
# COMMON MISCONCEPTIONS & CORRECTIONS
# =============================================================================
MISCONCEPTIONS_DATASET = [
    {
        "id": "misc_001",
        "misconception": "Correlation implies causation",
        "correct_understanding": "Correlation shows relationship, but causation requires temporal precedence, covariation, and no confounding variables",
        "example": "Ice cream sales correlate with drowning deaths, but both increase in summer (confounding variable)",
        "reasoning": "Critical thinking requires separating association from causation",
    },
    {
        "id": "misc_002",
        "misconception": "Absence of evidence is evidence of absence",
        "correct_understanding": "Absence of evidence is only evidence of absence if we expected to find evidence",
        "example": "Not finding something doesn't prove it doesn't exist; it depends on search thoroughness",
        "reasoning": "Logical fallacy; requires careful evaluation of evidence availability",
    },
    {
        "id": "misc_003",
        "misconception": "Larger sample size always gives better results",
        "correct_understanding": "Larger sample reduces sampling error, but biased sampling remains biased at any size",
        "example": "A poll of 100,000 people can be wrong if methodology is flawed",
        "reasoning": "Sample quality > quantity",
    },
]

# =============================================================================
# REASONING EXAMPLES & CASE STUDIES
# =============================================================================
REASONING_CASE_STUDIES = [
    {
        "id": "case_001",
        "title": "Debugging a Python Function",
        "problem": """Function returns wrong result:
        
def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)

Input: [1, 2, 3, 4, 5]
Expected: 3.0
Got: Error
""",
        "reasoning_process": [
            "1. Identify problem: Python 3 division (/) returns float automatically",
            "2. Check edge case: Empty list would cause ZeroDivisionError",
            "3. Verify logic: sum([1,2,3,4,5]) = 15, len = 5, 15/5 = 3.0",
            "4. Solution: Add guard for empty list",
        ],
        "solution": """def calculate_average(numbers):
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)""",
    },
]

def get_logic_dataset() -> list[dict]:
    """Get logic & reasoning dataset."""
    return LOGIC_REASONING_DATASET

def get_math_dataset() -> list[dict]:
    """Get mathematics dataset."""
    return MATH_REASONING_DATASET

def get_programming_dataset() -> list[dict]:
    """Get programming dataset."""
    return PROGRAMMING_DATASET

def get_science_dataset() -> list[dict]:
    """Get science dataset."""
    return SCIENCE_DATASET

def get_all_datasets() -> dict[str, list[dict]]:
    """Get all knowledge datasets.
    
    Returns:
        Dictionary with all available datasets
    """
    return {
        "logic": LOGIC_REASONING_DATASET,
        "math": MATH_REASONING_DATASET,
        "programming": PROGRAMMING_DATASET,
        "science": SCIENCE_DATASET,
        "patterns": PROBLEM_SOLVING_PATTERNS,
        "misconceptions": MISCONCEPTIONS_DATASET,
        "case_studies": REASONING_CASE_STUDIES,
    }

def get_dataset_summary() -> dict:
    """Get summary statistics of all datasets."""
    all_data = get_all_datasets()
    return {
        "total_items": sum(len(v) for v in all_data.values()),
        "categories": list(all_data.keys()),
        "counts": {k: len(v) for k, v in all_data.items()},
    }
