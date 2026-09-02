| Area | Text-only | Visual |
| --- | --- | --- |
| Endpoint | Port 8000 | Port 8001 |
| Best for | General literature searches | Plots, tables, diagrams, and page evidence |
| Models | Nomic + Qwen3 Reranker 0.6B | Qwen3-VL Embedding 2B + Reranker 2B |
| Speed | 0.3–0.9s warm | 8.2s warm; 22.7s cold |
| GPU memory | 2.8 GB | 9.6 GB |
| Host RAM | 1.3 GB | 1.8 GB |
| Docker image | 6.0 GB | 7.0 GB |
| Extra storage | Existing corpus | 8 GB models + ~3.4 GB projected visual index |
| Current status | Stable production version | 100-PDF pilot; 1,594 pages indexed |
| Recommendation | Default for routine searches | Use when visual evidence matters |

The visual version is isolated from the text database. Rollback only requires stopping the service on port 8001 and continuing to use the text-only service on port 8000.
