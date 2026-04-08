"""
DevOps & Infrastructure Expert Module
Phase 6: Extended Domain Experts

Expert in DevOps practices, CI/CD pipelines, containerization, 
infrastructure-as-code, monitoring, and deployment strategies.
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class DevOpsConcept:
    """DevOps knowledge concept."""
    name: str
    category: str
    description: str
    technologies: List[str]
    benefits: List[str]
    best_practices: List[str]


class DevOpsKnowledgeBase:
    """DevOps knowledge base with containerization, CI/CD, and infrastructure concepts."""
    
    CONCEPTS = [
        DevOpsConcept(
            name="Docker Containerization",
            category="Containerization",
            description="Package applications in isolated containers with dependencies for consistent deployment",
            technologies=["Docker Engine", "Docker Compose", "Docker Swarm"],
            benefits=[
                "Environment consistency across dev, test, production",
                "Fast startup times (seconds vs minutes for VMs)",
                "Resource efficiency (share OS kernel)",
                "Simplified dependency management",
                "Easy scaling and orchestration"
            ],
            best_practices=[
                "Use minimal base images (alpine, distroless)",
                "Layer caching optimization for build speed",
                "Run containers as non-root user",
                "Implement health checks",
                "Use environment variables for configuration",
                "Limit CPU and memory resources",
                "Keep container layers clean and organized"
            ]
        ),
        DevOpsConcept(
            name="Kubernetes Orchestration",
            category="Container Orchestration",
            description="Automate deployment, scaling, and management of containerized applications",
            technologies=["Kubernetes", "Helm", "Kustomize", "ArgoCD"],
            benefits=[
                "Automatic container scheduling and placement",
                "Self-healing (restart failed containers)",
                "Rolling updates with zero downtime",
                "Horizontal auto-scaling based on metrics",
                "Service discovery and load balancing",
                "Persistent storage management",
                "Multi-region deployment capability"
            ],
            best_practices=[
                "Use namespaces for isolation",
                "Define resource requests and limits",
                "Implement network policies for security",
                "Use ConfigMaps and Secrets for configuration",
                "Set up health probes (liveness, readiness)",
                "Use Helm for templating",
                "Implement proper logging and monitoring",
                "Use GitOps for declarative management"
            ]
        ),
        DevOpsConcept(
            name="CI/CD Pipelines",
            category="Continuous Integration & Deployment",
            description="Automate build, test, and deployment processes for rapid iteration",
            technologies=["Jenkins", "GitLab CI", "GitHub Actions", "CircleCI", "Travis CI"],
            benefits=[
                "Faster release cycles (from weeks to hours/minutes)",
                "Reduced manual errors and human overhead",
                "Early bug detection before production",
                "Consistent build and deployment process",
                "Rapid rollback capability",
                "Increased team productivity",
                "Better collaboration and visibility"
            ],
            best_practices=[
                "Implement trunk-based development",
                "Test on every commit (unit, integration, E2E)",
                "Automate security scanning (SAST, DAST)",
                "Keep pipeline fast (< 10 minutes)",
                "Parallelize test execution",
                "Use artifact repositories for versioning",
                "Implement approval gates for production",
                "Monitor pipeline performance metrics"
            ]
        ),
        DevOpsConcept(
            name="Infrastructure as Code (IaC)",
            category="Infrastructure Management",
            description="Define and manage infrastructure using code files (version control, automation)",
            technologies=["Terraform", "CloudFormation", "Ansible", "Pulumi", "Bicep"],
            benefits=[
                "Infrastructure versioning and history",
                "Reproducible deployments",
                "Error reduction through automation",
                "Faster disaster recovery",
                "Infrastructure as documentation",
                "Cost optimization through templating",
                "Team collaboration on infrastructure"
            ],
            best_practices=[
                "Use version control for all IaC files",
                "Separate prod/staging/dev configurations",
                "Implement code review for infrastructure changes",
                "Test IaC changes in isolated environments",
                "Use modules for reusability",
                "Document resource dependencies",
                "Implement enforcement policies (policy-as-code)",
                "Regular security audits of infrastructure"
            ]
        ),
        DevOpsConcept(
            name="Monitoring & Observability",
            category="Operations",
            description="Collect, aggregate, and analyze metrics, logs, and traces for system visibility",
            technologies=["Prometheus", "Grafana", "ELK Stack", "Datadog", "New Relic"],
            benefits=[
                "Early problem detection",
                "Root cause analysis capability",
                "Performance optimization insights",
                "SLA/SLO tracking",
                "Incident response automation",
                "Trending and capacity planning data",
                "Cost optimization opportunities"
            ],
            best_practices=[
                "Define clear SLIs, SLOs, and error budgets",
                "Monitor golden signals (latency, traffic, errors, saturation)",
                "Implement alert fatigue prevention",
                "Use structured logging (JSON)",
                "Correlate metrics, logs, and traces",
                "Maintain runbooks for common incidents",
                "Regular stress and chaos testing",
                "Continuous improvement culture"
            ]
        ),
        DevOpsConcept(
            name="Secrets Management",
            category="Security",
            description="Secure storage and rotation of sensitive data (passwords, API keys, certificates)",
            technologies=["HashiCorp Vault", "AWS Secrets Manager", "Azure Key Vault", "Kubernetes Secrets"],
            benefits=[
                "Prevent secrets in code repositories",
                "Centralized secrets management",
                "Automatic rotation capability",
                "Audit trail of secret access",
                "Fine-grained access control",
                "Encryption at rest and in transit",
                "Integration with CI/CD pipelines"
            ],
            best_practices=[
                "Never commit secrets to version control",
                "Use temporary credentials when possible",
                "Implement automatic rotation",
                "Audit all secret access",
                "Use RBAC for secret access",
                "Separate secrets by environment",
                "Encrypt secrets at rest",
                "Implement MFA for manual access"
            ]
        ),
        DevOpsConcept(
            name="Load Balancing & Service Mesh",
            category="Networking",
            description="Distribute traffic and manage microservice communication",
            technologies=["Nginx", "HAProxy", "Envoy", "Istio", "Linkerd"],
            benefits=[
                "High availability through redundancy",
                "Traffic distribution and routing optimization",
                "Circuit breaking and retry logic",
                "Service-to-service authentication",
                "Distributed tracing",
                "Gradual traffic shifting for deploys",
                "Centralized traffic policies"
            ],
            best_practices=[
                "Use health checks for active/passive detection",
                "Implement session persistence when needed",
                "Monitor connection pools",
                "Configure appropriate timeouts",
                "Use circuit breakers to prevent cascading failures",
                "Implement rate limiting",
                "Test failover scenarios",
                "Use gRPC for service communication when possible"
            ]
        ),
        DevOpsConcept(
            name="GitOps Deployment",
            category="Deployment Strategy",
            description="Use Git as single source of truth for infrastructure and application state",
            technologies=["ArgoCD", "Flux", "Weave GitOps"],
            benefits=[
                "Single source of truth",
                "Git audit trail for all changes",
                "Automated sync to target state",
                "Easy rollback to previous commits",
                "Pull-based (safer) vs push-based deployments",
                "Team collaboration and code review",
                "Self-documenting deployments"
            ],
            best_practices=[
                "Organize repos by environment",
                "Implement branch protection rules",
                "Require code review before merge",
                "Automated synchronization",
                "Status monitoring and alerts",
                "Test GitOps workflows regularly",
                "Implement progressive delivery (Canary, Blue-Green)",
                "Keep application and infrastructure configs together"
            ]
        )
    ]
    
    CLOUD_PLATFORMS = [
        {
            "name": "AWS",
            "services": {
                "compute": "EC2, ECS, EKS, Lambda",
                "storage": "S3, EBS, EFS, Glacier",
                "networking": "VPC, ALB, CloudFront, Route53",
                "database": "RDS, DynamoDB, Aurora, ElastiCache",
                "ci_cd": "CodePipeline, CodeBuild, CodeDeploy"
            }
        },
        {
            "name": "Google Cloud",
            "services": {
                "compute": "Compute Engine, GKE, Cloud Run, App Engine",
                "storage": "Cloud Storage, Persistent Disks, Cloud Filestore",
                "networking": "VPC, Cloud Load Balancing, Cloud CDN",
                "database": "Cloud SQL, Firestore, Bigtable, Redis",
                "ci_cd": "Cloud Build, Cloud Deploy"
            }
        },
        {
            "name": "Microsoft Azure",
            "services": {
                "compute": "VMs, ACS, AKS, Azure Functions",
                "storage": "Blob Storage, Managed Disks, Files, Queue Storage",
                "networking": "VNet, Load Balancer, Application Gateway",
                "database": "SQL Database, Cosmos DB, Database for PostgreSQL",
                "ci_cd": "Azure Pipelines, DevOps, GitHub Actions"
            }
        }
    ]
    
    KNOWLEDGE = CONCEPTS + CLOUD_PLATFORMS


class DevOpsExpert:
    """DevOps & Infrastructure Expert."""
    
    def __init__(self):
        self.kb = DevOpsKnowledgeBase()
        self.name = "DevOps & Infrastructure Expert"
        self.specialties = [
            "Containerization (Docker)",
            "Container Orchestration (Kubernetes)",
            "CI/CD Pipelines",
            "Infrastructure as Code",
            "Monitoring & Observability",
            "Cloud Platforms",
            "GitOps & Deployment"
        ]
    
    def design_deployment_pipeline(self, app_type: str, scale: str) -> Dict[str, Any]:
        """Design complete CI/CD pipeline for application."""
        pipelines = {
            "microservices-large": {
                "stages": [
                    "Source (Git webhook trigger)",
                    "Build (Docker image creation, push to registry)",
                    "Test (Unit, Integration, E2E tests in parallel)",
                    "Security scan (SAST, container scanning)",
                    "Deploy to staging (Blue-Green deployment)",
                    "Smoke tests on staging",
                    "Canary deploy to production (5% traffic)",
                    "Monitor metrics for 30 minutes",
                    "Full rollout or automatic rollback"
                ],
                "tools": "GitHub → GitHub Actions → Docker Registry → ArgoCD → Prometheus monitoring",
                "frequency": "20+ deployments per day",
                "rollback": "Automatic on metrics divergence > 5%"
            },
            "monolith-medium": {
                "stages": [
                    "Source (Git push)",
                    "Build (Compile, unit tests)",
                    "Integration tests",
                    "Security scanning",
                    "Build Docker image",
                    "Deploy to staging",
                    "Manual approval",
                    "Blue-Green deploy to production",
                    "Health checks and monitoring"
                ],
                "tools": "GitLab CI → Docker → Kubernetes → Helm",
                "frequency": "2-5 deployments per day",
                "rollback": "Manual, via Helm rollback command"
            },
            "serverless-small": {
                "stages": [
                    "Source (Git push)",
                    "Build (SAM/Serverless framework)",
                    "Test (Unit + Integration)",
                    "Deploy infrastructure (IaC)",
                    "Deploy functions",
                    "Integration tests in prod",
                    "Traffic shifting (if applicable)"
                ],
                "tools": "GitHub Actions → AWS Lambda → CloudFormation",
                "frequency": "Multiple per day",
                "rollback": "CloudFormation stack rollback"
            }
        }
        
        key = f"{app_type}-{scale}"
        return pipelines.get(key, pipelines["microservices-large"])
    
    def recommend_monitoring_stack(self, infrastructure: str) -> Dict[str, Any]:
        """Recommend monitoring solution for infrastructure type."""
        stacks = {
            "kubernetes": {
                "metrics": "Prometheus + Thanos for long-term storage",
                "visualization": "Grafana with Prometheus datasource",
                "logging": "ELK Stack or Loki for log aggregation",
                "tracing": "Jaeger or Zipkin for distributed tracing",
                "setup": [
                    "Install Prometheus Operator (kube-prometheus-stack)",
                    "Configure ServiceMonitor for app metrics",
                    "Deploy Grafana with prebuilt dashboards",
                    "Implement Alertmanager for alert routing",
                    "Integrate with PagerDuty/Slack for escalation"
                ],
                "metrics_to_track": [
                    "Pod CPU/Memory usage and limits",
                    "Container restart count",
                    "Network I/O",
                    "PVC usage",
                    "Application-specific metrics"
                ]
            },
            "vm-based": {
                "metrics": "Node Exporter (VMs) + Prometheus",
                "visualization": "Grafana dashboards",
                "logging": "Filebeat → ELK Stack",
                "tracing": "Jaeger or Datadog",
                "setup": [
                    "Deploy Prometheus server",
                    "Install Node Exporter on VMs",
                    "Configure Grafana datasource",
                    "Set alert rules",
                    "Configure log shipping"
                ],
                "metrics_to_track": [
                    "Host CPU/Memory/Disk usage",
                    "Network I/O",
                    "Process metrics",
                    "System load average",
                    "Application logs"
                ]
            },
            "serverless": {
                "metrics": "CloudWatch (AWS) / Cloud Monitoring (GCP)",
                "visualization": "Native dashboards or third-party",
                "logging": "CloudWatch Logs / Cloud Logging",
                "tracing": "X-Ray (AWS) / Cloud Trace (GCP)",
                "setup": [
                    "Enable detailed CloudWatch monitoring",
                    "Configure custom metrics",
                    "Create dashboards for key metrics",
                    "Set CloudWatch alarms",
                    "Enable X-Ray tracing"
                ],
                "metrics_to_track": [
                    "Function duration and count",
                    "Error rate and throttles",
                    "Cold start latency",
                    "Concurrent executions",
                    "Cost tracking"
                ]
            }
        }
        
        return stacks.get(infrastructure, stacks["kubernetes"])
    
    def disaster_recovery_strategy(self, rto_hours: int, rpo_hours: int) -> Dict[str, Any]:
        """Design disaster recovery strategy based on RTO/RPO requirements."""
        return {
            "rto": f"{rto_hours} hours",
            "rpo": f"{rpo_hours} hours",
            "strategy": self._select_dr_strategy(rto_hours, rpo_hours),
            "backup_approach": self._backup_strategy(rpo_hours),
            "testing_frequency": "Monthly full DR test",
            "documentation": "Runbook for each DR scenario"
        }
    
    @staticmethod
    def _select_dr_strategy(rto: int, rpo: int) -> str:
        if rto <= 1 and rpo <= 1:
            return "Active-Active multi-region with real-time sync"
        elif rto <= 4 and rpo <= 4:
            return "Active-Passive with automated failover (30min-1hr)"
        elif rto <= 24 and rpo <= 24:
            return "Regular backups with manual recovery procedures"
        else:
            return "Standard backups, restore on-demand"
    
    @staticmethod
    def _backup_strategy(rpo: int) -> str:
        if rpo <= 1:
            return "Continuous replication (databases) + hourly snapshots"
        elif rpo <= 8:
            return "Hourly snapshots + daily full backups"
        else:
            return "Daily full backups + weekly archive"
    
    def get_summary(self) -> Dict[str, Any]:
        """Get expert summary."""
        # Calculate total knowledge items from concepts and cloud platform services
        total_items = len(self.kb.CONCEPTS)
        for platform in self.kb.CLOUD_PLATFORMS:
            total_items += len(platform.get("services", {}).keys())
        total_items += len(self.kb.CLOUD_PLATFORMS)  # Count platforms themselves
        
        return {
            "expert": self.name,
            "specialties": self.specialties,
            "devops_concepts": len(self.kb.CONCEPTS),
            "cloud_platforms_covered": len(self.kb.CLOUD_PLATFORMS),
            "total_knowledge_items": total_items,
        }


if __name__ == "__main__":
    expert = DevOpsExpert()
    print(f"\n{expert.name}")
    print(f"Specialties: {', '.join(expert.specialties)}")
    
    print("\nCI/CD Pipeline Design for Microservices (Large Scale):")
    pipeline = expert.design_deployment_pipeline("microservices", "large")
    print(f"Tools: {pipeline['tools']}")
    print(f"Frequency: {pipeline['frequency']}")
    
    print("\nMonitoring Stack for Kubernetes:")
    monitoring = expert.recommend_monitoring_stack("kubernetes")
    print(f"Metrics: {monitoring['metrics']}")
    print(f"Visualization: {monitoring['visualization']}")
    
    print("\nExpert Summary:")
    summary = expert.get_summary()
    print(f"Total Knowledge Items: {summary['total_knowledge_items']}")
