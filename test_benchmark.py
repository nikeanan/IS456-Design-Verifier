# test_benchmark.py
import os
from ml.benchmark import ComplianceBenchmark
from report_generator import create_batch_summary_report
from dxf_validator import load_dxf_file, classify_dxf_entities, get_characteristic_dimension
from elements.beam import RCBeamVerifier

def run_test():
    ground_truth_path = os.path.join("tests", "ground_truth_sample.csv")
    
    print("1. Initializing Benchmark Framework...")
    benchmark = ComplianceBenchmark(ground_truth_path)
    
    print("2. Parsing DXF files from batch directory and running Rule Engine...")
    batch_dir = "CAD dxf"
    dxf_files = [os.path.join(batch_dir, f) for f in os.listdir(batch_dir) if f.endswith(".dxf")] if os.path.exists(batch_dir) else ["sample_plan.dxf"]
    
    predictions = []
    batch_results = []
    
    for dxf_file in dxf_files:
        if not os.path.exists(dxf_file):
            print(f"File not found: {dxf_file}")
            continue
            
        doc = load_dxf_file(dxf_file)
        classified = classify_dxf_entities(doc)
        
        # We will map DXF beam entities to RCBeamVerifier objects.
        # Since DXF only gives us geometry, we simulate loads and materials for this test.
        passed_count = 0
        failed_count = 0
        warnings_count = 0
        
        for i, entity in enumerate(classified['beams']):
            dim = get_characteristic_dimension(entity)
            element_id = f"B{i+1}"
            
            # Create a verifier with some mocked load data but real DXF width
            verifier = RCBeamVerifier(
                element_id=element_id, 
                b=dim, d=450, D=500, L=4000, 
                f_ck=25, f_y=500, A_st=1200, 
                M_eq=150, V_eq=100
            )
            is_compliant = verifier.evaluate_compliance()
            
            for check_name, status in verifier.checks.items():
                predictions.append({
                    "drawing_id": dxf_file,
                    "element_id": element_id,
                    "clause": check_name,
                    "status": status
                })
                if "FAIL" in status:
                    failed_count += 1
                elif "ACTION" in status or "WARNING" in status:
                    warnings_count += 1
                else:
                    passed_count += 1
                    
        total_elements = len(classified['beams']) + len(classified['columns'])
        
        # Add OCR beams if they exist
        if 'ocr_data' in classified:
            ocr = classified['ocr_data']
            total_elements += len(ocr.get('beams', [])) + len(ocr.get('columns', []))
            
            for i, b_data in enumerate(ocr.get('beams', [])):
                verifier = RCBeamVerifier(
                    element_id=f"OCR_B{i+1}", 
                    b=b_data['b'], d=b_data['D'] - 50, D=b_data['D'], L=4000, 
                    f_ck=ocr.get('f_ck', 25), f_y=ocr.get('f_y', 500), A_st=1200, 
                    M_eq=150, V_eq=100
                )
                verifier.evaluate_compliance()
                for check_name, status in verifier.checks.items():
                    predictions.append({
                        "drawing_id": dxf_file,
                        "element_id": f"OCR_B{i+1}",
                        "clause": check_name,
                        "status": status
                    })
                    if "FAIL" in status:
                        failed_count += 1
                    elif "ACTION" in status or "WARNING" in status:
                        warnings_count += 1
                    else:
                        passed_count += 1

        batch_results.append({
            "drawing_id": dxf_file,
            "total_elements": total_elements,
            "passed": passed_count,
            "failed": failed_count,
            "warnings": warnings_count
        })

    print("3. Evaluating predictions against ground truth...")
    metrics = benchmark.evaluate(predictions)
    
    print("\n--- Benchmark Results ---")
    print(f"Total Evaluated: {metrics['total_evaluated']}")
    print(f"Precision: {metrics['precision']:.2f}")
    print(f"Recall: {metrics['recall']:.2f}")
    print(f"F1-Score: {metrics['f1_score']:.2f}")
    
    print("\n4. Generating Batch Summary PDF Report...")
    pdf_bytes = create_batch_summary_report(batch_results, metrics)
    with open("batch_summary_report.pdf", "wb") as f:
        f.write(pdf_bytes)
        
    print("Batch report saved to: batch_summary_report.pdf")

if __name__ == "__main__":
    run_test()
