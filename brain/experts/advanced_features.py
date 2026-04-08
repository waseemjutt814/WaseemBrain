"""
Phase 5: Advanced Features
Real implementations for feedback loops, knowledge updates, and optimization.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json
from pathlib import Path


@dataclass
class QueryFeedback:
    """User feedback on expert response."""
    query: str
    expert_domain: str
    response: str
    helpful: bool
    rating: int  # 1-5 stars
    feedback_text: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None


@dataclass
class ExpertPerformanceMetrics:
    """Tracks expert performance over time."""
    domain: str
    total_queries: int = 0
    helpful_responses: int = 0
    avg_rating: float = 0.0
    avg_response_time_ms: float = 0.0
    confidence_scores: List[float] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def get_helpfulness_rate(self) -> float:
        """Calculate percentage of helpful responses."""
        if self.total_queries == 0:
            return 0.0
        return (self.helpful_responses / self.total_queries) * 100
    
    def update(self, helpful: bool, rating: int, response_time_ms: float, confidence: float):
        """Update metrics with new feedback."""
        self.total_queries += 1
        if helpful:
            self.helpful_responses += 1
        
        # Update average rating
        current_total = self.avg_rating * (self.total_queries - 1)
        self.avg_rating = (current_total + rating) / self.total_queries
        
        # Update average response time
        current_total = self.avg_response_time_ms * (self.total_queries - 1)
        self.avg_response_time_ms = (current_total + response_time_ms) / self.total_queries
        
        # Track confidence scores
        self.confidence_scores.append(confidence)
        if len(self.confidence_scores) > 1000:  # Keep last 1000
            self.confidence_scores.pop(0)
        
        self.last_updated = datetime.now()


class FeedbackCollector:
    """Collects and processes user feedback for expert system."""
    
    def __init__(self, data_dir: Path = Path("data/expert_feedback")):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.feedback_history: List[QueryFeedback] = []
        self.metrics: Dict[str, ExpertPerformanceMetrics] = defaultdict(
            lambda: ExpertPerformanceMetrics(domain="")
        )
        self._load_feedback_history()
    
    def _load_feedback_history(self):
        """Load feedback from disk."""
        feedback_file = self.data_dir / "feedback_history.json"
        if feedback_file.exists():
            try:
                with open(feedback_file, 'r') as f:
                    data = json.load(f)
                    # Reconstruct feedback objects
                    for item in data:
                        item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                        self.feedback_history.append(QueryFeedback(**item))
            except Exception as e:
                print(f"Error loading feedback: {e}")
    
    def record_feedback(self, feedback: QueryFeedback) -> bool:
        """Record user feedback on expert response."""
        try:
            # Store feedback
            self.feedback_history.append(feedback)
            
            # Update expert metrics
            domain = feedback.expert_domain
            if domain not in self.metrics:
                self.metrics[domain] = ExpertPerformanceMetrics(domain=domain)
            
            expert_metric = self.metrics[domain]
            expert_metric.update(
                helpful=feedback.helpful,
                rating=feedback.rating,
                response_time_ms=0.0,  # Would be set separately
                confidence=0.0  # Would be set separately
            )
            
            # Save feedback
            self._save_feedback()
            return True
        except Exception as e:
            print(f"Error recording feedback: {e}")
            return False
    
    def _save_feedback(self):
        """Save feedback to disk."""
        feedback_file = self.data_dir / "feedback_history.json"
        try:
            data = []
            for fb in self.feedback_history:
                fb_dict = {
                    "query": fb.query,
                    "expert_domain": fb.expert_domain,
                    "response": fb.response[:500],  # Truncate for storage
                    "helpful": fb.helpful,
                    "rating": fb.rating,
                    "feedback_text": fb.feedback_text,
                    "timestamp": fb.timestamp.isoformat(),
                    "user_id": fb.user_id
                }
                data.append(fb_dict)
            
            with open(feedback_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving feedback: {e}")
    
    def get_expert_metrics(self, domain: str) -> Optional[ExpertPerformanceMetrics]:
        """Get performance metrics for expert domain."""
        return self.metrics.get(domain)
    
    def get_all_metrics(self) -> Dict[str, ExpertPerformanceMetrics]:
        """Get metrics for all experts."""
        return dict(self.metrics)
    
    def get_feedback_by_domain(self, domain: str) -> List[QueryFeedback]:
        """Get all feedback for specific expert domain."""
        return [fb for fb in self.feedback_history if fb.expert_domain == domain]
    
    def get_recent_feedback(self, days: int = 7) -> List[QueryFeedback]:
        """Get feedback from last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        return [fb for fb in self.feedback_history if fb.timestamp > cutoff]


