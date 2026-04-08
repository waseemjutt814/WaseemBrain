"""
Machine Learning & AI Expert Module
Phase 6: Extended Domain Experts

Expert in machine learning algorithms, neural networks, deep learning,
model optimization, and AI system design.
"""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class MLConcept:
    """ML/AI knowledge concept."""
    name: str
    category: str
    description: str
    use_cases: List[str]
    best_practices: List[str]
    performance_metrics: Dict[str, str]


class MLKnowledgeBase:
    """Machine Learning knowledge base with comprehensive algorithms and techniques."""
    
    ALGORITHMS = [
        MLConcept(
            name="Neural Networks",
            category="Deep Learning",
            description="Artificial neural networks inspired by biological neurons, composed of interconnected layers",
            use_cases=["Image classification", "NLP", "Time series prediction", "Pattern recognition"],
            best_practices=[
                "Normalize input data to [0,1] or [-1,1]",
                "Use batch normalization between layers",
                "Implement dropout for regularization",
                "Monitor training with validation curves",
                "Use appropriate activation functions (ReLU, Sigmoid, Tanh)"
            ],
            performance_metrics={
                "accuracy": "85-99% on benchmark datasets",
                "training_time": "Hours to days depending on data size",
                "inference_latency": "10-100ms per sample"
            }
        ),
        MLConcept(
            name="Random Forest",
            category="Ensemble Learning",
            description="Ensemble of decision trees trained on random data subsets, combines predictions",
            use_cases=["Classification", "Regression", "Feature importance", "Outlier detection"],
            best_practices=[
                "Use 100-200 trees typically",
                "Tune max_depth to prevent overfitting",
                "Balance class weights for imbalanced data",
                "Use out-of-bag (OOB) error for validation",
                "Parallelize training across cores"
            ],
            performance_metrics={
                "accuracy": "90-95% typical",
                "training_time": "Seconds to minutes",
                "inference_latency": "1-5ms per sample"
            }
        ),
        MLConcept(
            name="Gradient Boosting",
            category="Ensemble Learning",
            description="Sequential ensemble method where each base learner corrects errors of previous ones",
            use_cases=["Kaggle competitions", "Credit scoring", "Fraud detection", "Risk modeling"],
            best_practices=[
                "Start with learning_rate=0.1",
                "Use early stopping with validation set",
                "Monitor variable importance",
                "Handle missing values appropriately",
                "Tune subsample and max_depth"
            ],
            performance_metrics={
                "accuracy": "92-98% on structured data",
                "training_time": "Minutes to hours",
                "inference_latency": "5-20ms per sample"
            }
        ),
        MLConcept(
            name="Support Vector Machines (SVM)",
            category="Supervised Learning",
            description="Finds optimal hyperplane to maximize margin between classes in feature space",
            use_cases=["Binary classification", "Multiclass classification", "Regression"],
            best_practices=[
                "Scale features to [-1,1]",
                "Use RBF kernel for non-linear data",
                "Tune C (regularization) and gamma",
                "Use class weights for imbalanced data",
                "Consider kernel approximation for large datasets"
            ],
            performance_metrics={
                "accuracy": "85-95%",
                "training_time": "Seconds to minutes",
                "inference_latency": "0.1-1ms per sample"
            }
        ),
        MLConcept(
            name="K-Means Clustering",
            category="Unsupervised Learning",
            description="Partitions data into K clusters by minimizing within-cluster variance",
            use_cases=["Customer segmentation", "Document clustering", "Data preprocessing"],
            best_practices=[
                "Standardize features before clustering",
                "Use elbow method to find optimal K",
                "Run multiple times with different initializations",
                "Use k-means++ initialization",
                "Monitor inertia and silhouette score"
            ],
            performance_metrics={
                "convergence": "10-50 iterations typical",
                "complexity": "O(n*k*i*d) where i=iterations",
                "silhouette_score": "0.5-0.8 for good clustering"
            }
        ),
        MLConcept(
            name="Convolutional Neural Networks (CNN)",
            category="Deep Learning",
            description="Neural networks with convolutional layers for spatial feature extraction",
            use_cases=["Image classification", "Object detection", "Image segmentation", "Video analysis"],
            best_practices=[
                "Use pre-trained models (ResNet, VGG, Inception)",
                "Apply data augmentation (rotation, flip, zoom)",
                "Use ReLU activations in conv layers",
                "Implement pooling for dimensionality reduction",
                "Fine-tune pre-trained models for domain-specific tasks"
            ],
            performance_metrics={
                "accuracy": "95%+ on ImageNet",
                "parameters": "Millions (ResNet50: 25M)",
                "training_time": "Days on GPU"
            }
        ),
        MLConcept(
            name="Recurrent Neural Networks (RNN/LSTM)",
            category="Deep Learning",
            description="Neural networks designed for sequential data with temporal dependencies",
            use_cases=["NLP", "Time series prediction", "Speech recognition", "Machine translation"],
            best_practices=[
                "Use LSTM/GRU cells to avoid vanishing gradients",
                "Apply gradient clipping",
                "Use teacher forcing during training",
                "Sequence length should be 20-100 typically",
                "Consider attention mechanisms for long sequences"
            ],
            performance_metrics={
                "perplexity": "20-100 on text tasks",
                "BLEU score": "20-40 on translation",
                "training_time": "Hours to days"
            }
        ),
        MLConcept(
            name="Transformer Networks",
            category="Deep Learning",
            description="Self-attention based architecture for parallel processing of sequences",
            use_cases=["NLP (BERT, GPT)", "Speech processing", "Multi-modal learning", "Time series"],
            best_practices=[
                "Use multi-head attention (8-16 heads)",
                "Apply layer normalization",
                "Use position encodings for sequence order",
                "Implement causal attention for autoregressive models",
                "Scale exponentially with data"
            ],
            performance_metrics={
                "perplexity": "10-50 on language modeling",
                "accuracy": "85-95% on NLU tasks",
                "parameters": "Millions to billions (GPT-3: 175B)"
            }
        )
    ]
    
    OPTIMIZATION_TECHNIQUES = [
        {"name": "Adam", "desc": "Adaptive moment estimation, combines momentum and RMSprop", "lr_range": "0.0001-0.01"},
        {"name": "SGD", "desc": "Stochastic gradient descent with momentum", "lr_range": "0.01-0.1"},
        {"name": "RMSprop", "desc": "Root mean square propagation, adaptive learning rates", "lr_range": "0.0001-0.01"},
        {"name": "AdaGrad", "desc": "Adapts learning rate per parameter", "lr_range": "0.01-1.0"}
    ]
    
    REGULARIZATION_TECHNIQUES = [
        {"name": "L1 Regularization", "desc": "Add sum of absolute weights to loss (produces sparse weights)"},
        {"name": "L2 Regularization", "desc": "Add sum of squared weights to loss (prevents large weights)"},
        {"name": "Dropout", "desc": "Randomly deactivate neurons during training to reduce co-adaptation"},
        {"name": "Early Stopping", "desc": "Stop training when validation performance plateaus"},
        {"name": "Data Augmentation", "desc": "Create variations of training data to improve generalization"},
        {"name": "Batch Normalization", "desc": "Normalize layer inputs to stabilize training"},
    ]
    
    EVALUATION_METRICS = [
        {"name": "Accuracy", "formula": "(TP+TN)/(TP+TN+FP+FN)", "use_case": "Balanced classification"},
        {"name": "Precision", "formula": "TP/(TP+FP)", "use_case": "Minimize false positives"},
        {"name": "Recall", "formula": "TP/(TP+FN)", "use_case": "Minimize false negatives"},
        {"name": "F1-Score", "formula": "2*(Precision*Recall)/(Precision+Recall)", "use_case": "Balanced metric"},
        {"name": "AUC-ROC", "formula": "Area under receiver operating characteristic curve", "use_case": "Threshold-independent evaluation"},
        {"name": "Mean Squared Error", "formula": "Average of squared differences", "use_case": "Regression tasks"},
    ]
    
    KNOWLEDGE = ALGORITHMS + OPTIMIZATION_TECHNIQUES + REGULARIZATION_TECHNIQUES + EVALUATION_METRICS


