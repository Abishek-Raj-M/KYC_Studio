"""
OCR Evaluation Reporter
Analyzes and visualizes OCR evaluation results
"""

import json
import os
import pandas as pd
from typing import Dict, List
import matplotlib.pyplot as plt
import seaborn as sns


class OCREvaluationReporter:
    """Generate reports and visualizations for OCR evaluation"""
    
    def __init__(self, results_dir: str = "./ocr_evaluation"):
        """
        Initialize reporter
        
        Args:
            results_dir: Directory containing evaluation results
        """
        self.results_dir = results_dir
        self.rag_results = []
        self.eval_results = None
        self.summary = {}
        
        self._load_results()
    
    def _load_results(self):
        """Load all evaluation results"""
        print(f"\n📂 Loading results from: {self.results_dir}")
        
        # Load RAG results
        rag_path = os.path.join(self.results_dir, "ocr_rag_results.json")
        if os.path.exists(rag_path):
            with open(rag_path, 'r', encoding='utf-8') as f:
                self.rag_results = json.load(f)
            print(f"✅ Loaded {len(self.rag_results)} RAG results")
        
        # Load evaluation results
        eval_path = os.path.join(self.results_dir, "ocr_evaluation_results.csv")
        if os.path.exists(eval_path):
            self.eval_results = pd.read_csv(eval_path)
            print(f"✅ Loaded evaluation results ({len(self.eval_results)} samples)")
        
        # Load summary
        summary_path = os.path.join(self.results_dir, "ocr_evaluation_summary.json")
        if os.path.exists(summary_path):
            with open(summary_path, 'r', encoding='utf-8') as f:
                self.summary = json.load(f)
            print(f"✅ Loaded summary")
    
    def print_overall_summary(self):
        """Print overall evaluation summary"""
        print("\n" + "="*70)
        print("OVERALL EVALUATION SUMMARY")
        print("="*70)
        
        if not self.summary:
            print("⚠️  No summary data available")
            return
        
        print(f"\n📊 Total Samples: {self.summary.get('total_samples', 0)}")
        print(f"📅 Evaluation Date: {self.summary.get('evaluation_date', 'Unknown')}")
        
        print("\n📈 Metric Scores:")
        metrics = self.summary.get('metrics', {})
        for metric_name, scores in metrics.items():
            mean = scores.get('mean', 0)
            std = scores.get('std', 0)
            print(f"\n  {metric_name.upper()}:")
            print(f"    Mean:  {mean:.3f}")
            print(f"    Std:   {std:.3f}")
            print(f"    Range: [{scores.get('min', 0):.3f}, {scores.get('max', 0):.3f}]")
    
    def show_best_and_worst_cases(self, n: int = 5):
        """Show best and worst performing samples"""
        if self.eval_results is None:
            print("\n⚠️  No evaluation results available")
            return
        
        print("\n" + "="*70)
        print(f"TOP {n} BEST PERFORMING SAMPLES")
        print("="*70)
        
        # Sort by average of all metrics
        metric_cols = [col for col in self.eval_results.columns 
                      if col not in ['question', 'answer', 'contexts', 'ground_truth']]
        
        if metric_cols:
            self.eval_results['avg_score'] = self.eval_results[metric_cols].mean(axis=1)
            
            # Best cases
            best = self.eval_results.nlargest(n, 'avg_score')
            
            for idx, (_, row) in enumerate(best.iterrows(), 1):
                print(f"\n{idx}. Question: {row['question'][:80]}...")
                print(f"   Average Score: {row['avg_score']:.3f}")
                for col in metric_cols:
                    print(f"   {col}: {row[col]:.3f}")
            
            # Worst cases
            print("\n" + "="*70)
            print(f"TOP {n} WORST PERFORMING SAMPLES")
            print("="*70)
            
            worst = self.eval_results.nsmallest(n, 'avg_score')
            
            for idx, (_, row) in enumerate(worst.iterrows(), 1):
                print(f"\n{idx}. Question: {row['question'][:80]}...")
                print(f"   Average Score: {row['avg_score']:.3f}")
                for col in metric_cols:
                    print(f"   {col}: {row[col]:.3f}")
                
                # Show why it failed
                print(f"\n   OCR Answer: {row['answer'][:100]}...")
                print(f"   Ground Truth: {row['ground_truth'][:100]}...")
    
    def analyze_failure_patterns(self):
        """Analyze common failure patterns"""
        print("\n" + "="*70)
        print("FAILURE PATTERN ANALYSIS")
        print("="*70)
        
        if self.eval_results is None:
            print("⚠️  No evaluation results available")
            return
        
        # Define failure threshold
        threshold = 0.5
        
        metric_cols = [col for col in self.eval_results.columns 
                      if col not in ['question', 'answer', 'contexts', 'ground_truth', 'avg_score']]
        
        print(f"\nSamples with scores below {threshold}:")
        
        for col in metric_cols:
            failures = self.eval_results[self.eval_results[col] < threshold]
            print(f"\n  {col}: {len(failures)} failures ({len(failures)/len(self.eval_results)*100:.1f}%)")
            
            if len(failures) > 0:
                print(f"    Sample questions:")
                for _, row in failures.head(3).iterrows():
                    print(f"      • {row['question'][:70]}...")
    
    def create_comparison_report(self, kg_results_path: str = "./ragas_data/evaluation_summary.json"):
        """Compare OCR results with KG ground truth results"""
        print("\n" + "="*70)
        print("COMPARISON: OCR vs KG GROUND TRUTH")
        print("="*70)
        
        if not os.path.exists(kg_results_path):
            print(f"⚠️  KG results not found: {kg_results_path}")
            return
        
        # Load KG results
        with open(kg_results_path, 'r', encoding='utf-8') as f:
            kg_summary = json.load(f)
        
        print("\n📊 Metric Comparison:")
        print("\n{:<25} {:<15} {:<15} {:<15}".format("Metric", "KG (Ground Truth)", "OCR", "Difference"))
        print("-" * 70)
        
        kg_metrics = kg_summary.get('metrics', {})
        ocr_metrics = self.summary.get('metrics', {})
        
        for metric_name in ocr_metrics.keys():
            kg_score = kg_metrics.get(metric_name, {}).get('mean', 0)
            ocr_score = ocr_metrics[metric_name]['mean']
            diff = ocr_score - kg_score
            
            diff_str = f"{diff:+.3f}"
            print(f"{metric_name:<25} {kg_score:.3f}{'':<10} {ocr_score:.3f}{'':<10} {diff_str}")
        
        print("\n📈 Interpretation:")
        print("  • Positive difference = OCR performed better")
        print("  • Negative difference = KG performed better")
        print("  • Difference near 0 = Similar performance")
    
    def export_detailed_report(self, output_file: str = None):
        """Export detailed report to file"""
        if output_file is None:
            output_file = os.path.join(self.results_dir, "detailed_report.txt")
        
        print(f"\n💾 Exporting detailed report to: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("OCR EVALUATION DETAILED REPORT\n")
            f.write("="*70 + "\n\n")
            
            # Summary
            f.write("SUMMARY\n")
            f.write("-"*70 + "\n")
            f.write(f"Total Samples: {self.summary.get('total_samples', 0)}\n")
            f.write(f"Evaluation Date: {self.summary.get('evaluation_date', 'Unknown')}\n\n")
            
            # Metrics
            f.write("METRIC SCORES\n")
            f.write("-"*70 + "\n")
            metrics = self.summary.get('metrics', {})
            for metric_name, scores in metrics.items():
                f.write(f"\n{metric_name.upper()}:\n")
                f.write(f"  Mean: {scores.get('mean', 0):.3f}\n")
                f.write(f"  Std:  {scores.get('std', 0):.3f}\n")
                f.write(f"  Min:  {scores.get('min', 0):.3f}\n")
                f.write(f"  Max:  {scores.get('max', 0):.3f}\n")
            
            # Sample results
            f.write("\n\nSAMPLE RESULTS\n")
            f.write("-"*70 + "\n")
            
            for i, result in enumerate(self.rag_results[:10], 1):
                f.write(f"\n{i}. Question: {result['question']}\n")
                f.write(f"   OCR Answer: {result['answer']}\n")
                f.write(f"   Ground Truth: {result['ground_truth']}\n")
                f.write(f"   Contexts: {len(result['contexts'])}\n")
                f.write("\n")
        
        print(f"✅ Report exported")


def main():
    """Main reporter entry point"""
    import sys
    
    print("="*70)
    print("OCR EVALUATION REPORTER")
    print("="*70)
    
    results_dir = "./ocr_evaluation"
    
    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    
    if not os.path.exists(results_dir):
        print(f"\n❌ Results directory not found: {results_dir}")
        sys.exit(1)
    
    # Create reporter
    reporter = OCREvaluationReporter(results_dir)
    
    # Generate reports
    reporter.print_overall_summary()
    reporter.show_best_and_worst_cases(n=5)
    reporter.analyze_failure_patterns()
    reporter.create_comparison_report()
    reporter.export_detailed_report()
    
    print("\n" + "="*70)
    print("✅ REPORTING COMPLETE!")
    print("="*70)


if __name__ == "__main__":
    main()