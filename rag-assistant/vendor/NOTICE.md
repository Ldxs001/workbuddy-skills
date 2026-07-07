# Bundled Third-Party Packages

This project bundles the following third-party packages in the `vendor/` directory.
Each is used under its respective open source license.

| Package | Version | License | 
|---------|---------|---------|
| [pypdf](https://github.com/py-pdf/pypdf) | 6.14.2 | BSD 3-Clause |
| [markdownify](https://github.com/matthewwithanm/python-markdownify) | 1.2.3 | MIT |
| [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/) | 4.15.0 | MIT |
| [soupsieve](https://github.com/facelessuser/soupsieve) | 2.8.4 | MIT |
| [six](https://github.com/benjaminp/six) | 1.17.0 | MIT |
| [typing_extensions](https://github.com/python/typing_extensions) | 4.16.0 | Python Software Foundation License |

## BSD 3-Clause (pypdf)

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

# Pre-downloaded Model Weights

The following model weight files are pre-downloaded into `data/models/`.
Users who redistribute this project must retain the corresponding license files.

| Model | Source | License |
|-------|--------|---------|
| [BAAI/bge-reranker-base](https://huggingface.co/BAAI/bge-reranker-base) | HuggingFace | MIT |
| [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) | HuggingFace | MIT |
| [maidalun1020/bce-embedding-base_v1](https://huggingface.co/maidalun1020/bce-embedding-base_v1) | HuggingFace | Apache 2.0 |
| [mixedbread-ai/mxbai-rerank-base-v1](https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v1) | HuggingFace | Apache 2.0 |

All four models use permissive open-source licenses compatible with this project's Apache 2.0 license.
