# ml/benchmark.py
import csv
import os

class ComplianceBenchmark:
    """
    Evaluates the rule engine's compliance checks against a manual ground truth.
    """
    def __init__(self, ground_truth_file: str):
        self.ground_truth_file = ground_truth_file
        self.ground_truth = self._load_ground_truth()
        
    def _load_ground_truth(self) -> dict:
        truth = {}
        if not os.path.exists(self.ground_truth_file):
            print(f"[Warning] Ground truth file not found: {self.ground_truth_file}")
            return truth
            
        with open(self.ground_truth_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row['drawing_id']}_{row['element_id']}_{row['clause']}"
                truth[key] = row['expected_status']
        return truth
        
    def evaluate(self, predictions: list) -> dict:
        """
        Evaluate predictions against ground truth.
        predictions: list of dicts with 'drawing_id', 'element_id', 'clause', 'status'
        """
        tp, fp, fn = 0, 0, 0
        for pred in predictions:
            key = f"{pred['drawing_id']}_{pred['element_id']}_{pred['clause']}"
            if key in self.ground_truth:
                expected = self.ground_truth[key]
                # Simplified binary classification (PASS vs FAIL/ACTION)
                pred_is_pass = "PASS" in pred['status']
                exp_is_pass = "PASS" in expected
                
                if pred_is_pass and exp_is_pass:
                    tp += 1
                elif not pred_is_pass and exp_is_pass:
                    fn += 1
                elif pred_is_pass and not exp_is_pass:
                    fp += 1
                elif not pred_is_pass and not exp_is_pass:
                    tp += 1 # correctly identified failure/action
                    
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "total_evaluated": len(predictions)
        }
