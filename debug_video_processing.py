import subprocess
import os
import glob
import time
import sys

def analyze_video_properties(video_path):
    """Analyze video file properties using ffprobe"""
    print(f"\n=== ANALYZING VIDEO: {video_path} ===")
    
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return False
    
    # Get file size
    file_size = os.path.getsize(video_path)
    print(f"📁 File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    # Use ffprobe to get detailed video information
    try:
        probe_cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        
        # Also get human-readable format
        probe_readable_cmd = [
            "ffprobe",
            "-hide_banner",
            video_path
        ]
        
        readable_result = subprocess.run(probe_readable_cmd, capture_output=True, text=True, check=True)
        print("📹 Video Information:")
        print(readable_result.stderr)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ ffprobe failed: {e}")
        print(f"   stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ ffprobe not found. FFmpeg tools not installed.")
        return False

def check_file_structure(video_path):
    """Check the beginning and end of the video file for moov atom"""
    print(f"\n=== CHECKING FILE STRUCTURE ===")
    
    try:
        with open(video_path, 'rb') as f:
            # Read first 1024 bytes
            f.seek(0)
            header = f.read(1024)
            print(f"📋 First 64 bytes (hex): {header[:64].hex()}")
            print(f"📋 First 64 bytes (ascii): {header[:64]}")
            
            # Check for common video signatures
            if header.startswith(b'\x00\x00\x00'):
                print("✅ Appears to be MP4/MOV format (starts with size box)")
            
            # Look for moov atom in header
            if b'moov' in header:
                print("✅ moov atom found in header (normal structure)")
            else:
                print("⚠️  moov atom NOT in header - likely at end of file")
            
            # Check file end for moov atom
            file_size = os.path.getsize(video_path)
            f.seek(max(0, file_size - 1024))
            footer = f.read(1024)
            
            if b'moov' in footer:
                print("✅ moov atom found at end of file (GoPro/live recording structure)")
            else:
                print("❌ moov atom not found at end either")
                
            # Look for mdat atom
            f.seek(0)
            first_chunk = f.read(8192)
            if b'mdat' in first_chunk:
                print("✅ mdat atom found (media data present)")
            else:
                print("⚠️  mdat atom not found in first 8KB")
                
    except Exception as e:
        print(f"❌ Error reading file: {e}")

def test_ffmpeg_methods(video_path, output_dir):
    """Test multiple FFmpeg extraction methods with detailed logging"""
    print(f"\n=== TESTING FFMPEG METHODS ===")
    
    # Create output directory
    if os.path.exists(output_dir):
        import shutil
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    # Define FFmpeg methods to test
    methods = [
        {
            "name": "Standard extraction",
            "cmd": ["ffmpeg", "-i", video_path, "-vf", "fps=1", "-y", "-v", "debug", 
                   os.path.join(output_dir, "method1_%06d.png")]
        },
        {
            "name": "GoPro optimized (genpts+ignore_index)",
            "cmd": ["ffmpeg", "-fflags", "+genpts+ignore_index", "-i", video_path,
                   "-vf", "fps=1", "-f", "image2", "-y", "-v", "debug",
                   os.path.join(output_dir, "method2_%06d.png")]
        },
        {
            "name": "Error tolerance (ignore_err)",
            "cmd": ["ffmpeg", "-err_detect", "ignore_err", "-fflags", "+genpts", 
                   "-i", video_path, "-vf", "fps=1", "-f", "image2", "-y", "-v", "debug",
                   os.path.join(output_dir, "method3_%06d.png")]
        },
        {
            "name": "Force MP4 demuxer",
            "cmd": ["ffmpeg", "-f", "mp4", "-fflags", "+genpts", "-i", video_path,
                   "-vf", "fps=1", "-f", "image2", "-y", "-v", "debug",
                   os.path.join(output_dir, "method4_%06d.png")]
        },
        {
            "name": "Concat demuxer workaround",
            "cmd": ["ffmpeg", "-fflags", "+genpts+igndts+ignidx", "-i", video_path,
                   "-r", "1", "-f", "image2", "-y", "-v", "debug",
                   os.path.join(output_dir, "method5_%06d.png")]
        },
        {
            "name": "Basic with verbose output",
            "cmd": ["ffmpeg", "-i", video_path, "-r", "1", "-y", "-v", "debug",
                   os.path.join(output_dir, "method6_%06d.png")]
        }
    ]
    
    successful_methods = []
    
    for i, method in enumerate(methods, 1):
        print(f"\n--- Method {i}: {method['name']} ---")
        print(f"Command: {' '.join(method['cmd'])}")
        
        # Clear previous outputs
        for f in glob.glob(os.path.join(output_dir, f"method{i}_*.png")):
            os.remove(f)
        
        start_time = time.time()
        
        try:
            result = subprocess.run(method['cmd'], capture_output=True, text=True, 
                                  check=True, timeout=60)
            
            execution_time = time.time() - start_time
            extracted_images = sorted(glob.glob(os.path.join(output_dir, f"method{i}_*.png")))
            
            if len(extracted_images) > 0:
                print(f"✅ SUCCESS: {len(extracted_images)} frames in {execution_time:.2f}s")
                successful_methods.append(method['name'])
            else:
                print(f"⚠️  Command succeeded but no frames extracted")
            
            # Show last few lines of stderr (contains useful info even on success)
            if result.stderr:
                stderr_lines = result.stderr.strip().split('\n')
                print("📝 Last few log lines:")
                for line in stderr_lines[-5:]:
                    if line.strip():
                        print(f"   {line}")
                        
        except subprocess.CalledProcessError as e:
            execution_time = time.time() - start_time
            print(f"❌ FAILED (exit code {e.returncode}) after {execution_time:.2f}s")
            
            if e.stderr:
                print("📝 Error details:")
                stderr_lines = e.stderr.strip().split('\n')
                for line in stderr_lines[-10:]:  # Show more error lines
                    if line.strip():
                        print(f"   {line}")
                        
        except subprocess.TimeoutExpired:
            print(f"⏱️  TIMEOUT after 60 seconds")
            
        except Exception as e:
            print(f"❌ UNEXPECTED ERROR: {e}")
    
    print(f"\n=== SUMMARY ===")
    if successful_methods:
        print(f"✅ Successful methods: {', '.join(successful_methods)}")
    else:
        print("❌ No methods succeeded")
    
    return successful_methods

def test_with_working_video():
    """Test with a known working video first"""
    working_video = "examples/videos/kitchen.mp4"
    
    if os.path.exists(working_video):
        print("🔧 Testing with known working video first...")
        analyze_video_properties(working_video)
        check_file_structure(working_video)
        successful = test_ffmpeg_methods(working_video, "debug_working_output")
        
        if successful:
            print("✅ Working video processed successfully with these methods:")
            for method in successful:
                print(f"   - {method}")
        else:
            print("❌ Even working video failed - FFmpeg installation issue")
            
        # Cleanup
        if os.path.exists("debug_working_output"):
            import shutil
            shutil.rmtree("debug_working_output")
            
        return len(successful) > 0
    else:
        print("⚠️  No working video found for comparison")
        return True

def main():
    """Main debugging function"""
    print("🔍 VIDEO PROCESSING DEBUGGER")
    print("=" * 50)
    
    # First test with working video
    working_test_passed = test_with_working_video()
    
    if not working_test_passed:
        print("\n❌ CRITICAL: Working video test failed. Check FFmpeg installation.")
        return
    
    # Test with problematic video (simulate the upload path)
    problem_video_path = None
    
    # Check recent upload directories
    upload_dirs = [d for d in os.listdir('.') if d.startswith('input_images_')]
    upload_dirs.sort(reverse=True)  # Most recent first
    
    for upload_dir in upload_dirs[:3]:  # Check last 3 uploads
        potential_files = glob.glob(os.path.join(upload_dir, "**", "*.MP4"), recursive=True)
        potential_files.extend(glob.glob(os.path.join(upload_dir, "**", "*.mp4"), recursive=True))
        
        if potential_files:
            problem_video_path = potential_files[0]
            print(f"\n🎯 Found recent uploaded video: {problem_video_path}")
            break
    
    if not problem_video_path:
        print("\n⚠️  No recent video uploads found.")
        print("Please upload a GoPro video through the Gradio interface first.")
        return
    
    # Analyze the problematic video
    print(f"\n🔍 ANALYZING PROBLEMATIC VIDEO")
    print("=" * 50)
    
    if analyze_video_properties(problem_video_path):
        check_file_structure(problem_video_path)
        successful_methods = test_ffmpeg_methods(problem_video_path, "debug_problem_output")
        
        if successful_methods:
            print(f"\n🎉 SOLUTION FOUND!")
            print(f"These methods work with your video:")
            for method in successful_methods:
                print(f"   ✅ {method}")
        else:
            print(f"\n🚨 NO SOLUTION FOUND")
            print("The video may be:")
            print("   - Corrupted or incomplete")
            print("   - Using an unsupported codec")
            print("   - Require specific FFmpeg build")
    
    # Cleanup
    if os.path.exists("debug_problem_output"):
        import shutil
        shutil.rmtree("debug_problem_output")

if __name__ == "__main__":
    main()
