# crisp

## Performance Notes & Reminders
> [!WARNING]
> **Cold Starts:** Stage 2 (Huffman) is CPU-bound, while Stage 1 (CNN) is GPU-preferred. The *first* API request to the PyTorch/FastAPI server will be artificially slow as the model handles initial memory loading. 
> 
> **Action:** Send a single "dummy" image through the pipeline on startup to warm up the models *before* running the final latency benchmarks.