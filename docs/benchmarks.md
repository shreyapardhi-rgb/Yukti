# Yukti Codec Benchmark Suite

Benchmarking Yukti against Raw bitstream, DEFLATE (zlib -9), Gzip, Bzip2, LZMA, and Run-Length Encoding (RLE).

| Scale | Distribution | Raw (bits) | Yukti (bits) | Ratio | zlib (bits) | RLE (bits) | Best Block | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 Kbit (1,024 bits) | Sparse (5% ones) | 1024 | 550 | 53.7% | 656 | 1632 | Block 64 | **COMPRESSES** |
| 1 Kbit (1,024 bits) | Dense (95% ones) | 1024 | 553 | 54.0% | 632 | 1552 | Block 64 | **COMPRESSES** |
| 1 Kbit (1,024 bits) | Random (50% ones) | 1024 | 1209 | 118.1% | 1112 | 8224 | Block 64 | **EXPANDS** |
| 1 Kbit (1,024 bits) | All Zeros | 1024 | 360 | 35.2% | 96 | 16 | Block 64 | **COMPRESSES** |
| 64 Kbit (65,536 bits) | Sparse (5% ones) | 65536 | 32416 | 49.5% | 24296 | 98512 | Block 64 | **COMPRESSES** |
| 64 Kbit (65,536 bits) | Dense (95% ones) | 65536 | 32601 | 49.8% | 24768 | 100112 | Block 64 | **COMPRESSES** |
| 64 Kbit (65,536 bits) | Random (50% ones) | 65536 | 75236 | 114.8% | 65624 | 526736 | Block 64 | **EXPANDS** |
| 64 Kbit (65,536 bits) | All Zeros | 65536 | 20520 | 31.3% | 248 | 16 | Block 64 | **COMPRESSES** |
| 1 Mbit (1,048,576 bits) (sampled 64k) | Sparse (5% ones) | 65536 | 32416 | 49.5% | 24296 | 98512 | Block 64 | **COMPRESSES** |
| 1 Mbit (1,048,576 bits) (sampled 64k) | Dense (95% ones) | 65536 | 32601 | 49.8% | 24768 | 100112 | Block 64 | **COMPRESSES** |
| 1 Mbit (1,048,576 bits) (sampled 64k) | Random (50% ones) | 65536 | 75236 | 114.8% | 65624 | 526736 | Block 64 | **EXPANDS** |
| 1 Mbit (1,048,576 bits) (sampled 64k) | All Zeros | 65536 | 20520 | 31.3% | 248 | 16 | Block 64 | **COMPRESSES** |
