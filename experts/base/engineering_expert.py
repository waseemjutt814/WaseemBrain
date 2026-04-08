"""System Engineering & Architecture Expert Module.

Provides comprehensive knowledge on system design, distributed systems,
microservices, scalability, and architectural patterns.
"""

from dataclasses import dataclass
from types import SimpleNamespace


@dataclass
class ArchitecturePattern:
    """Architecture design pattern."""
    name: str
    description: str
    benefits: list[str]
    tradeoffs: list[str]
    use_cases: list[str]
    implementation_examples: list[str]


class SystemArchitectureKnowledgeBase:
    """Comprehensive system engineering knowledge base."""
    
    ARCHITECTURE_PATTERNS = [
        ArchitecturePattern(
            name="Monolithic Architecture",
            description="Single unified codebase, one deployment unit",
            benefits=[
                "Simple to build initially",
                "Easy to test end-to-end",
                "Simple deployment",
                "Good for small teams",
            ],
            tradeoffs=[
                "Hard to scale individual components",
                "Technology lock-in",
                "Any change requires full deployment",
                "Single point of failure",
            ],
            use_cases=["Small applications", "MVP stage", "Simple CRUD apps"],
            implementation_examples=["Traditional MVC web app", "Single database backend"],
        ),
        ArchitecturePattern(
            name="Microservices Architecture",
            description="Small, independent, deployable services",
            benefits=[
                "Independent scaling",
                "Technology flexibility",
                "Independent deployment",
                "Fault isolation",
            ],
            tradeoffs=[
                "Distributed system complexity",
                "Network latency",
                "Eventual consistency challenges",
                "Operational complexity",
            ],
            use_cases=["Large applications", "Service teams", "Scaling platforms"],
            implementation_examples=["Netflix", "Uber", "Twitter"],
        ),
        ArchitecturePattern(
            name="Serverless Architecture",
            description="Event-driven computation without server management",
            benefits=[
                "No server management",
                "Auto-scaling",
                "Pay per use",
                "Faster deployment",
            ],
            tradeoffs=[
                "Vendor lock-in",
                "Cold start latency",
                "Limited execution time",
                "Monitoring complexity",
            ],
            use_cases=["APIs", "Data processing", "Scheduled tasks"],
            implementation_examples=["AWS Lambda", "Google Cloud Functions", "Azure Functions"],
        ),
    ]
    
    DESIGN_PRINCIPLES = [
        {
            "principle": "Single Responsibility",
            "description": "Each component has one reason to change",
            "benefit": "Easier to maintain and test",
            "example": "User service handles user management only",
        },
        {
            "principle": "Open/Closed",
            "description": "Open for extension, closed for modification",
            "benefit": "Add features without changing existing code",
            "example": "Strategy pattern for payment processing",
        },
        {
            "principle": "Dependency Inversion",
            "description": "Depend on abstractions, not concrete implementations",
            "benefit": "Loose coupling, easier testing",
            "example": "Inject database interface, not concrete DB",
        },
        {
            "principle": "DRY (Don't Repeat Yourself)",
            "description": "Single source of truth",
            "benefit": "Easier changes and maintenance",
            "example": "Extract common logic into utilities",
        },
    ]
    
    SCALABILITY_PATTERNS = [
        {
            "pattern": "Horizontal Scaling",
            "description": "Add more servers",
            "best_for": "Stateless services",
            "considerations": ["Load balancing", "Session management"],
            "technologies": ["Load balancers", "Container orchestration"],
        },
        {
            "pattern": "Vertical Scaling",
            "description": "Make server more powerful",
            "best_for": "Stateful components",
            "considerations": ["Single point of failure", "Cost"],
            "limitations": ["Hardware limits", "More expensive"],
        },
        {
            "pattern": "Database Sharding",
            "description": "Distribute data across multiple databases",
            "best_for": "Large datasets",
            "considerations": ["Consistency", "Shard key selection"],
            "trade_off": "Increased complexity",
        },
        {
            "pattern": "Caching",
            "description": "Store frequently accessed data in memory",
            "best_for": "Read-heavy workloads",
            "technologies": ["Redis", "Memcached"],
            "challenge": "Cache invalidation",
        },
    ]
    
    DISTRIBUTED_SYSTEM_CONCERNS = [
        {
            "concern": "Consistency",
            "options": [
                "Strong consistency (ACID)",
                "Eventual consistency (BASE)",
            ],
            "tradeoff": "Consistency vs Availability/Latency",
            "example": "CAP Theorem",
        },
        {
            "concern": "Reliability",
            "strategies": [
                "Redundancy",
                "Failover mechanisms",
                "Circuit breakers",
                "Retry logic",
            ],
            "goal": "System resilience",
        },
        {
            "concern": "Performance",
            "metrics": [
                "Latency (response time)",
                "Throughput (requests/sec)",
                "Bandwidth",
            ],
            "optimization": "Caching, CDN, parallel processing",
        },
    ]
    
    DATABASE_DESIGN_PATTERNS = [
        {
            "pattern": "Normalization",
            "description": "Reduce data redundancy",
            "use_case": "ACID databases",
            "pros": ["Consistency", "Storage efficiency"],
            "cons": ["More joins", "More complex queries"],
        },
        {
            "pattern": "Denormalization",
            "description": "Intentional data redundancy",
            "use_case": "NoSQL databases, read-heavy systems",
            "pros": ["Faster reads", "Simpler queries"],
            "cons": ["Update complexity", "Storage overhead"],
        },
        {
            "pattern": "Event Sourcing",
            "description": "Store system state as sequence of events",
            "use_case": "Audit trails, temporal queries",
            "pros": ["Complete history", "Debugging capability"],
            "cons": ["Event versioning", "State reconstruction"],
        },
    ]
    
    DEPLOYMENT_PATTERNS = [
        {
            "pattern": "Blue-Green Deployment",
            "description": "Run two identical environments, switch between",
            "zero_downtime": True,
            "rollback_capability": "Instant",
            "infrastructure_overhead": "2x",
        },
        {
            "pattern": "Canary Deployment",
            "description": "Gradual rollout to subset of users",
            "zero_downtime": True,
            "rollback_capability": "Quick",
            "risk_mitigation": "High",
        },
        {
            "pattern": "Rolling Deployment",
            "description": "Gradually replace old instances",
            "zero_downtime": True,
            "complexity": "Medium",
            "infrastructure_overhead": "Minimal",
        },
    ]
    
    API_DESIGN_PRINCIPLES = [
        {
            "principle": "RESTful Design",
            "core_concepts": [
                "Resources represented by URLs",
                "HTTP methods for operations",
                "Stateless communication",
            ],
            "benefits": ["Simple", "Widely understood"],
            "suitable_for": "CRUD operations",
        },
        {
            "principle": "GraphQL",
            "core_concepts": [
                "Query language for APIs",
                "Precise data fetching",
                "Single endpoint",
            ],
            "benefits": ["No over-fetching", "No under-fetching"],
            "suitable_for": "Complex queries",
        },
        {
            "principle": "API Versioning",
            "strategies": [
                "URL path: /v1/, /v2/",
                "Header: Accept: application/vnd.api+json;version=2",
                "Query: ?api_version=2",
            ],
            "best_practice": "Support multiple versions",
        },
    ]
    
    MONITORING_AND_OBSERVABILITY = [
        {
            "aspect": "Logging",
            "best_practices": [
                "Structured logging (JSON format)",
                "Correlation IDs for tracing",
                "Appropriate log levels",
                "Centralized log aggregation",
            ],
            "tools": ["ELK Stack", "Splunk", "CloudWatch"],
        },
        {
            "aspect": "Metrics",
            "key_metrics": [
                "Request latency (p50, p95, p99)",
                "Error rate",
                "Throughput",
                "Resource usage (CPU, memory)",
            ],
            "tools": ["Prometheus", "Grafana", "Datadog"],
        },
        {
            "aspect": "Tracing",
            "purpose": "Understand request flow in distributed systems",
            "tools": ["Jaeger", "Zipkin", "X-Ray"],
        },
    ]