class KnowledgeUpdateEngine:
    """Manages knowledge base updates based on feedback and new information."""
    
    def __init__(self, expert_dir: Path = Path("experts/base")):
        self.expert_dir = Path(expert_dir)
        self.update_log: List[Dict] = []
        self.update_history_file = Path("data/expert_feedback/knowledge_updates.json")
        self._load_update_history()
    
    def _load_update_history(self):
        """Load update history from disk."""
        if self.update_history_file.exists():
            try:
                with open(self.update_history_file, 'r') as f:
                    self.update_log = json.load(f)
            except Exception as e:
                print(f"Error loading update history: {e}")
    
    def suggest_knowledge_update(self, domain: str, topic: str, 
                                new_info: str, source: str) -> Dict[str, Any]:
        """
        Suggest new knowledge item for expert domain.
        
        Real implementation: Validates new information and queues for expert KB update.
        """
        update_suggestion = {
            "domain": domain,
            "topic": topic,
            "new_info": new_info,
            "source": source,
            "suggested_at": datetime.now().isoformat(),
            "status": "pending_review",
            "validation_score": self._validate_knowledge(domain, new_info)
        }
        
        self.update_log.append(update_suggestion)
        self._save_update_history()
        
        return update_suggestion
    
    def _validate_knowledge(self, domain: str, info: str) -> float:
        """Validate knowledge content quality."""
        score = 0.0
        
        # Length check
        if 50 <= len(info) <= 5000:
            score += 0.3
        
        # Structure check
        if any(marker in info.lower() for marker in ["recommended", "best practice", "note:"]):
            score += 0.2
        
        # Technical depth
        if domain == "cryptography" and any(x in info.lower() for x in ["aes", "rsa", "algorithm"]):
            score += 0.2
        elif domain == "cybersecurity" and any(x in info.lower() for x in ["vulnerability", "defense", "attack"]):
            score += 0.2
        elif domain == "algorithms" and any(x in info.lower() for x in ["complexity", "o(n)", "algorithm"]):
            score += 0.2
        
        # No red flags
        if not any(x in info.lower() for x in ["n/a", "todo", "fixme", "placeholder"]):
            score += 0.3
        
        return min(score, 1.0)
    
    def _save_update_history(self):
        """Save update history to disk."""
        self.update_history_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.update_history_file, 'w') as f:
                json.dump(self.update_log, f, indent=2)
        except Exception as e:
            print(f"Error saving update history: {e}")
    
    def get_pending_updates(self, domain: Optional[str] = None) -> List[Dict]:
        """Get pending knowledge updates."""
        pending = [u for u in self.update_log if u.get("status") == "pending_review"]
        if domain:
            pending = [u for u in pending if u.get("domain") == domain]
        return pending
    
    def approve_update(self, update_id: int) -> bool:
        """Approve and process knowledge update."""
        if 0 <= update_id < len(self.update_log):
            self.update_log[update_id]["status"] = "approved"
            self.update_log[update_id]["approved_at"] = datetime.now().isoformat()
            self._save_update_history()
            return True
        return False