class MLExpert:
    """Machine Learning & AI Expert."""
    
    def __init__(self):
        self.kb = MLKnowledgeBase()
        self.name = "Machine Learning & AI Expert"
        self.specialties = [
            "Deep Learning",
            "Supervised Learning",
            "Unsupervised Learning",
            "Reinforcement Learning",
            "Model Optimization",
            "Neural Architecture Design",
        ]
    
    def recommend_algorithm(self, problem_type: str) -> Dict[str, Any]:
        """Recommend ML algorithm for specific problem type."""
        recommendations = {
            "image-classification": {
                "primary": "Convolutional Neural Networks (CNN)",
                "alternatives": ["VGG-19", "ResNet-50", "EfficientNet"],
                "reasoning": "CNNs excel at spatial feature extraction in images",
                "setup": "Use pre-trained models, apply transfer learning for faster convergence"
            },
            "nlp": {
                "primary": "Transformer Networks (BERT/GPT)",
                "alternatives": ["RNN with attention", "LSTM", "GRU"],
                "reasoning": "Transformers handle long-range dependencies efficiently",
                "setup": "Fine-tune pre-trained models on domain-specific data"
            },
            "time-series": {
                "primary": "LSTM/GRU Networks",
                "alternatives": ["Transformer", "ARIMA", "Prophet"],
                "reasoning": "RNNs capture temporal patterns naturally",
                "setup": "Normalize data, use sequence-to-sequence architecture for forecasting"
            },
            "classification": {
                "primary": "Gradient Boosting (XGBoost/LightGBM)",
                "alternatives": ["Random Forest", "SVM", "Neural Network"],
                "reasoning": "Excellent for tabular/structured data",
                "setup": "Handle categorical features, tune hyperparameters"
            },
            "clustering": {
                "primary": "K-Means or DBSCAN",
                "alternatives": ["Hierarchical Clustering", "GMM", "Spectral Clustering"],
                "reasoning": "K-Means is scalable, DBSCAN finds arbitrary shapes",
                "setup": "Standardize features, use silhouette score for validation"
            }
        }
        
        return recommendations.get(problem_type, {
            "primary": "Start with simpler models (Linear/Logistic Regression)",
            "alternatives": ["Decision Tree", "Random Forest"],
            "reasoning": "Baseline models help understand data before complex methods"
        })
    
    def model_optimization_strategy(self, model_type: str, dataset_size: int) -> Dict[str, Any]:
        """Get optimization strategy for specific model."""
        strategy = {
            "hyperparameters": [],
            "training_techniques": [],
            "hardware_recommendations": None,
            "estimated_time": None
        }
        
        if "neural" in model_type.lower():
            strategy["hyperparameters"] = [
                "Learning rate: 0.001-0.01",
                "Batch size: 32-256",
                "Epochs: 50-500",
                "Dropout rate: 0.2-0.5"
            ]
            strategy["training_techniques"] = [
                "Use Adam optimizer",
                "Implement early stopping",
                "Apply batch normalization",
                "Use learning rate scheduling"
            ]
            strategy["hardware_recommendations"] = "GPU (NVIDIA A100 recommended)" if dataset_size > 1000000 else "GPU (RTX 3090) suitable"
            strategy["estimated_time"] = "Hours to days" if dataset_size > 1000000 else "30 minutes to 2 hours"
        
        elif "tree" in model_type.lower():
            strategy["hyperparameters"] = [
                "Max depth: 5-20",
                "Min samples split: 2-10",
                "Number of estimators: 100-1000",
                "Learning rate: 0.01-0.1"
            ]
            strategy["training_techniques"] = [
                "Use early stopping",
                "Monitor out-of-bag error",
                "Balance class weights",
                "Feature importance analysis"
            ]
            strategy["hardware_recommendations"] = "CPU with multi-core (8+ cores)"
            strategy["estimated_time"] = "Minutes to hours"
        
        return strategy
    
    def handle_class_imbalance(self, imbalance_ratio: float) -> Dict[str, str]:
        """Get strategies for handling class imbalance."""
        strategies = {
            "oversampling": "Duplicate minority samples (SMOTE recommended over random)",
            "undersampling": "Remove majority samples (may lose information)",
            "class_weights": "Use inverse frequency weighting in loss function",
            "threshold_tuning": "Adjust classification threshold based on precision-recall tradeoff",
            "ensemble": "Combine multiple models trained on different samples",
            "cost_sensitive": "Assign higher misclassification cost to minority class"
        }
        
        if imbalance_ratio < 1.5:
            return {"recommendation": "Class weights", "rationale": "Mild imbalance, simple weighting sufficient"}
        elif imbalance_ratio < 5:
            return {"recommendation": "SMOTE + Class Weights", "rationale": "Moderate imbalance, combine techniques"}
        else:
            return {"recommendation": "SMOTE + Ensemble", "rationale": "Severe imbalance, need combination of techniques"}
    
    def get_data_requirements(self, algorithm: str) -> Dict[str, Any]:
        """Get data requirements for specific algorithm."""
        requirements = {
            "neural-network": {
                "min_samples": 1000,
                "preferred": "50000+",
                "features": "100-10000",
                "preprocessing": "Normalization required",
                "missing_values": "Must be handled beforehand"
            },
            "random-forest": {
                "min_samples": 100,
                "preferred": "10000+",
                "features": "10-1000",
                "preprocessing": "Minimal required",
                "missing_values": "Can handle some"
            },
            "svm": {
                "min_samples": 50,
                "preferred": "1000-10000",
                "features": "10-1000",
                "preprocessing": "Scaling required",
                "missing_values": "Must be handled"
            },
            "logistic-regression": {
                "min_samples": 20,
                "preferred": "500+",
                "features": "5-100",
                "preprocessing": "Scaling recommended",
                "missing_values": "Must be handled"
            }
        }
        
        return requirements.get(algorithm, {
            "min_samples": "At least 50",
            "note": "More data generally improves performance"
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get expert summary."""
        return {
            "expert": self.name,
            "specialties": self.specialties,
            "algorithms_covered": len(self.kb.ALGORITHMS),
            "optimization_techniques": len(self.kb.OPTIMIZATION_TECHNIQUES),
            "regularization_methods": len(self.kb.REGULARIZATION_TECHNIQUES),
            "evaluation_metrics": len(self.kb.EVALUATION_METRICS),
            "total_knowledge_items": len(self.kb.KNOWLEDGE),
        }


if __name__ == "__main__":
    expert = MLExpert()
    print(f"\n{expert.name}")
    print(f"Specialties: {', '.join(expert.specialties)}")
    
    print("\nAlgorithm Recommendation for Image Classification:")
    rec = expert.recommend_algorithm("image-classification")
    print(f"Primary: {rec['primary']}")
    print(f"Alternatives: {rec['alternatives']}")
    
    print("\nExpert Summary:")
    summary = expert.get_summary()
    print(f"Total Knowledge Items: {summary['total_knowledge_items']}")
