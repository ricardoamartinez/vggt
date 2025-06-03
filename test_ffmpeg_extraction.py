import subprocess
import os
import glob
import time

def test_ffmpeg_extraction():
    """Test FFmpeg frame extraction speed"""
    
    # Use one of the example videos
    video_path = "examples/videos/kitchen.mp4"
    
    if not os.path.exists(video_path):
        print(f"Test video not found: {video_path}")
        return
    
    # Create test output directory
    test_dir = "test_ffmpeg_output"
    if os.path.exists(test_dir):
        import shutil
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    print(f"Testing FFmpeg extraction with: {video_path}")
    
    # Test FFmpeg extraction
    start_time = time.time()
    
    try:
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", "fps=1",  # Extract 1 frame per second
            "-y",  # Overwrite output files
            "-loglevel", "warning",  # Reduce log verbosity
            os.path.join(test_dir, "%06d.png")
        ]
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
        extraction_time = time.time() - start_time
        
        # Count extracted frames
        extracted_images = sorted(glob.glob(os.path.join(test_dir, "*.png")))
        
        print(f"✓ FFmpeg extraction successful!")
        print(f"  - Extracted {len(extracted_images)} frames")
        print(f"  - Time taken: {extraction_time:.3f} seconds")
        print(f"  - Speed: {len(extracted_images)/extraction_time:.1f} frames/second")
        
        # Compare with expected performance
        if extraction_time < 5.0:
            print("  - Performance: EXCELLENT (< 5s)")
        elif extraction_time < 10.0:
            print("  - Performance: GOOD (< 10s)")
        else:
            print("  - Performance: SLOW (> 10s)")
            
    except subprocess.CalledProcessError as e:
        print(f"✗ FFmpeg extraction failed: {e}")
        print(f"  stderr: {e.stderr}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
    
    # Cleanup
    if os.path.exists(test_dir):
        import shutil
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    test_ffmpeg_extraction()
