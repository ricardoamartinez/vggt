import torch
import time
import numpy as np
from vggt.models.vggt import VGGT
from vggt.utils.load_fn import load_and_preprocess_images
import glob
import os

def benchmark_inference():
    """
    Benchmark pure model inference time, isolating it from I/O and post-processing.
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if torch.cuda.get_device_capability()[0] >= 8 else torch.float16
    
    print(f"Device: {device}")
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    print(f"Compute Capability: {torch.cuda.get_device_capability()[0] if torch.cuda.is_available() else 'N/A'}")
    print(f"Using dtype: {dtype}")
    print("-" * 50)
    
    # Load model
    print("Loading VGGT model...")
    model = VGGT()
    _URL = "https://huggingface.co/facebook/VGGT-1B/resolve/main/model.pt"
    model.load_state_dict(torch.hub.load_state_dict_from_url(_URL))
    model.eval()
    model = model.to(device)
    print("Model loaded successfully")
    
    # Test different numbers of images
    test_cases = [1, 2, 4, 8, 10, 20, 50]
    
    # Use kitchen example images
    image_dir = "examples/kitchen/images"
    if not os.path.exists(image_dir):
        print(f"Error: {image_dir} not found")
        return
        
    all_image_paths = sorted(glob.glob(os.path.join(image_dir, "*")))
    
    results = []
    
    for num_images in test_cases:
        if num_images > len(all_image_paths):
            continue
            
        print(f"\nTesting with {num_images} images:")
        
        # Select subset of images
        image_paths = all_image_paths[:num_images]
        
        # Load and preprocess images (timed separately)
        start_load = time.time()
        images = load_and_preprocess_images(image_paths).to(device)
        load_time = time.time() - start_load
        
        print(f"  Image loading time: {load_time:.3f}s")
        print(f"  Images shape: {images.shape}")
        
        # Warmup run
        with torch.no_grad():
            with torch.amp.autocast('cuda', dtype=dtype):
                _ = model(images)
        torch.cuda.synchronize()
        
        # Benchmark runs
        num_runs = 3
        inference_times = []
        
        for run in range(num_runs):
            torch.cuda.synchronize()
            start_inference = time.time()
            
            with torch.no_grad():
                with torch.amp.autocast('cuda', dtype=dtype):
                    predictions = model(images)
            
            torch.cuda.synchronize()
            inference_time = time.time() - start_inference
            inference_times.append(inference_time)
        
        avg_inference_time = np.mean(inference_times)
        std_inference_time = np.std(inference_times)
        
        print(f"  Pure inference time: {avg_inference_time:.3f} ± {std_inference_time:.3f}s")
        print(f"  Memory usage: {torch.cuda.max_memory_allocated() / 1e9:.2f} GB")
        
        results.append({
            'num_images': num_images,
            'load_time': load_time,
            'inference_time': avg_inference_time,
            'memory_gb': torch.cuda.max_memory_allocated() / 1e9
        })
        
        # Reset memory tracking
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.empty_cache()
    
    print("\n" + "="*70)
    print("BENCHMARK RESULTS SUMMARY")
    print("="*70)
    print("Paper benchmarks (H100 GPU):")
    print("Input Frames |  1   |  2   |  4   |  8   | 10   | 20   | 50   |")
    print("Time (s)     | 0.04 | 0.05 | 0.07 | 0.11 | 0.14 | 0.31 | 1.04 |")
    print("Memory (GB)  | 1.88 | 2.07 | 2.45 | 3.23 | 3.63 | 5.58 |11.41 |")
    print()
    print("Our results (RTX 4080):")
    print("Input Frames |" + "|".join(f"{r['num_images']:5}" for r in results) + "|")
    print("Time (s)     |" + "|".join(f"{r['inference_time']:5.2f}" for r in results) + "|")
    print("Memory (GB)  |" + "|".join(f"{r['memory_gb']:5.2f}" for r in results) + "|")
    
    print("\nAnalysis:")
    for result in results:
        paper_time = get_paper_time(result['num_images'])
        if paper_time:
            slowdown = result['inference_time'] / paper_time
            print(f"  {result['num_images']} images: {slowdown:.1f}x slower than H100")

def get_paper_time(num_images):
    """Get interpolated time from paper benchmarks"""
    paper_data = {
        1: 0.04, 2: 0.05, 4: 0.07, 8: 0.11, 
        10: 0.14, 20: 0.31, 50: 1.04
    }
    return paper_data.get(num_images)

if __name__ == "__main__":
    benchmark_inference()