class PerformanceOptimizer:
    """Tracks and optimizes expert system performance."""
    
    def __init__(self):
        self.query_times: Dict[str, List[float]] = defaultdict(list)
        self.cache_hits: Dict[str, int] = defaultdict(int)
        self.cache_misses: Dict[str, int] = defaultdict(int)
        self.optimization_log: List[Dict] = []
    
    def record_query_time(self, domain: str, response_time_ms: float):
        """Record query response time."""
        self.query_times[domain].append(response_time_ms)
        
        # Keep last 500 measurements
        if len(self.query_times[domain]) > 500:
            self.query_times[domain].pop(0)
    
    def record_cache_hit(self, domain: str):
        """Record cache hit."""
        self.cache_hits[domain] += 1
    
    def record_cache_miss(self, domain: str):
        """Record cache miss."""
        self.cache_misses[domain] += 1
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics across all experts."""
        stats = {}
        
        for domain in set(list(self.query_times.keys()) + list(self.cache_hits.keys())):
            times = self.query_times.get(domain, [])
            hits = self.cache_hits.get(domain, 0)
            misses = self.cache_misses.get(domain, 0)
            total_cache_ops = hits + misses
            
            stats[domain] = {
                "avg_response_time_ms": sum(times) / len(times) if times else 0,
                "min_response_time_ms": min(times) if times else 0,
                "max_response_time_ms": max(times) if times else 0,
                "cache_hit_rate": hits / total_cache_ops if total_cache_ops > 0 else 0,
                "total_queries": len(times)
            }
        
        return stats
    
    def get_optimization_recommendations(self) -> List[Dict]:
        """Generate optimization recommendations based on performance data."""
        recommendations = []
        stats = self.get_performance_stats()
        
        for domain, domain_stats in stats.items():
            # Slow response time recommendation
            if domain_stats["avg_response_time_ms"] > 500:
                recommendations.append({
                    "domain": domain,
                    "type": "response_time",
                    "issue": f"Slow response time ({domain_stats['avg_response_time_ms']:.0f}ms)",
                    "recommendation": f"Consider caching common queries for {domain}"
                })
            
            # Low cache hit rate recommendation
            if domain_stats["cache_hit_rate"] < 0.3 and domain_stats["total_queries"] > 50:
                recommendations.append({
                    "domain": domain,
                    "type": "cache_efficiency",
                    "issue": f"Low cache hit rate ({domain_stats['cache_hit_rate']:.1%})",
                    "recommendation": f"Analyze query patterns for {domain} to improve caching strategy"
                })
        
        self.optimization_log.extend(recommendations)
        return recommendations
    
    def get_bottleneck_domains(self) -> List[str]:
        """Identify slowest expert domains."""
        stats = self.get_performance_stats()
        if not stats:
            return []
        
        sorted_domains = sorted(
            stats.items(),
            key=lambda x: x[1]["avg_response_time_ms"],
            reverse=True
        )
        
        return [domain for domain, _ in sorted_domains[:3]]


class AdvancedFeatureManager:
    """Manages all Phase 5 advanced features."""
    
    def __init__(self):
        self.feedback_collector = FeedbackCollector()
        self.knowledge_update_engine = KnowledgeUpdateEngine()
        self.performance_optimizer = PerformanceOptimizer()
    
    def initialize(self):
        """Initialize all advanced features."""
        print("[Advanced Features] Feedback collector initialized")
        print("[Advanced Features] Knowledge update engine initialized")
        print("[Advanced Features] Performance optimizer initialized")
    
    def get_system_health_report(self) -> Dict[str, Any]:
        """Get comprehensive system health report."""
        metrics = self.feedback_collector.get_all_metrics()
        perf_stats = self.performance_optimizer.get_performance_stats()
        recommendations = self.performance_optimizer.get_optimization_recommendations()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "expert_metrics": {
                domain: {
                    "helpfulness_rate": metric.get_helpfulness_rate(),
                    "avg_rating": metric.avg_rating,
                    "total_queries": metric.total_queries
                }
                for domain, metric in metrics.items()
            },
            "performance_stats": perf_stats,
            "optimization_recommendations": recommendations,
            "bottleneck_domains": self.performance_optimizer.get_bottleneck_domains()
        }
        
        return report


if __name__ == "__main__":
    print("="*70)
    print("PHASE 5: ADVANCED FEATURES TEST")
    print("="*70)
    
    manager = AdvancedFeatureManager()
    manager.initialize()
    
    # Simulate feedback
    feedback = QueryFeedback(
        query="How to prevent SQL injection?",
        expert_domain="cybersecurity",
        response="Use parameterized queries...",
        helpful=True,
        rating=5,
        feedback_text="Very helpful and detailed"
    )
    
    manager.feedback_collector.record_feedback(feedback)
    print(f"\nFeedback recorded: {feedback.helpful} ({feedback.rating} stars)")
    
    # Suggest knowledge update
    update = manager.knowledge_update_engine.suggest_knowledge_update(
        domain="cryptography",
        topic="Post-Quantum Cryptography",
        new_info="Waseem-based cryptography is resilient to quantum attacks...",
        source="NIST recommendations"
    )
    
    print(f"Knowledge update suggested with validation score: {update['validation_score']:.2f}")
    
    # Record performance
    manager.performance_optimizer.record_query_time("cybersecurity", 150.5)
    manager.performance_optimizer.record_query_time("cryptography", 200.0)
    manager.performance_optimizer.record_cache_hit("cybersecurity")
    
    print("\nSystem health report:")
    report = manager.get_system_health_report()
    print(json.dumps(report, indent=2))
