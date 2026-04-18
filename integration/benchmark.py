import json
import os
import sys
import glob

from integration.pipeline import warmup, run_pipeline

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DEFAULT_IMAGES_DIR = os.path.join(REPO_ROOT, "tests")


def find_images(directory):
    patterns = ["*.png", "*.jpg", "*.jpeg"]
    images = []
    for p in patterns:
        images.extend(glob.glob(os.path.join(directory, p)))
    return sorted(images)


def main():
    images_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGES_DIR
    images = find_images(images_dir)

    if not images:
        print(f"No images found in {images_dir}")
        sys.exit(1)

    print(f"Found {len(images)} image(s) in {images_dir}")
    print("Warming up services...")
    warmup()
    print("Warmup done. Starting benchmark...\n")

    results = []
    for img_path in images:
        name = os.path.basename(img_path)
        print(f"--- {name} ---")
        try:
            row = run_pipeline(img_path)
            results.append({
                "image": name,
                "lossless": row["text"] == row["recovered"],
                "text_length": len(row["text"]),
                "latency": row["latency"],
                "metrics": row["metrics"],
            })
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"image": name, "error": str(e)})

    ok = [r for r in results if "latency" in r]
    if not ok:
        print("\nNo successful runs.")
        return

    total_latencies = [r["latency"]["total"] for r in ok]
    stage1_latencies = [r["latency"]["stage1"] for r in ok]
    compress_latencies = [r["latency"]["compress"] for r in ok]
    decompress_latencies = [r["latency"]["decompress"] for r in ok]
    lossless_count = sum(1 for r in ok if r["lossless"])

    summary = {
        "n": len(ok),
        "lossless_pass_rate": lossless_count / len(ok),
        "total_latency": {
            "mean": sum(total_latencies) / len(total_latencies),
            "min": min(total_latencies),
            "max": max(total_latencies),
        },
        "stage1_latency": {
            "mean": sum(stage1_latencies) / len(stage1_latencies),
            "min": min(stage1_latencies),
            "max": max(stage1_latencies),
        },
        "compress_latency": {
            "mean": sum(compress_latencies) / len(compress_latencies),
            "min": min(compress_latencies),
            "max": max(compress_latencies),
        },
        "decompress_latency": {
            "mean": sum(decompress_latencies) / len(decompress_latencies),
            "min": min(decompress_latencies),
            "max": max(decompress_latencies),
        },
        "mean_compression_ratio": sum(r["metrics"]["compression_ratio"] for r in ok) / len(ok),
        "mean_entropy": sum(r["metrics"]["entropy"] for r in ok) / len(ok),
        "mean_encoding_efficiency": sum(r["metrics"]["encoding_efficiency"] for r in ok) / len(ok),
        "results": results,
    }

    out_path = os.path.join(REPO_ROOT, "docs", "metrics.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 52)
    print(f"  Images run        : {summary['n']}")
    print(f"  Lossless pass rate: {summary['lossless_pass_rate']*100:.1f}%")
    print(f"  Total latency     : mean={summary['total_latency']['mean']*1000:.1f}ms  min={summary['total_latency']['min']*1000:.1f}ms  max={summary['total_latency']['max']*1000:.1f}ms")
    print(f"  Stage 1 (OCR)     : mean={summary['stage1_latency']['mean']*1000:.1f}ms")
    print(f"  Compress          : mean={summary['compress_latency']['mean']*1000:.1f}ms")
    print(f"  Decompress        : mean={summary['decompress_latency']['mean']*1000:.1f}ms")
    print(f"  Compression ratio : {summary['mean_compression_ratio']:.3f}x")
    print(f"  Entropy           : {summary['mean_entropy']:.3f} bits/sym")
    print(f"  Encoding eff.     : {summary['mean_encoding_efficiency']*100:.1f}%")
    print("=" * 52)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