class SystemEngineeringExpert:
    """Expert module for system design and engineering."""

    def __init__(self):
        self.kb = SystemArchitectureKnowledgeBase()
        self.knowledge_base = SimpleNamespace(
            architecture_patterns=list(self.kb.ARCHITECTURE_PATTERNS),
            database_patterns=list(self.kb.DATABASE_DESIGN_PATTERNS),
            scalability_patterns=list(self.kb.SCALABILITY_PATTERNS),
        )
        self.name = "System Engineering & Architecture Expert"
        self.specialties = [
            "System Design",
            "Distributed Systems",
            "Microservices Architecture",
            "Database Design",
            "Scalability",
            "DevOps & Deployment",
        ]

    def recommend_architecture_details(self, requirement: str) -> dict[str, object]:
        normalized = requirement.lower().replace('-', '_').replace(' ', '_')
        recommendations = {
            'startup': {
                'recommended': 'Monolithic Architecture',
                'reason': 'Fast to MVP with lower operational overhead.',
            },
            'scale': {
                'recommended': 'Microservices Architecture',
                'reason': 'Independent scaling and fault isolation for growing systems.',
            },
            'realtime': {
                'recommended': 'Event-driven microservices',
                'reason': 'Reactive patterns fit low-latency and streaming workloads.',
            },
        }
        return recommendations.get(normalized, {'error': f'Unknown requirement: {requirement}'})

    def recommend_architecture(self, requirement: str, scale_hint: int | None = None) -> str:
        details = self.recommend_architecture_details(requirement)
        if 'error' in details:
            return f"Unknown architecture requirement: {requirement}."
        scale_text = f" for about {scale_hint} tenants/requests" if scale_hint is not None else ''
        return f"Recommended architecture{scale_text}: {details['recommended']}. {details['reason']}"

    def design_database(self, use_case: str, consistency: str | None = None) -> str:
        normalized = use_case.lower().replace('-', '_').replace(' ', '_')
        mapping = {
            'transactional': ('SQL database such as PostgreSQL', 'Normalization and ACID guarantees fit transactional consistency requirements.'),
            'relational_data': ('SQL database such as PostgreSQL', 'Normalization and rich querying fit structured relational data.'),
            'high_volume': ('NoSQL database such as DynamoDB or MongoDB', 'Horizontal scale and denormalized reads help with very high throughput.'),
            'graph_data': ('Graph database such as Neo4j', 'Graph traversal is the dominant access pattern.'),
        }
        recommendation = mapping.get(normalized)
        if recommendation is None:
            return f"Unknown database use case: {use_case}."
        consistency_text = f" Consistency target: {consistency}." if consistency else ''
        return f"Recommended database design: {recommendation[0]}. {recommendation[1]}{consistency_text}"

    def scaling_strategy(self, bottleneck: str) -> str:
        normalized = bottleneck.lower().replace('-', '_').replace(' ', '_')
        if normalized == 'horizontal':
            return 'Horizontal scaling is the default strategy for stateless services: add more instances behind a load balancer and keep session state externalized.'
        if normalized == 'vertical':
            return 'Vertical scaling buys time for stateful workloads, but it should be treated as a short-term scaling step because hardware ceilings remain.'
        if normalized == 'database':
            return 'Database scaling usually starts with caching and read replicas, then moves to partitioning or sharding when write pressure demands it.'
        if normalized == 'api':
            return 'API scaling should combine horizontal scaling, load balancing, and aggressive caching for hot paths.'
        return f"Scaling strategy for {bottleneck}: measure the bottleneck first, then choose the least complex scaling path that removes it."

    def get_summary(self) -> str:
        return f"System Engineering Expert covering {len(self.knowledge_base.architecture_patterns)} architecture patterns and {len(self.knowledge_base.database_patterns)} database design patterns."

    def answer_query(self, query: str) -> str:
        lowered = query.lower()
        if 'database' in lowered:
            return self.design_database('transactional')
        if 'scale' in lowered or 'scaling' in lowered:
            return self.scaling_strategy('horizontal')
        if 'microservice' in lowered or 'architecture' in lowered:
            return self.recommend_architecture('scale')
        return self.get_summary()
